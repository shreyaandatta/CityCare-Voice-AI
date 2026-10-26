"""
Fuzzy triage for CityCare Hospital's voice AI receptionist.

Reads a call transcript, turns it into four crisp numbers, and uses a
Mamdani fuzzy inference system to decide how urgent the call is.

Inputs:
  severity       0-10  how dangerous the symptoms sound
  distress       0-10  how panicked the caller is
  vulnerability  0-10  how at-risk the patient is (age, pregnancy, chronic illness)
  delay          0-30  days until the visit the caller asked for

Output:
  triage_score   0-100 -> Routine (<40), Urgent (40-70), Emergency (>70)
"""
import json
import re
from pathlib import Path

import numpy as np
import skfuzzy as fuzz
from skfuzzy import control as ctrl

LEX = json.loads((Path(__file__).parent / "lexicon.json").read_text())
NEGATION = re.compile(r"\b(no|not|without|nahi|nahin)\b[\w\s']{0,15}$")

# ---------- 1. Feature extraction ----------


def keyword_score(text, table):
    """Sum keyword weights. Longest phrases match first and are consumed,
    so 'chest pain' is not also counted as 'pain'. Negated mentions
    ('no fever') are skipped."""
    total = 0
    for key in sorted(table, key=len, reverse=True):
        pattern = re.compile(r"\b" + re.escape(key) + r"\b")
        while True:
            m = pattern.search(text)
            if not m:
                break
            if not NEGATION.search(text[:m.start()]):
                total += table[key]
            text = text[:m.start()] + " " * len(key) + text[m.end():]
    return total


def age_points(text, age=None):
    if age is None:
        m = re.search(r"(\d{1,3})\s*(?:years?|yrs?|saal)\b|\bage(?:d)?\s*(?:is\s*)?(\d{1,3})", text)
        if m:
            age = int(m.group(1) or m.group(2))
    if age is None:
        return 0
    if age <= 5 or age >= 65:
        return 5
    if age <= 12:
        return 3
    if age >= 50:
        return 2
    return 0


def extract_features(transcript, age=None):
    t = transcript.lower()
    severity = np.clip(keyword_score(t, LEX["severity"]), 0, 10)
    distress = np.clip(keyword_score(t, LEX["distress"]) + t.count("!"), 0, 10)
    vulnerability = np.clip(keyword_score(t, LEX["vulnerability"]) + age_points(t, age), 0, 10)

    m = re.search(r"in (\d+) days?", t)
    if m:
        delay = int(m.group(1))
    else:
        hits = [(len(k), d) for k, d in LEX["when"].items() if re.search(r"\b" + re.escape(k) + r"\b", t)]
        delay = max(hits)[1] if hits else LEX["default_delay_days"]
    return float(severity), float(distress), float(vulnerability), float(np.clip(delay, 0, 30))


# ---------- 2. Fuzzy sets ----------

severity = ctrl.Antecedent(np.arange(0, 10.1, 0.1), "severity")
distress = ctrl.Antecedent(np.arange(0, 10.1, 0.1), "distress")
vulnerability = ctrl.Antecedent(np.arange(0, 10.1, 0.1), "vulnerability")
delay = ctrl.Antecedent(np.arange(0, 30.1, 0.1), "delay")
triage = ctrl.Consequent(np.arange(0, 100.1, 0.5), "triage")  # centroid defuzzification

MF = {  # shared with the JavaScript version (see build_js.py)
    "severity": {"mild": [0, 0, 2, 4], "moderate": [2, 5, 5, 8], "severe": [6, 8, 10, 10]},
    "distress": {"calm": [0, 0, 2, 4], "anxious": [2, 5, 5, 8], "panicked": [6, 8, 10, 10]},
    "vulnerability": {"low": [0, 0, 2, 4], "medium": [2, 5, 5, 8], "high": [6, 8, 10, 10]},
    "delay": {"immediate": [0, 0, 1, 3], "soon": [1, 5, 5, 12], "flexible": [8, 15, 30, 30]},
    "triage": {"routine": [0, 0, 25, 45], "urgent": [30, 55, 55, 80], "emergency": [65, 85, 100, 100]},
}
for var in (severity, distress, vulnerability, delay, triage):
    for term, pts in MF[var.label].items():
        var[term] = fuzz.trapmf(var.universe, pts)

# ---------- 3. Rule base ----------
# Each rule: (conditions, output). Conditions are ANDed (min).
RULES = [
    ({"severity": "severe"}, "emergency"),
    ({"severity": "moderate", "distress": "panicked"}, "emergency"),
    ({"severity": "moderate", "vulnerability": "high"}, "urgent"),
    ({"severity": "moderate", "vulnerability": "medium"}, "urgent"),
    ({"severity": "moderate", "vulnerability": "low"}, "urgent"),
    ({"severity": "moderate", "delay": "immediate"}, "urgent"),
    ({"severity": "mild", "distress": "panicked"}, "urgent"),
    ({"severity": "mild", "vulnerability": "high"}, "urgent"),
    ({"severity": "mild", "delay": "immediate"}, "urgent"),
    ({"severity": "mild", "distress": "anxious", "delay": "soon"}, "urgent"),
    ({"severity": "mild", "distress": "calm", "vulnerability": "low", "delay": "flexible"}, "routine"),
    ({"severity": "mild", "distress": "calm", "vulnerability": "low", "delay": "soon"}, "routine"),
    ({"severity": "mild", "distress": "calm", "vulnerability": "medium"}, "routine"),
    ({"severity": "mild", "distress": "anxious", "vulnerability": "low", "delay": "flexible"}, "routine"),
    ({"severity": "mild", "distress": "anxious", "vulnerability": "medium", "delay": "flexible"}, "routine"),
]
VARS = {"severity": severity, "distress": distress, "vulnerability": vulnerability, "delay": delay}


def _antecedent(cond):
    terms = [VARS[v][t] for v, t in cond.items()]
    a = terms[0]
    for t in terms[1:]:
        a = a & t
    return a


system = ctrl.ControlSystem([ctrl.Rule(_antecedent(c), triage[o]) for c, o in RULES])

# ---------- 4. Inference ----------


def label(score):
    return "Emergency" if score > 70 else "Urgent" if score >= 40 else "Routine"


def simulate(sev, dis, vul, dly):
    sim = ctrl.ControlSystemSimulation(system)
    sim.input["severity"], sim.input["distress"] = sev, dis
    sim.input["vulnerability"], sim.input["delay"] = vul, dly
    sim.compute()
    return sim


def triage_values(sev, dis, vul, dly):
    s = round(float(simulate(sev, dis, vul, dly).output["triage"]), 1)
    return s, label(s)


def triage_call(transcript, age=None):
    sev, dis, vul, dly = extract_features(transcript, age)
    score, lab = triage_values(sev, dis, vul, dly)
    return {"severity": sev, "distress": dis, "vulnerability": vul, "delay_days": dly,
            "triage_score": score, "triage_label": lab}


if __name__ == "__main__":
    from samples import SAMPLES
    for name, text, _ in SAMPLES:
        r = triage_call(text)
        print(f"{name:28} sev={r['severity']:4} dis={r['distress']:4} vul={r['vulnerability']:4} "
              f"delay={r['delay_days']:4} -> {r['triage_score']:5} {r['triage_label']}")
