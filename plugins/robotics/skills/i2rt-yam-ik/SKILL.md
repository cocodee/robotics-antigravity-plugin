---
name: i2rt-yam-ik
description: Solves 6-DOF inverse kinematics for the I2RT YAM and YAM Pro robot arm using Mink + DAQP on combined YAM + gripper MJCF. Use only when computing joint targets or local Cartesian moves on an I2RT YAM or YAM Pro robot arm. Don't use for non-YAM inverse kinematics, general quadratic programming (QP) solvers, or non-robotics tasks.
metadata:
  publisher: google
---

## Host compatibility

Read [agent runtime conventions](../../rules/agent_runtime.md) before first
execution. Resolve scripts relative to this skill directory; no specific agent
SDK, model vendor, or UI is required. Install only dependencies used by the
selected operation. Preserve hardware safety limits and operator checkpoints.


# I2RT YAM Inverse Kinematics (`mink` + `daqp` via [`YamIk`](scripts/yam_ik.py))

Use bundled [`YamIk`](scripts/yam_ik.py) (`pip install mink daqp mujoco`, `<1 ms`/solve on Linux & macOS) parameterized by `arm_type` (`"yam"` or `"yam_pro"`) and `gripper_type` (`"linear_4310"`, `"crank_4310"`, `"linear_3507"`, `"flexible_4310"`, etc.) via `combine_arm_and_gripper_xml` — **never** load standalone `yam.xml` when driving a gripper-equipped arm because bare `yam.xml` has `nsite = 0`:

1. **`grasp_site` Frame Convention & Jaw-Closing Axis (`±Y_site`, NOT `+X_site`)**:
   - YAM has 3 parallel pitch axes (`J2 || J3 || J4`) and a `74.0 mm` `J4-J5` non-spherical wrist offset.
   - In `i2rt` gripper MJCFs, `+Z_site` is the forward approach vector and **parallel-jaw fingers open/close along `grasp_site` `±Y_site` (NOT `+X_site`)**.
   - Use `ik.make_grasp_pose(pos, approach_dir, jaw_perp_axis=...)` (for arbitrary 3D approach vectors — top-down, angled, or side grasps) or `ik.make_topdown_grasp_pose(x, y, z, obj_yaw_rad=None, tilt_deg=0.0)` (`tilt_deg=10–15` near outer reach `>75%`):
     - Pass `jaw_perp_axis=None` (`obj_yaw_rad=None`) for symmetric objects to keep wrist roll `J6` near neutral `0`.
     - For anisotropic objects where jaws must close perpendicular to a target axis `a`, pass `jaw_perp_axis=a` (`+X_site || ±a` so `±Y_site` closes across the object, automatically wrapped by `±pi` using the loaded MJCF's neutral `+X_site` at `J6 = 0` so `J6` stays inside `[-2.094, 2.094] rad`).
2. **Reliable Seeding & Mandatory FK Verification ([yam_ik.py](scripts/yam_ik.py))**:
   - Instantiate `ik = YamIk(arm_type=..., gripper_type=...)` once and call `q_goal = ik.solve(T_target, q_seed=...)`.
   - `Q_DEFAULT_SEED = [0.0, 1.2, 1.2, -1.2, 0.0, 0.0]` avoids stalling against `J4 in [-1.693, 1.571] rad` on downward grasps; pass `q_seed=q_actual[:6]` for local moves so `PostureTask` regularizes smoothly around the current configuration.
   - `YamIk.solve` enforces `solver="daqp"`, `ConfigurationLimit`, non-adjacent self-collision limits, frozen gripper DOFs (clamped to each model's `jnt_range`), fresh re-seeding every call, and strict MuJoCo FK verification (`pos_err <= 2 mm`), raising `ValueError` before motion if any phase waypoint is unreachable.
