import pytest
from crewai_agents import SeniorResearchAnalyst, Source


def fake_nlp_entities_mapping(text):
    # simplistic fake: return 'quantum computing' if seen
    t = text.lower()
    entities = set()
    if "quantum computing" in t:
        entities.add("quantum computing")
    if "ai" in t:
        entities.add("ai")
    return entities


def test_ner_allows_merge_with_shared_entity(monkeypatch):
    # Two snippets that share 'Quantum Computing' entity
    s1 = Source(title="A", url="u1", snippet="Quantum Computing is evolving.")
    s2 = Source(title="B", url="u2", snippet="Recent Quantum Computing research shows progress.")

    # monkeypatch the extract_entities function used in verify_facts via module-level helper
    monkeypatch.setattr("crewai_agents.SeniorResearchAnalyst._normalize_claim", lambda self, x: x.lower())

    # monkeypatch spacy loading path by injecting our fake function
    monkeypatch.setattr("crewai_agents.extract_entities", lambda text: fake_nlp_entities_mapping(text), raising=False)

    analyst = SeniorResearchAnalyst(search_tool=None)
    verified = analyst.verify_facts([s1, s2], min_support=2, ner_required=True)
    assert len(verified) >= 1


def test_ner_prevents_merge_when_no_shared_entity(monkeypatch):
    s1 = Source(title="A", url="u1", snippet="Method X outperforms method Y.")
    s2 = Source(title="B", url="u2", snippet="A survey found that most people prefer method Z.")

    monkeypatch.setattr("crewai_agents.SeniorResearchAnalyst._normalize_claim", lambda self, x: x.lower())
    monkeypatch.setattr("crewai_agents.extract_entities", lambda text: set(), raising=False)

    analyst = SeniorResearchAnalyst(search_tool=None)
    verified = analyst.verify_facts([s1, s2], min_support=2, ner_required=True)
    assert len(verified) == 0
