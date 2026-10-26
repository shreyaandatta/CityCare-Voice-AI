"""Run with:  python -m pytest fuzzy_triage   (or just: python test_triage.py)"""
from fuzzy_triage import triage_call, extract_features
from samples import SAMPLES


def test_sample_labels():
    for name, text, expected in SAMPLES:
        assert triage_call(text)["triage_label"] == expected, name


def test_negation_is_ignored():
    sev = extract_features("no fever and no chest pain")[0]
    assert sev == 0


def test_longest_phrase_wins():
    # 'chest pain' (6) must not also add 'pain' (2)
    assert extract_features("chest pain")[0] == 6


def test_age_raises_vulnerability():
    assert extract_features("my grandfather is 80 years old")[2] >= 8


if __name__ == "__main__":
    for f in [test_sample_labels, test_negation_is_ignored, test_longest_phrase_wins, test_age_raises_vulnerability]:
        f(); print("PASS", f.__name__)
