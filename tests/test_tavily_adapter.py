import os
import types
import pytest

from tavily_adapter import TavilyClient, TavilyError
from crewai_agents import Source


def test_missing_api_key_raises(monkeypatch):
    monkeypatch.delenv("TAVILY_API_KEY", raising=False)
    with pytest.raises(TavilyError):
        TavilyClient()


def test_search_parses_http_response(monkeypatch):
    # Provide an API key via env
    monkeypatch.setenv("TAVILY_API_KEY", "testkey")

    # fake requests.get
    class FakeResponse:
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

    monkeypatch.setattr("tavily_adapter.requests.get", fake_get)

    client = TavilyClient()
    results = client.search("topic X", limit=1)
    assert isinstance(results, list)
    assert len(results) == 1
    assert isinstance(results[0], Source)
    assert results[0].title == "T1"
