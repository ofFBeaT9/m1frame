"""
llm_client.py — Unified LLM adapter
Supports: Anthropic Claude | OpenAI-compatible (Ollama, vLLM, LM Studio, OpenAI)
"""

from __future__ import annotations

import os
import threading
import time
from pathlib import Path

import yaml
from dotenv import load_dotenv

from agents.headroom import check_headroom
from modules.adhd import ADHDFormatter
from modules.headroom import CompressionResult, HeadroomAdapter


def load_config(config_path: str = "config.yaml") -> dict:
    load_dotenv(Path(config_path).resolve().with_name(".env"), override=False)
    with open(config_path, encoding="utf-8") as f:
        cfg = yaml.safe_load(f) or {}
    if cfg.get('environment_file'):
        load_dotenv(Path(cfg['environment_file']), override=False)
    from modules.controller import effective_config
    return effective_config(cfg)


class LLMClient:
    """
    Single interface for any LLM backend.
    Usage:
        client = LLMClient()
        response = client.chat("What is 2+2?")
    """

    def __init__(self, config_path: str = "config.yaml", override_backend: str | None = None):
        self.cfg = load_config(config_path)
        self.backend = override_backend or self.cfg["backend"]
        self.adhd = ADHDFormatter(bool((self.cfg.get("adhd") or {}).get("enabled", False)))
        self.headroom = HeadroomAdapter(self.cfg.get("headroom"))
        self.last_compression: CompressionResult | None = None
        self._local = threading.local()
        from modules.receipts import current_receipt
        self.receipt = current_receipt.get()
        self._client = self._build_client()

    # ── Public API ────────────────────────────────────────────────────────────

    def chat(
        self,
        prompt: str,
        system: str = "",
        temperature: float | None = None,
        max_tokens: int | None = None,
        history: list[dict] | None = None,
        model: str | None = None,
    ) -> str:
        """Send a chat message and return the assistant reply as a string.

        `model` overrides the backend's configured model for this one call —
        e.g. routing a single expensive judgment call to a stronger model
        while everything else stays on the cheaper default. Ignored (falls
        back to the configured default) on backends where that doesn't apply.
        """
        check_headroom(self.cfg, self.backend, prompt, system, history, max_tokens, model)
        if not hasattr(self, "_local"):
            self._local = threading.local()
        started = time.perf_counter()
        self._local.usage = {}
        self._local.compression = None
        failed, status = False, None
        attempts = 0
        retries = max(0, min(int(self.cfg.get(self.backend, {}).get('max_retries', 1)), 2))
        try:
            for attempt in range(retries + 1):
                attempts += 1
                try:
                    if self.backend == "claude":
                        return self._claude_chat(prompt, system, temperature, max_tokens, history, model)
                    if self.backend == "claudecli":
                        return self._claudecli_chat(prompt, system, history, model)
                    return self._openai_chat(prompt, system, temperature, max_tokens, history, model)
                except Exception as exc:
                    code = getattr(exc, 'status_code', None)
                    daily = code == 429 and ('per-day' in str(exc) or 'daily' in str(exc).lower())
                    transient = code in {408, 409, 429, 500, 502, 503, 504} or type(exc).__name__ in {'APIConnectionError', 'APITimeoutError'}
                    if daily or not transient or attempt >= retries:
                        raise
                    time.sleep(0.25 * (2 ** attempt))
            raise RuntimeError('Provider retry loop ended without a result')
        except Exception as exc:
            failed, status = True, getattr(exc, 'status_code', None)
            if status in (401, 403):
                raise RuntimeError(
                    f"Provider access denied (HTTP {status}) for {self.backend}. "
                    "Verify account/model entitlement and network policy. No model or paid-provider "
                    "fallback was attempted; credentials were not changed.") from exc
            if status == 429:
                daily = 'per-day' in str(exc) or 'daily' in str(exc).lower()
                raise RuntimeError(
                    f"Provider {'daily free-model quota exhausted' if daily else 'rate limit reached'} (HTTP 429). "
                    "Wait for the provider reset or change account capacity locally. "
                    "No paid fallback or automatic purchase was attempted.") from exc
            raise
        finally:
            self._record_request(started, failed, status, attempts, model)

    def stream(self, prompt: str, system: str = "", temperature: float | None = None,
               history: list[dict] | None = None):
        """Generator that yields text chunks (streaming). Claude & OpenAI-compat."""
        # Buffer the provider stream before exposing any unvalidated text.
        from modules.output import delivery_text
        check_headroom(self.cfg, self.backend, prompt, system, history)
        if not hasattr(self, "_local"):
            self._local = threading.local()
        started = time.perf_counter()
        self._local.usage = {}
        self._local.compression = None
        failed, status = False, None
        try:
            if self.backend == "claude":
                chunks = self._claude_stream(prompt, system, temperature, history)
            elif self.backend == "claudecli":
                chunks = [self._claudecli_chat(prompt, system, history)]
            else:
                chunks = self._openai_stream(prompt, system, temperature, history)
            text = delivery_text(''.join(chunks))
            for offset in range(0, len(text), 256):
                yield text[offset:offset + 256]
        except Exception as exc:
            failed, status = True, getattr(exc, 'status_code', None)
            raise
        finally:
            self._record_request(started, failed, status, 1, stream=True)

    def _record_request(self, started, failed, status, attempts, model=None, stream=False):
        if getattr(self, "receipt", None) is None:
            return
        usage = self._local.usage
        compression = self._local.compression
        self.receipt.request(
            backend=self.backend, model=model or self.cfg[self.backend].get('model'),
            seconds=round(time.perf_counter()-started, 3), failed=failed, attempts=attempts,
            stream=stream, status_code=status, usage_available=bool(usage),
            input_tokens=usage.get('prompt_tokens', usage.get('input_tokens', 0)),
            output_tokens=usage.get('completion_tokens', usage.get('output_tokens', 0)),
            tokens_saved=getattr(compression, 'tokens_saved', 0),
            compression_applied=getattr(compression, 'applied', False),
            compression_error=bool(getattr(compression, 'error', None)))

    # ── Private builders ──────────────────────────────────────────────────────

    def _build_client(self):
        if self.backend == "claudecli":
            return None  # no SDK client — we shell out to the Claude Code CLI
        if self.backend == "claude":
            try:
                import anthropic
                api_key = os.environ.get(self.cfg["claude"]["api_key_env"])
                if not api_key and not os.environ.get("ANTHROPIC_AUTH_TOKEN"):
                    raise RuntimeError(
                        f"Missing {self.cfg['claude']['api_key_env']} for backend claude. "
                        "Configure the credential in the local .env or choose a configured backend."
                    )
                bcfg = self.cfg["claude"]
                return anthropic.Anthropic(api_key=api_key, timeout=max(5, min(float(bcfg.get("timeout", 60)), 120)),
                                           max_retries=0)
            except ImportError:
                raise ImportError("Run: pip install anthropic") from None
        else:
            try:
                from openai import OpenAI
                bcfg = self.cfg[self.backend]
                api_key_env = bcfg.get("api_key_env")
                api_key = os.environ.get(api_key_env) if api_key_env else "ollama"
                if api_key_env and not api_key:
                    raise RuntimeError(f"Missing {api_key_env} for backend {self.backend}")
                base_url = bcfg.get("base_url")
                return OpenAI(api_key=api_key or "local", base_url=base_url,
                              timeout=max(5, min(float(bcfg.get("timeout", 60)), 120)), max_retries=0)
            except ImportError:
                raise ImportError("Run: pip install openai") from None

    # ── Claude ────────────────────────────────────────────────────────────────

    def _claude_chat(self, prompt, system, temperature, max_tokens, history, model=None) -> str:
        bcfg = self.cfg["claude"]
        messages = self._build_messages(prompt, history)
        messages = self._prepare_messages(messages, model or bcfg["model"])
        kwargs = dict(
            model=model or bcfg["model"],
            max_tokens=max_tokens or bcfg["max_tokens"],
            messages=messages,
        )
        if system:
            kwargs["system"] = system
        if temperature is not None:
            kwargs["temperature"] = temperature
        elif bcfg.get("temperature") is not None:
            kwargs["temperature"] = bcfg["temperature"]

        response = self._client.messages.create(**kwargs)
        self._local.usage = response.usage.model_dump() if response.usage else {}
        return response.content[0].text

    def _claude_stream(self, prompt, system, temperature, history=None):
        bcfg = self.cfg["claude"]
        messages = self._prepare_messages(
            self._build_messages(prompt, history), bcfg["model"]
        )
        kwargs = dict(
            model=bcfg["model"],
            max_tokens=bcfg["max_tokens"],
            messages=messages,
        )
        if system:
            kwargs["system"] = system
        if temperature is not None:
            kwargs["temperature"] = temperature
        with self._client.messages.stream(**kwargs) as stream:
            yield from stream.text_stream

    # ── Claude Code CLI (no API key — uses your `claude` auth) ────────────────
    def _claudecli_chat(self, prompt, system, history, model=None) -> str:
        """Run the prompt through the Claude Code CLI headlessly (`claude -p`).
        Lets m1frame run with zero API key by reusing your Claude Code login."""
        import subprocess
        bcfg = self.cfg.get("claudecli", {}) or {}
        messages = self._build_messages(prompt, history)
        if system:
            messages.insert(0, {"role": "system", "content": system})
        messages = self._prepare_messages(messages, model or bcfg.get("model") or "claudecli")
        # System text is preserved separately by the CLI's explicit system flag.
        dialogue = [m for m in messages if m.get("role") != "system"]
        full = "\n".join(f"{m.get('role')}: {m.get('content')}" for m in dialogue) if history else prompt
        args = ["claude", "-p", "--output-format", "text", "--tools", "",
                "--strict-mcp-config", "--mcp-config", '{"mcpServers":{}}',
                "--no-session-persistence"]
        model = model or bcfg.get("model")
        if model:
            args += ["--model", str(model)]
        internal_system = (
            "You are one internal model call inside M1Frame. Follow the assigned role. "
            "Do not start another workflow, run repository startup routines, or invoke host tools. "
            "M1Frame executes tool requests itself through its bounded registry protocol.\n\n"
            + system)
        args += ["--system-prompt", internal_system]
        # Claude Code refuses to launch inside another Claude Code session. That guard
        # exists to stop an interactive session spawning itself; a headless `-p` call is
        # a separate short-lived process, so drop the marker for the child only. Without
        # this, the claudecli backend cannot be used from the m1frame MCP server.
        env = {k: v for k, v in os.environ.items() if k != "CLAUDECODE"}
        env["M1FRAME_INTERNAL_CALL"] = "1"
        if os.name == "nt" and not env.get("CLAUDE_CODE_GIT_BASH_PATH"):
            import shutil
            git = shutil.which("git")
            if git:
                bash = Path(git).resolve().parent.parent / "bin" / "bash.exe"
                if bash.is_file():
                    env["CLAUDE_CODE_GIT_BASH_PATH"] = str(bash)
        try:
            res = subprocess.run(args, input=full, capture_output=True, text=True, encoding="utf-8",
                                 timeout=bcfg.get("timeout", 300), env=env)
        except FileNotFoundError:
            raise RuntimeError("Claude Code CLI ('claude') not found on PATH. "
                               "Install Claude Code, or set backend to 'claude' with an API key.") from None
        if res.returncode != 0:
            # The CLI reports some failures (auth, entitlement) on stdout with an empty
            # stderr, which used to surface here as a blank error message.
            detail = (res.stderr or "").strip() or (res.stdout or "").strip()
            raise RuntimeError(f"claude CLI error (exit {res.returncode}): {detail[:300]}")
        return (res.stdout or "").strip()

    # ── OpenAI-compatible ────────────────────────────────────────────────────

    def _openai_options(self, model: str) -> dict:
        bcfg = self.cfg[self.backend]
        extra: dict = {}
        if self.backend == "openrouter" and bcfg.get("free_only", False):
            if not model.endswith(":free"):
                raise ValueError("OpenRouter free_only requires an explicit :free model")
            extra["provider"] = {"max_price": {"prompt": 0, "completion": 0}}
        if self.backend == "openrouter" and "reasoning_enabled" in bcfg:
            extra["reasoning"] = {"enabled": bool(bcfg["reasoning_enabled"])}
        return {"extra_body": extra} if extra else {}

    def _openai_chat(self, prompt, system, temperature, max_tokens, history, model=None) -> str:
        bcfg = self.cfg[self.backend]
        messages = []
        if system:
            messages.append({"role": "system", "content": system})
        if history:
            messages.extend(history)
        messages.append({"role": "user", "content": prompt})
        messages = self._prepare_messages(messages, model or bcfg["model"])

        response = self._client.chat.completions.create(
            model=model or bcfg["model"],
            messages=messages,
            max_tokens=max_tokens or bcfg["max_tokens"],
            temperature=temperature if temperature is not None else bcfg.get("temperature", 0.2),
            **self._openai_options(model or bcfg["model"]),
        )
        usage = getattr(response, "usage", None)
        self.last_usage = usage.model_dump() if usage else {}
        self._local.usage = self.last_usage
        msg = response.choices[0].message
        # Internal reasoning is not a substitute for a completed answer.
        if not msg.content:
            raise RuntimeError("Provider returned no final answer; reasoning-only output is not a deliverable")
        return msg.content

    def _openai_stream(self, prompt, system, temperature, history=None):
        bcfg = self.cfg[self.backend]
        messages = []
        if system:
            messages.append({"role": "system", "content": system})
        messages.extend(self._build_messages(prompt, history))
        messages = self._prepare_messages(messages, bcfg["model"])
        stream = self._client.chat.completions.create(
            model=bcfg["model"],
            messages=messages,
            max_tokens=bcfg["max_tokens"],
            temperature=temperature if temperature is not None else bcfg.get("temperature", 0.2),
            stream=True,
            **self._openai_options(bcfg["model"]),
        )
        delivered = False
        for chunk in stream:
            if not chunk.choices:
                continue
            d = chunk.choices[0].delta
            delta = d.content
            if delta:
                delivered = True
                yield delta
        if not delivered:
            raise RuntimeError("Provider returned no final answer in the stream")

    # ── Helpers ───────────────────────────────────────────────────────────────

    @staticmethod
    def _build_messages(prompt: str, history: list[dict] | None) -> list[dict]:
        messages = list(history) if history else []
        messages.append({"role": "user", "content": prompt})
        return messages

    def _prepare_messages(self, messages: list[dict], model: str) -> list[dict]:
        adapter = getattr(self, "headroom", None)
        if adapter is None:
            adapter = HeadroomAdapter(self.cfg.get("headroom"))
        result = adapter.compress_messages(messages, model=model)
        self.last_compression = result
        if hasattr(self, "_local"):
            self._local.compression = result
        receipt = getattr(self, "receipt", None)
        if receipt is not None:
            receipt.event("headroom_checked", pillar="headroom",
                          status=("error" if result.error else "compressed" if result.applied
                                  else "checked_no_change" if result.available else "disabled"),
                          tokens_before=result.tokens_before, tokens_after=result.tokens_after,
                          available=result.available, required=bool(adapter.config.get("required")))
        if adapter.config.get("required") and (not result.available or result.error):
            raise RuntimeError("Required Headroom processing failed or is unavailable; request not sent.")
        return result.messages

    def __repr__(self):
        return f"<LLMClient backend={self.backend}>"
