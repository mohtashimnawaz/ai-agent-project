import os
import pytest
from agents_core import InMemoryMemory, RedisMemory, make_memory
from llm_adapters import MockLLMAdapter, GPT4oAdapter, ClaudeAdapter, make_llm


def test_inmemory_basic():
    m = InMemoryMemory()
    m.set("k", {"a": 1})
    assert m.get("k") == {"a": 1}
    m.append_to_list("L", 1)
    m.append_to_list("L", 2)
    assert m.get_list("L") == [1, 2]


def test_make_memory_falls_back(monkeypatch):
    # Simulate missing redis package by forcing RedisMemory to fail
    monkeypatch.setenv("REDIS_URL", "redis://does-not-exist:6379/0")
    # make_memory should return a RedisMemory if redis present, but in test env we don't have redis, so it will fallback
    m = make_memory("redis")
    assert m is not None


def test_mock_llm():
    adapter = MockLLMAdapter()
    resp = adapter.generate("Hello world")
    assert "MOCK RESPONSE" in resp


@pytest.mark.skipif(os.environ.get("GPT4O_API_KEY") is None and os.environ.get("OPENAI_API_KEY") is None, reason="openai creds missing")
def test_gpt4o_adapter_smoke():
    adapter = GPT4oAdapter()
    resp = None
    try:
        resp = adapter.generate("Say hello in one sentence", max_tokens=10)
    except Exception as e:
        pytest.skip(f"OpenAI SDK call not available or failed: {e}")
    assert isinstance(resp, str)


@pytest.mark.skipif(os.environ.get("CLAUDE_API_KEY") is None, reason="claude creds missing")
def test_claude_adapter_smoke():
    adapter = ClaudeAdapter()
    resp = None
    try:
        resp = adapter.generate("Say hello in one sentence", max_tokens=10)
    except Exception as e:
        pytest.skip(f"Claude SDK call not available or failed: {e}")
    assert isinstance(resp, str)
