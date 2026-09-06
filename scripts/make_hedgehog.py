#!/usr/bin/env python3
"""Two 3D views of the same object inside the box: the 400 raw GraspGen-X samples, and
the candidates left after constraint-aware regeneration.

    python scripts/make_hedgehog.py [object]

Reads data/examples/<object>.npz (object_cloud, raw_grasps, regenerated_grasps) and
data/examples/box_geometry.json. Everything is in the cell's world frame, in metres.
"""
import json, os, sys
import numpy as np
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from mpl_toolkits.mplot3d.art3d import Poly3DCollection

HERE = os.path.dirname(os.path.abspath(__file__))
D, F = os.path.join(HERE, "..", "data", "examples"), os.path.join(HERE, "..", "figures")
STUB = 0.055          # drawn length of each approach segment, from the fingertip contact backwards
CO = 0.1865           # grasp frame origin -> fingertip closing point along +Z:
                      # 0.1365 m + the 0.05 m finger extension of our long-finger WSG-50
                      # (hand_lab._close_off). Checked against the clouds: with this value
                      # the contact points sit a median of 1.5 cm from the object surface.
MAX_D = 0.05          # candidates whose contact lands further than this from the cloud are
                      # not drawn (2-3 per panel): they are sampler outliers and only add clutter
UP, CONE = 90.0, 60.0
C_UP, C_SIDE, C_CONE, C_REG = "#c0392b", "#e59f1a", "#2e8b57", "#1f5f8b"
C_CLOUD, C_BOX, C_FLOOR = "#2b2b2b", "#7a5c33", "#d8c39b"

def geom(G):
    ap = G[:, :3, 2]
    p = G[:, :3, 3] + CO * ap                                   # fingertip contact point
    return p, p - STUB * ap, np.degrees(np.arccos(np.clip(-ap[:, 2], -1.0, 1.0)))

def draw_box(ax, b):
    x0, x1, y0, y1, z0, z1 = (b[k] for k in ("x0", "x1", "y0", "y1", "z0", "z1"))
    faces = [[(x0, y0, z0), (x1, y0, z0), (x1, y1, z0), (x0, y1, z0)],          # floor
             [(x0, y1, z0), (x1, y1, z0), (x1, y1, z1), (x0, y1, z1)],          # far wall
             [(x0, y0, z0), (x0, y1, z0), (x0, y1, z1), (x0, y0, z1)],          # left wall
             [(x1, y0, z0), (x1, y1, z0), (x1, y1, z1), (x1, y0, z1)]]          # right wall
    ax.add_collection3d(Poly3DCollection(faces[:1], facecolor=C_FLOOR, edgecolor="none", alpha=0.95, zorder=1))
    ax.add_collection3d(Poly3DCollection(faces[1:], facecolor=C_FLOOR, edgecolor="none", alpha=0.22, zorder=4))
    P = np.array([[x0, y0, z0], [x1, y0, z0], [x1, y1, z0], [x0, y1, z0],
                  [x0, y0, z1], [x1, y0, z1], [x1, y1, z1], [x0, y1, z1]])
    for a, b_ in [(0, 1), (1, 2), (2, 3), (3, 0), (4, 5), (5, 6), (6, 7), (7, 4), (0, 4), (1, 5), (2, 6), (3, 7)]:
        ax.plot(*zip(P[a], P[b_]), color=C_BOX, lw=1.4, zorder=5)

def near_cloud(p, cloud, dmax=MAX_D):
    """Mask of contact points within dmax of the object's point cloud."""
    d = np.sqrt(((p[:, None, :] - cloud[None, ::3, :]) ** 2).sum(-1)).min(1)
    return d <= dmax

def panel(ax, cloud, G, b, colour, title, sub):
    # mplot3d's automatic depth sorting paints the opaque floor over the point cloud;
    # order the artists by hand instead (segments below 0 · floor 1 · segments above 2 ·
    # cloud 3 · translucent walls 4 · box edges 5)
    ax.computed_zorder = False
    draw_box(ax, b)
    a, c, ang = geom(G)
    keep = near_cloud(a, cloud)
    a, c, ang = a[keep], c[keep], ang[keep]
    for i in range(len(a)):
        under = min(a[i, 2], c[i, 2]) < b["z0"]          # segment escaping below the box floor
        ax.plot([a[i, 0], c[i, 0]], [a[i, 1], c[i, 1]], [a[i, 2], c[i, 2]],
                color=colour(ang[i]), lw=0.85, alpha=0.8, solid_capstyle="round",
                zorder=0 if under else 2)
    ax.scatter(cloud[:, 0], cloud[:, 1], cloud[:, 2], s=2.2, c=C_CLOUD, alpha=0.85, lw=0,
               depthshade=False, zorder=3)
    cx, cy, cz = (b["x0"] + b["x1"]) / 2, (b["y0"] + b["y1"]) / 2, b["z0"]
    hx = (b["x1"] - b["x0"]) / 2 + 0.035
    ax.set_xlim(cx - hx, cx + hx); ax.set_ylim(cy - hx, cy + hx); ax.set_zlim(cz - 0.085, cz + 1.15 * hx)
    ax.set_box_aspect((2 * hx, 2 * hx, 1.15 * hx + 0.085), zoom=1.75)
    ax.view_init(elev=22, azim=-72); ax.set_axis_off()
    return title, sub

def main() -> int:
    obj = sys.argv[1] if len(sys.argv) > 1 else "yellow_trim"
    z = np.load(os.path.join(D, f"{obj}.npz")); b = json.load(open(os.path.join(D, "box_geometry.json")))
    cloud, raw, reg = z["object_cloud"], z["raw_grasps"], z["regenerated_grasps"]
    ang = geom(raw)[2]
    n_up, n_side, n_cone = int((ang > UP).sum()), int(((ang > CONE) & (ang <= UP)).sum()), int((ang <= CONE).sum())
    n_far = int((~near_cloud(geom(raw)[0], cloud)).sum() + (~near_cloud(geom(reg)[0], cloud)).sum())

    fig = plt.figure(figsize=(11.5, 5.4))
    ax1 = fig.add_subplot(1, 2, 1, projection="3d"); ax2 = fig.add_subplot(1, 2, 2, projection="3d")
    panel(ax1, cloud, raw, b, lambda t: C_UP if t > UP else (C_SIDE if t > CONE else C_CONE), "", "")
    panel(ax2, cloud, reg, b, lambda t: C_REG, "", "")
    for x, t, sub in ((0.27, "GraspGen-X, as sampled", f"400 candidates · {n_up} approach from under the floor"),
                      (0.76, "after constraint-aware regeneration", f"{len(reg)} candidates, all admissible in the box")):
        fig.text(x, 0.96, t, ha="center", fontsize=12.5, fontweight="bold")
        fig.text(x, 0.90, sub, ha="center", fontsize=10, color="#333")
    hs = [plt.Line2D([], [], color=c, lw=2.4) for c in (C_UP, C_SIDE, C_CONE, C_REG)]
    fig.legend(hs, [f"points up, under the floor ({n_up})", f"into a side wall ({n_side})",
                    f"inside the top-down cone ({n_cone})", f"regenerated ({len(reg)})"],
               loc="lower center", ncol=4, frameon=False, fontsize=9.5, bbox_to_anchor=(0.5, 0.18))
    ext = 100 * (cloud.max(0) - cloud.min(0))
    ins = ((cloud[:, 0] > b["x0"]) & (cloud[:, 0] < b["x1"]) & (cloud[:, 1] > b["y0"]) & (cloud[:, 1] < b["y1"]))
    lo, hi = np.percentile(cloud[ins], [2, 98], axis=0)
    gap = 100 * min(lo[1] - b["y0"], b["y1"] - hi[1])
    fig.text(0.5, 0.105, "Being inside the cone is not the same as being usable: those candidates still have "
             "to clear the walls, the floor and the neighbours.\nMeasured over 333 attempts, 3.9 candidates per "
             "attempt survive every container gate without regeneration, and 55.4 with it (§2).",
             ha="center", va="top", fontsize=9.5, color="#222", linespacing=1.5)
    fig.text(0.5, 0.015, f"{ext[0]:.0f} × {ext[1]:.0f} cm object, {gap:.1f} cm from the nearest wall · "
             f"{100 * (b['x1'] - b['x0']):.0f} × {100 * (b['y1'] - b['y0']):.0f} × "
             f"{100 * (b['z1'] - b['z0']):.0f} cm box · each segment is a candidate's approach axis from its "
             f"fingertip contact · {n_far} far outliers omitted",
             ha="center", fontsize=8.5, color="#777")
    fig.subplots_adjust(left=0.0, right=1.0, top=0.94, bottom=0.28, wspace=0.0)
    out = os.path.join(F, f"fig0_hedgehog_{obj}.png")
    fig.savefig(out, dpi=170); plt.close(fig)
    print(f"{obj}: raw 400 (up {n_up}, side {n_side}, cone {n_cone}) -> regenerated {len(reg)} · {out}")
    return 0

if __name__ == "__main__":
    raise SystemExit(main())
