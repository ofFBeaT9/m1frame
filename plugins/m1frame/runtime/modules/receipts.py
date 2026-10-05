"""Durable, bounded execution evidence without model reasoning or secrets."""
from __future__ import annotations

import contextvars
import functools
import inspect
import json
import threading
import time
import uuid
from pathlib import Path

current_receipt: contextvars.ContextVar = contextvars.ContextVar('receipt', default=None)


class RunReceipt:
    def __init__(self):
        self.id = uuid.uuid4().hex
        self.started = time.perf_counter()
        self.lock = threading.Lock()
        self.data = {'id': self.id, 'status': 'running', 'events': [], 'requests': []}

    def event(self, event, **data):
        # Only authoritative operational fields belong in the receipt.
        fields = {'pillar', 'idx', 'ms', 'id', 'name', 'failed', 'receipt_id',
                  'observation', 'arguments', 'score', 'passed', 'filename',
                  'page_type', 'reason', 'status', 'gate', 'tokens_before',
                  'tokens_after', 'model', 'backend', 'enforced', 'path'}
        payload = {key: value for key, value in data.items() if key in fields}
        with self.lock:
            self.data['events'].append({'type': event, **payload})

    def request(self, **data):
        with self.lock:
            self.data['requests'].append(data)

    def finish(self, result=None, error=None):
        self.data['seconds'] = round(time.perf_counter() - self.started, 3)
        self.data['status'] = 'error' if error else 'completed'
        if error:
            self.data['error'] = {'type': type(error).__name__,
                                  'status_code': getattr(error, 'status_code', getattr(error.__cause__, 'status_code', None))}
        if result is not None:
            self.data['approved'] = result.get('approved')
            page = result.get('wiki_page')
            self.data['wiki_page'] = getattr(page, 'filename', None) if page else None
            self.data['learning_saved'] = bool(result.get('skill'))
        requests = self.data['requests']
        self.data['metrics'] = {
            'model_requests': len(requests),
            'provider_attempts': sum(r.get('attempts', 1) for r in requests),
            'failed_requests': sum(bool(r.get('failed')) for r in requests),
            'reported_input_tokens': sum(r.get('input_tokens', 0) or 0 for r in requests),
            'reported_output_tokens': sum(r.get('output_tokens', 0) or 0 for r in requests),
            'usage_available_requests': sum(bool(r.get('usage_available')) for r in requests),
            'compression_estimated_tokens_saved': sum(r.get('tokens_saved', 0) or 0 for r in requests),
            'tool_calls': sum(e['type'] == 'tool_called' for e in self.data['events']),
        }
        directory = Path('runs/receipts')
        directory.mkdir(parents=True, exist_ok=True)
        target = directory / (self.id + '.json')
        target.write_text(json.dumps(self.data, ensure_ascii=False, indent=2, default=str), encoding='utf-8')
        return str(target.resolve())


def record_run(fn):
    @functools.wraps(fn)
    def wrapped(*args, **kwargs):
        bound = inspect.signature(fn).bind(*args, **kwargs)
        downstream = bound.arguments.get('emit')
        receipt = RunReceipt()
        def emit(event, **data):
            receipt.event(event, **data)
            if downstream:
                downstream(event, **data)
        bound.arguments['emit'] = emit
        token = current_receipt.set(receipt)
        try:
            result = fn(*bound.args, **bound.kwargs)
            result['receipt'] = receipt.finish(result)
            result['run_id'] = receipt.id
            result['usage'] = receipt.data.get('metrics', {})
            return result
        except Exception as exc:
            receipt.finish(error=exc)
            raise
        finally:
            current_receipt.reset(token)
    return wrapped
