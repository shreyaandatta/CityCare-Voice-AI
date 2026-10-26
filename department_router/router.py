"""
Department router: a Multinomial Naive Bayes text classifier that maps a
caller's symptom description to a hospital department.

  python router.py "my knee hurts when I walk"   -> Orthopaedics
"""
import csv, json, sys
from pathlib import Path

from sklearn.feature_extraction.text import CountVectorizer
from sklearn.naive_bayes import MultinomialNB
from sklearn.pipeline import make_pipeline

HERE = Path(__file__).parent
TOKEN_PATTERN = r"(?u)\b\w\w+\b"   # same tokenizer is used in the n8n JavaScript version


def load_data(name="train_data.csv"):
    with open(HERE / name) as f:
        rows = list(csv.DictReader(f))
    return [r["text"] for r in rows], [r["department"] for r in rows]


def build_model():
    return make_pipeline(
        CountVectorizer(lowercase=True, token_pattern=TOKEN_PATTERN, ngram_range=(1, 1)),
        MultinomialNB(alpha=0.3),
    )


def train():
    X, y = load_data()
    return build_model().fit(X, y)


def export_model(model, path):
    """Save priors and word log-probabilities so JavaScript can run the same model."""
    vec, nb = model.named_steps["countvectorizer"], model.named_steps["multinomialnb"]
    vocab = vec.get_feature_names_out()
    data = {
        "classes": list(nb.classes_),
        "log_prior": [round(float(x), 3) for x in nb.class_log_prior_],
        "log_prob": {w: [round(float(nb.feature_log_prob_[c][i]), 2) for c in range(len(nb.classes_))]
                     for i, w in enumerate(vocab)},
    }
    Path(path).write_text(json.dumps(data, separators=(",", ":")))
    return data


def predict(model, text):
    probs = model.predict_proba([text])[0]
    best = probs.argmax()
    return model.classes_[best], round(float(probs[best]), 3)


if __name__ == "__main__":
    m = train()
    export_model(m, HERE / "model.json")
    for text in sys.argv[1:] or ["my knee hurts when I walk", "my father has chest pain",
                                  "baby has high fever", "I am pregnant and dizzy",
                                  "itchy red rash on arms", "kaan mein bahut dard"]:
        print(f"{text!r:40} -> {predict(m, text)}")
