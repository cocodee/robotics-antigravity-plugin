---
name: i2rt-yam-bringup
description: >-
  Checks and installs the I2RT YAM SDK (i2rt), configures Linux socketcan or
  macOS gs_usb CAN bringup for I2RT YAM robot arms, and provides a wave smoke
  test (wave.py). Use only before bringing up or programming a physical or
  simulated I2RT YAM robot arm, or when asked to run a wave gesture on an I2RT
  YAM robot. Don't use for non-YAM CAN bus debugging (e.g. automotive OBD-II or
  industrial PLC CAN networks) or non-robotics tasks.
metadata:
  publisher: google
---

## Host compatibility

Read [agent runtime conventions](../../rules/agent_runtime.md) before first
execution. Resolve scripts relative to this skill directory; no specific agent
SDK, model vendor, or UI is required. Install only dependencies used by the
selected operation. Preserve hardware safety limits and operator checkpoints.


# I2RT YAM SDK & CAN Bringup

Ensure the official I2RT YAM Python SDK (`i2rt`) and host CAN transport are ready before running YAM robot code (`i2rt` drives physical YAM Damiao motors over 1 Mbps CAN via `python-can`; only `get_yam_robot(..., sim=True)` runs without CAN):

1. **SDK Check & Install**:
   - Check `python3 -c "from i2rt.robots.utils import ArmType, GripperType; print('i2rt ready')"`.
   - If missing (`i2rt` is not on PyPI), clone `git clone https://github.com/i2rt-robotics/i2rt.git` and install with `pip install -e ./i2rt` (or `pip install --no-deps --no-build-isolation -e ./i2rt` plus `numpy mujoco mink ruckig python-can pyyaml portal crcmod-plus dm-env` if `pyproject.toml` pins conflict with host Python).

2. **Real-Hardware CAN Bringup (Linux `socketcan` vs. macOS [`macos_can.py`](scripts/macos_can.py))**:
   - **Linux**: Bring up `socketcan` at 1 Mbps (`sudo ip link set can0 up type can bitrate 1000000`) and pass `channel="can0"` to `get_yam_robot`.
   - **macOS (Apple Silicon & Intel)**: `i2rt`'s `get_yam_robot` and `run_startup_checks` require `"can"` in `channel` and hardcode `bustype="socketcan"`, which macOS lacks; moreover, `python-can`'s built-in `GsUsbBus` calls `detach_kernel_driver(0)` (`Access denied` without `sudo`) and `dev.reset()` (wedging `gs_usb` STM32 `EP 0x81` when TX echoes are unread).
   - On macOS, ensure `libusb` and `gs-usb` are installed (`brew install libusb && pip install gs-usb pyusb` for candleLight / CANable / I2RT USB-CAN adapters) and call `install_mac_can()` from bundled [`macos_can.py`](scripts/macos_can.py) once before `get_yam_robot(channel="can0", ...)`:
     - Safe no-op on Linux; auto-discovers `libusb-1.0.dylib` across `/opt/homebrew/lib`, `/usr/local/lib`, and `/opt/local/lib` inside isolated `venv`/`conda` environments without `DYLD_LIBRARY_PATH`.
     - Maps `"can0"`, `"can1"`, ... deterministically across single or bimanual `gs_usb` adapters without `detach_kernel_driver` or `dev.reset()`, filters TX echoes (`echo_id != GS_USB_NONE_ECHO_ID`), drains `clean_error` bursts, runs a silent motor-independent `GS_CAN_MODE_LOOP_BACK` health check (with DFU auto-recovery only if `EP 0x81` is wedged), and also supports PCAN (`interface="pcan"`) or SLCAN (`interface="slcan", backend_channel="/dev/cu.usbmodem..."`).


3. **Safe Shutdown**:
   - Park the arm gently near the table before calling `robot.close()` so it never drops (since `robot.close()` sets all motor torques to zero).

4. **Bring-Up Wave Task ([`wave.md`](references/tasks/wave.md), [`wave.py`](scripts/wave.py))**:
   - Run [`wave.py`](scripts/wave.py) (`--sim` offline or `--channel can0` on
     hardware) for a free-space wave smoke test; see
     [`references/tasks/wave.md`](references/tasks/wave.md) for keyframes and
     flags.
