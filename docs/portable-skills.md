# 通用 Agent 技能

本仓库的技能说明使用 `SKILL.md`，实现主要是 Python。具备文件读写和
命令执行能力的 Agent 可以使用这些技能；图像任务还需要图像查看能力。
普通聊天客户端仅加载说明不会获得本地执行、相机或机械臂访问能力。

## 哪些可以复用

逐项依赖与实现方式见[各技能的依赖与实现方式](skill-dependencies-and-implementation.md)。

| 分类 | 技能 | 条件 |
|---|---|---|
| 感知与控制 | rgb-object-localization、motion-planning、visual-servoing、i2rt-yam-ik | 相机标定、NumPy/OpenCV 或相应 IK/规划依赖；几何代码不依赖模型 API |
| 仿真与训练 | mujoco-playground、mujoco-playground-rl | MuJoCo、Playground/reaf-sim；训练按任务需要 GPU、Warp、RSL-RL |
| 验证与迭代 | iteration、sim2real-iteration、sim2real-gauntlet | 前两者主要是流程，Gauntlet 包提供可运行的验证代码 |
| 资产制作 | blender-creation、mujoco-audit、mujoco-showcase-shot | Blender、MuJoCo 以及所用版本的渲染 API |
| 硬件操作 | so101-bringup、so101-calibration、i2rt-yam-bringup、fr3-duo-control | 对应机器人、SDK、通信接口、相机和操作人员检查 |
| 可视化 | mujoco-studio-sidecar | Python studiod 可独立运行，使用实际端口的浏览器 URL |
| 示例分享 | share-example | 普通文件和视频；客户端会话导出为可选输入 |

`plugins.json`、`plugin.json` 和 `sidecars/mujoco_studio` 的 Node UI 代理是
Antigravity 适配层，不作为通用技能导出。保留它们以兼容原插件。

## 导出与安装

从仓库根目录运行，无需安装第三方 Python 包：

```bash
python3 tools/export_skills.py --output ./dist/robotics-skills
```

输出是 18 个技能目录及许可证。脚本不会覆盖已有目录。每个技能包含自己
引用的规则副本；技能间的组合依赖仍通过同级目录引用。建议安装完整集合，
不要只复制一个 `SKILL.md` 或忽略其脚本、参考文件。

对支持本地 `SKILL.md` 的客户端，将导出的技能目录放入客户端指定的技能
搜索目录。Codex 的常见位置为 `~/.codex/skills/`；避免覆盖同名技能，保留
导出目录中的 LICENSE。其他客户端采用各自的加载方式。
不支持技能发现的 Agent 可以从目标 `SKILL.md` 开始按需读取引用文件，并通过
其终端工具执行脚本。无需加载 Antigravity 插件清单。

这不是 ChatGPT 网页聊天的插件安装包，也不是 MCP server。如果要让仅支持
远程工具调用的客户端使用这些功能，还需单独提供执行服务或 MCP 适配器。

## 调用功能

路径均相对于安装后的技能目录，例如：

```bash
python3 <skills-dir>/mujoco-studio-sidecar/scripts/studiod.py --workspace_dir=<workspace-dir>
python3 <skills-dir>/mujoco-audit/scripts/audit_scenarios.py --help
```

先检查所选命令和依赖。Gauntlet 可作为独立 Python 包安装：

```bash
python3 -m pip install -e <skills-dir>/sim2real-gauntlet
```

RGB 定位脚本提供 `ray_plane_contour_pose`、`fit_plane_homography`、
`map_homography_xy_and_yaw` 和 `triangulate_matched_points` 等函数；
它不直接调用 Gemini 或 OpenAI。由 Agent 或可选感知服务提供图像目标信息，
再由标定后的几何计算获得三维结果。无需为“GPT 兼容”替换这些数学实现。

官方 MuJoCo API 技能仍需从 MuJoCo 仓库或对应 Python 包的 `doc/skills`
获取，详见根 README。所需依赖和硬件约束保留在各技能中。

## 迁移范围与验证边界

技能已加入共同的运行约定；专有工具名改为能力描述；资产制作和审计可由
单个 Agent 执行；Studio 提供浏览器 URL；分享不再要求读取客户端内部日志。
物理机器人安全规则和操作检查保留。

导出和文档结构检查不等于机器人功能验证。完整仿真、GPU 训练和实机流程
仍需在具备对应依赖及硬件的环境中验证。远程 Studio 需要客户端端口转发。
