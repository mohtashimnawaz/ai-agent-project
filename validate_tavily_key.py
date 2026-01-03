"""Utility to validate a Tavily API key by performing a safe, non-destructive search."""
from tavily_adapter import TavilyClient, TavilyError


def validate_key():
    try:
        client = TavilyClient()
        results = client.search("test", limit=1)
        print("Success: returned", len(results), "results")
    except TavilyError as e:
        print("Tavily validation failed:", e)
    except Exception as e:
        print("Unexpected error:", e)


if __name__ == "__main__":
    validate_key()
