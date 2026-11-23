---
name: fr3-duo-control
description: Franka Duo robot only (Franka Research 3 / FR3 Duo dual-arm cell with Robotiq 2F-85 grippers, ZED Mini and RealSense D405 cameras). Brings up, homes, and controls it via pylibfranka on hardware or in MuJoCo sim. Use only when the user names Franka Duo, FR3 Duo, or fr3_duo.
metadata:
  publisher: google
---

## Host compatibility

Read [agent runtime conventions](../../rules/agent_runtime.md) before first
execution. Resolve scripts relative to this skill directory; no specific agent
SDK, model vendor, or UI is required. Install only dependencies used by the
selected operation. Preserve hardware safety limits and operator checkpoints.


# Franka Research 3 Duo Control (`fr3_duo`)

Operate and program a dual-arm **FR3 Duo** (`left`/`right` 7-DOF FR3 arms, Robotiq 2F-85 grippers, overhead ZED Mini stereo camera, and wrist RealSense D405 RGB cameras) under `R1–R16` in [safety_rules.md](references/safety_rules.md) and [hardware_limits.md](references/hardware_limits.md). For offline `mode="sim"`, canonical `MjSpec` scenes, and live MuJoCo Studio workflows, see [mujoco_sim.md](references/mujoco_sim.md).

## 1. Setup Gate

1. **Offline sim only:** Run `Fr3DuoRobot(cfg, mode="sim")` directly (`default_robot_config()` works with no hardware or `config/robot_config.json`; set `MUJOCO_GL=egl` or `osmesa` on headless Linux for `render_sim_cameras`).
2. **Missing/incomplete `config/robot_config.json`, or bring-up/homing/diagnostics:** Follow [bringup_checklist.md](references/bringup_checklist.md) via [bringup.py](scripts/bringup.py) (`uv run scripts/bringup.py`, e.g. `--dry-run`, `--step geometry`, `--up-to all`, `--step home --yes`; orchestrates [discover_hardware.py](scripts/discover_hardware.py), [check_cameras.py](scripts/check_cameras.py), [check_robot.py](scripts/check_robot.py)). Split operator prompts cleanly across **two turns** during Stage 1 rather than dumping all checks at once:
   * **Turn 1 (connection prerequisite -> run `--step preflight --read-only`):** Confirm only left/right FR3 FCI IPs (stating robot vs. operator left/right) and that joints are unlocked, FCI is enabled, and physical E-stop is within reach. Let `--step preflight` auto-check tilted Desk gravity/payload, USB/RS-485 ports, cameras, and conflicting processes before asking the operator to intervene.
   * **Turn 2 (Stage 1b geometry -> run `--step geometry`):** Show/attach [fr3_duo_dimensions_reference.png](assets/fr3_duo_dimensions_reference.png) inline to the operator and confirm the 6 measurements in meters (`m`): `base_height_m`, `table_height_m` -> `z_table_m`, `table_front_offset_m`, `table_width_m`, `table_depth_m`, and `tcp_offset_z_m` (`0.145 m` stock 2F-85 silicone pads vs `0.185 m` extended fingers). Defer the optional `tmux` prompt (`R11`) until live motion stages.
   Before live hardware actuation or downstream skill composition, `config/robot_config.json` must satisfy `validate_robot_config_complete(cfg) == []` (`arms.{left,right}.{ip,gripper_port}`, all 3 `cameras.*` entries, and `geometry_confirmed=True`).
3. **Hardware already verified (`R2`, complete config):** Skip bring-up motion checks; run your task with `Fr3DuoRobot(cfg, mode="hardware", dry_run=True)` (or `Fr3DuoSafetyChecker`), then wait for explicit `"go"` (`R1`) before `dry_run=False`.

## 2. Canonical Contract, Coordinate Frames & Runtime Control API

* **Base frame (`base` / `franka_fr3_duo_world`):** `+X` forward across tabletop (`[0.15, 0.95] m`), `+Y` robot-left (`[-0.55, +0.55] m`; operator-right facing pedestal), `+Z` up (`z_table_m` typically `[-0.03, +0.05] m`). `left` and `right` are from the **robot's perspective (not the operator's when facing the pedestal)**—state both when prompting a human.
* **Joints, Grippers & Tool Center Point (TCP):** `state_16d` order is `[left_q1..q7, left_grip, right_q1..q7, right_grip]` (`{side}/fr3_joint1..7`). TCP is `{side}/robotiq_gripper_{side}/pinch_site` (`0.145 m` default `tcp_offset_z_m`); gripper `0.0 = 85 mm open`, `1.0 = 0 mm closed` (empty pinch stalls at `0.82–0.91`).
* **4 Canonical RGB Streams (`1280x720` USB/UVC):** `head_camera_left`, `head_camera_right` (split from `2560x720` ZED Mini stereo), `wrist_camera_left`, `wrist_camera_right` (`{side}/wrist_camera/wrist_camera_{side}` D405).
* **Python / `uv` Environment (`pylibfranka`):** `pylibfranka` ships pre-built Linux x86_64 wheels for Python `3.9–3.12` (`requires-python = ">=3.9,<3.13"` in [bringup.py](scripts/bringup.py)). Run `uv run scripts/bringup.py ...` directly, or pass `uv run --python 3.12 <task_script>.py` / create `.venv` with `--python 3.12` for custom task scripts.
* **Architecture (`Fr3DuoRobot` -> `Fr3DuoRealBackend` / `Fr3DuoSimBackend` -> Hardware Controllers + Services):**
  1. **Robot & Backends:**
     * [fr3_duo_robot.py](scripts/fr3_duo_robot.py): `Fr3DuoRobot(cfg, mode="sim"|"hardware", dry_run=False)` context manager validating moves via `Fr3DuoSafetyChecker` and dispatching to `Fr3DuoRealBackend` or `Fr3DuoSimBackend` (`read_state`, `recover_errors`, `render_sim_cameras`, `activate_grippers`, `move_gripper`, `move_arm_waypoints`, `move_bimanual_waypoints`). `Fr3DuoRealBackend` reads `state.current_errors` and attempts `pylibfranka.Robot.automatic_error_recovery()` on recoverable errors/reflexes; extend `fr3_arm_controller.py` + `fr3_duo_robot.py` when adding `pylibfranka` or real-backend features.
  2. **Hardware Controllers:**
     * [fr3_arm_controller.py](scripts/fr3_arm_controller.py): Core `pylibfranka` wrapper (`ArmWorkerProcess` isolated 1 kHz FCI worker, `read_pylibfranka_state`, `recover_pylibfranka_errors`, `audit_arm_desk_config`, `validate_arm_readiness`, `probe_arm_readonly`, `read_arm_joints_or_rest`).
     * [robotiq_gripper_controller.py](scripts/robotiq_gripper_controller.py): `RobotiqGripper`, `RobotiqStatus`, `resolve_serial_ports`, `select_gripper_ports`.
     * [fr3_camera_controller.py](scripts/fr3_camera_controller.py): `Fr3DuoCameraController` (freshness `<= 0.30 s`, side-by-side ZED stereo split), `render_contact_sheet`, `discover_uvc_devices`, `check_linux_usb_permissions`.
  3. **Services / Shared Utilities:**
     * [fr3_config.py](scripts/fr3_config.py): `RobotConfig`, `ArmConfig`, `ArmsConfig`, `CamerasConfig`, `DEFAULT_CONFIG_PATH`, `default_robot_config`, `load_robot_config`, `save_robot_config`, `normalize_robot_config`, `table_box_bounds`, `validate_robot_config_complete`, `detect_preempt_rt`, `resolve_realtime_config`.
     * [fr3_mjcf.py](scripts/fr3_mjcf.py): `build_fr3_duo_spec(cfg)` & `build_fr3_duo_mjcf(cfg)` (single canonical Menagerie `MjSpec` builder + sparse GitHub cache), `DEFAULT_REST_POSE_RAD`.
     * [fr3_kinematics.py](scripts/fr3_kinematics.py): `compute_arm_fk`, `compute_arm_pinch_from_flange`, `estimate_external_wrench_base`, `get_camera_calibration_opencv`, `project_base_points_opencv`.
     * [fr3_safety.py](scripts/fr3_safety.py): `FR3_HW_MAX_VEL_RAD_S`, `FR3_HW_MAX_ACC_RAD_S2` (`7.5` J1–J2, `9.5` J3–J7), `FR3_HW_MAX_JERK_RAD_S3` (`3500` / `4500`), `MIN_INTER_ARM_CLEARANCE_M` (`0.030`), `generate_quintic_trajectory`, `validate_joint_waypoints`, `AbortWatcher`, `Fr3DuoSafetyChecker`.

## 3. Composition Map (`rgb-object-localization` -> `motion-planning` -> `fr3_duo_robot` -> `visual-servoing` / `iteration`)

* **Perception & planning (`rgb-object-localization`, `motion-planning`, `visual-servoing`):** Pass `get_camera_calibration_opencv(...)` (`K`, `T_base_cam`) to `ray_plane_contour_pose`, `build_fr3_duo_mjcf(cfg)` to `mp.RobotArmPlanner(..., arm="left"|"right")` (`add_other_arm_to_scene`), and `wrist_camera_{side}` (`intrinsics_tuple`, `T_ee_cam`) to `ibvs.Ibvs`.
* **Iteration & Studio / Sim (`iteration`, `mujoco-studio-sidecar`, `sim2real-gauntlet`):** Stage scripts with 4-cam MP4 capture; build interactive Studio scenes via `fr3_mjcf.build_fr3_duo_spec` ([mujoco_sim.md](references/mujoco_sim.md)) or grade offline.

Import sibling `robotics` scripts relative to `skills/fr3-duo-control/` (`../rgb-object-localization/scripts`, `../motion-planning/scripts`, `../visual-servoing/scripts`; include `pillow` and `scipy` via `--with pillow --with scipy` or `.venv` when composing `motion-planning`):

```python
from pathlib import Path
import sys
import tempfile

_SKILLS_DIR = Path(__file__).resolve().parents[2]
for rel in ("fr3-duo-control/scripts", "motion-planning/scripts", "rgb-object-localization/scripts", "visual-servoing/scripts"):
  sys.path.insert(0, str(_SKILLS_DIR / rel))

from fr3_config import load_robot_config
from fr3_mjcf import build_fr3_duo_mjcf
from fr3_kinematics import get_camera_calibration_opencv
from fr3_duo_robot import Fr3DuoRobot
from fr3_safety import clamp_q_to_padded_limits
import motion_planner as mp
import rgb_localization
import ibvs

cfg = load_robot_config("config/robot_config.json")
mj_model, mjcf_xml = build_fr3_duo_mjcf(cfg)
tmp_xml = Path(tempfile.mkdtemp(prefix="fr3_mp_")) / "fr3_duo.xml"
tmp_xml.write_text(mjcf_xml, encoding="utf-8")
left_planner = mp.RobotArmPlanner(mjcf_path=str(tmp_xml), arm="left", gripper_cmd=0.0)
scene = mp.Scene3D()
table_center, table_half_extents = cfg.table_box_bounds()
scene.add_aligned_box("table", center=table_center, half_extents=table_half_extents, group="table")
with Fr3DuoRobot(cfg, mode="sim") as robot:  # pass dry_run=True to validate real moves offline first
  state = robot.read_state()
  left_planner.add_other_arm_to_scene(scene, other_arm_q=state["right"]["q_rad"], other_gripper_cmd=state["right"]["gripper_ratio"])
  cal = get_camera_calibration_opencv(mj_model, state["left"]["q_rad"], state["right"]["q_rad"])

  # 1. Localize target (OpenCV T_base_cam) or triangulate (MuJoCo mj_pose for mp.*)
  pose_3d = rgb_localization.ray_plane_contour_pose(mask_u8, cal["head_camera_left"]["K"], cal["head_camera_left"]["T_base_cam"], z_plane_m=float(cfg.z_table_m))
  table_pt = mp.intersect_ray_plane(640.0, 360.0, cal["head_camera_left"]["mj_pose"], cal["head_camera_left"]["mp_intrinsics"], plane_z=float(cfg.z_table_m))

  # 2. Plan & execute sparse waypoints (clamping J4 safety margin to [−2.9421, −0.2518])
  plan = left_planner.plan_arm(scene, state["left"]["q_rad"], q_pregrasp)
  safe_wps = [clamp_q_to_padded_limits(q).tolist() for q in plan["waypoints"]]
  robot.move_arm_waypoints("left", safe_wps)

  # 3. Close-range eye-in-hand IBVS alignment before grasp
  ibvs_left = ibvs.Ibvs(*cal["wrist_camera_left"]["intrinsics_tuple"])
  step = ibvs_left.compute_step(u, v, z_depth, u_goal, v_goal, cal["wrist_camera_left"]["T_ee_cam"])
```
