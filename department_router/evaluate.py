"""Train on the generated data, test on the separate hand-written phrases in test_data.csv."""
from pathlib import Path
import matplotlib; matplotlib.use("Agg")
import matplotlib.pyplot as plt
from sklearn.metrics import accuracy_score, classification_report, ConfusionMatrixDisplay
from router import load_data, build_model

X_train, y_train = load_data("train_data.csv")
X_test, y_test = load_data("test_data.csv")
pred = build_model().fit(X_train, y_train).predict(X_test)
print(f"Test accuracy on {len(X_test)} unseen hand-written phrases: {accuracy_score(y_test, pred):.1%}"
      f"  (trained on {len(X_train)} generated examples)\n")
print(classification_report(y_test, pred, zero_division=0))

fig, ax = plt.subplots(figsize=(9, 8))
ConfusionMatrixDisplay.from_predictions(y_test, pred, ax=ax, xticks_rotation=45, colorbar=False, cmap="Blues")
ax.set_title("Department router - confusion matrix (unseen test set)")
plt.tight_layout(); plt.savefig(Path(__file__).parent / "confusion_matrix.png", dpi=150)
