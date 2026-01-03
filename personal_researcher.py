"""PersonalResearcher agent: full flow from Tavily search to verified facts to LLM-assisted synthesis and saving.

Flow:
 - Use SeniorResearchAnalyst to collect and verify facts (cross-source verification)
 - Use LLMAdapter to write an executive summary and additional analysis
 - Use TechnicalContentWriter to assemble and save a final Markdown report

The implementation is conservative: only verified facts (from SeniorResearchAnalyst.verify_facts)
are provided to the writer. The LLM only receives the verified facts and a short instruction prompt.
"""
from __future__ import annotations
from typing import List, Optional
import logging
import datetime

from crewai_agents import SeniorResearchAnalyst, TechnicalContentWriter, VerifiedFact, Source
from llm_adapters import make_llm, LLMAdapter, MockLLMAdapter

logger = logging.getLogger(__name__)
logging.basicConfig(level=logging.INFO)


class PersonalResearcher:
    def __init__(self, search_tool, llm: Optional[LLMAdapter] = None, output_path: str = "research_report.md"):
        self.search_tool = search_tool
        self.analyst = SeniorResearchAnalyst(search_tool=search_tool)
        self.llm = llm or make_llm()
        self.writer = TechnicalContentWriter(output_path=output_path)
        self.output_path = output_path

    def _llm_summarize(self, topic: str, facts: List[VerifiedFact]) -> str:
        if facts is None or len(facts) == 0:
            return "No verified facts available to summarize."
        # Build a compact prompt describing the facts
        prompt = f"You are a concise technical researcher. Write a 3-paragraph executive summary for the topic '{topic}' based on the following verified facts:\n\n"
        for i, vf in enumerate(facts, start=1):
            prompt += f"Fact {i}: {vf.claim} (supported by {len(vf.supporting_sources)} sources).\n"
        prompt += "\nKeep it concise, factual, and cite that the claims were cross-verified by multiple sources."

        try:
            summary = self.llm.generate(prompt, max_tokens=400)
            return summary
        except Exception as e:
            logger.warning("LLM summarize failed: %s", e)
            # Fallback: simple summary
            return "Summary unavailable (LLM error)."

    def run(self, topic: str) -> str:
        logger.info("PersonalResearcher: running topic %s", topic)
        facts = self.analyst.run(topic)
        # Generate LLM summary
        try:
            summary = self._llm_summarize(topic, facts)
        except Exception as e:
            logger.warning("Error generating summary: %s", e)
            summary = ""

        # Create a structured report via writer
        md = self.writer.synthesize(topic, facts)
        # Insert summary under Executive Summary heading
        # naive insertion: find the Executive Summary header and replace its content until next header
        if "## Executive Summary" in md:
            parts = md.split("## Executive Summary\n\n")
            before = parts[0]
            rest = "## Executive Summary\n\n" + summary + "\n\n" + parts[1]
            md = before + rest
        else:
            md = f"# Research Report: {topic}\n\n" + "## Executive Summary\n\n" + summary + "\n\n" + md

        # add generation timestamp and LLM note
        md += f"\n\n---\n_Report generated on {datetime.date.today().isoformat()} with LLM-assisted summary._\n"

        self.writer.save(md)
        return md


if __name__ == "__main__":
    # demonstration with mock if run directly
    from crewai_agents import MockTavilyClient
    from llm_adapters import MockLLMAdapter

    client = MockTavilyClient()
    llm = MockLLMAdapter()
    pr = PersonalResearcher(search_tool=client, llm=llm, output_path="research_report.md")
    pr.run("Artificial Intelligence")
    print("Report written to research_report.md")
