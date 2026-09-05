#!/usr/bin/env python3
"""3D view of GraspGen's 400 samples on one object inside the box, before and after
constraint-aware regeneration. Uses data/examples/<object>.npz and box_geometry.json.

    python scripts/make_hedgehog.py [object]
"""
import json, os, sys
import numpy as np
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt

here = os.path.dirname(os.path.abspath(__file__)); D = os.path.join(here, "..", "data", "examples"); F = os.path.join(here, "..", "figures")
obj = sys.argv[1] if len(sys.argv) > 1 else "camiseta_doblada"
z = np.load(os.path.join(D, f"{obj}.npz")); box = json.load(open(os.path.join(D, "box_geometry.json")))
cloud, raw, reg = z["object_cloud"], z["raw_grasps"], z["regenerated_grasps"]
L = 0.06                 # drawn length of each gripper stub, from the contact point back along the approach axis
CO = 0.1365              # GraspGen frame origin -> fingertip contact, along +Z (WSG-50 with our fingers)

def segs(G):
    ap = G[:, :3, 2]; p = G[:, :3, 3] + CO * ap          # fingertip contact point
    return p, p - L * ap, np.degrees(np.arccos(np.clip(-ap[:, 2], -1, 1)))

def draw_box(ax):
    x0, x1, y0, y1, z0, z1 = (box[k] for k in ("x0", "x1", "y0", "y1", "z0", "z1"))
    P = np.array([[x0, y0, z0], [x1, y0, z0], [x1, y1, z0], [x0, y1, z0], [x0, y0, z1], [x1, y0, z1], [x1, y1, z1], [x0, y1, z1]])
    E = [(0, 1), (1, 2), (2, 3), (3, 0), (4, 5), (5, 6), (6, 7), (7, 4), (0, 4), (1, 5), (2, 6), (3, 7)]
    for a, b in E:
        ax.plot(*zip(P[a], P[b]), color="#8b6b3e", lw=1.2)
    xx, yy = np.meshgrid([x0, x1], [y0, y1]); ax.plot_surface(xx, yy, np.full_like(xx, z0), color="#c9a978", alpha=0.35, lw=0)

def panel(ax, G, title, colour):
    draw_box(ax)
    ax.scatter(cloud[::2, 0], cloud[::2, 1], cloud[::2, 2], s=1.2, c="#444", alpha=0.6, lw=0)
    a, b, ang = segs(G)
    for i in range(len(a)):
        c = colour(ang[i])
        ax.plot([a[i, 0], b[i, 0]], [a[i, 1], b[i, 1]], [a[i, 2], b[i, 2]], color=c, lw=0.8, alpha=0.85)
    ax.set_title(title, fontsize=10.5)
    cx, cy = (box["x0"] + box["x1"]) / 2, (box["y0"] + box["y1"]) / 2; r = 0.21
    ax.set_xlim(cx - r, cx + r); ax.set_ylim(cy - r, cy + r); ax.set_zlim(box["z0"] - 0.10, box["z0"] + 0.32)
    ax.set_box_aspect((1, 1, 0.9)); ax.view_init(elev=22, azim=-55); ax.set_axis_off()

fig = plt.figure(figsize=(11, 4.6))
ax1 = fig.add_subplot(1, 2, 1, projection="3d"); ax2 = fig.add_subplot(1, 2, 2, projection="3d")
n_up = int((segs(raw)[2] > 90).sum())
panel(ax1, raw, f"400 raw GraspGen samples · {n_up} approach from above the object's far side or from below", lambda t: "#c0392b" if t > 90 else ("#e0a020" if t > 60 else "#2e8b57"))
panel(ax2, reg, f"{len(reg)} candidates after constraint-aware regeneration", lambda t: "#1f5f8b")
fig.text(0.5, 0.02, "red: approach points up · orange: 60–90° from vertical · green: inside the top-down cone · brown: box walls and floor", ha="center", fontsize=8.5, color="#333")
fig.subplots_adjust(left=0.0, right=1.0, top=0.96, bottom=0.05, wspace=0.0); fig.savefig(os.path.join(F, f"fig0_hedgehog_{obj}.png"), dpi=160); plt.close(fig)
print(f"{obj}: raw {len(raw)} (up {n_up}) -> regenerated {len(reg)}")
