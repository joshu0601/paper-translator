from app.services.translation import MockTranslationProvider, extract_term_candidates


def test_extract_term_candidates_uses_acronym_initials():
    text = (
        "This paper studies offloading in multiaccess edge computing (MEC). We model it as a "
        "Multi-Objective Markov Decision Process (MOMDP) and use deep reinforcement learning (DRL) "
        "with Proximal Policy Optimization (PPO) [8]. Mobile devices (MDs) are considered."
    )
    terms = extract_term_candidates(text)
    assert "multiaccess edge computing" in terms
    assert "Multi-Objective Markov Decision Process" in terms
    assert "deep reinforcement learning" in terms
    assert "Proximal Policy Optimization" in terms
    assert "Mobile devices" in terms
    assert not any(t.lower().startswith(("in ", "as a ", "with ")) for t in terms)


def test_mock_translation_keeps_original_casing():
    out = MockTranslationProvider().translate_batch(["We reduce latency and low-latency cost."], {"Latency": "延遲"})
    assert out[0].startswith("〔模擬翻譯〕")
    assert "latency（延遲）" in out[0]
    assert "Latency（延遲）" not in out[0]
