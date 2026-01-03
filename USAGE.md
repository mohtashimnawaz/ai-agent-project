CrewAI two-agent example

Overview
- SeniorResearchAnalyst: finds sources (Tavily-compatible) and verifies claims by cross-source agreement.
- TechnicalContentWriter: generates a Markdown report from verified facts and saves it to `research_report.md`.

Quickstart (mock):

1. Run with mocked Tavily search:

    python run_team.py --topic "Your topic here"

2. The script will produce `research_report.md` in the working directory.

Plugging in a real Tavily client
- The project includes `tavily_adapter.TavilyClient` which implements the `SearchTool` protocol used by `SeniorResearchAnalyst`.

Environment variables (for `TavilyClient`):
- `TAVILY_API_KEY` (required): your Tavily API key/token
- `TAVILY_API_BASE` (optional): base URL for the Tavily API (defaults to https://api.tavily.ai)

Quick example (real client):

    export TAVILY_API_KEY=your_real_key
    python run_team.py --topic "Your topic here" --no-mock

Running tests
- Install pytest (e.g., `pip install pytest`) and run `pytest -q` to execute the unit tests (adapter and end-to-end mock tests).

Notes on verification
- The researcher performs conservative verification: claims must appear (by normalized sentence match) in at least two sources to be considered verified.
- You can adjust behavior by changing `min_support` in `SeniorResearchAnalyst.verify_facts`.
