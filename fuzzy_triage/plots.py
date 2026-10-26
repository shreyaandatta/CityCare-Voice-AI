"""Draw membership functions, a control surface and a worked defuzzification example."""
from pathlib import Path
import numpy as np, matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from fuzzy_triage import severity, distress, vulnerability, delay, triage, simulate, triage_values

OUT = Path(__file__).parent / "images"; OUT.mkdir(exist_ok=True)

fig, axes = plt.subplots(5, 1, figsize=(8, 13))
for ax, var, title in zip(axes, [severity, distress, vulnerability, delay, triage],
        ["Severity (0-10)", "Distress (0-10)", "Vulnerability (0-10)", "Delay in days (0-30)", "Triage score (0-100)"]):
    for name, term in var.terms.items():
        ax.plot(var.universe, term.mf, linewidth=2, label=name)
    ax.set_title(title); ax.set_ylabel("membership"); ax.set_ylim(-0.05, 1.05)
    ax.legend(loc="center right"); ax.grid(alpha=.3)
plt.tight_layout(); plt.savefig(OUT / "membership_functions.png", dpi=150); plt.close()

s = np.linspace(0, 10, 21); v = np.linspace(0, 10, 21)
S, V = np.meshgrid(s, v)
Z = np.vectorize(lambda a, b: triage_values(a, 2, b, 5)[0])(S, V)
fig = plt.figure(figsize=(8, 6)); ax = fig.add_subplot(111, projection="3d")
ax.plot_surface(S, V, Z, cmap="viridis", edgecolor="none")
ax.set_xlabel("Severity"); ax.set_ylabel("Vulnerability"); ax.set_zlabel("Triage score")
ax.set_title("Control surface (distress = 2, delay = 5 days)")
plt.tight_layout(); plt.savefig(OUT / "control_surface.png", dpi=150); plt.close()

score, lab = triage_values(5, 3, 7, 4)
triage.view(sim=simulate(5, 3, 7, 4))
plt.title(f"Centroid defuzzification = {score} -> {lab}\n(severity 5, distress 3, vulnerability 7, delay 4)")
plt.tight_layout(); plt.savefig(OUT / "defuzzification_example.png", dpi=150); plt.close()
print("saved to", OUT)
