"""
llm_client.py — Unified LLM adapter
Supports: Anthropic Claude | OpenAI-compatible (Ollama, vLLM, LM Studio, OpenAI)
"""

from __future__ import annotations
import os
import yaml
from pathlib import Path
from typing import Optional


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

    def __init__(self, config_path: str = "config.yaml", override_backend: Optional[str] = None):
        self.cfg = load_config(config_path)
        self.backend = override_backend or self.cfg["backend"]
        self._client = self._build_client()

    # ── Public API ────────────────────────────────────────────────────────────

    def chat(
        self,
        prompt: str,
        system: str = "",
        temperature: Optional[float] = None,
        max_tokens: Optional[int] = None,
        history: Optional[list[dict]] = None,
    ) -> str:
        """Send a chat message and return the assistant reply as a string."""
        if self.backend == "claude":
            return self._claude_chat(prompt, system, temperature, max_tokens, history)
        else:
            return self._openai_chat(prompt, system, temperature, max_tokens, history)

    def stream(self, prompt: str, system: str = "", temperature: Optional[float] = None):
        """Generator that yields text chunks (streaming). Claude & OpenAI-compat."""
        if self.backend == "claude":
            yield from self._claude_stream(prompt, system, temperature)
        else:
            yield from self._openai_stream(prompt, system, temperature)

    # ── Private builders ──────────────────────────────────────────────────────

    def _build_client(self):
        if self.backend == "claude":
            try:
                import anthropic
                api_key = os.environ.get(self.cfg["claude"]["api_key_env"])
                return anthropic.Anthropic(api_key=api_key)
            except ImportError:
                raise ImportError("Run: pip install anthropic")
        else:
            try:
                from openai import OpenAI
                bcfg = self.cfg[self.backend]
                api_key_env = bcfg.get("api_key_env")
                api_key = os.environ.get(api_key_env) if api_key_env else "ollama"
                base_url = bcfg.get("base_url")
                return OpenAI(api_key=api_key or "local", base_url=base_url)
            except ImportError:
                raise ImportError("Run: pip install openai")

    # ── Claude ────────────────────────────────────────────────────────────────

    def _claude_chat(self, prompt, system, temperature, max_tokens, history) -> str:
        bcfg = self.cfg["claude"]
        messages = self._build_messages(prompt, history)
        kwargs = dict(
            model=bcfg["model"],
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
            for text in stream.text_stream:
                yield text

    # ── OpenAI-compatible ────────────────────────────────────────────────────

    def _openai_chat(self, prompt, system, temperature, max_tokens, history) -> str:
        bcfg = self.cfg[self.backend]
        messages = []
        if system:
            messages.append({"role": "system", "content": system})
        if history:
            messages.extend(history)
        messages.append({"role": "user", "content": prompt})

        response = self._client.chat.completions.create(
            model=bcfg["model"],
            messages=messages,
            max_tokens=max_tokens or bcfg["max_tokens"],
            temperature=temperature if temperature is not None else bcfg.get("temperature", 0.2),
        )
        return response.choices[0].message.content

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
            delta = chunk.choices[0].delta.content
            if delta:
                yield delta

    # ── Helpers ───────────────────────────────────────────────────────────────

    @staticmethod
    def _build_messages(prompt: str, history: Optional[list[dict]]) -> list[dict]:
        messages = list(history) if history else []
        messages.append({"role": "user", "content": prompt})
        return messages

    def __repr__(self):
        return f"<LLMClient backend={self.backend}>"
