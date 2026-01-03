"""Agent base, tool registry, and memory interfaces for the PersonalResearcher agent.

- Agent: implements a simple reasoning loop skeleton (plan -> act -> observe -> reflect)
- ToolRegistry: holds tools by name (search, llm, writer, etc.)
- Memory interface + RedisMemory implementation (pluggable)

Design: keep minimal and testable. Redis is used for production memory; a simple in-memory fallback
is provided for tests/local use.
"""
from __future__ import annotations
from typing import Any, Dict, Optional, Protocol, List
import os
import json
import logging

logger = logging.getLogger(__name__)
logging.basicConfig(level=logging.INFO)


class Tool(Protocol):
    def run(self, *args, **kwargs) -> Any:  # pragma: no cover - protocol
        ...


class ToolRegistry:
    def __init__(self):
        self._tools: Dict[str, Tool] = {}

    def register(self, name: str, tool: Tool) -> None:
        self._tools[name] = tool

    def get(self, name: str) -> Tool:
        return self._tools[name]


# --- Memory interface ---

class Memory(Protocol):
    def set(self, key: str, value: Any) -> None:
        ...

    def get(self, key: str) -> Optional[Any]:
        ...

    def append_to_list(self, key: str, value: Any) -> None:
        ...

    def get_list(self, key: str) -> List[Any]:
        ...


class InMemoryMemory:
    """Simple in-process memory for tests or single-process runs."""

    def __init__(self):
        self._store: Dict[str, Any] = {}

    def set(self, key: str, value: Any) -> None:
        self._store[key] = value

    def get(self, key: str) -> Optional[Any]:
        return self._store.get(key)

    def append_to_list(self, key: str, value: Any) -> None:
        lst = self._store.get(key) or []
        lst.append(value)
        self._store[key] = lst

    def get_list(self, key: str) -> List[Any]:
        return list(self._store.get(key) or [])


# Attempt to import redis at module level so tests can monkeypatch `agents_core.redis`
try:
    import redis
except Exception:
    redis = None


class RedisMemory:
    """Redis-based memory implementation. Requires `redis` package.

    Configuration:
      - REDIS_URL env var (e.g., redis://localhost:6379/0)

    Use `InMemoryMemory` in tests if you don't have Redis available.
    """

    def __init__(self, redis_url: Optional[str] = None):
        redis_url = redis_url or os.environ.get("REDIS_URL") or "redis://localhost:6379/0"
        if redis is None:  # pragma: no cover - platform deps
            raise RuntimeError("`redis` package required for RedisMemory")

        self._client = redis.from_url(redis_url, decode_responses=True)

    def set(self, key: str, value: Any) -> None:
        self._client.set(key, json.dumps(value))

    def get(self, key: str) -> Optional[Any]:
        v = self._client.get(key)
        if v is None:
            return None
        try:
            return json.loads(v)
        except Exception:
            return v

    def append_to_list(self, key: str, value: Any) -> None:
        self._client.rpush(key, json.dumps(value))

    def get_list(self, key: str) -> List[Any]:
        vals = self._client.lrange(key, 0, -1)
        out: List[Any] = []
        for v in vals:
            try:
                out.append(json.loads(v))
            except Exception:
                out.append(v)
        return out


# --- Agent base (reasoning loop) ---

class Agent:
    """A minimal agent skeleton that can be extended for domain-specific behavior.

    Methods to override:
      - plan: produce a set of actions/questions to execute
      - act: execute an action using tools
      - observe: process tool results
      - reflect: update memory or internal state
    """

    def __init__(self, name: str, tools: ToolRegistry, memory: Optional[Memory] = None):
        self.name = name
        self.tools = tools
        self.memory = memory or InMemoryMemory()
        self.history_key = f"agent:{self.name}:history"

    def plan(self, context: Dict[str, Any]) -> List[Dict[str, Any]]:
        """Return a list of actions. Action is a dict with 'tool' and 'args'"""
        raise NotImplementedError

    def act(self, action: Dict[str, Any]) -> Any:
        tool_name = action.get("tool")
        tool = self.tools.get(tool_name)
        args = action.get("args", [])
        kwargs = action.get("kwargs", {})
        logger.info("Agent %s invoking tool %s", self.name, tool_name)
        return tool.run(*args, **kwargs)

    def observe(self, result: Any) -> Dict[str, Any]:
        """Process tool result and return any observations."""
        # default no-op
        return {"result": result}

    def reflect(self, observation: Dict[str, Any]) -> None:
        # append to history
        self.memory.append_to_list(self.history_key, observation)

    def run_once(self, context: Dict[str, Any]) -> Any:
        actions = self.plan(context)
        results = []
        for action in actions:
            res = self.act(action)
            obs = self.observe(res)
            self.reflect(obs)
            results.append(res)
        return results


# small utility: build memory from env

def make_memory(backend: str = "redis") -> Memory:
    if backend == "redis":
        try:
            return RedisMemory()
        except Exception as e:
            logger.warning("RedisMemory construction failed, falling back to InMemoryMemory: %s", e)
            return InMemoryMemory()
    else:
        return InMemoryMemory()
