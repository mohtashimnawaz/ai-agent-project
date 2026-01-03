import os
from agents_core import Agent, ToolRegistry, InMemoryMemory
from llm_adapters import MockLLMAdapter


class DummySearch:
    def run(self, q, limit=5):
        return [{"title":"T1","url":"u","snippet":"This is about X","published":"2023-01-01"}]


class SimpleResearcher(Agent):
    def plan(self, context):
        return [{"tool":"search","args":[context.get('topic')], "kwargs": {"limit": 5}}]

    def observe(self, result):
        # return the first snippet
        data = result[0]
        return {"claim": data.get("snippet")}


def test_agent_flow():
    tools = ToolRegistry()
    tools.register("search", DummySearch())
    memory = InMemoryMemory()
    agent = SimpleResearcher("test", tools, memory=memory)
    res = agent.run_once({"topic":"X"})
    assert memory.get_list(agent.history_key)
    assert isinstance(res, list)
