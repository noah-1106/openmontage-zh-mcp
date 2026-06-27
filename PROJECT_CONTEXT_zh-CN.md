# OpenMontage - 共享项目上下文

本文档是项目架构与约定的唯一事实来源。各平台专用的 Agent 文件（CLAUDE.md、CODEX.md、CURSOR.md、COPILOT.md）应指向本文档，而不是重复其内容。

## 项目定位

OpenMontage 是一个开源的、由 AI 智能体编排的视频制作平台。

## 架构：指令驱动（Agent 优先）

AI 智能体本身就是"大脑"。Python 只负责工具执行与持久化。其余一切——编排、创意决策、审核、阶段切换——都存在于智能体遵循的指令中（YAML 清单 + Markdown 技能）。

```
智能体读取流水线清单 (YAML) → 读取阶段导演技能 (MD)
→ 使用工具 (Python BaseTool) → 自我审核 (meta skill)
→ 写入检查点 (Python utility) → 提交给人类审批
```

**没有 Python 编排器、没有 Python 审核器、没有 Python 处理器。** 智能体驱动整条流水线。

## 权威来源

- **智能体指南与约定：** `AGENT_GUIDE.md`（工具清单、流水线选择、阶段智能体、协议）
- **技能索引：** `skills/INDEX.md`
- **工具注册表：** `tools/tool_registry.py`
- **流水线清单：** `pipeline_defs/`
- **产物 Schema：** `schemas/artifacts/`
- **风格手册：** `styles/*.yaml`（schema: `schemas/styles/playbook.schema.json`）
- **阶段导演技能：** `skills/pipelines/<pipeline>/<stage>-director.md`
- **元技能：** `skills/meta/*.md`（审核员、检查点协议、技能创建者）
- **架构深入：** `docs/ARCHITECTURE.md`

## 知识架构（三层）

```
第 1 层：tools/tool_registry.py     → "有哪些工具"（运行时能力、状态、成本）
第 2 层：skills/                    → "OpenMontage 如何使用它们"（项目约定）
第 3 层：.agents/skills/            → "技术本身如何工作"（通用 API 规则、skills.sh）
```

每个工具的 `agent_skills[]` 字段连接第 1 层到第 3 层。完整映射见 `skills/INDEX.md`。

## 关键模式

- **流水线状态机：** `idea -> script -> scene_plan -> assets -> edit -> compose -> publish`
- **指令驱动阶段：** 每个阶段都有一份导演技能（MD），教智能体如何执行
- **流水线清单：** 声明式 YAML，定义阶段、技能、工具、审核重点、审批关卡
- **能力优先的工具设计：** 每个主要能力族都应暴露一个选择器工具 + 明确的提供商工具
  - 示例：`tts_selector` + `elevenlabs_tts` / `google_tts` / `openai_tts` / `piper_tts`
  - 示例：`video_selector` + `heygen_video` / `wan_video` / `hunyuan_video` / `ltx_video_local` / `ltx_video_modal` / `cogvideo_video`
- **风格手册：** YAML 定义视觉语言、字体、动效、音频、资产生成约束
- **产物是权威：** `brief`、`script`、`scene_plan`、`asset_manifest`、`edit_decisions`、`render_report`、`publish_log`
- **每个工具都继承自 `tools/base_tool.py`**（ToolContract）
- **检查点策略** 存在于流水线清单（每个阶段的 `human_approval_default`）+ `skills/meta/checkpoint-protocol.md`
- **审核员** 是元技能（`skills/meta/reviewer.md`），仅提供建议，最多 2 轮
- **成本追踪器**（`tools/cost_tracker.py`）管理预算：估算 → 预留 → 对账
- **规范产物** 通过 `schemas/artifacts/` 中的 JSON Schema 验证

## 关键文件

| 文件 | 用途 |
|------|------|
| `config.yaml` | 全局配置 |
| `lib/config_model.py` | 运行时配置加载器（Pydantic） |
| `lib/checkpoint.py` | 检查点写入/读取 |
| `lib/pipeline_loader.py` | 流水线清单加载器与辅助函数 |
| `lib/media_profiles.py` | 平台特定的渲染配置 |
| `styles/playbook_loader.py` | 风格手册加载器、校验器与设计智能（颜色/字体/无障碍） |
| `tools/base_tool.py` | ToolContract 基类 |
| `tools/tool_registry.py` | 工具发现与报告 |
| `tools/cost_tracker.py` | 预算治理 |
| `tools/video/video_stitch.py` | 多片段组装（拼接、空间合成、验证、预览） |
| `tools/video/video_compose.py` | 运行时感知合成编排器——根据 `edit_decisions.render_runtime` 路由到 Remotion / HyperFrames / FFmpeg |
| `tools/video/hyperframes_compose.py` | HyperFrames 运行时——工作区物化、`hyperframes lint`/`validate`/`render`、FFmpeg 兜底检查 |
| `tools/character/character_animation.py` | 本地角色动画工具——角色规范、SVG 绑定方案、姿势库、动作时间线、HyperFrames 包、QA 报告 |
| `lib/hyperframes_style_bridge.py` | 手册 → CSS 自定义属性 + `DESIGN.md` 桥接，用于 HyperFrames 工作区 |
| `remotion-composer/src/components/` | 8 个 Remotion 组件（TextCard、StatCard、ProgressBar、CalloutBox、ComparisonCard + charts/） |
| `.agents/skills/hyperframes*/` | 内置 HyperFrames 第 3 层技能（创作契约、CLI、注册表、website-to-video） |
| `skills/core/hyperframes.md` | 第 2 层——何时选择 HyperFrames 而非 Remotion，产物 → 工作区映射 |
| `schemas/styles/playbook.schema.json` | 手册 schema v2，含设计令牌（chart_palette、scale_system、weight_matrix、color_rules） |
| `tests/qa/` | 逐工具输出检查的质量验证脚本 |

## 可用流水线

| 流水线 | 清单 | 类型 |
|--------|------|------|
| `talking-head` | `pipeline_defs/talking-head.yaml` | 基于素材 |
| `animated-explainer` | `pipeline_defs/animated-explainer.yaml` | AI 生成 |
| `screen-demo` | `pipeline_defs/screen-demo.yaml` | 屏幕录制 |
| `clip-factory` | `pipeline_defs/clip-factory.yaml` | 短视频批量提取 |
| `podcast-repurpose` | `pipeline_defs/podcast-repurpose.yaml` | 播客再利用 |
| `cinematic` | `pipeline_defs/cinematic.yaml` | 电影感剪辑 |
| `animation` | `pipeline_defs/animation.yaml` | 动画优先 |
| `character-animation` | `pipeline_defs/character-animation.yaml` | 本地绑定角色动画 |
| `hybrid` | `pipeline_defs/hybrid.yaml` | 素材+辅助混合 |
| `avatar-spokesperson` | `pipeline_defs/avatar-spokesperson.yaml` | 虚拟人讲解 |
| `localization-dub` | `pipeline_defs/localization-dub.yaml` | 本地化与配音 |
| `framework-smoke` | `pipeline_defs/framework-smoke.yaml` | 测试用 |

## 新增流水线

1. 在 `pipeline_defs/` 创建 YAML 清单（由 `pipeline_manifest.schema.json` 校验）
2. 在 `skills/pipelines/<pipeline-name>/` 创建阶段导演技能（7 个技能：idea 到 publish）
3. 在清单中引用元技能（审核员、检查点协议）
4. 在清单中添加兼容的风格手册
5. 在 `tests/contracts/` 添加契约测试

## 新增工具

1. 继承 `tools/base_tool.py` 中的 `BaseTool`
2. 放入正确的能能力包（`tools/audio/`、`tools/video/`、`tools/enhancement/`、`tools/analysis/`、`tools/graphics/`、`tools/avatar/`、`tools/subtitle/`）
3. 优先使用 选择器+提供商 模式：
   - 一个能力路由器工具，方便智能体使用
   - 每个真实提供商/运行时路径一个具体工具
4. 填写所有契约字段（name、version、tier、capability、provider、supports、fallback_tools、agent_skills 等）
5. 实现 `execute()` 并返回 `ToolResult`
6. 通过 `tools/tool_registry.py` 自动发现，不要依赖临时导入
7. 如果工具 I/O 复杂，在 `schemas/tools/` 添加 JSON Schema
8. 运行时路径正确后再添加测试
