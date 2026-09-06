#!/usr/bin/env python3
"""Cover image: the container gates applied to both sides, as a designed figure.

Reads data/gate_comparison/{regen_off,regen_on}.npz + box_geometry.json (dumped from the
two runs) so it regenerates without the raw traces.

    python scripts/make_cover.py
"""
import json, os
import numpy as np
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from mpl_toolkits.mplot3d.art3d import Poly3DCollection

HERE = os.path.dirname(os.path.abspath(__file__))
D, F = os.path.join(HERE, "..", "data", "gate_comparison"), os.path.join(HERE, "..", "figures")
CO, STUB = 0.1865, 0.062
BG, INK, DIM = "#0e1014", "#f2f4f7", "#8b93a1"
OK, KILL = "#37d67a", "#e0524a"
BOX_LINE, BOX_FILL, CLOUD = "#6b5a44", "#c8b394", "#cfd6e0"

def draw_box(ax, b):
    x0, x1, y0, y1, z0, z1 = (b[k] for k in ("x0", "x1", "y0", "y1", "z0", "z1"))
    faces = [[(x0, y0, z0), (x1, y0, z0), (x1, y1, z0), (x0, y1, z0)],
             [(x0, y1, z0), (x1, y1, z0), (x1, y1, z1), (x0, y1, z1)],
             [(x0, y0, z0), (x0, y1, z0), (x0, y1, z1), (x0, y0, z1)],
             [(x1, y0, z0), (x1, y1, z0), (x1, y1, z1), (x1, y0, z1)]]
    ax.add_collection3d(Poly3DCollection(faces[:1], facecolor=BOX_FILL, edgecolor="none", alpha=0.30, zorder=1))
    ax.add_collection3d(Poly3DCollection(faces[1:], facecolor=BOX_FILL, edgecolor="none", alpha=0.08, zorder=4))
    P = np.array([[x0, y0, z0], [x1, y0, z0], [x1, y1, z0], [x0, y1, z0],
                  [x0, y0, z1], [x1, y0, z1], [x1, y1, z1], [x0, y1, z1]])
    for i, j in [(0, 1), (1, 2), (2, 3), (3, 0), (4, 5), (5, 6), (6, 7), (7, 4), (0, 4), (1, 5), (2, 6), (3, 7)]:
        ax.plot(*zip(P[i], P[j]), color=BOX_LINE, lw=1.1, zorder=5, alpha=0.85)

def panel(ax, z, b):
    ax.computed_zorder = False
    ax.set_facecolor(BG)
    draw_box(ax, b)
    G, alive, cloud = z["grasps"], z["clears_container"].astype(bool), z["object_cloud"]
    ap = G[:, :3, 2]; p = G[:, :3, 3] + CO * ap; q = p - STUB * ap
    for i in np.argsort(alive):                                  # survivors painted last
        ax.plot([p[i, 0], q[i, 0]], [p[i, 1], q[i, 1]], [p[i, 2], q[i, 2]],
                color=OK if alive[i] else KILL, lw=1.6 if alive[i] else 0.7,
                alpha=0.95 if alive[i] else 0.30, zorder=2 if alive[i] else 0, solid_capstyle="round")
    ax.scatter(cloud[::2, 0], cloud[::2, 1], cloud[::2, 2], s=1.6, c=CLOUD, alpha=0.55, lw=0,
               depthshade=False, zorder=3)
    cx, cy, cz = (b["x0"] + b["x1"]) / 2, (b["y0"] + b["y1"]) / 2, b["z0"]
    hx = (b["x1"] - b["x0"]) / 2 + 0.02
    ax.set_xlim(cx - hx, cx + hx); ax.set_ylim(cy - hx, cy + hx); ax.set_zlim(cz - 0.05, cz + 1.0 * hx)
    ax.set_box_aspect((2 * hx, 2 * hx, 1.0 * hx + 0.05), zoom=1.9)
    ax.view_init(elev=20, azim=-70); ax.set_axis_off()
    return int(alive.sum())

def main() -> int:
    b = json.load(open(os.path.join(D, "box_geometry.json")))
    fig = plt.figure(figsize=(12, 5.55), facecolor=BG)
    for k, (tag, title) in enumerate((("regen_off", "generate → filter"),
                                      ("regen_on", "generate → regenerate → filter"))):
        ax = fig.add_subplot(1, 2, k + 1, projection="3d", facecolor=BG)
        n = panel(ax, np.load(os.path.join(D, f"{tag}.npz")), b)
        x = 0.243 + 0.497 * k
        fig.text(x, 0.885, title, ha="center", fontsize=13.5, color=INK, fontweight="bold")
        fig.text(x, 0.255, f"{n}", ha="center", fontsize=52, color=OK if k else DIM, fontweight="bold")
        fig.text(x, 0.195, "of 400 candidates clear the box", ha="center", fontsize=10.5, color=DIM)
    fig.text(0.5, 0.962, "G R A S P G E N - X   I N S I D E   A   C O N T A I N E R", ha="center",
             fontsize=9, color=DIM, fontweight="bold")
    hs = [plt.Line2D([], [], color=c, lw=3) for c in (OK, KILL)]
    leg = fig.legend(hs, ["clears the walls, the floor, the neighbours and the descent sweep",
                          "killed by the container"],
                     loc="lower center", ncol=2, frameon=False, fontsize=10,
                     bbox_to_anchor=(0.5, 0.02), labelcolor=DIM, handlelength=1.6, columnspacing=2.6)
    fig.subplots_adjust(left=0.0, right=1.0, top=0.86, bottom=0.32, wspace=0.02)
    out = os.path.join(F, "cover.png")
    fig.savefig(out, dpi=170, facecolor=BG); plt.close(fig)
    print("written", out)
    return 0

if __name__ == "__main__":
    raise SystemExit(main())
