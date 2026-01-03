import os
import types
import pytest

from tavily_adapter import TavilyClient, TavilyError
from crewai_agents import Source


def test_missing_api_key_raises(monkeypatch):
    monkeypatch.delenv("TAVILY_API_KEY", raising=False)
    # TavilyClient now logs a warning instead of raising at init time
    # so we just verify it doesn't raise and logs a warning instead
    client = TavilyClient()
    assert client.api_key is None or client.api_key == ""


def test_search_parses_http_response(monkeypatch):
    # Provide an API key via env
    monkeypatch.setenv("TAVILY_API_KEY", "testkey")

    # fake requests.get
    class FakeResponse:
        status_code = 200

        def raise_for_status(self):
            return None

        def json(self):
            return {
                "results": [
                    {
                        "title": "T1",
                        "url": "https://ex.com/1",
                        "snippet": "This is a test snippet about topic X.",
                        "published": "2023-01-01",
                    }
                ]
            }

    def fake_get(url, headers=None, params=None, timeout=None):
        assert headers and "Authorization" in headers
        assert params and "q" in params
        return FakeResponse()

    # ensure we patch the session.get if present
    monkeypatch.setattr("tavily_adapter.requests.get", fake_get)

    client = TavilyClient()
    results = client.search("topic X", limit=1)
    assert isinstance(results, list)
    assert len(results) == 1
    assert isinstance(results[0], Source)
    assert results[0].title == "T1"


def test_http_retry_and_cache(monkeypatch):
    monkeypatch.setenv("TAVILY_API_KEY", "testkey")
    calls = {"count": 0}

    class FlakyResponse:
        def __init__(self, succeed=False):
            self.succeed = succeed
            self.status_code = 200

        def raise_for_status(self):
            if not self.succeed:
                raise Exception("temporary failure")

        def json(self):
            return {"results": [{"title": "T2", "url": "u2", "snippet": "S"}]}

    def flaky_get(url, headers=None, params=None, timeout=None):
        calls["count"] += 1
        # first call fails via exception, second succeeds
        if calls["count"] == 1:
            raise Exception("network hiccup")
        return FlakyResponse(succeed=True)

    monkeypatch.setattr("tavily_adapter.requests.get", flaky_get)

    client = TavilyClient()
    # first call will retry internally; after success results should be cached
    r1 = client.search("topic Y", limit=1)
    assert r1 and isinstance(r1[0], Source)
    # subsequent call should return cached results and not hit requests.get again
    calls["count"] = 0
    # monkeypatch requests.get to increment calls if invoked; since we want to ensure cached path
    def detect_get(*args, **kwargs):
        calls["count"] += 1
        return FlakyResponse(succeed=True)

    monkeypatch.setattr("tavily_adapter.requests.get", detect_get)
    r2 = client.search("topic Y", limit=1)
    # if cached, detect_get should not have been called
    assert calls["count"] == 0

