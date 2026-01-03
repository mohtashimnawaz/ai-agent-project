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
    p.add_argument("--no-mock", dest="use_mock", action="store_false", help="Use a real Tavily client instead of the mock (not implemented)" )
    args = p.parse_args()

    md, facts = run_sequential_team(topic=args.topic, output_path=args.output, use_mock=args.use_mock)
    print(f"Completed. Verified facts: {len(facts)}. Report saved to {args.output}")


if __name__ == "__main__":
    main()
