#!/usr/bin/env python3
"""Render a trace the way the cell's own funnel viewer draws it: the WSG-50 sketched with
its real dimensions at every candidate, red for rejected and green for kept, over the
object's point cloud inside the box.

    python scripts/make_visor_shot.py <trace_off> <trace_on> [stage]

Gripper geometry copied from tools/view_embudo.py (`pinza`), so the drawing matches the
viewer: half aperture 0.055 m, fingertip 0.204 m, closing point 0.1865 m, grip band
0.139-0.206 m along +Z of the grasp frame.
"""
import json, os, sys
import numpy as np
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from mpl_toolkits.mplot3d.art3d import Line3DCollection, Poly3DCollection

EXT = 0.05
TIP, BAND0, CLOSE, HY = 0.154 + EXT, 0.089 + EXT, 0.1365 + EXT, 0.055
SEGS = np.array([[(0, -HY, BAND0), (0, -HY, TIP)],          # finger A
                 [(0, +HY, BAND0), (0, +HY, TIP)],          # finger B
                 [(0, -HY, BAND0), (0, +HY, BAND0)],        # crossbar
                 [(0, 0, BAND0 - 0.05), (0, 0, BAND0)],     # stem to the flange
                 [(0, -HY, CLOSE), (0, +HY, CLOSE)]])       # closing line
GREEN, RED = "#28c85a", "#dc3c32"                            # the viewer's VERDE / ROJO
BG, CLOUD, GRID = "#ffffff", "#5a6068", "#b9a06a"

def gripper_lines(G):
    """(5, 2, 3) segments of one gripper, in world coordinates."""
    return np.einsum("ij,skj->ski", G[:3, :3], SEGS) + G[:3, 3]

def stage(d, key):
    ix = json.load(open(os.path.join(d, "indice.json")))
    for e in ix["etapas"]:
        if key in e["fichero"]:
            return np.load(os.path.join(d, e["fichero"]), allow_pickle=True), e
    return None, None

def survivors(d):
    """Every candidate the cell had to choose from, and which of them clear the container.

    Poses stay consistent from the top-down gate through the wall sweep, so the survivors
    of the last container gate can be matched back onto the full set by pose. After that
    gate the trace stores the post-descent pose, which is why the chain stops there.
    """
    G = stage(d, "topdown_labpick")[0]["grasps"]
    z = stage(d, "antimesa_antipared")[0]
    keep = {tuple(np.round(g, 5).ravel()) for g, a in zip(z["grasps"], z["vivos"]) if a}
    return G, np.array([tuple(np.round(g, 5).ravel()) in keep for g in G])

def draw_box(ax, b, nx=6, ny=3):
    x0, x1, y0, y1, z0, z1 = (b[k] for k in ("x0", "x1", "y0", "y1", "z0", "z1"))
    ax.add_collection3d(Poly3DCollection(
        [[(x0, y0, z0), (x1, y0, z0), (x1, y1, z0), (x0, y1, z0)]],
        facecolor="#f0e6cf", edgecolor="none", alpha=0.85, zorder=1))
    L = []
    for i in range(nx + 1):                                   # floor grid, as the viewer draws it
        x = x0 + (x1 - x0) * i / nx
        L.append([(x, y0, z0), (x, y1, z0)])
    for j in range(ny + 1):
        y = y0 + (y1 - y0) * j / ny
        L.append([(x0, y, z0), (x1, y, z0)])
    P = np.array([[x0, y0, z0], [x1, y0, z0], [x1, y1, z0], [x0, y1, z0],
                  [x0, y0, z1], [x1, y0, z1], [x1, y1, z1], [x0, y1, z1]])
    for i, j in [(0, 1), (1, 2), (2, 3), (3, 0), (4, 5), (5, 6), (6, 7), (7, 4), (0, 4), (1, 5), (2, 6), (3, 7)]:
        L.append([tuple(P[i]), tuple(P[j])])
    ax.add_collection3d(Line3DCollection(L, colors=GRID, linewidths=0.9, zorder=2))

def load(d):
    """A trace folder, or one of the .npz dumps under data/seed7."""
    if d.endswith(".npz"):
        z = np.load(d)
        return z["grasps"], z["clears_container"].astype(bool), z["object_cloud"]
    G, alive = survivors(d)
    return G, alive, stage(d, "nube_del_objeto")[0]["pts"]

def panel(ax, d, b, elev=18, azim=-68):
    ax.computed_zorder = False
    ax.set_facecolor(BG)
    draw_box(ax, b)
    G, alive, cloud = load(d)
    for group, colour, lw, al, z in ((~alive, RED, 0.45, 0.40, 3), (alive, GREEN, 1.7, 1.0, 6)):
        segs = [s for g in G[group] for s in gripper_lines(g)]
        if segs:
            ax.add_collection3d(Line3DCollection(segs, colors=colour, linewidths=lw,
                                                 alpha=al, zorder=z))
    ax.scatter(cloud[::2, 0], cloud[::2, 1], cloud[::2, 2], s=2.0, c=CLOUD, alpha=0.8,
               lw=0, depthshade=False, zorder=5)
    cx, cy = (b["x0"] + b["x1"]) / 2, (b["y0"] + b["y1"]) / 2
    hx = (b["x1"] - b["x0"]) / 2 + 0.075
    ax.set_xlim(cx - hx, cx + hx); ax.set_ylim(cy - hx, cy + hx)
    ax.set_zlim(b["z0"] - 0.07, b["z0"] + 1.05 * hx)
    ax.set_box_aspect((2 * hx, 2 * hx, 1.05 * hx + 0.07), zoom=1.85)
    ax.view_init(elev=elev, azim=azim); ax.set_axis_off()
    return len(G), int(alive.sum())

def main() -> int:
    if len(sys.argv) > 2 and os.path.isdir(sys.argv[1]):   # two trace folders
        doff, don, b = sys.argv[1], sys.argv[2], json.load(
            open(os.path.join(os.path.dirname(os.path.abspath(sys.argv[1])), "caja.json")))
    else:                                                  # the dumps committed under data/seed7
        D = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "data", "seed7")
        pre = sys.argv[1] + "_" if len(sys.argv) > 1 else ""      # "" = usb_c_cable, "yt_" = yellow_trim
        doff, don = os.path.join(D, pre + "regen_off.npz"), os.path.join(D, pre + "regen_on.npz")
        b = json.load(open(os.path.join(D, "box_geometry.json")))
    fig = plt.figure(figsize=(13, 5.6), facecolor=BG)
    for k, d in enumerate((doff, don)):
        ax = fig.add_subplot(1, 2, k + 1, projection="3d", facecolor=BG)
        n, ok = panel(ax, d, b)
        print(f"{'without' if k == 0 else 'with'} regeneration: {n} candidates drawn, {ok} usable")
        fig.text(0.26 + 0.48 * k, 0.055, f"{ok} of {n} usable", ha="center", fontsize=15,
                 fontweight="bold", color=GREEN if k else "#555")
    fig.subplots_adjust(left=0.0, right=1.0, top=1.0, bottom=0.10, wspace=0.0)
    out = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "figures", f"visor_shot{'_yt' if len(sys.argv) > 1 and not os.path.isdir(sys.argv[1]) else ''}.png")
    fig.savefig(out, dpi=170, facecolor=BG); plt.close(fig)
    print("written", out)
    return 0

if __name__ == "__main__":
    raise SystemExit(main())
