---
name: so101-bringup
description: >-
  Guides physical SO-101 6-DOF robot arm bring-up from plug-in to Stage 3 Hello
  World motion and video: uv install, port/camera discovery (Stages 0-1),
  Feetech STS3215 joint calibration and abort-retreat checks (Stage 2), Hello
  World (Stage 3), and workspace USB bandwidth/frame checks (Stage 4). Use only
  when setting up, calibrating, checking, or operating an SO-101 robot arm and
  cameras. Don't use for non-SO-101 webcam, CNC, or 3D printer tasks.
metadata:
  publisher: google
---

## Host compatibility

Read [agent runtime conventions](../../rules/agent_runtime.md) before first
execution. Resolve scripts relative to this skill directory; no specific agent
SDK, model vendor, or UI is required. Install only dependencies used by the
selected operation. Preserve hardware safety limits and operator checkpoints.


# SO-101 Hardware Bring-Up, Camera Verification & Stage 3 "Hello World"

Follow this staged workflow under `R1–R16` (auto-advancing across software, `--dry-run`, and read-only steps without extra confirmation prompts) to bring up an **SO-101 follower arm** (`so101_follower`, 6× Feetech STS3215 servos) and **1 or more cameras** (minimal setup: arm + 1 camera; recommended setup: fixed/overhead + wrist camera) using [safety_rules.md](references/safety_rules.md), [hardware_limits.md](references/hardware_limits.md), and [tabletop_pick_place.json](references/tasks/tabletop_pick_place.json). The fast path to Hello World is Stage 0 → 1 → 2 → 3; optional Stage 4 runs afterwards (required before Stage 5):

1. **Stage 0 — Environment, `NOTES.md` & Dedicated `tmux` Session `robot` (`R11–R16`, auto-advances to Stage 1)**:
   - Summarize safety and working rules `R1–R16` from [safety_rules.md](references/safety_rules.md) before touching hardware.
   - Install with `uv` and shallow clones. LeRobot provides `lerobot-find-port`, `lerobot-calibrate`, motor drivers, and forward/inverse kinematics (`RobotKinematics`, `kinematics` extra); SO-ARM100 is only needed for the URDF and its meshes, so sparse-checkout `Simulation/SO101`. Check `ffmpeg`, and initialize `NOTES.md` and git (`R12`, `R13`):
     ```bash
     uv venv .venv && source .venv/bin/activate
     git clone --depth 1 https://github.com/huggingface/lerobot repos/lerobot
     uv pip install -e "repos/lerobot[feetech,kinematics]" opencv-python numpy
     git clone --depth 1 --filter=blob:none --sparse https://github.com/TheRobotStudio/SO-ARM100 repos/SO-ARM100
     git -C repos/SO-ARM100 sparse-checkout set Simulation/SO101
     ```
   - Create a persistent `tmux` session named `robot` (`tmux new-session -d -s robot`), verify two-way command/capture (`tmux send-keys` + `tmux capture-pane`), tell the human how to watch live (`tmux attach -t robot`), and proceed directly to Stage 1 without waiting for sign-off.

2. **Stage 1 — Read-Only Serial Bus & Camera Discovery (Torque OFF, `R4`, `R16`)**:
   - Auto-detect the serial port with [read_motors.py](scripts/read_motors.py)
     `--port auto` (uses the single `/dev/tty.usbmodem*` or `/dev/ttyACM*`
     device) to verify all 6 STS3215 servos (IDs `1..6` at `1,000,000` baud)
     respond with `Torque_Enable = 0` and read their EEPROM calibration into
     LeRobot's default calibration cache when valid (`calibration_valid: true`
     and `calibration_file` in `motors_readonly.json`). Only if zero or several
     candidates are found, fall back to `lerobot-find-port` inside `tmux`
     session `robot` (human unplugs/re-plugs USB):
     ```bash
     python3 scripts/read_motors.py --port auto --output data/stage1/motors_readonly.json
     ```
   - Automatically enumerate OS cameras, capture stills (`camera_0.png`, `camera_1.png`, ...), and check lighting brightness (`0–255`, flagging `TOO_DARK` or `TOO_BRIGHT_OR_GLARE`) using [discover_cameras.py](scripts/discover_cameras.py). If exactly 1 camera is found, use it without asking (role `wrist` if the jaw tips are visible at the bottom of the still, otherwise `fixed`). Ask the human about roles only when 2 or more cameras are found or a laptop built-in camera is detected (not recommended; it must stay completely still facing the robot).
   - Save the port, `calibration_file` (and `rest_pose` when computed from
     EEPROM), camera roles/indices, and stills in `config/robot_config.json`
     and `NOTES.md`.

3. **Stage 2 — Joint Calibration, `rest_pose` & Abort Key (`R1–R5`, single `"go"` for bring-up motion)**:
   - Reuse motor EEPROM calibration by default without asking the human to
     recalibrate: if `data/stage1/motors_readonly.json` reports
     `calibration_valid: true` (or a valid calibration file already exists in
     LeRobot's cache and matches EEPROM via `run_preflight()`), reuse
     `calibration_file` and skip `lerobot-calibrate`. Otherwise (uncalibrated
     EEPROM or explicit recalibration request), with torque OFF (`R16`), run
     `lerobot-calibrate` inside `tmux` session `robot` (human moves arm to
     middle of joint ranges + `Enter`, then sweeps full min-to-max ranges +
     `Enter`) and flag any body joint with span `< 45°` (or gripper `< 20°`):
     ```bash
     lerobot-calibrate --robot.type=so101_follower \
       --robot.port=/dev/tty.usbmodem... --robot.id=my_follower
     ```
   - Automatically run `--mode abort-test --dry-run` (`R2`, torque OFF, planned from the Stage 1 read-only snapshot) without asking for confirmation, then ask the human once for `"go"` (`R1`, covering `--mode abort-test` and Stage 3 `hello_world.py` while the workspace remains clear; any `connect()` turns torque ON, so nothing connects before the `"go"`). Run a single slow `5°` base nudge with [check_robot.py](scripts/check_robot.py) during which the human types `q` + `Enter`; the script records `rest_pose` before moving:
     ```bash
     python3 scripts/check_robot.py --mode abort-test --dry-run
     python3 scripts/check_robot.py --mode abort-test
     ```
   - Confirm that `q` + `Enter` triggers an immediate smooth unwind along `travelled_waypoints` back to `rest_pose` (`R3`) and sets `Torque_Enable = 0` (`R4`), then proceed directly to Stage 3.

4. **Stage 3 — "Hello World" Motion & Video (Minimal-Setup Milestone, `R1–R8`, auto `--dry-run` + covered by Stage 2 `"go"`)**:
   - Works with the **minimal setup (arm + 1 camera, e.g., wrist camera)** or the 2-camera setup using [hello_world.py](scripts/hello_world.py) (or `check_robot.py --mode hello-world`). Its built-in pre-flight (`R6`) verifies all 6 servos, the calibration, and `<= 0.30 s` frame freshness on every configured camera before torque ON.
   - Run `--dry-run` automatically without asking (`R2`), then execute live `hello_world.py` under Stage 2's powered-motion `"go"` (only re-asking under `R1` if pre-flight failed or the human entered the workspace): start timestamped MP4 video recording (`logs/stage3_hello_world_wrist.mp4`, `R7`) before leaving `rest_pose`, move smoothly from `rest_pose` to the **calibration midpoint (`0.0°` on all 5 body joints)** within `R5` limits (`<= 45°/step`, `<= 90°/s`, `5°` margin, FK height floor), **open and close the gripper jaws once**, return smoothly to `rest_pose`, and disable motor torque (`R4`):
     ```bash
     python3 scripts/hello_world.py --config config/robot_config.json --dry-run
     python3 scripts/hello_world.py --config config/robot_config.json --output-mp4 logs/stage3_hello_world_wrist.mp4
     ```
   - Inspect start, midpoint, and end video frames before reporting Stage 3 with the 6-field `R14` report.

5. **Stage 4 (Optional: After Hello World, Required Before Stage 5) — USB Topology/Bandwidth, Reference Frames & 10-Second Video (`R6`, `R7`, `R10`)**:
   - Automatically inspect the OS USB tree (`system_profiler SPUSBDataType` / `lsusb -t`), compare `YUYV` vs `MJPG` bandwidth against USB 2.0 (`480 Mb/s` theoretical / `~320 Mb/s` usable), and benchmark live streaming FPS and frame gaps across all configured cameras using [benchmark_cameras.py](scripts/benchmark_cameras.py):
     ```bash
     python3 scripts/benchmark_cameras.py --config references/tasks/tabletop_pick_place.json
     ```
   - Automatically check lighting/glare diagnostics and save baseline reference frames for drift detection (`R10`) with [check_cameras.py](scripts/check_cameras.py), then record a 10-second timestamped MP4 + JSONL stream with [record_overhead.py](scripts/record_overhead.py). If a fixed/overhead camera is configured, proceed to optional Stage 5 in [../so101-calibration/SKILL.md](../so101-calibration/SKILL.md):
     ```bash
     python3 scripts/check_cameras.py --config references/tasks/tabletop_pick_place.json --save-references
     python3 scripts/record_overhead.py --config references/tasks/tabletop_pick_place.json --duration-sec 10.0
     ```

6. **Configuration & Safety Invariants**:
   - All shared helper functions live in [so101_common.py](scripts/so101_common.py); never import internal monorepo-specific libraries inside plugin scripts or tests.
   - Keep `max_step_deg <= 45.0` (`20.0–30.0` default), `max_speed_deg_per_sec <= 90.0` (`30.0` default), `joint_margin_deg >= 5.0` (never blocking moves away from or back to a `rest_pose` that sits inside the margin), and `rest_tolerance_deg <= 5.0` across bring-up motion configs. Stage 5 guarded touch-down (`<= 12°/s`) and hand-eye sweep (`<= 15°/s`) stay slow.
   - Leave STS3215 motor torque **ON** and print an explicit human warning if any exit path cannot verify return to `rest_pose`.
