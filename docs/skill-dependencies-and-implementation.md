# 各技能的依赖与实现方式

本文依据本仓库的技能说明和代码整理。18 个技能分为带 Python 实现的功能技能，以及指导 Agent 操作的流程技能。以下列出主要依赖，按所选功能安装即可，无需一次安装全部依赖。

这是代码与文档层面的梳理，不代表全部依赖已安装，也不代表仿真、训练或真机流程已通过运行验证。具体安装要求以各技能说明、脚本及包配置为准。

## 感知、规划与控制

| Skill | 主要依赖 | 实现方式 |
|---|---|---|
| `rgb-object-localization` | NumPy、OpenCV、相机标定参数；可选 Kornia/PyTorch、Gemini API | `rgb_localization.py` 实现射线与平面求交、单应性映射、双目三角测量，计算物体位置和朝向。图像目标可由 Agent、本地分割或外部模型提供，几何计算不依赖模型厂商。 |
| `motion-planning` | MuJoCo、NumPy、Pillow，机器人 MJCF 模型 | `motion_planner.py` 使用自适应双向 RRT-Connect 搜索路径，再做路径简化、碰撞与间隙检查。支持物体六自由度路径、机械臂关节轨迹和直线接触动作。 |
| `visual-servoing` | NumPy、OpenCV，相机内参与手眼标定 | `ibvs.py` 实现基于图像的视觉伺服：从目标与夹爪的图像误差计算修正量，持续反馈调整位置和姿态。支持几何射线对齐及特征匹配，无需 GPU。 |
| `i2rt-yam-ik` | MuJoCo、Mink、DAQP、NumPy，以及 I2RT 机器人模型 | `yam_ik.py` 加载机械臂与夹爪组合模型，将末端目标姿态转为优化问题，通过 Mink 和 QP 求解器 DAQP 计算关节目标。 |

## 硬件接入与标定

| Skill | 主要依赖 | 实现方式 |
|---|---|---|
| `so101-bringup` | LeRobot 的 Feetech/运动学组件、NumPy、OpenCV、SO-101 模型；录像按需使用 FFmpeg | 多个脚本分别完成串口发现、电机读取、相机检查、校准检查和基础动作。通过 LeRobot 驱动舵机，保存配置、诊断结果及录像。 |
| `so101-calibration` | 上述 SO-101 环境、固定相机、夹爪标记 | `detect_marker.py` 检测标记；`measure_table.py` 通过受控探测估计桌面高度；`calibrate_handeye.py` 收集机械臂三维位置与图像对应点，拟合投影关系。 |
| `i2rt-yam-bringup` | I2RT SDK、`python-can`、USB-CAN 设备；macOS 额外需要 libusb、gs-usb/pyusb | 配置 Linux SocketCAN 或 macOS USB-CAN 通信，通过 SDK 连接机械臂。`wave.py` 执行基础动作测试，`macos_can.py` 提供平台适配。 |
| `fr3-duo-control` | 真机使用 pylibfranka、夹爪串口通信、OpenCV/NumPy；仿真使用 MuJoCo、Menagerie 模型 | `Fr3DuoRobot` 统一封装真机和仿真后端。下层分别控制双臂、Robotiq 夹爪与相机，并提供运动学、安全检查和轨迹生成；真机 FCI 控制放在独立工作进程。 |

## 仿真、训练与验证

| Skill | 主要依赖 | 实现方式 |
|---|---|---|
| `mujoco-playground` | MuJoCo Playground、reaf-sim、MuJoCo、NumPy；组合任务按需使用 IK、规划、视觉依赖 | `playground_sim2real.py` 封装场景构建和设备访问，以统一的 `DeviceLayer` 接口运行控制器，并组合定位、规划、伺服功能，减少仿真与真机之间的代码差异。 |
| `mujoco-playground-rl` | Playground、reaf-sim、PyTorch、Warp、RSL-RL、Menagerie；GPU 加速训练环境 | 主要提供任务编写与训练流程：定义观测、动作、奖励、重置和设备组件，再调用外部训练栈。仓库中的 `rl_task_check.py` 用于检查任务，训练引擎本身不在仓库里。 |
| `sim2real-gauntlet` | Python ≥3.11、MuJoCo、Playground/reaf-sim、PyTorch、NumPy、dm-env、absl-py | 独立 Python 包 `robosim_gauntlet`。通过 T0–T4 分级扰动、传感器故障与延迟封装运行控制器，记录日志并评估成功率、安全违规和故障退出；支持失败复现及配对随机实验。 |
| `sim2real-iteration` | `sim2real-gauntlet` 及对应任务环境 | 流程技能，无独立执行引擎。指导 Agent 做场景预检、定位最早失败点、从失败状态继续实验，并用相同随机条件比较控制器候选方案。 |
| `iteration` | 可执行的机器人脚本、结果测量及录像能力；独立审查为可选 | 流程技能。将任务拆成阶段，每阶段执行、观察、测量、修正。成功依据是松手并稳定后的实际状态，而非发出的运动命令。 |

## 资产制作、可视化与分享

| Skill | 主要依赖 | 实现方式 |
|---|---|---|
| `blender-creation` | Blender 的 bpy/bmesh、MuJoCo、NumPy、SciPy、trimesh、Pillow；复杂凸分解可选 CoACD | Agent 编写并运行无界面 Blender 脚本；辅助代码负责网格、材质和资产组织。输出 MJCF、网格、纹理及物理参数，再调用审计与展示技能验证。 |
| `mujoco-audit` | MuJoCo、NumPy、SciPy、trimesh、Pillow、absl-py；修复时按需使用 CoACD | `audit_scenarios.py` 做静态检查和 10 类物理场景测试，输出指标与可视化结果。检测由程序完成，具体修复主要由 Agent 根据报告修改模型。 |
| `mujoco-showcase-shot` | 支持 Filament `mjrf` 的 MuJoCo、NumPy、Pillow、absl-py、PyAV；部分路径需要 FFmpeg | `render_showcase_shot.py` 渲染 360° 展示、关节运动和碰撞几何叠加，生成 MP4 与关键帧图。能否使用取决于安装版本是否提供所需渲染 API。 |
| `mujoco-studio-sidecar` | 提供 `mujoco.studio` 和 WebViewer 的 MuJoCo 环境、浏览器；Antigravity 面板可选 Node.js | Python `studiod` 管理仿真、场景热更新、会话及状态接口，浏览器显示实时 3D。Node sidecar 只负责宿主面板集成，通用客户端可直接访问 HTTP 地址。 |
| `share-example` | 文件读写、ZIP 打包能力；视频压缩可选 FFmpeg，会话记录可选 | 流程技能，无专用打包程序。Agent 收集最终文件，排除敏感内容、脱敏、压缩视频、生成 ZIP 和 GitHub Discussions 预填链接。 |

## 通用化方向

保留数值计算和硬件封装代码，让技能负责选择与调用；把模型感知、终端执行、图像查看和浏览器访问留给客户端适配。目前多数功能已经符合这个结构，硬件 SDK、训练栈和新版 MuJoCo API 是部署时最主要的环境依赖。

技能源文件位于 [`plugins/robotics/skills/`](../plugins/robotics/skills/)。通用技能的导出、安装和运行约定见[通用技能指南](portable-skills.md)。
