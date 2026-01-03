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
    # Two very similar snippets that will merge via fuzzy matching
    # Both mention "quantum computing" so they share an entity
    s1 = Source(title="A", url="u1", snippet="Quantum computing is a revolutionary technology.")
    s2 = Source(title="B", url="u2", snippet="Quantum computing is a revolutionary technology.")

    # monkeypatch the extract_entities function
    import crewai_agents_helpers
    monkeypatch.setattr(crewai_agents_helpers, "extract_entities", fake_nlp_entities_mapping)
    
    analyst = SeniorResearchAnalyst(search_tool=None)
    verified = analyst.verify_facts([s1, s2], min_support=2, ner_required=True)
    # With two sources supporting the same claim and shared entity, should have 1 verified fact
    assert len(verified) >= 1


def test_ner_prevents_merge_when_no_shared_entity(monkeypatch):
    # Make snippets long enough to pass normalization filter
    s1 = Source(title="A", url="u1", snippet="Method X outperforms method Y in comprehensive benchmarks across multiple datasets.")
    s2 = Source(title="B", url="u2", snippet="A recent survey found that most people prefer method Z for production workloads.")

    import crewai_agents_helpers
    monkeypatch.setattr(crewai_agents_helpers, "extract_entities", lambda text: set())

    analyst = SeniorResearchAnalyst(search_tool=None)
    verified = analyst.verify_facts([s1, s2], min_support=2, ner_required=True)
    assert len(verified) == 0
