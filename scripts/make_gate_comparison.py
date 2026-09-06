#!/usr/bin/env python3
"""Same gates, both sides: candidates that clear the container (walls, floor, neighbours,
descent sweep) with the sampler's raw poses vs. after constraint-aware regeneration.

Both panels come from the cell's own gates, from two runs of the same batch of three
objects in the box, one with regeneration off and one with it on.

    python scripts/make_gate_comparison.py <trace_regen_off> <trace_regen_on>
"""
import json, os, sys
import numpy as np
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from mpl_toolkits.mplot3d.art3d import Poly3DCollection

CO, STUB = 0.1865, 0.055
C_KILL, C_OK, C_CLOUD, C_BOX, C_FLOOR = "#c0392b", "#2e8b57", "#2b2b2b", "#7a5c33", "#d8c39b"

def stage(d, key):
    """(grasps, alive) of the trace stage whose file name contains `key`."""
    ix = json.load(open(os.path.join(d, "indice.json")))
    for e in ix["etapas"]:
        if key in e["fichero"]:
            z = np.load(os.path.join(d, e["fichero"]), allow_pickle=True)
            if "grasps" not in z.files:                       # the cloud stage stores points
                return z["pts"], None, e
            return z["grasps"], z["vivos"].astype(bool), e
    return None, None, None

def survivors(d):
    """Candidates entering the container gates, and which of them clear all of them."""
    g5, v5, _ = stage(d, "escena_suelo_pasillo")
    g6, v6, _ = stage(d, "antimesa_antipared")
    if g5 is None:
        return None, None
    keep = {tuple(np.round(g, 5).ravel()) for g, a in zip(g6, v6) if a} if g6 is not None else set()
    alive = np.array([tuple(np.round(g, 5).ravel()) in keep for g in g5])
    return g5, alive

def geom(G):
    ap = G[:, :3, 2]
    p = G[:, :3, 3] + CO * ap
    return p, p - STUB * ap

def draw_box(ax, b):
    x0, x1, y0, y1, z0, z1 = (b[k] for k in ("x0", "x1", "y0", "y1", "z0", "z1"))
    F = [[(x0, y0, z0), (x1, y0, z0), (x1, y1, z0), (x0, y1, z0)],
         [(x0, y1, z0), (x1, y1, z0), (x1, y1, z1), (x0, y1, z1)],
         [(x0, y0, z0), (x0, y1, z0), (x0, y1, z1), (x0, y0, z1)],
         [(x1, y0, z0), (x1, y1, z0), (x1, y1, z1), (x1, y0, z1)]]
    ax.add_collection3d(Poly3DCollection(F[:1], facecolor=C_FLOOR, edgecolor="none", alpha=0.95, zorder=1))
    ax.add_collection3d(Poly3DCollection(F[1:], facecolor=C_FLOOR, edgecolor="none", alpha=0.22, zorder=4))
    P = np.array([[x0, y0, z0], [x1, y0, z0], [x1, y1, z0], [x0, y1, z0],
                  [x0, y0, z1], [x1, y0, z1], [x1, y1, z1], [x0, y1, z1]])
    for i, j in [(0, 1), (1, 2), (2, 3), (3, 0), (4, 5), (5, 6), (6, 7), (7, 4), (0, 4), (1, 5), (2, 6), (3, 7)]:
        ax.plot(*zip(P[i], P[j]), color=C_BOX, lw=1.4, zorder=5)

def panel(ax, cloud, G, alive, b):
    ax.computed_zorder = False
    draw_box(ax, b)
    a, c = geom(G)
    for i in np.argsort(alive):                       # survivors last, on top
        ax.plot([a[i, 0], c[i, 0]], [a[i, 1], c[i, 1]], [a[i, 2], c[i, 2]],
                color=C_OK if alive[i] else C_KILL, lw=1.1 if alive[i] else 0.6,
                alpha=0.9 if alive[i] else 0.35, zorder=2 if alive[i] else 0,
                solid_capstyle="round")
    ax.scatter(cloud[:, 0], cloud[:, 1], cloud[:, 2], s=2.0, c=C_CLOUD, alpha=0.85, lw=0,
               depthshade=False, zorder=3)
    cx, cy, cz = (b["x0"] + b["x1"]) / 2, (b["y0"] + b["y1"]) / 2, b["z0"]
    hx = (b["x1"] - b["x0"]) / 2 + 0.035
    ax.set_xlim(cx - hx, cx + hx); ax.set_ylim(cy - hx, cy + hx); ax.set_zlim(cz - 0.085, cz + 1.15 * hx)
    ax.set_box_aspect((2 * hx, 2 * hx, 1.15 * hx + 0.085), zoom=1.75)
    ax.view_init(elev=22, azim=-72); ax.set_axis_off()

def main() -> int:
    doff, don = sys.argv[1], sys.argv[2]
    b = json.load(open(os.path.join(os.path.dirname(os.path.abspath(doff)), "caja.json")))
    out = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "figures", "fig0_same_gates.png")
    fig = plt.figure(figsize=(11.5, 5.4))
    axes = [fig.add_subplot(1, 2, i + 1, projection="3d") for i in range(2)]
    n = {}
    for ax, d, t, x in zip(axes, (doff, don),
                           ("generate → filter", "generate → regenerate → filter"), (0.27, 0.76)):
        cloud = stage(d, "nube_del_objeto")[0]
        G, alive = survivors(d)
        panel(ax, cloud, G, alive, b)
        n[t] = (len(G), int(alive.sum()))
        fig.text(x, 0.96, t, ha="center", fontsize=12.5, fontweight="bold")
        fig.text(x, 0.90, f"{int(alive.sum())} of the 400 samples clear the container",
                 ha="center", fontsize=10, color="#333")
        print(f"{t}: {len(G)} reach the container gates, {int(alive.sum())} clear them  [{os.path.basename(d)}]")
    hs = [plt.Line2D([], [], color=c, lw=2.4) for c in (C_OK, C_KILL)]
    fig.legend(hs, ["clears the walls, the floor, the neighbours and the descent sweep",
                    "killed by the container"],
               loc="lower center", ncol=2, frameon=False, fontsize=9.5, bbox_to_anchor=(0.5, 0.155))
    fig.text(0.5, 0.105, "Same object, same box, same gates of the cell — the only difference is whether the "
             "candidates were regenerated under the container's constraints.\nThree objects were in the box; "
             "across the two runs the survivors went 8 → 84 on the first pick and 32 → 46 on the second.",
             ha="center", va="top", fontsize=9.5, color="#222", linespacing=1.5)
    fig.text(0.5, 0.015, "One pick from each of two runs of the same batch (yellow_trim, usb_c_cable, "
             "rubiks_cube). The batch is dropped into the box, so the arrangement is not identical between runs.",
             ha="center", fontsize=8.5, color="#777")
    fig.subplots_adjust(left=0.0, right=1.0, top=0.94, bottom=0.25, wspace=0.0)
    fig.savefig(out, dpi=170); plt.close(fig)
    print("written", out)
    return 0

if __name__ == "__main__":
    raise SystemExit(main())
