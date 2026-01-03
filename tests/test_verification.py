from crewai_agents import SeniorResearchAnalyst, Source


def test_fuzzy_merge_verification():
    # two sources with slightly different phrasing should merge into one verified fact
    s1 = Source(title="A", url="u1", snippet="A 2023 survey on topic found that 70% of practitioners adopt hybrid techniques.")
    s2 = Source(title="B", url="u2", snippet="A 2023 survey on topic found that 70 of practitioners adopt hybrid techniques.")

    analyst = SeniorResearchAnalyst(search_tool=None)
    verified = analyst.verify_facts([s1, s2], min_support=2)
    assert len(verified) >= 1
    # representative claim should include '70' or '70%'
    rep = verified[0].claim
    assert "70" in rep


def test_no_merge_when_different():
    s1 = Source(title="A", url="u1", snippet="Method X outperforms method Y on benchmarks.")
    s2 = Source(title="B", url="u2", snippet="A survey found that most people prefer method Z.")
    analyst = SeniorResearchAnalyst(search_tool=None)
    v = analyst.verify_facts([s1, s2], min_support=2)
    assert len(v) == 0
