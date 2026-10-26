"""
Generate the JavaScript for the n8n Code nodes from the Python sources, so
both versions always share the same lexicon, membership functions, rules
and trained model.   Run:  python n8n/build_code_nodes.py
"""
import json, sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path[:0] = [str(ROOT / "fuzzy_triage"), str(ROOT / "department_router")]
from fuzzy_triage import LEX, MF, RULES  # noqa: E402

OUT = Path(__file__).parent / "code_nodes"
OUT.mkdir(exist_ok=True)

COMMON = r"""
// Only the caller's words matter (the agent's own lines would add noise).
function callerText(j) {
  const t = j.transcript || '';
  const user = t.split('\n').filter(l => /^\s*user\s*:/i.test(l)).map(l => l.replace(/^\s*user\s*:/i, '')).join(' ');
  // Prefer the caller's own words; fall back to the extracted symptoms, then the whole transcript.
  return user || j.symptoms || t;
}
"""

TRIAGE = COMMON + r"""
// ---- Fuzzy triage (Mamdani, generated from fuzzy_triage/fuzzy_triage.py) ----
const LEX = __LEX__;
const MF = __MF__;
const RULES = __RULES__;
const trap = (x, [a, b, c, d]) => Math.max(0, Math.min(b === a ? 1 : (x - a) / (b - a), 1, d === c ? 1 : (d - x) / (d - c)));
const clip = (v, lo, hi) => Math.min(hi, Math.max(lo, v));
const esc = s => s.replace(/[.*+?^${}()|[\]\\]/g, '\\$&');
const NEG = /\b(no|not|without|nahi|nahin)\b[\w\s']{0,15}$/;

function keywordScore(text, table) {
  let total = 0;
  for (const key of Object.keys(table).sort((a, b) => b.length - a.length)) {
    const re = new RegExp('\\b' + esc(key) + '\\b');
    let m;
    while ((m = re.exec(text))) {
      if (!NEG.test(text.slice(0, m.index))) total += table[key];
      text = text.slice(0, m.index) + ' '.repeat(key.length) + text.slice(m.index + key.length);
    }
  }
  return total;
}
function agePoints(text, age) {
  if (age == null || age === '' || isNaN(+age)) {
    const m = text.match(/(\d{1,3})\s*(?:years?|yrs?|saal)\b|\bage(?:d)?\s*(?:is\s*)?(\d{1,3})/);
    age = m ? +(m[1] || m[2]) : null;
  }
  if (age == null) return 0;
  age = +age;
  return age <= 5 || age >= 65 ? 5 : age <= 12 ? 3 : age >= 50 ? 2 : 0;
}
function extract(text, age) {
  const t = text.toLowerCase();
  const severity = clip(keywordScore(t, LEX.severity), 0, 10);
  const distress = clip(keywordScore(t, LEX.distress) + (t.match(/!/g) || []).length, 0, 10);
  const vulnerability = clip(keywordScore(t, LEX.vulnerability) + agePoints(t, age), 0, 10);
  let delay = LEX.default_delay_days;
  const m = t.match(/in (\d+) days?/);
  if (m) delay = +m[1];
  else {
    const hits = Object.entries(LEX.when).filter(([k]) => new RegExp('\\b' + esc(k) + '\\b').test(t))
      .sort((a, b) => b[0].length - a[0].length || b[1] - a[1]);
    if (hits.length) delay = hits[0][1];
  }
  return { severity, distress, vulnerability, delay_days: clip(delay, 0, 30) };
}
function infer(x) {
  const input = { severity: x.severity, distress: x.distress, vulnerability: x.vulnerability, delay: x.delay_days };
  const fire = {};
  for (const [cond, out] of RULES) {               // AND = min, aggregation = max
    const s = Math.min(...Object.entries(cond).map(([v, term]) => trap(input[v], MF[v][term])));
    fire[out] = Math.max(fire[out] || 0, s);
  }
  let num = 0, den = 0;                            // centroid defuzzification
  for (let y = 0; y <= 100; y += 0.5) {
    const mu = Math.max(...Object.entries(MF.triage).map(([term, p]) => Math.min(fire[term] || 0, trap(y, p))));
    num += y * mu; den += mu;
  }
  return den ? Math.round(num / den * 10) / 10 : 0;
}

const f = extract(callerText($json), $json.age);
const triage_score = infer(f);
const triage_label = triage_score > 70 ? 'Emergency' : triage_score >= 40 ? 'Urgent' : 'Routine';
return { json: { ...$json, ...f, triage_score, triage_label } };
"""

ROUTER = COMMON + r"""
// ---- Department router (Multinomial Naive Bayes, generated from department_router/model.json) ----
const MODEL = __MODEL__;
function route(text) {
  const tokens = (text.toLowerCase().match(/\b\w\w+\b/g) || []);
  const feats = tokens;
  const scores = MODEL.log_prior.slice();
  for (const f of feats) {
    const lp = MODEL.log_prob[f];
    if (lp) lp.forEach((v, c) => { scores[c] += v; });
  }
  const max = Math.max(...scores);
  const exp = scores.map(s => Math.exp(s - max));
  const sum = exp.reduce((a, b) => a + b, 0);
  const best = scores.indexOf(max);
  return { department: MODEL.classes[best], confidence: Math.round(exp[best] / sum * 1000) / 1000 };
}

let department, route_confidence, route_source;
const asked = ($json.preferred_department || '').toLowerCase();
const named = MODEL.classes.find(c => asked && (c.toLowerCase().includes(asked) || asked.includes(c.toLowerCase())));
if ($json.triage_label === 'Emergency') {
  [department, route_confidence, route_source] = ['Emergency', 1, 'triage'];
} else if (named) {
  [department, route_confidence, route_source] = [named, 1, 'caller asked'];
} else {
  const r = route(callerText($json));
  [department, route_confidence, route_source] = [r.department, r.confidence, 'naive bayes'];
}
return { json: { ...$json, department, route_confidence, route_source } };
"""

model = json.loads((ROOT / "department_router" / "model.json").read_text())
(OUT / "fuzzy_triage.js").write_text(
    TRIAGE.replace("__LEX__", json.dumps(LEX)).replace("__MF__", json.dumps(MF))
          .replace("__RULES__", json.dumps([[c, o] for c, o in RULES])).lstrip())
(OUT / "department_router.js").write_text(ROUTER.replace("__MODEL__", json.dumps(model, separators=(",", ":"))).lstrip())
print("wrote", *sorted(p.name for p in OUT.glob("*.js")))
