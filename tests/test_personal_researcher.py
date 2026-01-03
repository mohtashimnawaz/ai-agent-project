import tempfile
import os
from personal_researcher import PersonalResearcher
from crewai_agents import Source


class FakeSearch:
    def search(self, topic, limit=10):
        return [
            Source(title="A", url="u1", snippet=f"{topic} is evolving rapidly with trend X.", published="2023-01-01"),
            Source(title="B", url="u2", snippet=f"Recent {topic} work highlights trend X and Y.", published="2023-01-02"),
            Source(title="C", url="u3", snippet=f"Other commentary on {topic}.", published="2021-01-01"),
        ]


class FakeLLM:
    def generate(self, prompt, **kwargs):
        return "This is an LLM-generated executive summary."


def test_personal_researcher_end_to_end(tmp_path):
    out = tmp_path / "pr_report.md"
    search = FakeSearch()
    llm = FakeLLM()
    agent = PersonalResearcher(search_tool=search, llm=llm, output_path=str(out))
    md = agent.run("Test Topic")
    assert out.exists()
    text = out.read_text()
    assert "executive summary" in text.lower() or "executive" in text.lower()
    assert "Key Verified Facts" in text
