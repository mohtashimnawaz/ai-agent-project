import os
from crewai_agents import SeniorResearchAnalyst, MockTavilyClient, TechnicalContentWriter, run_sequential_team


def test_analyst_verifies_facts():
    client = MockTavilyClient()
    analyst = SeniorResearchAnalyst(search_tool=client, search_limit=6, top_k=6)
    verified = analyst.run("Test Topic")
    # With the mock, there are repeated sample sentences across sources, so expect at least one verified fact
    assert isinstance(verified, list)
    assert len(verified) >= 1


def test_writer_saves_report(tmp_path):
    out = tmp_path / "out_report.md"
    writer = TechnicalContentWriter(output_path=str(out))
    # small synthetic fact
    class S:
        def __init__(self):
            self.title = "T1"
            self.url = "https://example.com"
            self.snippet = "Test snippet about a claim that is long enough to pass filters."
            self.published = None
    rf = [
        type("VF", (), {"claim": "test claim about topic", "supporting_sources": [S(), S()]})
    ]
    md = writer.synthesize("Test Topic", rf)
    writer.save(md)
    assert out.exists()
    text = out.read_text()
    assert "test claim about topic" in text


def test_end_to_end_creates_file(tmp_path):
    out = tmp_path / "report.md"
    md, facts = run_sequential_team(topic="Integration Topic", output_path=str(out), use_mock=True)
    assert out.exists()
    assert isinstance(facts, list)
    assert md.startswith("# Research Report")
