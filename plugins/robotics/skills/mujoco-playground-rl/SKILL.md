---
name: mujoco-playground-rl
description: >-
  Authors, inspects in MuJoCo Studio, audits, trains, and deploys
  GPU-accelerated RL tasks on MuJoCo Playground and MuJoCo Menagerie 3D robots
  using PyTorch/Warp reaf-sim flat_scene (DeviceLayer / TaskLayer) and RSL-RL.
  Use by default when creating a MuJoCo Playground RL environment, training or
  evaluating locomotion/manipulation RL policies, or deploying RSL-RL
  checkpoints. Don't use for non-RL controllers (use mujoco-playground) or
  non-MuJoCo RL.
metadata:
  publisher: google
---

## Host compatibility

Read [agent runtime conventions](../../rules/agent_runtime.md) before first
execution. Resolve scripts relative to this skill directory; no specific agent
SDK, model vendor, or UI is required. Install only dependencies used by the
selected operation. Preserve hardware safety limits and operator checkpoints.


# MuJoCo Playground RL Task Authoring & Training ([`rl_task_check.py`](scripts/rl_task_check.py))

Create, interactively verify in MuJoCo Studio, audit, train (`Impl.WARP` + RSL-RL), and deploy new RL tasks on any `mujoco_menagerie` robot (floating-base quadrupeds/humanoids or fixed-base arms) in `mujoco_playground`:

1. **Workspace & Accelerator Setup**:
   - Clone and sync: `git clone https://github.com/google-deepmind/mujoco_playground.git && cd mujoco_playground && make sync` (or `make sync-cu12` on Linux CUDA 12 drivers `< 580`, or `make sync-cpu` on macOS for authoring, Studio inspection, CPU smoke tests, and checkpoint playback; pass `--default-index https://pypi.org/simple` to `uv` and `--no-sync` to `uv run`).

2. **Robot Scene, MuJoCo Studio Inspection, & `DeviceLayer` (`mujoco_playground/robots/<robot>/sim/{device,scene}.py`)**:
   - Load `spec = asset.get("github:google-deepmind/mujoco_menagerie/<dir>/<file>.xml").spec()`. Name unnamed geoms (`f"{body.name}_geom_{i}"`), ensure any freejoint is named (`"root"`), add a `"terrain"` plane geom on `worldbody` if absent, set `spec.option.timestep = 0.004` (`control_timestep = 0.02`, `decimation = 5`) and `mjINT_IMPLICITFAST`, and size `cfg.sim.nconmax` / `cfg.sim.njmax` (`tolerance = 1e-8`, `ls_tolerance = 0.01`, keeping default solver iteration caps).
   - Replace torque `<motor>`s with PD position servos (`for a in list(spec.actuators): spec.delete(a)`, `add_actuator(name=j, target=j)` with `trntype=mjTRN_JOINT`, `gaintype=mjGAIN_FIXED`, `biastype=mjBIAS_AFFINE`, `gainprm[0]=kp`, `biasprm[1]=-kp`, `biasprm[2]=-kd`, `ctrllimited=False`, `forcelimited=True`, `forcerange=[-effort, effort]`; e.g. `kp=25.0, kd=0.5, armature=0.01` for quadrupeds), lower high passive torque-model joint `damping`/`frictionloss` (e.g. `damping=0.1, frictionloss=0.0`), filter self-collisions via `contype/conaffinity` bitmasks, and add an `"init_state"` standing keyframe.
   - **Interactive Studio Verification (`mujoco-studio-sidecar` +
     `mujoco-studio`)**: Load **`mujoco-studio-sidecar`** and
     **`mujoco-studio`** to inspect and
     hot-reload the robot `MjSpec` (publishing the spec from
     `SimPlugin.on_load_model` in `<workspace_dir>/sim_plugin.py`, checking
     standing keyframe stability, PD gains, contacts, and custom
     `ViewerPlugin`s) in `[MuJoCo Studio Web](http://127.0.0.1:<http_port>/)`
     by launching `<mujoco-studio-sidecar>/scripts/studiod.py
     --workspace_dir=<dir>` with `<playground_dir>/.venv/bin/python`
     (the host's background-process option, checking `/_studio/status` after edits) before batch
     training.
   - Wire `reaf.simulation.torch` (`reaf_sim`) devices via `flat_scene.Component` (never pass `name=`, `nworld=`, or `xpu_device=`):
     - `reaf_sim.ActuatorDevice(targets=list(JOINT_NAMES), measurements=["joint_pos", "joint_vel"])` (`"robot"` -> `"robot/ctrl"`, `"robot/joint_pos"`, `"robot/joint_vel"`).
     - Floating base: `reaf_sim.FreeDevice(body_name="base", joint_name="root", measurements=["xpos", "xquat", "joint_vel"])` (`"base"` -> `"base/xpos"`, `"base/xquat"` `[w,x,y,z]`, and `"base/joint_vel"` where `[:, :3]` is **world** linear velocity -> `reaf_sim.math.quat_rotate_inverse(quat, vel[:, :3])`, while `[:, 3:6]` is **already body-frame** angular velocity).
     - Contacts: `flat_scene.Component(reaf_sim.ContactSensorDevice, fields=("found", "force"), history_length=decimation).configure_spec(objtype="geom", objname=..., reftype="geom", refname="terrain")` on feet and body/limb geoms.

3. **Sync-Free `TaskLayer` (`mujoco_playground/tasks/<category>/<task>/{task,mdp}.py`)**:
   - Actions: `command_feature_producers={"action_history": flat_scene.Component(reaf_sim.ActionHistory, key="action", feature_shape=(num_joints,), history_length=1)}` (`f["action"]` is `a_t`, `f["action_history"][:, 0]` is `a_{t-1}`) and `command_processors={"action_scale": flat_scene.Component(reaf_sim.TransformActions, input_key="action", output_key="robot/ctrl", scale=0.25, offset=DEFAULT_JOINT_POS)}`.
   - Stateful Producers & Observations: Subclass `reaf_sim.FeatureProducer` implementing `name`, `produced_features_spec` (per-world shapes **without** `nworld`), `required_features_keys` (consume `"time"` and step timers by `dt = (t - self._last_time).clamp(min=0.0)` so partial resets are idempotent), `produce_features`, and `reset`; wrap reward/critic-only producers with `.mark_privileged()` so `make_deployment_config` prunes them.
   - Sync-Free GPU Rules: Never call `.item()`, `.cpu()`, `.numpy()`, `.new_tensor()`, `bool()`, `.any()`, or `.all()` inside `step`/`obs_*`/`reward_*`; build gravity via `g = torch.zeros((n, 3), device=q.device, dtype=q.dtype); g[:, 2] = -1.0` and cache CPU `flat_scene.Obs` tensor kwargs per `(device, dtype)`. Configure `ObsGroup`s (`"policy"` noisy, `"critic"` clean) with `.configure(output_shape=(D,))` on every `flat_scene.Obs` (actor: body `ang_vel`, `projected_gravity`, `command`, `joint_pos - default_pos`, `joint_vel`, `action`; critic adds body `lin_vel`).
   - Rewards, Terminations, & Reset: Combine `exp(-||v_xy - cmd_xy||^2 / 0.25)` (`1.5`), `exp(-(w_z - cmd_wz)^2 / 0.25)` (`0.75`), `v_z^2` (`-2.0`), `||w_xy||^2` (`-0.05`), `||g_proj_xy||^2` (`-2.5`), `||a_t - a_{t-1}||^2` (`-0.01`), `||qvel||^2` (`-1e-4`), stand-still `||q - q_def||_1 * (||cmd|| < 0.05)` (`-0.5`), and undesired contacts (`-1.0`); `FunctionalRewardProvider` multiplies terms by `control_dt`, so divide touchdown impulses by `control_dt`. Terminate on falls (`g_proj[:, 2] > -0.3` or `z < min_z`) via `torch.where(..., TerminationResult.TERMINATE, TerminationResult.DO_NOT_TERMINATE)`, and reset standing `qpos`/`qvel` in `EnvironmentReset.on_reset` via `torch.where(env_mask.unsqueeze(1), ...)`.

4. **Register, Validate, Train, Preview in Studio, & Deploy**:
   - Add an `RslRlOnPolicyRunnerCfg` dataclass in `_src/rl/rsl_rl/env_rl_config.py` (`obs_groups={"actor": ["policy"], "critic": ["critic"]}`, `vecenv_wrapper_cfg=RslRlVecEnvWrappercfg(is_finite_horizon=False)`, `nworld=4096`, `num_steps_per_env=24`, `actor/critic.hidden_dims=(256, 128, 128)`, `obs_normalization=True`) and register an **uncalled** `env_cfg_fn` in `_src/rl/env_registry.py`.
   - Audit & smoke-test (CPU + `torch.cuda.set_sync_debug_mode("error")` `Impl.WARP` + `make_deployment_config`): `uv run --no-sync python <skill_dir>/scripts/rl_task_check.py --repo_root=. --task_dir=mujoco_playground/tasks/<category>/<task> --env_id=<EnvId>`.
   - Train & preview in MuJoCo Studio: `WP_CACHE_PATH=/tmp/wp_cache uv run --no-sync python -m mujoco_playground.rl.rsl_rl.train --env=<EnvId> --wp_kernel_cache_dir=/tmp/wp_cache --logdir=/tmp/rslrl_logs/<run>`. Preview checkpoints interactively in MuJoCo Studio via `uv run --no-sync python -m mujoco_playground.rl.rsl_rl.play --env=<EnvId> --resume_path=... --gfx=web --hot_reload=plugins` (or `--gfx=""` for native desktop Studio, authoring custom `ViewerPlugin`s per `mujoco-studio`), or deploy with `flat_scene.make_deployment_config(cfg, observation_groups=("policy",))` + `wrapper.TorchDeviceLayerWrapper`.
