CrewAI two-agent example

Overview
- SeniorResearchAnalyst: finds sources (Tavily-compatible) and verifies claims by cross-source agreement.
- TechnicalContentWriter: generates a Markdown report from verified facts and saves it to `research_report.md`.

Quickstart (mock):

1. Run with mocked Tavily search:

    python run_team.py --topic "Your topic here"

2. The script will produce `research_report.md` in the working directory.

Plugging in a real Tavily client
- Implement a class with a `search(topic: str, limit: int) -> List[Source]` method (see `crewai_agents.Source`) and pass that to `SeniorResearchAnalyst`.
- Replace `MockTavilyClient()` used in `run_sequential_team` with your real client.

Notes on verification
- The researcher performs conservative verification: claims must appear (by normalized sentence match) in at least two sources to be considered verified.
- You can adjust behavior by changing `min_support` in `SeniorResearchAnalyst.verify_facts`.
