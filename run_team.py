"""CLI orchestrator for the two-agent team (sequential).

Usage:
    python run_team.py --topic "Your topic here" [--output research_report.md] [--no-mock]
"""
import argparse
from crewai_agents import run_sequential_team


def main():
    p = argparse.ArgumentParser(description="Run a two-agent research -> writer team (sequential)")
    p.add_argument("--topic", required=True, help="Research topic; put in quotes if multi-word")
    p.add_argument("--output", default="research_report.md", help="Output markdown file path")
    p.add_argument(
        "--no-mock",
        dest="use_mock",
        action="store_false",
        help="Use a real Tavily client instead of the mock (requires TAVILY_API_KEY env var)",
    )
    p.add_argument("--llm", default=None, choices=["gpt4o", "claude", "mock"], help="LLM provider to use (overrides LLM_PROVIDER env var)")
    p.add_argument("--memory", default="redis", choices=["redis", "inmemory"], help="Memory backend (redis or inmemory)")
    args = p.parse_args()

    try:
        # construct memory and pass down
        from agents_core import make_memory
        memory = make_memory(backend=args.memory)

        if args.agent == "personal_researcher":
            # run the agent flow
            from tavily_adapter import TavilyClient
            from personal_researcher import PersonalResearcher
            from llm_adapters import make_llm

            if args.use_mock:
                from crewai_agents import MockTavilyClient
                search_tool = MockTavilyClient()
            else:
                search_tool = TavilyClient()

            llm = make_llm(provider=args.llm) if args.llm else make_llm()
            agent = PersonalResearcher(search_tool=search_tool, llm=llm, output_path=args.output)
            md = agent.run(args.topic)
            facts = []
            print(f"PersonalResearcher completed. Report saved to {args.output}")
        else:
            md, facts = run_sequential_team(topic=args.topic, output_path=args.output, use_mock=args.use_mock)

        print(f"Completed. Verified facts: {len(facts)}. Report saved to {args.output}")
    except Exception as e:
        print("Error running team:", e)
        raise


if __name__ == "__main__":
    main()
