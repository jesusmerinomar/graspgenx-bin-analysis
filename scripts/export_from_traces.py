#!/usr/bin/env python3
"""Export per-candidate approach angles from the lab's per-attempt trace folders.

Not needed to reproduce the figures (the CSVs it writes are committed under data/).
Kept so the numbers are traceable to the raw sampler output.

    python scripts/export_from_traces.py <traces_dir>

Each trace folder holds <NN>_regen_admisible.npz with `grasps` (400, 4, 4): the raw
GraspGen samples in the world frame (GraspGen convention: +Z of the grasp frame is
the approach direction, X is the finger closing line). The <NN>_regenerados.npz file
holds the candidates after our constraint-aware regeneration step.
"""
import csv, glob, json, os, sys
import numpy as np

src = sys.argv[1] if len(sys.argv) > 1 else "traces"
here = os.path.dirname(os.path.abspath(__file__))
data = os.path.join(here, "..", "data")

def angle_from_down(G):
    ap = G[:, :3, 2]                               # approach axis, world frame
    return np.degrees(np.arccos(np.clip(-ap[:, 2], -1.0, 1.0)))  # 0 = straight down, 180 = straight up

rows_cand, rows_trace, samples = [], [], {}
reasons = {}
rows_conf = []          # per regenerated candidate: discriminator confidence vs. surviving the box gates
def _key(G):
    return [tuple(np.round(g, 5).ravel()) for g in G]
for d in sorted(glob.glob(os.path.join(src, "intento_*"))):
    f2 = glob.glob(os.path.join(d, "*_regen_admisible.npz"))
    if not f2:
        continue
    z = np.load(f2[0], allow_pickle=True)
    G = z["grasps"]
    if G.shape[0] != 400:
        continue
    ix = json.load(open(os.path.join(d, "indice.json")))
    obj = ix.get("objeto", "?")
    tid = os.path.basename(d)
    a = angle_from_down(G)
    for i, ai in enumerate(a):
        rows_cand.append((tid, obj, "raw", i, round(float(ai), 2)))
    f3 = glob.glob(os.path.join(d, "*_regenerados.npz"))
    a3 = None
    if f3:
        G3 = np.load(f3[0], allow_pickle=True)["grasps"]
        a3 = angle_from_down(G3)
        for i, ai in enumerate(a3):
            rows_cand.append((tid, obj, "regenerated", i, round(float(ai), 2)))
    f5 = glob.glob(os.path.join(d, "*_escena_suelo_pasillo.npz"))
    f6 = glob.glob(os.path.join(d, "*_antimesa_antipared.npz"))
    if f3 and f5 and f6:
        conf = dict(zip(_key(G3), np.load(f3[0], allow_pickle=True)["confs"]))
        z6 = np.load(f6[0], allow_pickle=True)
        alive = set(k for k, v in zip(_key(z6["grasps"]), z6["vivos"]) if v)
        for k in _key(np.load(f5[0], allow_pickle=True)["grasps"]):
            if k in conf:
                rows_conf.append((tid, obj, round(float(conf[k]), 4), int(k in alive)))
    if f5:
        for m in np.load(f5[0], allow_pickle=True)["motivos"]:
            reasons[str(m)] = reasons.get(str(m), 0) + 1
    rows_trace.append((tid, obj, 400, int((a > 90).sum()), int((a <= 60).sum()),
                       int(((a <= 60) | (a >= 120)).sum()), len(a3) if a3 is not None else ""))
    if obj not in samples:                          # one full example per object
        f1 = glob.glob(os.path.join(d, "*_nube_del_objeto.npz"))
        samples[obj] = dict(raw_grasps=G, object_cloud=np.load(f1[0])["pts"] if f1 else None,
                            regenerated_grasps=G3 if f3 else None)

with open(os.path.join(data, "candidate_angles.csv"), "w", newline="") as fo:
    w = csv.writer(fo); w.writerow(["trace", "object", "stage", "idx", "angle_from_down_deg"]); w.writerows(rows_cand)
with open(os.path.join(data, "per_trace_summary.csv"), "w", newline="") as fo:
    w = csv.writer(fo)
    w.writerow(["trace", "object", "n_raw", "n_pointing_up", "n_in_cone60", "n_in_cone60_with_flip", "n_regenerated"])
    w.writerows(rows_trace)
with open(os.path.join(data, "confidence_vs_feasibility.csv"), "w", newline="") as fo:
    w = csv.writer(fo); w.writerow(["trace", "object", "discriminator_confidence", "survives_box_gates"]); w.writerows(rows_conf)
with open(os.path.join(data, "scene_gate_reasons.csv"), "w", newline="") as fo:
    w = csv.writer(fo); w.writerow(["reason", "count"]); w.writerows(sorted(reasons.items(), key=lambda kv: -kv[1]))
os.makedirs(os.path.join(data, "examples"), exist_ok=True)
for obj, s in samples.items():
    np.savez_compressed(os.path.join(data, "examples", f"{obj}.npz"),
                        **{k: v for k, v in s.items() if v is not None})
print(f"{len(rows_trace)} traces, {len(rows_cand)} candidate rows, {len(samples)} example objects")
