#!/usr/bin/env python3
"""Rebuild data/funnel_per_cell.csv from the lab's run logs (not published: they are
multi-MB Isaac Sim logs). One row per (object, object pose) attempt inside the box.
The gate names match the log lines quoted in the README.

    python scripts/parse_logs.py /path/to/lab_logs
"""
import csv, glob, os, re, sys

rx_cell = re.compile(r"══ (\d+)/(\d+): ([a-z_0-9]+)\[(P\d)\] ══")
rx_reg = re.compile(r"REGEN admisible★: (\d+) → (\d+) \((\d+) ya cabían · (\d+) REORIENTADOS, de ellos (\d+) volteados · (\d+) en zona muerta\)")
rx_td = re.compile(r"filtro top-down: (\d+)/(\d+) agarres")
rx_fc = re.compile(r"filtro candidatos: (\d+) → (\d+) \(topdown-(\d+) escena-(\d+) suelo-(\d+) pasillo-(\d+)\)")
rx_am = re.compile(r"filtro anti-mesa: (\d+)/(\d+) agarres")
rx_ap = re.compile(r"anti-pared★: (\d+)/(\d+) sobreviven")
rx_res = re.compile(r"→ ([a-z_0-9]+)\[(P\d)\]: (OK|[A-Z\-]+)")

def g(rx, seg, k, cast=int):
    m = rx.search(seg)
    return cast(m.group(k)) if m else ""

src = sys.argv[1] if len(sys.argv) > 1 else "/home/jesus/Escritorio/lab_logs"
out = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "data", "funnel_per_cell.csv")
rows = []
for f in sorted(glob.glob(os.path.join(src, "*.log")) + glob.glob(os.path.join(src, "barrida", "*.log"))):
    txt = open(f, errors="ignore").read()
    if "box_pared_ypos" not in txt:          # only runs with the box walls loaded
        continue
    cells = list(rx_cell.finditer(txt))
    for i, m in enumerate(cells):
        seg = txt[m.start():cells[i + 1].start() if i + 1 < len(cells) else len(txt)]
        reg = rx_reg.search(seg)
        rows.append([os.path.basename(f), m.group(3), m.group(4), "on" if reg else "off",
                     int(reg.group(1)) if reg else 400, g(rx_reg, seg, 2), g(rx_reg, seg, 3), g(rx_reg, seg, 5), g(rx_reg, seg, 6),
                     g(rx_td, seg, 1), g(rx_fc, seg, 2), g(rx_am, seg, 1), g(rx_ap, seg, 1), g(rx_res, seg, 3, str)])
with open(out, "w", newline="") as fo:
    w = csv.writer(fo)
    w.writerow(["log", "object", "object_pose", "regeneration", "n_raw", "after_regeneration", "already_admissible",
                "flipped", "dead_zone", "after_topdown_cone", "after_scene_floor_corridor", "after_table_gate",
                "after_wall_sweep", "outcome"])
    w.writerows(rows)
print(len(rows), "cells ->", out)
