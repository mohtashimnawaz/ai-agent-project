import os
import fakeredis
import pytest

from agents_core import RedisMemory


def test_redis_memory_with_fakeredis(monkeypatch):
    # monkeypatch redis.from_url to return fakeredis instance
    import redis as real_redis

    def fake_from_url(url, decode_responses=True):
        return fakeredis.FakeRedis()

    monkeypatch.setattr("agents_core.redis", real_redis)
    monkeypatch.setattr(real_redis, "from_url", fake_from_url)

    mem = RedisMemory(redis_url="redis://localhost:6379/0")
    mem.set("k", {"a": 1})
    assert mem.get("k") == {"a": 1}
    mem.append_to_list("L", 1)
    mem.append_to_list("L", 2)
    assert mem.get_list("L") == [1, 2]
