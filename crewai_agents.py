"""crewai_agents.py

Two-agent team for research -> writing workflow.

- SeniorResearchAnalyst: uses a SearchTool (Tavily-compatible) to find top sources and verifies facts across sources.
- TechnicalContentWriter: synthesizes verified facts into a Markdown report and saves to disk.

Design goals:
- Sequential flow: analyst -> writer
- Researcher passes *only* verified facts (cross-source verified) to writer
- Easy to plug in a real Tavily client or use the included MockTavilyClient for testing
"""
from __future__ import annotations
from dataclasses import dataclass, asdict
from typing import List, Protocol, Optional, Dict, Tuple
import re
import datetime
import json
import logging

from crewai_agents_helpers import extract_entities

logger = logging.getLogger(__name__)
logging.basicConfig(level=logging.INFO)

# --- Models ---

@dataclass
class Source:
    title: str
    url: str
    snippet: str
    published: Optional[str] = None  # ISO date or free-form
    metadata: Optional[Dict] = None

@dataclass
class VerifiedFact:
    claim: str
    supporting_sources: List[Source]

# --- SearchTool protocol (Tavily interface adapter) ---

class SearchTool(Protocol):
    def search(self, topic: str, limit: int = 10) -> List[Source]:
        """Return a list of Source objects for the given topic."""
        ...

# --- Mock Tavily client for testing/demo ---

class MockTavilyClient:
    """A simple mock search client that returns synthetic sources for a topic.

    Replace or subclass with a real Tavily client implementing search(topic, limit).
    """

    def search(self, topic: str, limit: int = 10) -> List[Source]:
        sample_snippets = [
            f"{topic} is primarily defined as an evolving area with multiple approaches.",
            f"Recent research on {topic} highlights three main trends: efficiency, scalability, and privacy.",
            f"Experts in {topic} recommend combining methods A and B for better results.",
            f"A 2023 survey on {topic} found that 70% of practitioners adopt hybrid techniques.",
            f"A study concluded that method X outperforms method Y on benchmarks for {topic}.",
        ]
        sources: List[Source] = []
        for i in range(limit):
            s = Source(
                title=f"{topic} - Article {i+1}",
                url=f"https://example.com/{topic.replace(' ', '_')}/{i+1}",
                snippet=sample_snippets[i % len(sample_snippets)],
                published=(datetime.date(2022 + (i % 3), 1, 1).isoformat()),
                metadata={"rank": i + 1},
            )
            sources.append(s)
        return sources

# --- SeniorResearchAnalyst ---

class SeniorResearchAnalyst:
    """Searches for sources and verifies facts before passing to writer.

    Verification approach (simple, conservative):
    - Extract candidate claims (simple sentence extraction from snippets)
    - Normalize claims and count occurrences across sources
    - Keep claims that appear in at least two distinct sources (cross-source verification)
    - Attach supporting sources

    This ensures the writer consumes only verified facts.
    """

    def __init__(self, search_tool: SearchTool, search_limit: int = 20, top_k: int = 10):
        self.search_tool = search_tool
        self.search_limit = search_limit
        self.top_k = top_k

    def search_and_collect(self, topic: str) -> List[Source]:
        logger.info("Searching for sources on topic: %s", topic)
        sources = self.search_tool.search(topic, limit=self.search_limit)
        # simple ranking: keep top_k
        selected = sources[: self.top_k]
        logger.info("Collected %d sources", len(selected))
        return selected

    @staticmethod
    def _sentences_from_text(text: str) -> List[str]:
        # naive sentence split
        sentences = re.split(r"(?<=[.!?])\s+", text.strip())
        # filter tiny sentences
        return [s.strip() for s in sentences if len(s.strip()) >= 20]

    @staticmethod
    def _normalize_claim(s: str) -> str:
        s2 = s.lower()
        s2 = re.sub(r"\s+", " ", s2)
        s2 = re.sub(r"[^a-z0-9 .,]", "", s2)
        s2 = s2.strip()
        return s2

    def verify_facts(self, sources: List[Source], min_support: int = 2, fuzzy_threshold: int = 80, ner_required: bool = False) -> List[VerifiedFact]:
        # extract candidate sentences from each source
        claim_map: Dict[str, List[Source]] = {}
        for src in sources:
            text = src.snippet or ""
            sents = self._sentences_from_text(text)
            for s in sents:
                norm = self._normalize_claim(s)
                if len(norm) < 40:  # skip short, low-content
                    continue
                claim_map.setdefault(norm, [])
                # add source only once per claim
                if not any(existing.url == src.url for existing in claim_map[norm]):
                    claim_map[norm].append(src)

        # Merge similar claims using fuzzy matching to allow minor variations
        claims = list(claim_map.keys())
        clusters: List[Dict] = []  # list of {rep: claim, members: [claim], sources: set()}

        try:
            from rapidfuzz import fuzz
            _have_fuzzy = True
        except Exception:
            fuzz = None
            _have_fuzzy = False

        for c in claims:
            placed = False
            for cl in clusters:
                rep = cl["rep"]
                sim = 0
                if _have_fuzzy:
                    sim = fuzz.token_sort_ratio(c, rep)
                else:
                    # fallback to substring match
                    sim = 100 if (c in rep or rep in c) else 0
                if sim >= fuzzy_threshold:
                    cl["members"].append(c)
                    for src in claim_map[c]:
                        cl["sources"].add(src.url)
                    placed = True
                    break
            if not placed:
                cl = {"rep": c, "members": [c], "sources": set([s.url for s in claim_map[c]])}
                clusters.append(cl)

        # collect claims with enough supporting sources (after merging)
        verified: List[VerifiedFact] = []

        # extract_entities is imported at module top from crewai_agents_helpers

        for cl in clusters:
            src_urls = cl["sources"]
            # gather Source objects from original map for these URLs
            supporting_srcs: List[Source] = []
            seen = set()
            for member in cl["members"]:
                for s in claim_map[member]:
                    if s.url in seen:
                        continue
                    supporting_srcs.append(s)
                    seen.add(s.url)

            if len(supporting_srcs) >= min_support:
                # if ner_required, ensure at least one overlapping entity across supporting sources
                if ner_required:
                    entity_sets = [extract_entities(s.snippet or "") for s in supporting_srcs]
                    if not entity_sets:
                        continue
                    # intersect entities across sources; require at least one in common
                    inter = set.intersection(*[es for es in entity_sets if es]) if entity_sets else set()
                    if not inter:
                        continue
                # pick representative claim text as the longest member (heuristic)
                rep_claim = max(cl["members"], key=lambda x: len(x))
                verified.append(VerifiedFact(claim=rep_claim, supporting_sources=supporting_srcs))

        # sort by number of supporting sources desc
        verified.sort(key=lambda vf: len(vf.supporting_sources), reverse=True)
        logger.info("Verified %d facts", len(verified))
        return verified

    def run(self, topic: str) -> List[VerifiedFact]:
        sources = self.search_and_collect(topic)
        verified = self.verify_facts(sources)
        return verified

# --- TechnicalContentWriter ---

class TechnicalContentWriter:
    """Synthesize verified facts into a structured Markdown report and save it."""

    def __init__(self, output_path: str = "research_report.md"):
        self.output_path = output_path

    def synthesize(self, topic: str, facts: List[VerifiedFact]) -> str:
        header = f"# Research Report: {topic}\n"
        meta = f"_Generated on {datetime.date.today().isoformat()}_\n\n"
        summary = "## Executive Summary\n\n"
        if facts:
            summary += f"This report synthesizes {len(facts)} cross-verified facts about **{topic}**. Each fact is supported by multiple sources.\n\n"
        else:
            summary += "No verified facts were found for this topic with current search parameters.\n\n"

        body = "## Key Verified Facts\n\n"
        for i, vf in enumerate(facts, start=1):
            body += f"### Fact {i}\n\n"
            body += f"- **Claim:** {vf.claim}\n"
            body += f"- **Supported by:**\n"
            for src in vf.supporting_sources:
                published = f" ({src.published})" if src.published else ""
                body += f"  - [{src.title}]({src.url}){published}\n"
            body += "\n"

        sources_section = "## All Sources (top)\n\n"
        # list unique sources
        seen_urls = set()
        for vf in facts:
            for src in vf.supporting_sources:
                if src.url in seen_urls:
                    continue
                seen_urls.add(src.url)
                sources_section += f"- [{src.title}]({src.url}) - snippet: {src.snippet}\n"

        md = header + meta + summary + body + sources_section
        return md

    def save(self, md_text: str) -> None:
        with open(self.output_path, "w", encoding="utf-8") as f:
            f.write(md_text)
        logger.info("Saved report to %s", self.output_path)

# --- Helper utility for sequential orchestration (example usage) ---

def run_sequential_team(topic: str, output_path: str = "research_report.md", use_mock: bool = True, search_tool: Optional[SearchTool] = None) -> Tuple[str, List[VerifiedFact]]:
    """Run the two-agent team sequentially and write the report.

    - If `search_tool` is provided it will be used directly.
    - If `use_mock` is True a `MockTavilyClient` will be used.
    - Otherwise the function will attempt to construct a `TavilyClient` from env vars.

    Returns the markdown string and the list of verified facts.
    """
    if search_tool is None:
        if use_mock:
            search_tool = MockTavilyClient()
        else:
            # lazy import to avoid hard dependency when using mock
            try:
                from tavily_adapter import TavilyClient
            except Exception as e:
                raise ValueError("TavilyClient not available; ensure tavily_adapter.py exists and dependencies are installed") from e

            # construct from env vars (TAVILY_API_KEY required)
            search_tool = TavilyClient()

    analyst = SeniorResearchAnalyst(search_tool=search_tool)
    writer = TechnicalContentWriter(output_path=output_path)

    # Optionally wire memory and LLM via tools for a future Agent-based flow
    try:
        from llm_adapters import make_llm
        from agents_core import make_memory
        llm = make_llm()
        memory = make_memory()
        # register tools for future agent flows (keeps backwards compatibility)
        tools = ToolRegistry()
        tools.register("search", search_tool)
        tools.register("llm", type("LLMTool", (), {"run": lambda self, prompt, **kwargs: llm.generate(prompt, **kwargs)})())
    except Exception:
        tools = None
        memory = None

    verified_facts = analyst.run(topic)
    md = writer.synthesize(topic, verified_facts)
    writer.save(md)
    return md, verified_facts

if __name__ == "__main__":
    # quick demonstration
    md, facts = run_sequential_team("Artificial Intelligence", output_path="research_report.md", use_mock=True)
    print(f"Generated {len(facts)} verified facts. Report written to research_report.md")
