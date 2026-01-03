from tavily_adapter import TavilyClient


def test_cache_metrics_local_cache():
    client = TavilyClient()
    key = client._cache_key("m1", 1)
    # ensure empty
    assert client.get_cache_metrics()["hits"] == 0
    assert client.get_cache_metrics()["misses"] == 0

    # prime local cache
    client._set_cache(key, [{"title":"x","url":"u","snippet":"s"}])
    _ = client._get_cached(key)
    metrics = client.get_cache_metrics()
    assert metrics["hits"] >= 1
