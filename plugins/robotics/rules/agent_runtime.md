# Agent runtime conventions

These skills support agents that can read files and execute local commands.
Image-based workflows additionally require image inspection; web reference
intake requires browsing or user-provided reference files. A chat-only client
cannot execute the Python helpers without a connected execution environment.

## Paths and tools

- `<skill_dir>` is the directory containing the active `SKILL.md`.
- `<PLUGIN_DIR>` / `$PLUGIN_DIR` means the parent of the installed `skills/`
  directory in the original layout. In a flat skill installation, resolve
  `<PLUGIN_DIR>/skills/<name>` to the sibling `<name>` skill directory instead.
  Substitute example placeholders before running commands; they are not shell
  variables supplied automatically by a client.
- `<ArtifactDir>` is a task-specific output directory chosen by the user or
  created by the agent. Use a temporary directory for scratch work and keep
  deliverables in the requested workspace. No application-specific brain or
  conversation directory is required.
- Use the host's terminal, file, image, web, and process tools by capability;
  tool names in upstream examples are not required APIs. Inspect video frames
  with timestamps when native video input is unavailable, and disclose that
  reduced coverage. Never claim to have viewed media without inspecting it.
- Delegation is optional. Execute work in the current agent when no worker
  facility is available or authorized. Long-running services need a supported
  process/session manager; record how to stop them.

## Execution and dependencies

Inspect helper imports and the selected workflow before installing dependencies.
Use an isolated Python environment. MuJoCo, Blender, robot SDKs, cameras,
GPU training stacks, and MuJoCo's official API skills are external dependencies,
not capabilities provided by an LLM. Do not assume a particular SDK or rendering
API exists in the installed version. Report missing or incompatible features.

Geometry, IK, planning, and local segmentation helpers are model-independent.
The Gemini perception example is optional; merely finding an API key does not
select that provider. Other providers or host vision may produce detections,
but coordinate conventions and calibration must be validated independently.
Never upload camera frames to an external provider without task authorization.

## Studio and physical robots

Studio's Python daemon supports a direct HTTP viewer without the Node sidecar.
Read the actual `http_port` and `control_port` from its session file. The viewer
and control API use different ports. Return a browser URL, or a forwarded URL
for remote execution; a guessed port or proprietary link is not sufficient.
The Antigravity Node sidecar remains an optional host adapter.

Default to simulation when no physical robot operation has been requested.
Retain each robot's safety rules, limits, calibration requirements, stop
procedures, and operator confirmations. A portable skill never grants hardware
access or permission to bypass the host's security boundaries.
