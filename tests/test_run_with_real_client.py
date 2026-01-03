import pytest
from crewai_agents import run_sequential_team


def test_run_requires_api_key(monkeypatch):
    monkeypatch.delenv("TAVILY_API_KEY", raising=False)
    with pytest.raises(Exception):
        run_sequential_team(topic="Anything", use_mock=False)
