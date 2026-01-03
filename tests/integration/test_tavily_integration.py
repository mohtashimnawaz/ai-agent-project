import os
import pytest
from tavily_adapter import TavilyClient


@pytest.mark.integration
@pytest.mark.skipif(os.environ.get("TAVILY_API_KEY") is None, reason="TAVILY_API_KEY not set")
def test_tavily_search_integration():
    client = TavilyClient()
    res = client.search("Quantum Computing", limit=2)
    assert isinstance(res, list)
    assert len(res) >= 1


@pytest.mark.integration
@pytest.mark.skipif(os.environ.get("TAVILY_API_KEY") is None or os.environ.get("TAVILY_REDIS_CACHE_URL") is None, reason="TAVILY_API_KEY or TAVILY_REDIS_CACHE_URL not set")
def test_tavily_search_with_redis_cache_integration():
    client = TavilyClient(redis_cache_url=os.environ.get("TAVILY_REDIS_CACHE_URL"))
    # call twice and expect the second to be served from cache
    client._redis_cache.flushall()
    client.search("Integration Topic", limit=1)
    metrics = client.get_cache_metrics()
    assert metrics["misses"] >= 1
    client.search("Integration Topic", limit=1)
    assert client.get_cache_metrics()["hits"] >= 1
