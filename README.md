# GraspGen-X inside a container

**Bin-picking measurements on top of [NVIDIA GraspGen-X](https://github.com/NVlabs/GraspGenX)**

<p>
<a href="https://github.com/NVlabs/GraspGenX"><img alt="Built on GraspGen-X" src="https://img.shields.io/badge/built%20on-GraspGen--X-76B900"></a>
<a href="https://arxiv.org/abs/2606.00998"><img alt="GraspGen-X paper" src="https://img.shields.io/badge/arxiv-2606.00998-blue"></a>
<a href="https://developer.nvidia.com/isaac/sim"><img alt="Isaac Sim 6.0.1" src="https://img.shields.io/badge/Isaac%20Sim-6.0.1-76B900"></a>
<img alt="License" src="https://img.shields.io/badge/License-MIT-lightgrey">
</p>

![GraspGen-X inside a container](figures/hero.png)

<sub>Every candidate GraspGen-X proposed for the cable, drawn the way the cell's own
funnel viewer draws it. Both runs use the same seeded drop, so the only difference between
them is the regeneration. Numbers and method in §4.</sub>

[![the cell running, 2:26 at 1x speed](figures/video_thumb.png)](media/cell_demo.mp4)

<sub>The cell these measurements come from — click to play (2:26, 1× speed, 9 MB). The
small panel in its corner is the live candidate view: the grasps GraspGen-X proposed for
the object being picked, and the one that was chosen. Rigid objects and FEM garments,
inside a 38 × 18 × 14 cm cardboard box.</sub>

**What this is.** Numbers, figures and per-candidate data from running
[GraspGen-X](https://github.com/NVlabs/GraspGenX) (`b942909`) as the grasp generator of a
bin-picking cell in simulation: a UR5e with a WSG-50 parallel gripper picking rigid
objects and garments **out of a cardboard box**. GraspGen-X is used unmodified, through
its public sampler API and our own gripper descriptor (`gripper/wsg50_long/config.json`,
generated with their gripper wizard). Everything here is measured on that setup; nothing
is tuned for the plot. Scripts under `scripts/` regenerate every figure from the CSVs
under `data/`.

**This is a continuation of their work, not a fork.** No GraspGen-X code is copied here.
`scripts/run_graspgenx_on_example.py` shows how to reproduce our starting point from
their repository and our example clouds, so every number below can be traced back to
their sampler.

**Why we measured it.** GraspGen-X is trained on free-floating objects with SO(3)
augmentation. On a table that is fine: you keep the top-down samples and discard the
rest. **Inside a container it is not fine.** Every candidate has to clear four walls, a
floor and whatever else is in the box, and the standard pipeline
(*generate → filter by collision → rank*) can only *remove* candidates. It cannot create
the ones the sampler never produced. The consequence, measured over 82 attempts inside a
40 × 24 cm box: **of 400 samples, 4 survive on average**, and the 4 that survive are not
the good ones. This repository documents that, and the two things that fixed it for us.

> Setting: Isaac Sim 6.0.1 · UR5e · WSG-50 parallel gripper (110 mm stroke) ·
> wrist RGB-D → segmented object point cloud → GraspGen-X (parallel-jaw descriptor,
> 400 samples per object) · cardboard box, inner floor 40.2 × 24.0 cm, walls 14.4 cm ·
> objects: gloves, socks, mesh bag, folded t-shirt (FEM cloth), mouse, drill, cube,
> USB cable, trim · motion planning with cuRobo.

---

## 1. Half of the samples point away from the box floor

Approach direction of the 400 raw GraspGen-X samples, for 45 attempts (18,000 candidates) on
objects lying inside the box. 0° = straight down, 180° = straight up.

![approach angles](figures/fig1_approach_angles.png)

| | raw samples |
|---|---|
| approach points **up** (> 90° from vertical) | **47.9 %** (per attempt: min 165, max 235 of 400) |
| inside a 60° top-down cone | 23.1 % |

The raw distribution is close to uniform over the sphere, which is what SO(3)
augmentation on floating objects produces. The sampler does not know a floor exists,
let alone a box. This is the same bias reported in
[NVlabs/GraspGen#22](https://github.com/NVlabs/GraspGen/issues/22) ("mostly side grasps");
in our traces it is already present in the raw samples, before any discriminator scoring.

## 2. Inside a box, the filters keep ~1 % of the samples

Mean survivors per gate, one row per (object, object pose) attempt inside the box.
Gates, in order: top-down cone (≤ 60°); swept gripper volume vs. walls, floor,
neighbouring objects and the descent corridor; fingertips above the box floor at the
post-descent pose; full descent sweep against the four walls.

![funnel](figures/fig2_funnel_in_box.png)

| pipeline | attempts | samples | after cone | after scene | after floor gate | after wall sweep | pick + place OK |
|---|---|---|---|---|---|---|---|
| generate → filter | 82 | 400 | 72.5 | 11.8 | 5.3 | **3.9** | 33 / 77 |
| generate → **regenerate** → filter | 251 | 400 → 148.9 | 140.6 | 109.4 | 63.0 | **55.4** | 131 / 245 |

Two things to notice:

1. **The container is the killer, not the cone.** The cone removes 82 % of the samples,
   but the *scene* gate (walls, floor, neighbours) then removes 84 % of what is left,
   and the wall sweep a further third. On a table the scene gate is nearly a no-op.
2. **Fewer candidates means worse candidates.** With 4 survivors there is nothing to
   rank. The survivors near a wall are systematically the perpendicular or nearly
   vertical ones, which grab the least material. In our logs the failure mode moved
   from "no plan" to "grasped and slipped": the system does not fail to find a grasp,
   it confidently executes a bad one.

> The success-rate columns are **not** a clean A/B: the two groups come from different
> weeks of development and other parts of the pipeline changed in between. The
> candidate counts are the clean measurement; treat the outcomes as an order of
> magnitude. A controlled comparison is in preparation.

## 3. Fix 1, free: flip every sample 180° about the closing axis

A symmetric parallel gripper closes along one axis. Rotating a grasp 180° about that
axis, **around the contact point** (not the gripper origin, which would move the contact
by tens of centimetres), keeps both fingertip contacts and reverses the approach: a
sample that entered from below now enters from above, grasping exactly the same thing.
With the flipped copies added, the candidates inside the top-down cone go from
**92 to 170 per 400 (+84 %)** at zero inference cost. They still have to pass the scene
gates, so this is a supply fix, not a guarantee.

![flip](figures/fig3_flip.png)

## 4. Fix 2: regenerate under the container's constraints instead of filtering

The sampler is good at saying **where** to grasp (the contact on the object) and, inside
a box, bad at saying **how** (the orientation). So instead of discarding a candidate that
would hit a wall, we keep its contact point and look for an orientation that fits the
container.

Every candidate the cell had to choose from, drawn the way its own funnel viewer draws
them: red if the container kills it, green if it clears the walls, the floor, the
neighbours and the whole descent. Two runs of the same batch of three objects, with the
drop seeded so the arrangement is **identical** in both — the only difference is the
regeneration:

| object | generate → filter | generate → regenerate → filter |
|---|---|---|
| `usb_c_cable`, flat on the box floor (the cover) | **3** usable of 400 | **49** usable |
| `usb_c_cable`, other batch | 9 usable of 400 | 39 usable |
| `yellow_trim`, tall, reaching near the rim | 17 usable of 400 | 72 usable |
| `power_drill`, bulky | 11 usable of 400 | **7 usable** |

**The drill is the case where this does not pay off**, and it is worth stating plainly.
Regenerating it drops 285 of the 400 contacts into a dead zone — no orientation of the
gripper fits between the walls for those contact points — and the 115 that survive yield
fewer usable grasps than filtering the raw samples did. The gain is largest exactly where
the sampler struggles most: small or flat objects lying deep in the container. For a bulky
object that already has viable top-down grasps, there is nothing to recover.

The earlier pair of runs, without a seeded drop, gave the same picture:

| pick | generate → filter | generate → regenerate → filter |
|---|---|---|
| `yellow_trim` | 400 → 129 in cone → 58 → **32** | 400 → 273 regenerated → 262 → 200 → **84** |
| `usb_c_cable` | 400 → 73 in cone → 30 → **8** | 400 → 197 regenerated → 196 → 119 → **46** |

These are four pairs of picks, not a statistic. The aggregate over the runs measured in
§2 is 3.9 survivors per attempt without regeneration and 55.4 with it.

Notice where the candidates die without regeneration: of the 73 that clear the cone in
the second row, **40 are killed by the scene gate**, which is the walls and the
neighbouring objects. That gate is nearly a no-op on a table.

![scene gate reasons](figures/fig4_scene_gate_reasons.png)

The method itself, with baselines and ablations, is being written up separately. This
repository contains the diagnosis, the flip, and this measurement.

## 5. Why the sampler's confidence cannot pick the grasp inside a box

Once candidates survive, one has to be chosen. GraspGen ships a discriminator whose
confidence is meant to rank its own samples, and on a free-standing rigid object that
is a reasonable choice. Inside a container, with garments, it is not, for two reasons
we can measure.

**It does not know about the box.** We took the discriminator's confidence of each
candidate and asked whether it predicts surviving the container gates (walls, floor,
neighbours, descent sweep). It does not: AUC 0.45 over 6,847 candidates, i.e. slightly
*worse* than a coin flip, and of the 8 highest-confidence candidates per attempt only
**1.4 fit in the box**.

![confidence vs box](figures/fig5_confidence_vs_box.png)

**It does not know what a good closure is on our objects.** The discriminator was
trained to tell a stable grasp from an unstable one on rigid meshes. Whether the jaws
will close on *material*, and on the right material, is a different question, and on
cloth it is the whole question. Over 328 closure/outcome pairs from our logs, the
**shape of the closure** predicts the pick far better than any score assigned before it:

| how the jaws closed | pick + place OK |
|---|---|
| both jaws stopped on material, symmetrically | 205 / 277 · **74 %** |
| one jaw stopped, the other went to its stop | 2 / 12 · 17 % |
| both jaws went to their stop (closed on nothing) | 1 / 39 · **3 %** |

So the ranking has to look at the geometry of the closure itself, on the object's own
point cloud, and it has to look at different things for different objects:

- **where the centre of mass sits** relative to the closing line: off-centre grasps of
  a rigid object twist and slip; on a garment the same offset is harmless;
- **how much material ends up between the fingertips**, and whether it is the part
  of the object the closure was aimed at, or a fold or an edge that will slide out;
- **where the fingertips land**: on a rigid object a fingertip landing *on* the object
  is a collision and the candidate must be vetoed; on cloth the material does not stop
  at the jaw, so the same rule, applied blindly, vetoes almost every candidate;
- **whether the closing line crosses the feature** (a cuff, a handle, a fold) or runs
  along it, and whether it pinches the tip of the feature, from where it slips;
- **verticality**, only as a mild tie-breaker so the planner does not get to choose;
- and the sampler's confidence itself, used as a **floor**, not as the score: the
  network's *no* travels much better than its *yes*.

The weights, and which of these terms is a veto and which a multiplier, depend on the
object class. That is the part we keep in the cell and do not describe here; the point
of this section is only that a single confidence learned on a fixed set of rigid meshes
is not enough to choose a grasp inside a box.

## 6. Two questions we would like answered

1. Is contact with large static obstacles (a box wall a few millimetres from the
   object) considered in-distribution for GraspGen, or is the intended usage to crop
   the scene so that the object appears free-floating?
2. For the orientation bias of [#22](https://github.com/NVlabs/GraspGen/issues/22): in our
   traces it is present at sampling time. Is that expected from the training
   augmentation, and would a floor-aware conditioning be in scope?

## Data

| file | content |
|---|---|
| `data/candidate_angles.csv` | one row per candidate: attempt, object, stage (`raw` / `regenerated`), angle between approach direction and straight-down |
| `data/per_trace_summary.csv` | one row per attempt: samples pointing up, inside the cone, inside the cone with flip, regenerated count |
| `data/funnel_per_cell.csv` | one row per (object, pose) attempt inside the box: survivors after each gate, regeneration on/off, outcome |
| `data/seed7/*.npz` | the seeded pair behind the figure in §4 (`yt_` = yellow_trim, otherwise usb_c_cable): every candidate, whether it clears the container, and the object cloud |
| `data/gate_comparison/*.npz` | the earlier, unseeded pair of runs quoted at the end of §4 |
| `data/scene_gate_reasons.csv` | why regenerated candidates die at the scene gate |
| `data/confidence_vs_feasibility.csv` | one row per candidate: discriminator confidence and whether it survived the container gates |
| `gripper/wsg50_long/config.json` | the WSG-50 descriptor we feed to GraspGen-X (their wizard format) |
| `data/examples/<object>.npz` | full example per object: `object_cloud` (N×3, world frame, metres), `raw_grasps` (400×4×4, GraspGen convention: +Z approach, X closing line), `regenerated_grasps` |

Object poses P1–P4 in `funnel_per_cell.csv` are object orientations (canonical, lying,
on edge, upside-down), not positions in the box.

## Reproduce

```bash
pip install -r requirements.txt
python scripts/make_figures.py       # figures/ + headline numbers, from data/
python scripts/make_hero.py          # the cover, from data/seed7/ + figures/src/
```

```bash
# reproduce the starting point with GraspGen-X itself (needs their repo + checkpoints + a GPU)
GRASPGENX_CHECKPOINTS=<ckpt root> python scripts/run_graspgenx_on_example.py yellow_trim
```

`scripts/export_from_traces.py` and `scripts/parse_logs.py` document how the CSVs were
produced from the cell's per-candidate traces and run logs (not published; multi-GB).

## Citing GraspGen-X

Everything here builds on their model. If you use this repository, cite their work:

```bibtex
@inproceedings{graspgenx2026,
  title     = {GraspGen-X: Cross-Embodiment 6-DOF Diffusion-based Grasping},
  author    = {Han, Beining and Chao, Yu-Wei and Coumans, Erwin and Eppner, Clemens
               and Sundaralingam, Balakumar and Deng, Jia and Birchfield, Stan
               and Murali, Adithyavairavan},
  booktitle = {Proceedings of the IEEE/CVF Conference on Computer Vision and
               Pattern Recognition (CVPR)},
  year      = {2026},
}
```

Thanks to the GraspGen-X authors for releasing the model, the checkpoints and the
gripper wizard; without them none of this would exist.

## Who

Jesús Merino and Jorge Pascual, [NEURYN Robotics](https://neurynrobotics.com), Madrid.
Robot learning for garment handling. Contact: through GitHub or the website.

MIT license.
