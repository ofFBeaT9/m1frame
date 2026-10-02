"""
llm_client.py â€” Unified LLM adapter
Supports: Anthropic Claude | OpenAI-compatible (Ollama, vLLM, LM Studio, OpenAI)
"""

from __future__ import annotations

import os
from pathlib import Path

import yaml
from dotenv import load_dotenv

from agents.headroom import check_headroom
from modules.adhd import ADHDFormatter
from modules.headroom import CompressionResult, HeadroomAdapter


def load_config(config_path: str = "config.yaml") -> dict:
    load_dotenv(Path(config_path).resolve().with_name(".env"), override=False)
    with open(config_path, encoding="utf-8") as f:
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
        self.adhd = ADHDFormatter(bool((self.cfg.get("adhd") or {}).get("enabled", False)))
        self.headroom = HeadroomAdapter(self.cfg.get("headroom"))
        self.last_compression: CompressionResult | None = None
        self._client = self._build_client()

    # â”€â”€ Public API â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€

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

        `model` overrides the backend's configured model for this one call â€”
        e.g. routing a single expensive judgment call to a stronger model
        while everything else stays on the cheaper default. Ignored (falls
        back to the configured default) on backends where that doesn't apply.
        """
        check_headroom(self.cfg, self.backend, prompt, system, history, max_tokens, model)
        if self.backend == "claude":
            return self._claude_chat(prompt, system, temperature, max_tokens, history, model)
        elif self.backend == "claudecli":
            return self._claudecli_chat(prompt, system, history, model)
        else:
            return self._openai_chat(prompt, system, temperature, max_tokens, history, model)

    def stream(self, prompt: str, system: str = "", temperature: float | None = None,
               history: list[dict] | None = None):
        """Generator that yields text chunks (streaming). Claude & OpenAI-compat."""
        check_headroom(self.cfg, self.backend, prompt, system, history)
        if self.backend == "claude":
            yield from self._claude_stream(prompt, system, temperature, history)
        elif self.backend == "claudecli":
            yield self._claudecli_chat(prompt, system, history)   # CLI returns whole reply
        else:
            yield from self._openai_stream(prompt, system, temperature, history)

    # â”€â”€ Private builders â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€

    def _build_client(self):
        if self.backend == "claudecli":
            return None  # no SDK client â€” we shell out to the Claude Code CLI
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
                if api_key_env and not api_key:
                    raise RuntimeError(f"Missing {api_key_env} for backend {self.backend}")
                base_url = bcfg.get("base_url")
                return OpenAI(api_key=api_key or "local", base_url=base_url,
                              timeout=bcfg.get("timeout", 60), max_retries=bcfg.get("max_retries", 1))
            except ImportError:
                raise ImportError("Run: pip install openai") from None

    # â”€â”€ Claude â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€

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

    # â”€â”€ Claude Code CLI (no API key â€” uses your `claude` auth) â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€
    def _claudecli_chat(self, prompt, system, history, model=None) -> str:
        """Run the prompt through the Claude Code CLI headlessly (`claude -p`).
        Lets m1frame run with zero API key by reusing your Claude Code login."""
        import subprocess
        bcfg = self.cfg.get("claudecli", {}) or {}
        full = prompt
        if history:
            convo = "\n".join(f"{m.get('role')}: {m.get('content')}" for m in history)
            full = convo + "\nuser: " + prompt
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

    # â”€â”€ OpenAI-compatible â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€

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

    # â”€â”€ Helpers â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€

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
        return result.messages

    def __repr__(self):
        return f"<LLMClient backend={self.backend}>"
