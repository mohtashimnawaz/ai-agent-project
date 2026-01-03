"""Tavily client adapter implementing the `SearchTool` protocol used by the researcher.

This adapter tries to use the official `tavily` SDK if installed, otherwise falls back to a simple
HTTP-based implementation using `requests`.

Configuration (recommended via environment variables):
- TAVILY_API_KEY: API key/token for Tavily (required for real requests)
- TAVILY_API_BASE: Base URL for Tavily API (optional; adapter defaults to a common base)

To use with the orchestration CLI, run:
    TAVILY_API_KEY=your_key python run_team.py --topic "..." --no-mock

NOTE: The exact fields returned by Tavily may differ; adjust parsing in `search` if needed.
"""
from __future__ import annotations
import os
from typing import List, Optional
import logging

from crewai_agents import Source, SearchTool

logger = logging.getLogger(__name__)

# Try to import the SDK if available
try:
    import tavily  # type: ignore
    _HAS_SDK = True
except Exception:
    tavily = None  # type: ignore
    _HAS_SDK = False

# Import requests at module level so tests can monkeypatch `tavily_adapter.requests` directly
try:
    import requests
except Exception:
    requests = None

# Import redis at module level so tests can monkeypatch `tavily_adapter.redis` directly
try:
    import redis
except Exception:
    redis = None


class TavilyError(Exception):
    pass


class TavilyClient(SearchTool):
    def __init__(
        self,
        api_key: Optional[str] = None,
        base_url: Optional[str] = None,
        timeout: int = 10,
        cache_ttl: int = 300,
        max_retries: int = 3,
        backoff_factor: float = 0.5,
        redis_cache_url: Optional[str] = None,
    ):
        self.api_key = api_key or os.environ.get("TAVILY_API_KEY")
        self.base_url = base_url or os.environ.get("TAVILY_API_BASE") or "https://api.tavily.ai"
        self.timeout = timeout
        self.cache_ttl = int(os.environ.get("TAVILY_CACHE_TTL", str(cache_ttl)))
        self.max_retries = int(os.environ.get("TAVILY_MAX_RETRIES", str(max_retries)))
        self.backoff_factor = float(os.environ.get("TAVILY_BACKOFF_FACTOR", str(backoff_factor)))
        # Redis cache URL may be passed explicitly or via env
        self.redis_cache_url = redis_cache_url or os.environ.get("TAVILY_REDIS_CACHE_URL")

        if not self.api_key:
            # Don't raise at construction time; allow tests and local flows to instantiate without a key.
            logger.warning("TAVILY_API_KEY not set. Requests may fail without an API key.")

        # If redis cache URL provided, try to instantiate a redis client for shared caching
        self._redis_cache = None
        if self.redis_cache_url:
            if redis is None:
                logger.warning("redis package not available; redis cache disabled")
            else:
                try:
                    self._redis_cache = redis.from_url(self.redis_cache_url, decode_responses=True)
                except Exception as e:
                    logger.warning("Failed to connect to redis cache, disabling redis cache: %s", e)

        # SDK detection
        if _HAS_SDK:
            try:
                # Try to instantiate the SDK client. The exact SDK constructor may vary; adapt if needed.
                self._client = tavily.Client(api_key=self.api_key, base_url=self.base_url)
                self._use_sdk = True
            except Exception as e:
                logger.warning("Failed to instantiate tavily SDK client; falling back to HTTP: %s", e)
                self._client = None
                self._use_sdk = False
        else:
            self._client = None
            self._use_sdk = False

        # HTTP session with retries/backoff
        try:
            # use module-level `requests` when available
            if requests is None:
                raise RuntimeError("requests package not available")
            from requests.adapters import HTTPAdapter
            from urllib3.util import Retry

            self._session = requests.Session()
            retry_strategy = Retry(
                total=self.max_retries,
                backoff_factor=self.backoff_factor,
                status_forcelist=[429, 500, 502, 503, 504],
                allowed_methods=["GET", "POST"],
                raise_on_status=False,
            )
            adapter = HTTPAdapter(max_retries=retry_strategy)
            self._session.mount("https://", adapter)
            self._session.mount("http://", adapter)
        except Exception as e:
            logger.warning("requests/Retry not available; HTTP retries disabled: %s", e)
            self._session = None

        # Simple in-memory cache: {cache_key: (timestamp, results)}
        self._cache: dict = {}
        # Simple cache metrics
        self._cache_hits = 0
        self._cache_misses = 0

    def get_cache_metrics(self):
        return {"hits": self._cache_hits, "misses": self._cache_misses}

    def _cache_key(self, topic: str, limit: int) -> str:
        return f"tavily:{topic}:{limit}"

    def _get_cached(self, key: str):
        # Try Redis shared cache first if available
        if self._redis_cache is not None:
            try:
                v = self._redis_cache.get(key)
                if v is None:
                    self._cache_misses += 1
                    return None
                import json

                loaded = json.loads(v)
                # Convert back to Source objects if possible
                out = []
                for item in loaded:
                    if isinstance(item, dict) and "title" in item and "url" in item:
                        out.append(Source(**item))
                    else:
                        out.append(item)
                self._cache_hits += 1
                return out
            except Exception as e:
                logger.warning("Redis cache get failed, falling back to local cache: %s", e)
                self._cache_misses += 1

        entry = self._cache.get(key)
        if not entry:
            self._cache_misses += 1
            return None
        ts, value = entry
        import time

        if (time.time() - ts) > self.cache_ttl:
            # expired
            del self._cache[key]
            self._cache_misses += 1
            return None
        self._cache_hits += 1
        return value

    def _set_cache(self, key: str, value):
        # Try Redis shared cache first if available
        if self._redis_cache is not None:
            try:
                import json
                # Convert Source objects to serializable dicts
                serializable = []
                for item in value:
                    if hasattr(item, "__dict__") or hasattr(item, "__dataclass_fields__"):
                        # convert dataclass-like objects
                        try:
                            serializable.append(item.__dict__)
                        except Exception:
                            # fallback to asdict if dataclass
                            from dataclasses import asdict

                            try:
                                serializable.append(asdict(item))
                            except Exception:
                                serializable.append(str(item))
                    else:
                        serializable.append(item)

                self._redis_cache.setex(key, int(self.cache_ttl), json.dumps(serializable))
                return
            except Exception as e:
                logger.warning("Redis cache set failed, falling back to local cache: %s", e)

        import time

        self._cache[key] = (time.time(), value)
    def search(self, topic: str, limit: int = 10) -> List[Source]:
        cache_k = self._cache_key(topic, limit)
        cached = self._get_cached(cache_k)
        if cached is not None:
            logger.debug("TavilyClient: returning cached results for %s", topic)
            return cached

        # Try SDK path first
        if self._use_sdk and self._client is not None:
            try:
                # SDK APIs vary so try common names.
                if hasattr(self._client, "search"):
                    resp = self._client.search(topic, limit=limit)
                elif hasattr(self._client, "search_documents"):
                    resp = self._client.search_documents(topic, limit=limit)
                else:
                    raise TavilyError("Tavily SDK present but search method not detected. Please adapt TavilyClient to your SDK.")
                results = self._parse_results(resp)
                self._set_cache(cache_k, results)
                return results
            except Exception as e:
                logger.warning("Tavily SDK search failed; falling back to HTTP: %s", e)
                # continue to HTTP fallback

        # HTTP fallback
        try:
            import requests
        except Exception:
            raise TavilyError("requests package is required for HTTP fallback")

        url = f"{self.base_url.rstrip('/')}/search"
        headers = {"Authorization": f"Bearer {self.api_key}", "Accept": "application/json"}
        params = {"q": topic, "limit": limit}

        try:
            # Prefer module-level requests.get so tests can monkeypatch it; fall back to session if absent
            if requests is not None:
                # Use simple retry loop calling module-level requests.get so tests can control behavior
                import time
                last_exc = None
                attempts = max(1, self.max_retries + 1)
                for attempt in range(attempts):
                    try:
                        r = requests.get(url, headers=headers, params=params, timeout=self.timeout)
                        # If we got a response object, break
                        break
                    except Exception as e:
                        last_exc = e
                        # backoff (only sleep if backoff_factor > 0)
                        if self.backoff_factor and attempt < attempts - 1:
                            time.sleep(self.backoff_factor * (2 ** attempt))
                        continue
                else:
                    # all attempts exhausted
                    raise TavilyError(f"HTTP search failed after retries: {last_exc}")
            elif self._session is not None:
                r = self._session.get(url, headers=headers, params=params, timeout=self.timeout)
            else:
                raise TavilyError("requests package required for HTTP fallback")

            # If status code indicates error, try to provide helpful message
            if getattr(r, "status_code", 200) >= 400:
                raise TavilyError(f"Tavily HTTP error: {getattr(r, 'status_code', 'unknown')} - {getattr(r, 'text', '')}")
            data = r.json()
        except TavilyError:
            raise
        except Exception as e:
            raise TavilyError(f"HTTP search failed: {e}")

        # Expect `data` to contain a `results` list; adapt if the real API differs
        results = data.get("results") if isinstance(data, dict) else None
        if results is None:
            # Try to interpret top-level list
            if isinstance(data, list):
                results = data
            else:
                raise TavilyError("Unexpected search response format from Tavily API (no 'results' list)")

        parsed = self._parse_results(results)
        self._set_cache(cache_k, parsed)
        return parsed

    @staticmethod
    def _parse_results(results) -> List[Source]:
        out: List[Source] = []
        for item in results[:]:
            if not isinstance(item, dict):
                continue
            title = item.get("title") or item.get("headline") or item.get("name") or "Untitled"
            url = item.get("url") or item.get("link") or item.get("uri")
            snippet = item.get("snippet") or item.get("summary") or item.get("excerpt") or ""
            published = item.get("published") or item.get("published_at") or item.get("date")
            out.append(Source(title=title, url=url, snippet=snippet, published=published, metadata=item))
        return out
