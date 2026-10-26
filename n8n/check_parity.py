"""Check that the n8n JavaScript gives the same answers as the Python models."""
import json, subprocess, sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path[:0] = [str(ROOT / "fuzzy_triage"), str(ROOT / "department_router")]
from fuzzy_triage import triage_call
from samples import SAMPLES
from router import train, load_data

JS = r"""
const fs = require('fs'), [tri, rou] = ['fuzzy_triage.js', 'department_router.js'].map(f => fs.readFileSync(process.argv[1] + '/' + f, 'utf8'));
const inputs = JSON.parse(fs.readFileSync(0, 'utf8'));
console.log(JSON.stringify(inputs.map(t => {
  const a = new Function('$json', tri)({ transcript: 'User: ' + t }).json;
  const r = new Function('$json', rou)({ ...a, triage_label: 'Routine' }).json;   // force routing so the classifier is tested
  return { ...a, department: r.department };
})));
"""
texts = [t for _, t, _ in SAMPLES]
X_test, _ = load_data("test_data.csv")
out = json.loads(subprocess.run(["node", "-e", JS, str(ROOT / "n8n" / "code_nodes")],
                                input=json.dumps(texts + X_test), capture_output=True, text=True, check=True).stdout)

bad = 0
for t, js in zip(texts, out):
    py = triage_call(t)
    ok = py["triage_label"] == js["triage_label"] and abs(py["triage_score"] - js["triage_score"]) <= 1
    bad += not ok
    print(("OK  " if ok else "DIFF"), f"py={py['triage_score']:5} {py['triage_label']:9} js={js['triage_score']:5} {js['triage_label']}")
model = train()
pred = model.predict(X_test)
same = sum(p == j["department"] for p, j in zip(pred, out[len(texts):]))
print(f"router: JS matches Python on {same}/{len(X_test)} test phrases")
sys.exit(1 if bad or same != len(X_test) else 0)
