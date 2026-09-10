#!/usr/bin/env python3
"""Regenerate every figure and the headline numbers from the CSVs under data/.

    python scripts/make_figures.py
"""
import csv, os
from collections import defaultdict
import numpy as np
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt

here = os.path.dirname(os.path.abspath(__file__))
D = os.path.join(here, "..", "data"); F = os.path.join(here, "..", "figures")
os.makedirs(F, exist_ok=True)
CONE = 60.0
plt.rcParams.update({"font.size": 10, "axes.spines.top": False, "axes.spines.right": False})
C_RAW, C_REG, C_FLIP, C_OFF, C_ON = "#8a8a8a", "#1f5f8b", "#d69e00", "#c0392b", "#2e8b57"

# ── 1. approach-angle distribution, raw vs regenerated ──────────────────────
ang = defaultdict(list)
for r in csv.DictReader(open(os.path.join(D, "candidate_angles.csv"))):
    ang[r["stage"]].append(float(r["angle_from_down_deg"]))
raw, reg = np.array(ang["raw"]), np.array(ang["regenerated"])
bins = np.arange(0, 181, 10)
fig, ax = plt.subplots(figsize=(7.2, 3.6))
ax.axvspan(0, CONE, color=C_ON, alpha=0.10, lw=0)
ax.axvspan(90, 180, color=C_OFF, alpha=0.08, lw=0)
ax.hist(raw, bins=bins, weights=np.full(len(raw), 100 / len(raw)), color=C_RAW, alpha=0.9, label=f"raw GraspGen samples (n={len(raw):,})")
ax.hist(reg, bins=bins, weights=np.full(len(reg), 100 / len(reg)), color=C_REG, alpha=0.65, label=f"after constraint-aware regeneration (n={len(reg):,})")
ax.text(CONE / 2, ax.get_ylim()[1] * 0.93, "top-down cone\n(≤60° from vertical)", ha="center", va="top", fontsize=8.5, color=C_ON)
ax.text(135, ax.get_ylim()[1] * 0.93, "approach points UP\n(useless inside a bin)", ha="center", va="top", fontsize=8.5, color=C_OFF)
ax.set_xlabel("angle between approach direction and straight-down (deg)"); ax.set_ylabel("% of candidates")
ax.set_xlim(0, 180); ax.legend(loc="center right", fontsize=8.5, frameon=False)
ax.set_title("Where do GraspGen's approach directions point for objects inside a box?", fontsize=10.5)
fig.tight_layout(); fig.savefig(os.path.join(F, "fig1_approach_angles.png"), dpi=160); plt.close(fig)
pct_up = 100 * (raw > 90).mean(); pct_cone = 100 * (raw <= CONE).mean(); pct_cone_reg = 100 * (reg <= CONE).mean()

# ── 2. the funnel inside the box, regeneration off vs on ────────────────────
cells = list(csv.DictReader(open(os.path.join(D, "funnel_per_cell.csv"))))
gates = [("n_raw", "GraspGen\nsamples"), ("after_topdown_cone", "top-down\ncone"),
         ("after_scene_floor_corridor", "walls, floor,\nneighbours, corridor"),
         ("after_table_gate", "fingertips above\nbox floor"), ("after_wall_sweep", "descent sweep\nvs 4 walls")]
def mean_gate(rows, k):
    v = [float(r[k]) for r in rows if r[k] not in ("", None)]
    return (np.mean(v), len(v)) if v else (np.nan, 0)
off = [r for r in cells if r["regeneration"] == "off" and r["after_topdown_cone"] != ""]
on = [r for r in cells if r["regeneration"] == "on" and r["after_topdown_cone"] != ""]
m_off = [mean_gate(off, k)[0] for k, _ in gates]; m_on = [mean_gate(on, k)[0] for k, _ in gates]
m_on[0] = mean_gate(on, "after_regeneration")[0]      # with regeneration the cone sees the regenerated set
fig, ax = plt.subplots(figsize=(7.2, 3.8))
x = np.arange(len(gates)); wdt = 0.38
b1 = ax.bar(x - wdt / 2, m_off, wdt, color=C_OFF, label=f"generate → filter (n={len(off)} attempts)")
b2 = ax.bar(x + wdt / 2, m_on, wdt, color=C_ON, label=f"generate → regenerate → filter (n={len(on)} attempts)")
for b, v in list(zip(b1, m_off)) + list(zip(b2, m_on)):
    ax.text(b.get_x() + b.get_width() / 2, v * 1.15, f"{v:.0f}", ha="center", va="bottom", fontsize=8.5)
ax.set_yscale("log"); ax.set_ylim(1, 900); ax.set_xticks(x); ax.set_xticklabels([g for _, g in gates], fontsize=8.5)
ax.set_ylabel("candidates surviving (mean per attempt, log)")
ax.set_title("Inside a 40×24 cm box the standard pipeline keeps ~1 % of the samples", fontsize=10.5)
ax.legend(fontsize=8.5, frameon=False, loc="upper right")
fig.tight_layout(); fig.savefig(os.path.join(F, "fig2_funnel_in_box.png"), dpi=160); plt.close(fig)

# ── 3. the 180° flip about the closing axis ─────────────────────────────────
tr = list(csv.DictReader(open(os.path.join(D, "per_trace_summary.csv"))))
NAMES = {"black_gloves": "black gloves", "camiseta_doblada": "folded t-shirt",
         "usb_c_cable": "USB-C cable", "yellow_trim": "yellow trim"}
objs = sorted(set(r["object"] for r in tr))
mr = [np.mean([int(r["n_in_cone60"]) for r in tr if r["object"] == o]) for o in objs]
mf = [np.mean([int(r["n_in_cone60_with_flip"]) for r in tr if r["object"] == o]) for o in objs]
fig, ax = plt.subplots(figsize=(6.4, 3.3))
x = np.arange(len(objs))
ax.bar(x - 0.2, mr, 0.4, color=C_RAW, label="raw samples inside the cone")
ax.bar(x + 0.2, mf, 0.4, color=C_FLIP, label="raw ∪ flipped 180° about closing axis")
for i in range(len(objs)):
    ax.text(x[i] - 0.2, mr[i] + 4, f"{mr[i]:.0f}", ha="center", fontsize=8.5); ax.text(x[i] + 0.2, mf[i] + 4, f"{mf[i]:.0f}", ha="center", fontsize=8.5)
ax.set_xticks(x); ax.set_xticklabels([NAMES.get(o, o) for o in objs], fontsize=8.5); ax.set_ylabel("candidates in top-down cone (of 400)")
ax.set_ylim(0, 260); ax.set_title("A parallel gripper is symmetric: flipping each sample is free", fontsize=10.5)
ax.legend(fontsize=8.5, frameon=False, loc="upper center", ncol=2, bbox_to_anchor=(0.5, 1.0))
fig.tight_layout(); fig.savefig(os.path.join(F, "fig3_flip.png"), dpi=160); plt.close(fig)
tot_r = np.mean([int(r["n_in_cone60"]) for r in tr]); tot_f = np.mean([int(r["n_in_cone60_with_flip"]) for r in tr])

# ── 4. what still kills candidates at the scene gate, after regeneration ─────
rs = {r["reason"]: int(r["count"]) for r in csv.DictReader(open(os.path.join(D, "scene_gate_reasons.csv")))}
groups = {"passes": ["pasa", "pasa_roce", "pasa_dudoso"], "hits a box wall": ["escena"],
          "hits a neighbouring object": ["escena_vecino"], "descent corridor blocked": ["pasillo", "pasillo_vecino"],
          "below box floor": ["suelo"], "other": ["desplaz"]}
vals = {k: sum(rs.get(n, 0) for n in v) for k, v in groups.items()}; tot = sum(vals.values())
fig, ax = plt.subplots(figsize=(7.0, 2.9))
keys = list(vals); col = {"passes": C_ON, "other": C_RAW}
ax.barh(keys[::-1], [100 * vals[k] / tot for k in keys][::-1], color=[col.get(k, C_OFF) for k in keys[::-1]])
for i, k in enumerate(keys[::-1]):
    ax.text(100 * vals[k] / tot + 0.8, i, f"{100 * vals[k] / tot:.1f} %", va="center", fontsize=8.5)
ax.set_xlim(0, 85); ax.set_xlabel(f"% of {tot:,} regenerated candidates at the scene gate")
ax.set_title("After regeneration, what still kills a candidate is the container", fontsize=10)
fig.tight_layout(); fig.savefig(os.path.join(F, "fig4_scene_gate_reasons.png"), dpi=160); plt.close(fig)

# ── 5. does the discriminator's confidence predict fitting in the box? ───────
cf = list(csv.DictReader(open(os.path.join(D, "confidence_vs_feasibility.csv"))))
c_ok = np.array([float(r["discriminator_confidence"]) for r in cf if r["survives_box_gates"] == "1"])
c_ko = np.array([float(r["discriminator_confidence"]) for r in cf if r["survives_box_gates"] == "0"])
rng = np.random.default_rng(0); a = rng.choice(c_ok, min(len(c_ok), 3000), replace=False); b = rng.choice(c_ko, min(len(c_ko), 3000), replace=False)
auc = (a[:, None] > b[None, :]).mean() + 0.5 * (a[:, None] == b[None, :]).mean()
top8 = []
for t in sorted(set(r["trace"] for r in cf)):
    rr = sorted([r for r in cf if r["trace"] == t], key=lambda r: -float(r["discriminator_confidence"]))[:8]
    top8.append(sum(r["survives_box_gates"] == "1" for r in rr))
fig, ax = plt.subplots(figsize=(7.2, 3.3))
bins = np.linspace(0, 1, 26)
ax.hist(c_ko, bins=bins, weights=np.full(len(c_ko), 100 / len(c_ko)), color=C_OFF, alpha=0.6, label=f"killed by walls / floor / neighbours (n={len(c_ko):,})")
ax.hist(c_ok, bins=bins, weights=np.full(len(c_ok), 100 / len(c_ok)), color=C_ON, alpha=0.6, label=f"fits in the box (n={len(c_ok):,})")
ax.set_xlabel("GraspGen discriminator confidence of the candidate"); ax.set_ylabel("% of candidates")
ax.set_title(f"Confidence does not know about the box: AUC = {auc:.2f} · top-8 by confidence → {np.mean(top8):.1f} fit", fontsize=10)
ax.legend(fontsize=8.5, frameon=False)
fig.tight_layout(); fig.savefig(os.path.join(F, "fig5_confidence_vs_box.png"), dpi=160); plt.close(fig)

# ── headline numbers ─────────────────────────────────────────────────────────
zm = [float(r["dead_zone"]) for r in cells if r["dead_zone"] != ""]
ok_off = sum(r["outcome"] == "OK" for r in off); n_off = sum(r["outcome"] != "" for r in off)
ok_on = sum(r["outcome"] == "OK" for r in on); n_on = sum(r["outcome"] != "" for r in on)
print(f"raw samples: {len(raw):,} from {len(tr)} attempts · pointing up {pct_up:.1f} % · inside 60° cone {pct_cone:.1f} % · after regeneration inside cone {pct_cone_reg:.1f} %")
print(f"flip: cone {tot_r:.1f} -> {tot_f:.1f} per 400 (+{100 * (tot_f / tot_r - 1):.0f} %)")
print("funnel OFF:", [f"{v:.1f}" for v in m_off], f"n={len(off)}  pick+place OK {ok_off}/{n_off}")
print("funnel ON :", [f"{v:.1f}" for v in m_on], f"n={len(on)}  pick+place OK {ok_on}/{n_on}")
print(f"dead zone: mean {np.mean(zm):.0f}/400 contact points with no admissible orientation (n={len(zm)})")
print(f"confidence vs box gates: AUC {auc:.3f} · mean conf fits {c_ok.mean():.3f} / killed {c_ko.mean():.3f} · top-8 by conf fit {np.mean(top8):.1f}/8 (n={len(top8)})")
print("scene gate after regeneration:", {k: f"{100 * v / tot:.1f}%" for k, v in vals.items()})
