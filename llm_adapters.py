"""Pluggable LLM adapters for GPT-4o and Claude 3.5 Sonnet.

Adapters check for SDK availability and env-based API keys. Each adapter implements
`generate(prompt, **kwargs) -> str`.

Env vars used:
- GPT4O_API_KEY (for GPT-4o/openai-compatible)
- CLAUDE_API_KEY (for Claude/Anthropic-like)
- LLM_PROVIDER can be used externally to choose a provider (gpt4o|claude|mock)
"""
from __future__ import annotations
from typing import Protocol, Optional, Dict
import os
import logging

logger = logging.getLogger(__name__)


class LLMAdapter(Protocol):
    def generate(self, prompt: str, **kwargs) -> str:  # pragma: no cover - protocol
        ...


class MockLLMAdapter:
    def generate(self, prompt: str, **kwargs) -> str:
        return f"MOCK RESPONSE FOR: {prompt[:200]}"


# GPT-4o adapter (example using an 'openai' compatible interface)
class GPT4oAdapter:
    def __init__(self, api_key: Optional[str] = None):
        self.api_key = api_key or os.environ.get("GPT4O_API_KEY") or os.environ.get("OPENAI_API_KEY")
        if not self.api_key:
            raise RuntimeError("GPT4o API key not found in GPT4O_API_KEY or OPENAI_API_KEY env vars")
        try:
            import openai
            self._client = openai
            self._client.api_key = self.api_key
        except Exception as e:  # pragma: no cover - platform deps
            logger.warning("openai package not available; GPT4oAdapter will raise if used: %s", e)
            self._client = None

    def generate(self, prompt: str, **kwargs) -> str:
        if self._client is None:
            raise RuntimeError("openai package not available for GPT4oAdapter")
        # Minimal example using the completions-like interface; adjust to your SDK
        resp = self._client.ChatCompletion.create(model=kwargs.get("model", "gpt-4o-mini"), messages=[{"role": "user", "content": prompt}], max_tokens=kwargs.get("max_tokens", 512))
        # Extract text
        if isinstance(resp, dict):
            # compatibility with dict-like responses
            choices = resp.get("choices") or []
            if choices:
                return choices[0].get("message", {}).get("content", "")
        # fallback
        return str(resp)


# Claude adapter (example using an 'anthropic-like' interface)
class ClaudeAdapter:
    def __init__(self, api_key: Optional[str] = None):
        self.api_key = api_key or os.environ.get("CLAUDE_API_KEY")
        if not self.api_key:
            raise RuntimeError("Claude API key not found in CLAUDE_API_KEY env var")
        try:
            import anthropic
            self._client = anthropic
            # instantiate client if SDK requires
            # self._client = anthropic.Client(self.api_key)
        except Exception as e:  # pragma: no cover - platform deps
            logger.warning("anthropic package not available; ClaudeAdapter will raise if used: %s", e)
            self._client = None

    def generate(self, prompt: str, **kwargs) -> str:
        if self._client is None:
            raise RuntimeError("anthropic package not available for ClaudeAdapter")
        # Minimal example - adjust to the exact SDK you have
        resp = self._client.Completion.create(prompt=prompt, max_tokens=kwargs.get("max_tokens", 512))
        if isinstance(resp, dict):
            return resp.get("completion", "")
        return str(resp)


# Factory helper

def make_llm(provider: Optional[str] = None) -> LLMAdapter:
    # Default to GPT-4o for best general-purpose reasoning unless overridden
    provider = provider or os.environ.get("LLM_PROVIDER") or "gpt4o"
    provider = provider.lower()
    if provider == "gpt4o":
        return GPT4oAdapter()
    elif provider == "claude":
        return ClaudeAdapter()
    else:
        return MockLLMAdapter()
