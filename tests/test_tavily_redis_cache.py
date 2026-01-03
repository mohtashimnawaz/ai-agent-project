import fakeredis
import json
from tavily_adapter import TavilyClient


def test_tavily_redis_shared_cache(monkeypatch):
    # create a fake redis client and patch tavily_adapter.redis.from_url
    fake_redis = fakeredis.FakeRedis()

    class FakeRedisModule:
        @staticmethod
        def from_url(url, decode_responses=True):
            return fake_redis

    monkeypatch.setattr("tavily_adapter.redis", FakeRedisModule)

    calls = {"count": 0}

    class FakeResponse:
        status_code = 200

        def json(self):
            return {"results": [{"title": "T1", "url": "u1", "snippet": "S"}]}

    def fake_get(url, headers=None, params=None, timeout=None):
        calls["count"] += 1
        return FakeResponse()

    monkeypatch.setattr("tavily_adapter.requests.get", fake_get)

    client = TavilyClient(redis_cache_url="redis://localhost:6379/0")
    # first call should hit HTTP
    r1 = client.search("topic Z", limit=1)
    assert calls["count"] == 1
    # second call should be served from redis cache (no new HTTP call)
    r2 = client.search("topic Z", limit=1)
    assert calls["count"] == 1
    # verify cached payload stored in redis
    cache_key = client._cache_key("topic Z", 1)
    cached = fake_redis.get(cache_key)
    assert cached is not None
    payload = json.loads(cached)
    assert isinstance(payload, list)
