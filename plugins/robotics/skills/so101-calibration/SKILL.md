---
name: so101-calibration
description: >-
  Stage 5 3D hand-eye projection and tabletop surface height (z_table)
  calibration for the physical SO-101 6-DOF robot arm with a fixed/overhead
  workspace camera: fixed-camera check, two-cue gripper marker verification,
  guarded 3 mm vertical touch-down probing, and 3x4 projective hand-eye least
  squares. Use only after SO-101 Stage 3 bring-up when calibrating a physical
  SO-101 arm to a fixed camera. Don't use for non-robot camera or bed-leveling
  calibration.
metadata:
  publisher: google
---

## Host compatibility

Read [agent runtime conventions](../../rules/agent_runtime.md) before first
execution. Resolve scripts relative to this skill directory; no specific agent
SDK, model vendor, or UI is required. Install only dependencies used by the
selected operation. Preserve hardware safety limits and operator checkpoints.


# SO-101 Stage 5 (Optional · Requires Fixed Camera) — Tabletop Touch-Down & 3D Hand-Eye Calibration

After completing Stages 0–3 in [../so101-bringup/SKILL.md](../so101-bringup/SKILL.md) (including optional Stage 4: the USB bandwidth check and reference frames, which `R10` drift checks require) and following all safety rules (`R1–R16`) in [safety_rules.md](../so101-bringup/references/safety_rules.md), measure the physical tabletop height `z_table` and fit the 3D fixed/overhead camera projection matrix using [calibration_notes.md](references/calibration_notes.md):

1. **Step 0 — Verify Fixed/Overhead Camera Configuration**:
   - Check `NOTES.md` and `config/robot_config.json` (`get_fixed_camera_role_and_config` in [so101_common.py](scripts/so101_common.py)).
   - Stage 5 requires a stationary **fixed/overhead camera** viewing the arm and tabletop. If the human only set up a wrist camera (minimal 1-camera setup), stop with a clear message explaining that Stage 5 requires a fixed camera and ask whether they want to add one or finish at Stage 3 ("Hello World").

2. **Part A — Two-Cue Gripper Marker Verification ([detect_marker.py](scripts/detect_marker.py), `R9`, `R16`)**:
   - With motor torque OFF (`R16`), ask the human to place a unique high-contrast marker on the gripper **after the wrist joint** (e.g., a royal-blue triangle sticker or high-contrast Post-it triangle on the flat matte-white wrist camera mount plate) and verify `1` unique detection with `0` background false positives:
     ```bash
     python3 scripts/detect_marker.py --config config/marker_detect.json --image data/stage4/reference_overhead.png
     ```
   - **Cue 1 (marker colour & solidity):** Filters on chromatic BGR excess (`(B - G) >= min_b_minus_g`, `(G - R) >= min_g_minus_r`, `B >= min_b`) or custom `hsv_lower`..`hsv_upper` with a `3×3` dilation, bounded area, and convex-hull solidity.
   - **Cue 2 (mount surround contrast):** Checks the concentric annulus `r ∈ [10, 32] px` around each candidate centroid for bright matte-white pixels (`white_surround_fraction >= 0.35`) or high surround luminance contrast, rejecting background specks.

3. **Part B & Part C Dry-Runs + Single `"go"` for Touch-Down & 3D Hand-Eye Sweep ([measure_table.py](scripts/measure_table.py) & [calibrate_handeye.py](scripts/calibrate_handeye.py), `R1`, `R2`, `R5`, `R8`, `R10`)**:
   - Automatically run both `measure_table.py --dry-run` and `calibrate_handeye.py --dry-run` (`R2`) without asking for confirmation to validate planned FK tip heights (`SO101Follower.urdf`, `R8`), the **`-0.050 m` (`5 cm` below base plane) hard safety floor** (`R5`), and the multi-height workspace grid (`z_clearances_above_table_m = [0.035, 0.065] m`).
   - Ask the human to clear the central tabletop target patch (`patch_xy_m = [0.200, 0.000]`) and obtain a **single `"go"` (`R1`)** covering both Part B (`measure_table.py`) and Part C (`calibrate_handeye.py`):
     ```bash
     python3 scripts/measure_table.py --dry-run
     python3 scripts/calibrate_handeye.py --dry-run
     python3 scripts/measure_table.py
     python3 scripts/calibrate_handeye.py
     python3 scripts/calibrate_handeye.py --fit-from-log
     ```
   - **Part B (`measure_table.py`):** Descends vertically at `3.0 mm/step` (`<= 12°/s`), establishes a free-air gravity sag & servo load baseline over the first 4 probes, and halts immediately when `sag_excess`, `load_excess`, or Z-stall indicates contact, recording `z_table_m`, saving annotated contact images, unwinding back to `rest_pose` (`R3`), and turning torque off (`R4`).
   - **Part C (`calibrate_handeye.py`):** Combines the multi-height grid samples above `z_table_m` with the guarded touch-down contact sample (`Pose 0` at `z_table_m`) and fits a perspective-regularized (`reg_lambda = 500.0`) `3×4` projective matrix `M` (`fit_projective_handeye`) plus closed-form ray-plane unprojection `pixel_to_world_at_z(M, u, v, z_plane_m)`.

4. **Verification, Line-of-Sight Gate & Phase 2 Readiness (`R10`, `R14`)**:
   - Visually inspect `touchdown_contact_overhead.png`, `touchdown_contact_wrist.png`, and `handeye_calibration_grid.png` to verify contact location and projected tabletop metric grid alignment.
   - Confirm `rmse_reprojection_px` (`<= 8.0 px`, hold-out `< 15.0 px` under `R10`) and `rmse_localization_mm` (`< 3.0 mm` at `z_table_m`), and confirm `robot.bus` `Present_Position` returned within `5°` of `rest_pose` with `Torque_Enable = 0`.
   - Report Stage 5 completion using the 6-field `R14` format before proceeding to Phase 2 vision-guided pick-and-place.

5. **Coordinate Conventions & Safety Invariants**:
   - Robot base frame (`gripper_frame_link`): `+X` forward from base, `+Y` left, `+Z` upward (`z_table_m` typically ~`-0.024 m` below shoulder base origin).
   - Fixed/overhead camera pixels `(u, v)` follow top-left image origin (`1280×720`); `pixel_to_world_at_z` unprojects any tabletop pixel `(u, v)` onto horizontal plane `Z = z_plane_m`.
   - All shared calibration and trajectory helpers live in [so101_common.py](scripts/so101_common.py); never lower `z_hard_floor_m` below `-0.050 m` or modify `SO101Follower` gripper current/torque limits.
