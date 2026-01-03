# AI Agent Project

Two-agent example: a Senior Research Analyst (search + verify) and a Technical Content Writer (synthesizes verified facts into Markdown).

Tavily integration
- The project includes `tavily_adapter.TavilyClient` which will be used when running with `--no-mock`.
- Configure the client with `TAVILY_API_KEY` (required) and optionally `TAVILY_API_BASE`.

Run (mock):

    python run_team.py --topic "Quantum Computing"

Run (real Tavily):

    export TAVILY_API_KEY=your_real_key
    python run_team.py --topic "Quantum Computing" --no-mock

See `USAGE.md` for more details.