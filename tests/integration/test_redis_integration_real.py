import os
import pytest
from tavily_adapter import TavilyClient


@pytest.mark.integration
@pytest.mark.skipif(os.environ.get("TAVILY_REDIS_CACHE_URL") is None, reason="TAVILY_REDIS_CACHE_URL not set")
def test_redis_cache_real():
    url = os.environ.get("TAVILY_REDIS_CACHE_URL")
    client = TavilyClient(redis_cache_url=url)
    client._redis_cache.flushall()
    client.search("Integration Topic 2", limit=1)
    # ensure something stored
    key = client._cache_key("Integration Topic 2", 1)
    v = client._redis_cache.get(key)
    assert v is not None
