// Only the caller's words matter (the agent's own lines would add noise).
function callerText(j) {
  const t = j.transcript || '';
  const user = t.split('\n').filter(l => /^\s*user\s*:/i.test(l)).map(l => l.replace(/^\s*user\s*:/i, '')).join(' ');
  return [user || t, j.symptoms].filter(Boolean).join(' ');
}

// ---- Fuzzy triage (Mamdani, generated from fuzzy_triage/fuzzy_triage.py) ----
const LEX = {"severity": {"chest pain": 6, "heart attack": 8, "breathless": 5, "can't breathe": 7, "cannot breathe": 7, "difficulty breathing": 6, "shortness of breath": 5, "unconscious": 8, "fainted": 6, "collapsed": 7, "seizure": 7, "fits": 6, "stroke": 8, "face drooping": 7, "slurred speech": 6, "paralysis": 7, "heavy bleeding": 7, "bleeding": 4, "accident": 5, "fracture": 4, "broken": 3, "burn": 4, "poisoning": 7, "overdose": 7, "high fever": 4, "fever": 4, "vomiting": 2, "vomiting blood": 7, "severe": 3, "unbearable": 4, "pain": 2, "swelling": 1, "dizzy": 2, "headache": 1, "cough": 1, "cold": 1, "rash": 1, "itching": 1, "sore throat": 1, "seene mein dard": 6, "saans": 4, "behosh": 8, "bukhar": 2, "dard": 2, "khoon": 4, "checkup": -1, "check-up": -1, "follow up": -1, "follow-up": -1, "routine": -1, "report": -1, "vaccination": -1}, "distress": {"please": 1, "urgent": 3, "emergency": 4, "help": 2, "hurry": 3, "scared": 2, "worried": 2, "asap": 3, "immediately": 3, "right now": 3, "really bad": 2, "terrible": 2, "dying": 4, "panic": 3, "jaldi": 3, "madad": 2}, "vulnerability": {"pregnant": 7, "pregnancy": 7, "newborn": 5, "infant": 5, "baby": 4, "child": 3, "kid": 3, "elderly": 4, "old": 2, "grandfather": 3, "grandmother": 3, "diabetic": 3, "diabetes": 3, "heart patient": 4, "bp patient": 3, "blood pressure": 2, "asthma": 3, "kidney": 3, "cancer": 4, "dialysis": 4, "transplant": 4}, "when": {"today": 0, "right now": 0, "tonight": 0, "now": 0, "aaj": 0, "tomorrow": 1, "kal": 1, "day after tomorrow": 2, "this week": 4, "next week": 9, "next month": 30, "whenever": 20, "any time": 20, "anytime": 20}, "default_delay_days": 7};
const MF = {"severity": {"mild": [0, 0, 2, 4], "moderate": [2, 5, 5, 8], "severe": [6, 8, 10, 10]}, "distress": {"calm": [0, 0, 2, 4], "anxious": [2, 5, 5, 8], "panicked": [6, 8, 10, 10]}, "vulnerability": {"low": [0, 0, 2, 4], "medium": [2, 5, 5, 8], "high": [6, 8, 10, 10]}, "delay": {"immediate": [0, 0, 1, 3], "soon": [1, 5, 5, 12], "flexible": [8, 15, 30, 30]}, "triage": {"routine": [0, 0, 25, 45], "urgent": [30, 55, 55, 80], "emergency": [65, 85, 100, 100]}};
const RULES = [[{"severity": "severe"}, "emergency"], [{"severity": "moderate", "distress": "panicked"}, "emergency"], [{"severity": "moderate", "vulnerability": "high"}, "urgent"], [{"severity": "moderate", "vulnerability": "medium"}, "urgent"], [{"severity": "moderate", "vulnerability": "low"}, "urgent"], [{"severity": "moderate", "delay": "immediate"}, "urgent"], [{"severity": "mild", "distress": "panicked"}, "urgent"], [{"severity": "mild", "vulnerability": "high"}, "urgent"], [{"severity": "mild", "delay": "immediate"}, "urgent"], [{"severity": "mild", "distress": "anxious", "delay": "soon"}, "urgent"], [{"severity": "mild", "distress": "calm", "vulnerability": "low", "delay": "flexible"}, "routine"], [{"severity": "mild", "distress": "calm", "vulnerability": "low", "delay": "soon"}, "routine"], [{"severity": "mild", "distress": "calm", "vulnerability": "medium"}, "routine"], [{"severity": "mild", "distress": "anxious", "vulnerability": "low", "delay": "flexible"}, "routine"], [{"severity": "mild", "distress": "anxious", "vulnerability": "medium", "delay": "flexible"}, "routine"]];
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
