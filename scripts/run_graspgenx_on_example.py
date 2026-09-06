#!/usr/bin/env python3
"""Reproduce the starting point of this analysis with GraspGen-X itself.

This repository contains no GraspGen-X code. To regenerate the raw samples that every
figure here is measured on, install their repository and run this script; it feeds one
of our example object clouds to their sampler with the same settings our cell uses.

    git clone https://github.com/NVlabs/GraspGenX          # we used commit b942909
    cd GraspGenX && <follow their install + checkpoint instructions>
    cp -r <this repo>/gripper/wsg50_long ext/gripper_descriptions/x_grippers/
    GRASPGENX_CHECKPOINTS=<ckpt root> python <this repo>/scripts/run_graspgenx_on_example.py yellow_trim

Requires a CUDA GPU and their checkpoints. Not run in CI.

The object cloud is in the cell's world frame, in metres; GraspGen-X expects it centred,
so we subtract the centroid before sampling and add it back to the returned poses. The
returned 4x4 poses follow the GraspGen convention: +Z is the approach axis, X is the
finger closing line, and the frame origin sits behind the fingertips by the descriptor's
`fingertip` offset.
"""
import os
import sys

import numpy as np

GRIPPER = "wsg50_long"     # our descriptor, in gripper/wsg50_long/config.json
NUM_GRASPS = 400           # what our cell asks for per object
THRESHOLD = -1.0           # no thresholding here: we want the full raw distribution

def main() -> int:
    obj = sys.argv[1] if len(sys.argv) > 1 else "yellow_trim"
    here = os.path.dirname(os.path.abspath(__file__))
    z = np.load(os.path.join(here, "..", "data", "examples", f"{obj}.npz"))
    cloud = z["object_cloud"]

    # their API; CHECKPOINTS is the checkpoint root that holds gen/ and dis/,
    # as set up by their "Setup Checkpoints and Gripper Assets" instructions
    import omegaconf
    from graspgenx.grasp_server import GraspGenXSampler, load_grasp_gen_model

    ckpt = os.environ.get("GRASPGENX_CHECKPOINTS", "")
    if not ckpt:
        print("set GRASPGENX_CHECKPOINTS to the checkpoint root (contains gen/ and dis/)")
        return 2
    cfg = omegaconf.OmegaConf.load(os.path.join(ckpt, "gen", "config.yaml"))
    sampler = GraspGenXSampler(cfg, gripper_name=GRIPPER,
                               model=load_grasp_gen_model(cfg))

    centre = cloud.mean(axis=0)
    poses, scores, _ = sampler.sample(cloud - centre, threshold=THRESHOLD,
                                      num_grasps=NUM_GRASPS, remove_outliers=True)
    poses = poses.cpu().numpy().astype(np.float64)
    poses[:, :3, 3] += centre                                   # back to the world frame

    approach = poses[:, :3, 2]
    ang = np.degrees(np.arccos(np.clip(-approach[:, 2], -1.0, 1.0)))
    print(f"{obj}: {len(poses)} samples · {int((ang > 90).sum())} point up "
          f"({100 * (ang > 90).mean():.0f} %) · {int((ang <= 60).sum())} inside the 60° cone")
    print(f"reference from our traces (data/per_trace_summary.csv): ~48 % up, ~23 % in cone")
    out = os.path.join(here, "..", f"graspgenx_{obj}.npz")
    np.savez_compressed(out, grasps=poses, scores=scores.cpu().numpy(), object_cloud=cloud)
    print("written", out)
    return 0

if __name__ == "__main__":
    raise SystemExit(main())
