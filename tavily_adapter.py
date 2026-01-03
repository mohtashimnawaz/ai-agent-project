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


class TavilyError(Exception):
    pass


class TavilyClient(SearchTool):
    def __init__(self, api_key: Optional[str] = None, base_url: Optional[str] = None, timeout: int = 10):
        self.api_key = api_key or os.environ.get("TAVILY_API_KEY")
        self.base_url = base_url or os.environ.get("TAVILY_API_BASE") or "https://api.tavily.ai"
        self.timeout = timeout

        if not self.api_key:
            raise TavilyError("TAVILY_API_KEY not set. Set env var or pass api_key to TavilyClient.")

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

    def search(self, topic: str, limit: int = 10) -> List[Source]:
        if self._use_sdk and self._client is not None:
            # Attempt to call SDK's search; SDK APIs vary so try common names.
            try:
                if hasattr(self._client, "search"):
                    resp = self._client.search(topic, limit=limit)
                elif hasattr(self._client, "search_documents"):
                    resp = self._client.search_documents(topic, limit=limit)
                else:
                    raise TavilyError("Tavily SDK present but search method not detected. Please adapt TavilyClient to your SDK.")
                # Expect SDK response to be an iterable of dicts with 'title','url','snippet','published'
                return self._parse_results(resp)
            except Exception as e:
                raise TavilyError(f"Tavily SDK search failed: {e}")
        else:
            # Fallback to HTTP using requests to call a simple search endpoint.
            import requests

            url = f"{self.base_url.rstrip('/')}/search"
            headers = {"Authorization": f"Bearer {self.api_key}", "Accept": "application/json"}
            params = {"q": topic, "limit": limit}
            try:
                r = requests.get(url, headers=headers, params=params, timeout=self.timeout)
                r.raise_for_status()
                data = r.json()
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

            return self._parse_results(results)

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
