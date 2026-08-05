"""
llm_client.py — Unified LLM adapter
Supports: Anthropic Claude | OpenAI-compatible (Ollama, vLLM, LM Studio, OpenAI)
"""

from __future__ import annotations

import os

import yaml


def load_config(config_path: str = "config.yaml") -> dict:
    with open(config_path) as f:
        return yaml.safe_load(f)


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
        if self.backend == "claude":
            return self._claude_chat(prompt, system, temperature, max_tokens, history, model)
        elif self.backend == "claudecli":
            return self._claudecli_chat(prompt, system, history, model)
        else:
            return self._openai_chat(prompt, system, temperature, max_tokens, history, model)

    def stream(self, prompt: str, system: str = "", temperature: float | None = None):
        """Generator that yields text chunks (streaming). Claude & OpenAI-compat."""
        if self.backend == "claude":
            yield from self._claude_stream(prompt, system, temperature)
        elif self.backend == "claudecli":
            yield self._claudecli_chat(prompt, system, None)   # CLI returns whole reply
        else:
            yield from self._openai_stream(prompt, system, temperature)

    # ── Private builders ──────────────────────────────────────────────────────

    def _build_client(self):
        if self.backend == "claudecli":
            return None  # no SDK client — we shell out to the Claude Code CLI
        if self.backend == "claude":
            try:
                import anthropic
                api_key = os.environ.get(self.cfg["claude"]["api_key_env"])
                return anthropic.Anthropic(api_key=api_key)
            except ImportError:
                raise ImportError("Run: pip install anthropic") from None
        else:
            try:
                from openai import OpenAI
                bcfg = self.cfg[self.backend]
                api_key_env = bcfg.get("api_key_env")
                api_key = os.environ.get(api_key_env) if api_key_env else "ollama"
                base_url = bcfg.get("base_url")
                return OpenAI(api_key=api_key or "local", base_url=base_url)
            except ImportError:
                raise ImportError("Run: pip install openai") from None

    # ── Claude ────────────────────────────────────────────────────────────────

    def _claude_chat(self, prompt, system, temperature, max_tokens, history, model=None) -> str:
        bcfg = self.cfg["claude"]
        messages = self._build_messages(prompt, history)
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
        return response.content[0].text

    def _claude_stream(self, prompt, system, temperature):
        bcfg = self.cfg["claude"]
        kwargs = dict(
            model=bcfg["model"],
            max_tokens=bcfg["max_tokens"],
            messages=[{"role": "user", "content": prompt}],
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
        full = prompt
        if history:
            convo = "\n".join(f"{m.get('role')}: {m.get('content')}" for m in history)
            full = convo + "\nuser: " + prompt
        args = ["claude", "-p", "--output-format", "text"]
        model = model or bcfg.get("model")
        if model:
            args += ["--model", str(model)]
        if system:
            args += ["--append-system-prompt", system]
        try:
            res = subprocess.run(args, input=full, capture_output=True, text=True,
                                 timeout=bcfg.get("timeout", 300))
        except FileNotFoundError:
            raise RuntimeError("Claude Code CLI ('claude') not found on PATH. "
                               "Install Claude Code, or set backend to 'claude' with an API key.") from None
        if res.returncode != 0:
            raise RuntimeError(f"claude CLI error: {(res.stderr or '').strip()[:300]}")
        return (res.stdout or "").strip()

    # ── OpenAI-compatible ────────────────────────────────────────────────────

    def _openai_chat(self, prompt, system, temperature, max_tokens, history, model=None) -> str:
        bcfg = self.cfg[self.backend]
        messages = []
        if system:
            messages.append({"role": "system", "content": system})
        if history:
            messages.extend(history)
        messages.append({"role": "user", "content": prompt})

        response = self._client.chat.completions.create(
            model=model or bcfg["model"],
            messages=messages,
            max_tokens=max_tokens or bcfg["max_tokens"],
            temperature=temperature if temperature is not None else bcfg.get("temperature", 0.2),
        )
        msg = response.choices[0].message
        # Reasoning models (e.g. Gemma 4 via LM Studio / Ollama) may return an
        # empty `content` and place the text in `reasoning_content`. Fall back so
        # the pipeline never silently receives an empty string.
        return msg.content or getattr(msg, "reasoning_content", None) or ""

    def _openai_stream(self, prompt, system, temperature):
        bcfg = self.cfg[self.backend]
        messages = []
        if system:
            messages.append({"role": "system", "content": system})
        messages.append({"role": "user", "content": prompt})
        stream = self._client.chat.completions.create(
            model=bcfg["model"],
            messages=messages,
            max_tokens=bcfg["max_tokens"],
            temperature=temperature if temperature is not None else bcfg.get("temperature", 0.2),
            stream=True,
        )
        for chunk in stream:
            d = chunk.choices[0].delta
            delta = d.content or getattr(d, "reasoning_content", None)
            if delta:
                yield delta

    # ── Helpers ───────────────────────────────────────────────────────────────

    @staticmethod
    def _build_messages(prompt: str, history: list[dict] | None) -> list[dict]:
        messages = list(history) if history else []
        messages.append({"role": "user", "content": prompt})
        return messages

    def __repr__(self):
        return f"<LLMClient backend={self.backend}>"
