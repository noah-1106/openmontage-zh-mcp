# OpenMontage - 智能体指南

从这里开始。这是 OpenMontage 的完整操作指南与智能体契约。

关于架构、关键文件与约定，请参阅 [`PROJECT_CONTEXT_zh-CN.md`](PROJECT_CONTEXT_zh-CN.md)。

> **English version:** See [`AGENT_GUIDE.md`](AGENT_GUIDE.md).

## 通过 MCP 使用 OpenMontage

本仓库同时提供 **MCP Server**（`openmontage_mcp`）。当用户通过 MCP 连接时（Claude Code、Cursor、Copilot、CrewAI 等），智能体仍然遵循本指南记录的业务流程 —— 只有工具调用的传输层发生了变化。

### MCP 暴露了什么

MCP 暴露的是**工具能力**，而不是业务流程。可用的 MCP 工具包括：

| MCP 工具 | 作用 | 底层调用 |
|---|---|---|
| `list_capabilities` | 起飞检查时的能力菜单 | `registry.provider_menu_summary()` |
| `run_tool` | 按名称执行任意 OpenMontage 工具 | `registry.get(name).execute(inputs)` |
| `render_video` | 渲染最终视频 | `video_compose` 的 `operation=render` |
| `run_pipeline_stage` | 推进一个流水线阶段 | `pipeline_loader.load_pipeline()` + 检查点 |
| `get_pipeline_status` | 查询流水线进度 | `checkpoint.get_completed_stages()` |
| `get_job_status` | 轮询异步任务状态 | 内存中的 job tracker |

### MCP 工作流规则

1. **业务流程不变。** 制作仍然按 `idea → research → proposal → script → scene_plan → assets → edit → compose` 推进。
2. **起飞检查仍然必须。** 使用 `list_capabilities`（或通过 `run_tool` 调用注册表工具）发现可用工具并展示能力菜单。
3. **执行前仍须阅读阶段导演技能。** MCP 不能替代 `skills/pipelines/<pipeline>/<stage>-director.md` 的阅读。
4. **仍然要呈现两种合成运行时。** 当 Remotion 和 HyperFrames 都可用时，在选定 `render_runtime` 前向用户展示两种选项。
5. **仍然要决定创作模式。** 模板化（`composition_mode: "templated"`）适合批量和草稿；工坊模式（`composition_mode: "atelier"`）适合重要作品。该决策独立于运行时选择，提案阶段就要确定。
6. **不要绕开工具即兴编码。** MCP 已经暴露了工具注册表，不要编写临时 Python 脚本绕过它。

### MCP 配置示例

```json
{
  "mcpServers": {
    "openmontage": {
      "command": "python",
      "args": [
        "-m",
        "openmontage_mcp.server",
        "--project-dir",
        "/path/to/openmontage-zh-mcp"
      ]
    }
  }
}
```

如果项目安装在虚拟环境中，请使用该虚拟环境的 Python 路径。

## 首次交互 — 入门引导

当用户的第一条消息含糊、 exploratory，或询问你能做什么（"帮我做个视频"、"你能做什么？"、"帮我创作点东西"、"我想做内容"）时，**首先**阅读入门技能：

**阅读：** `skills/meta/onboarding.md`

该技能教你进行探索、分类用户环境、用通俗语言展示能力，并根据可用工具提供起始提示词。目标：让用户在 60 秒内从"好奇"进入"做视频"状态。

当用户带着**具体、可执行的需求**到来时（例如："制作一个 60 秒关于黑洞的解说视频"），跳过入门，直接进入规则零。

## 参考视频入口

当用户以**视频 URL 或本地视频文件作为灵感**提供时 — 例如：

- "能帮我做一个像这样的视频吗？"
- "我非常喜欢这个 YouTube Short。给我做个类似的。"
- "用这个 Reel 作为参考。"

— **不要**将其视为普通的网络搜索或提示词编写请求。

这是 OpenMontage 中的**一等工作流**。

### 必需行为

1. **阅读：** `skills/meta/video-reference-analyst.md`
2. 使用本地分析工具（`video_analyzer`、转录提取、场景检测、帧采样）**运行参考分析工作流**
3. 对参考视频产生**扎实总结**：
   - 内容
   - 节奏
   - 结构
   - 风格
   - 它为何有效
4. **然后**运行常规能力审计和流水线选择
5. 为用户版本呈现 **2-3 个差异化概念** — 不是复制品

### 重要区分

- **参考驱动请求：** "给我做个像这样的" -> 使用 `video-reference-analyst.md`
- **源素材请求：** "剪辑这段素材" / "把它剪成片段" -> 使用 `source_media_review` 和合适的素材驱动流水线

如果模型漏掉这个区分，往往会退回普通搜索 + 猜测。这在 OpenMontage 中是不正确的。

## 规则零 — 所有制作都必须经过流水线

**任何视频制作请求都必须经过流水线系统。没有例外。**

当用户要求制作、创建、产出或生成任何视频内容 — 预告片、解说视频、片段、动画或任何其他视频 — 智能体必须：

1. **识别流水线。** 将请求匹配到 `pipeline_defs/` 中的某条流水线。如果不清楚，询问用户。
2. **阅读流水线清单。** `pipeline_defs/<pipeline>.yaml` — 了解阶段、工具和质量关卡。
3. **运行起飞检查 (preflight)。** 通过注册表发现可用工具。展示能力菜单。
4. **按阶段执行。** 对每个阶段，在执行该阶段任何工作之前，先阅读阶段导演技能（`skills/pipelines/<pipeline>/<stage>-director.md`）。
5. **调用工具前阅读第 3 层技能。** 在使用任何带有 `agent_skills` 字段的工具之前，阅读 `.agents/skills/` 中引用的技能。这些技能包含特定提供商的提示词指导、参数优化和质量技巧，能显著提升输出。

**不要：**
- 编写临时 Python 脚本直接调用工具
- 跳过流水线直接进行 API 调用
- 未阅读阶段导演技能就生成资产
- 使用工具前不检查其第 3 层技能中的提示词指导
- 绕过起飞检查、检查点或审核

智能体现在技能中，而非即兴代码中。阅读导演技能和第 3 层知识的智能体，其产出会显著优于用通用提示词直接调用工具的版本。

## OpenMontage 是什么

OpenMontage 是一个指令驱动的视频制作系统。AI 智能体本身就是"智能" — 它阅读指令（流水线清单 + 阶段导演技能 + 元技能）并使用工具驱动流水线。

```
智能体读取流水线清单 (YAML) -> 读取阶段导演技能 (MD)
-> 使用工具 (Python BaseTool 子类) -> 自我审核 (元技能)
-> 写入检查点 (Python 工具) -> 提交给人类审批
```

**Python = 工具 + 持久化。** Python 代码中不存在编排逻辑、创意决策、审核逻辑或检查点策略。智能体在指令指导下做出这些决策。

核心循环：

1. 选择流水线。
2. 运行起飞检查。
3. 从注册表发现真实工具。
4. 向用户展示概念、工具方案、制作计划和成本。
5. 按阶段执行并写入检查点。

## 决策沟通契约

对于任何有意义的制作决策，智能体必须在行动前进行沟通。用户永远不应该在事后推断选择了哪个提供商、模型或渲染路径。

### 执行前宣布

在进行任何付费或重要的生成调用之前，说明：

- 确切的工具名称，
- 提供商，
- 模型或提供商变体，
- 选择原因，
- 是样本运行还是批量运行。

### 重大变更前询问

智能体必须在更改任何重大制作选择前询问用户，包括：

- 切换提供商，
- 切换模型族或提供商变体，
- 从视频主导切换到静态图主导的处理方式，
- 切换会改变输出特征合成引擎，
- 删除旁白、音乐或其他已批准的创意元素，
- 从样本模式切换到批量模式。

在已批准的提供商/模型路径内进行的 minor 提示词优化，除非实质性改变创意方向，否则不需要单独批准。

### 呈现两种合成运行时（硬性规则）

当机器上同时可用 Remotion 和 HyperFrames 时（检查 `video_compose.get_info()["render_engines"]`），智能体**必须在提案阶段向用户呈现两个选项**，然后才能锁定 `render_runtime`。智能体可以推荐其中一个并说明理由 — 但即使流水线清单或导演技能建议了某个"默认"，也禁止默默选择。

呈现必须包含每个运行时的以下内容：

1. 用一句话通俗描述它最擅长什么，**针对当前这个简报**。
2. 用一句话诚实地说明权衡（为什么它可能不是这里的正确选择）。
3. 智能体的推荐及理由，关联到简报的 delivery_promise 和视觉方案。

然后等待用户明确批准再继续。将完整候选列表 — 两个运行时以及任何适用的 "ffmpeg" 选项 — 作为 `render_runtime_selection` 决策中的 `options_considered` 记录到 `decision_log`。当两个运行时都可用时，决策日志只记录一个运行时属于**关键审核发现**。

例外：如果机器上只有一个运行时可用，智能体可以继续使用它，但必须明确说明（"这台机器上没有安装 HyperFrames；我将继续使用 Remotion。如果需要替代方案，请安装 HyperFrames。"）。`render_runtime_selection` 决策仍需将不可用选项记录为 `rejected_because: "runtime not available on this machine"`。

此规则适用于所有调用 `video_compose` 的流水线 — 不仅限于第一波。流水线的导演技能可能会推荐某个运行时，但该推荐只是与用户对话的输入，而非决策。

### 合成创作模式 — 模板化 vs 工坊（Atelier）

与*运行时*正交的是*创作模式*：即**如何构建合成**。把它作为独立的提案决策呈现，并记录到 `decision_log`（`category: "composition_mode"`）。

- **模板化（Templated）** — 将现成的 `cut.type` 场景类型（`text_card`、`stat_card`、`bar_chart`……）组装进 `Explainer`/`CinematicRenderer` 等标准合成。快速、便宜、可靠，也是大多数视频看起来相似的原因。适合批量输出、本地化变体、快速草稿和低风险内部片段。
- **工坊（Atelier）** — **从零开始手搓整个合成**：定制场景、一次性主题、为这部作品单独设计的运动，通过 `composition_mode: "atelier"` 渲染（见 `video_compose` → `_render_via_atelier`）。不复用创意组件；每次都有全新的视觉语言。

**重要作品默认走工坊模式** — 营销片、发布会、品牌片、任何需要惊艳效果的单条解说视频。判断准则是：*复用引擎知识，绝不复用创意组件。* 在工坊模式下，现成的 scene-type 目录、`hyperframes-registry` 区块、fixtures 和成品组件都**禁用** — 它们是固化样式，会让作品重新变得雷同。动手前必须先读 **`skills/meta/bespoke-composition.md`**，它规定了流程：美术方向（`visual-style`）→ 运动原理（迪士尼 12 原则，通过 `framer-motion`/`lottie-bodymovin`）→ 引擎机制（`remotion-best-practices`，且 stock 组件**只作为机制参考手册**阅读）→ 通过工坊路径渲染。最后做一次**独特性审查**：*这条视频会不会是任何其他产品的视频？它是否复用了我之前做过的某种样式？* — 这是"参考复刻"的反面。工坊模式比模板化消耗更多 token 和迭代次数；提案时要明确告知用户，让他们知情选择。

### 明确升级阻断

当发生阻断时，智能体必须立即使用以下结构呈现：

1. 尝试了什么
2. 什么失败了
3. 问题是认证、提供商访问、工具 bug，还是提示词/设计质量
4. 接下来有哪些选择
5. 智能体推荐哪个选择及理由

在用户批准前不要继续替代路径。

### 推荐风格

当要求用户选择时，不要只列出选项。智能体应该：

- 提供候选列表，
- 简要解释权衡，
- 推荐一个选项，
- 等待批准后再继续。

### 禁止单方面替换

如果批准的路径被阻断，智能体可以调查并准备替代方案，但不能在用户批准前执行这些替代方案。

这尤其适用于：

- 提供商替换，
- 模型替换，
- 后备工具，
- 用仅提示词替代参考驱动生成，
- 用静态图动画替代真实动态。

## 编排器

智能体本身就是制作状态机的编排器：

`research -> proposal -> script -> scene_plan -> assets -> edit -> compose`

智能体：

1. 读取流水线清单（`pipeline_defs/*.yaml`）以了解流程
2. 调用 `checkpoint.get_next_stage()` 查找从何处恢复
3. 读取阶段的导演技能（`skills/pipelines/<pipeline>/<stage>-director.md`）以了解 HOW
4. 使用工具（`tools/`）实现具体能力
5. 使用审核员元技能（`skills/meta/reviewer.md`）进行自我审核
6. 通过检查点协议（`skills/meta/checkpoint-protocol.md`）写入检查点
7. 当 `human_approval_default: true` 时向人类请求批准

基础设施文件：

- `lib/checkpoint.py` — 读取/写入检查点、阶段验证
- `tools/cost_tracker.py` — 预算治理
- `lib/pipeline_loader.py` — 清单加载与辅助函数

## 项目目录约定

每次制作运行都会在 `projects/` 下创建一个项目工作区。该目录被 gitignore — 所有生成的资产都是可重新生成的。

```
projects/<project-name>/
├── artifacts/          # 每个阶段的 JSON 产物（research_brief、script、scene_plan 等）
├── assets/
│   ├── images/         # 生成的图像（PNG）
│   ├── video/          # 生成的视频片段（MP4）
│   ├── audio/          # 旁白片段 + 最终混音（MP3/WAV）
│   ├── music/          # 背景音乐轨（MP3）
│   └── subtitles.srt   # 生成的字幕
└── renders/
    └── final.mp4       # 最终渲染视频（交付物）
```

**命名约定**：使用源自视频标题的 kebab-case（例如：`hidden-math-of-nature`、`how-music-rewires-brain`）。

在流水线初始化时、任何阶段运行之前创建项目目录。所有工具和智能体都应将输出写入这些路径 — 永远不要写入仓库根目录或临时位置。

## 音乐库

用户可以将免版税音乐轨放入 `music_library/`（gitignored）。资产导演会在回退到 API 音乐生成之前检查该文件夹。

```
music_library/
├── ambient_track.mp3
├── cinematic_epic.mp3
└── ...
```

如果该文件夹有音轨，提案和资产阶段应将其作为选项与生成音乐一起呈现。详见 proposal-director 和 asset-director 技能。

## 可用流水线

| 流水线 | 最适合 | 稳定性 |
|----------|----------|-----------|
| `animated-explainer` | 主题到完全生成的解说 | production |
| `talking-head` | 素材驱动的演讲者视频 | beta |
| `screen-demo` | 屏幕录制和演示 | production |
| `clip-factory` | 从单一长素材批量生成片段 | beta |
| `podcast-repurpose` | 播客精彩片段和衍生内容 | beta |
| `cinematic` | 预告片、先导片、情绪驱动剪辑 | production |
| `animation` | 动态图形和动画优先视频 | production |
| `character-animation` | 本地绑定卡通角色和可复用角色表演 | beta |
| `hybrid` | 源素材加辅助视觉 | production |
| `avatar-spokesperson` | 主持人驱动的虚拟形象或唇形同步视频 | production |
| `localization-dub` | 字幕、配音和翻译变体 | beta |
| `framework-smoke` | 测试：最小两阶段冒烟测试 | test |

> **Beta 流水线** 尚未完全审计。它们可用，但预计有粗糙边缘。当用户选择时说明这一点。

## 强制起飞检查

在进行任何创意工作之前执行此操作。**首先使用 `provider_menu_summary()` — 它是面向人类的汇总。** 原始的 `support_envelope()` 输出是消防水带（配置良好的机器上会有数兆字节 JSON）；将其粘贴到聊天中会淹没用户。

```bash
python -c "
from tools.tool_registry import registry
import json
registry.discover()
print(json.dumps(registry.provider_menu_summary(), indent=2))
"
```

汇总返回四个字段，智能体应将其翻译成通俗语言：

- `composition_runtimes` — `ffmpeg`、`remotion`、`hyperframes` 的布尔值。这是"呈现两种合成运行时（硬性规则）"检查的事实来源。
- `capabilities[]` — 每个能力族一条记录，包含 `configured / total` 计数和提供商列表。可直接用于 "N of M 已配置" 菜单。
- `setup_offers[]` — 不可用但其安装只需 1 分钟环境变量配置的工具。在提供升级时优先展示这些。
- `runtime_warnings[]` — 具体信号，例如 "hyperframes: npm package not resolvable"。将这些原样呈现给用户 — 它们属于会破坏治理契约的静默失败 bug。

然后，当汇总不够时，进行更深入的检查：

```bash
# 完整菜单 — 按能力分组显示可用/不可用。
python -c "from tools.tool_registry import registry; import json; registry.discover(); print(json.dumps(registry.provider_menu(), indent=2))"

# 原始 envelope — 每个工具的完整契约。慢/消防水带；仅用于调试。
python -c "from tools.tool_registry import registry; import json; registry.discover(); print(json.dumps(registry.support_envelope(), indent=2))"
```

然后：

1. 读取 `pipeline_defs/` 中选中的清单。
2. 将每个 `required_tools` 条目与注册表核对。
3. 为不可用工具检查 `fallback_tools`。
4. 报告：`passed`、`degraded` 或 `blocked` 之一。
5. 在用户了解真实能力范围之前，不要开始制作。

### 中文字体可用性检查

对于任何包含中文文本渲染的制作（字幕、标题、覆盖层、Pillow 图形、Remotion 预览），在起飞检查阶段必须确认中文字体兜底可用。

运行：

```bash
python3 scripts/install_chinese_fonts.py
```

- 成功：记录字体缓存路径，继续制作。
- 失败：明确告知用户中文字幕/标题可能显示为“□□□”豆腐块。此时不要静默继续，而应：
  1. 说明失败原因（通常是网络无法下载 Noto Sans SC fallback）；
  2. 提供替代方案：稍后重试、手动放置中文字体到 `~/.openmontage/fonts/`、或改用 Remotion/Google Fonts 路径（如果该路径可用）。

如果项目明确以中文交付，字体检查失败应标记为 `degraded` 或 `blocked`，并在提案中如实呈现。

### 提供商菜单（起飞检查必需）

已通过上面的 `provider_menu_summary()` 获取。阅读该输出并**将其作为能力菜单呈现给用户**，而不是平铺工具列表。只在需要汇总中缺少的逐工具细节时才直接使用 `provider_menu()`。

**呈现方式：**

```
你的能力

  视频生成：  0/13 已配置
  图像生成：  1/7 已配置
  文本转语音： 1/3 已配置
  音乐生成：  1/1 已配置
  合成：      3/3 已配置（FFmpeg、video_stitch、video_trimmer）

  你现在可以用图像 + TTS + FFmpeg 制作视频。
  快速升级选项 — 见下文。
```

对于每个有不可用提供商的能力，从菜单输出中读取 `install_instructions` 字段，并按工作量分组展示设置选项：

```
快速设置选项（每项 1 分钟 — 在 .env 中设置环境变量）

  视频生成（0/13 -> 解锁最大升级）：
    每个不可用提供商都列出自身的 install_instructions。
    从 provider_menu 输出中读取并按环境变量分组展示。
    示例：如果 3 个工具需要 FAL_KEY，分组展示："FAL_KEY 解锁 3 个提供商"

  图像生成（1/7 -> 更多风格选项）：
    同样模式 — 从每个不可用工具读取 install_instructions。

  文本转语音（1/3）：
    同样模式。

本地选项（免费，需要硬件）：
  从菜单中读取 runtime=LOCAL 或 runtime=LOCAL_GPU 的工具。

已可用：
  列出可用的内容。用户应该对他们已有的能力感到满意。
```

**规则：**
- 不要硬编码提供商名称、API key 名称或设置 URL。
  从每个工具的 `install_instructions` 字段读取。
- 始终显示比例："X of Y configured" — 这让广度一目了然。
- 按能力分组，而不是按单个工具。
- 先展示他们现在能做什么，再展示可以解锁什么。
- 如果用户拒绝设置，继续用最佳可用路径 — 不要唠叨。
- 如果多个工具共享同一个环境变量，按该环境变量分组（从 `dependencies` 字段读取）。

### 设置提供协议

当工具为 `UNAVAILABLE` 但可通过简单配置修复时，**向用户提供设置帮助，而不是默默绕过限制。** 许多工具只差一个环境变量就能工作。

| 修复复杂度 | 操作 |
|----------------|--------|
| **1 分钟修复**（环境变量） | 主动提出现在帮助配置 — 从工具读取 `install_instructions`。优先使用中文配置向导：`python3 scripts/config_wizard.py`。用户也可以直接给你 API Key，由你通过 `--non-interactive --json` 代为写入配置。 |
| **5 分钟修复**（安装） | 解释需要安装什么以及为什么 — 从工具读取 `install_instructions`。中文字体兜底属于此类：运行 `python3 scripts/install_chinese_fonts.py`。 |
| **复杂修复**（GPU、模型下载） | 说明限制、解释它能解锁什么，然后继续 |

**规则：**
- 始终告诉用户他们缺少什么以及能获得什么
- 展示成本差异（免费本地 vs 付费 API）
- 如果用户拒绝设置，继续用最佳可用路径 — 不要唠叨
- 将相关修复分组（共享同一环境变量依赖的工具）

### 合成运行时（video_compose 内部）

`video_compose` 有**三个**渲染引擎/运行时。它们是平行的，不是排序的 — 选择在提案阶段做出，并锁定在 `edit_decisions.render_runtime`。检查哪些可用：

```bash
python -c "
from tools.tool_registry import registry
registry.discover()
info = registry._tools['video_compose'].get_info()
print('Render engines:', info.get('render_engines'))
print('Remotion note:', info.get('remotion_note'))
print('HyperFrames note:', info.get('hyperframes_note'))
"
```

| 引擎 | 用于 | 需要 |
|--------|----------|----------|
| **FFmpeg** | 纯视频剪辑、拼接、裁剪、字幕烧录 | `ffmpeg` 二进制（始终可用） |
| **Remotion** | 基于 React 的合成：静态图 → 动画视频、文字卡片、数据卡片、图表、标注、对比、弹簧物理过渡、词级字幕烧录、TalkingHead 虚拟人 | Node.js (`npx`) + `remotion-composer/` + `node_modules` |
| **HyperFrames** | 基于 HTML/CSS/GSAP 的合成：动态排版、产品宣传、发布短片、网站转视频、注册表驱动的场景、SVG 角色绑定 | Node.js ≥ 22 + FFmpeg + `npx`（通过 `npx hyperframes` 调用） |

`render_runtime` 在**提案阶段锁定**（`proposal_packet.production_plan.render_runtime`），并**原样贯穿 edit_decisions**。`video_compose` 根据该字段路由；静默切换运行时被禁止。如果所选运行时在合成时不可用，按照上面的"明确升级阻断"结构升级。详见 `skills/core/hyperframes.md` 中的 Remotion 与 HyperFrames 决策矩阵。

### 关键规则：需要动态的请求

对于任何交付物本质上依赖动态而非静态覆盖的请求，将动态视为硬性要求。例如：

- 科幻预告片，
- 基于生成片段的电影级先导片，
- hype 剪辑，
- 虚拟形象或智能体视频，
- 任何其承诺依赖于运动镜头而非静态帧的简报。

对于这些请求：

- 如果计划的视觉处理依赖某个运行时，必须在 upfront 确认所选 `render_runtime`（Remotion、HyperFrames 或 FFmpeg）可用。
- 禁止静态图回退。不要悄悄将工作变成 Ken Burns 预告片、动画故事板或幻灯片视频。
- 当它将批准的交付物从动态主导视频变为静态主导视频时，禁止仅使用 FFmpeg 回退。
- **禁止静默运行时切换。** 如果锁定了 `render_runtime="hyperframes"` 但 HyperFrames 不可用，不要改路由到 Remotion。升级阻断、提出选项、获得用户批准、记录 `render_runtime_selection` 决策 — 然后再继续。
- 立即冒泡关键问题。如果所选运行时不可用、渲染失败，或提供商片段生成失败导致批准的处​​理被阻断，在继续前停止并告诉用户。
- 除非用户明确批准降级为动画故事板或概念验证，否则不要在降级输出上花费更多 token 或时间。

**当 Remotion 可用时**，智能体应围绕它设计制作计划：
- 使用 `flat-motion-graphics` 剧本的解说视频 -> Remotion 动画场景，不是 Ken Burns
- 数据驱动视频 -> Remotion 数据卡片和图表，不是静态图截图
- 任何使用静态图像的流水线 -> Remotion 弹簧动画，不是 FFmpeg 平移缩放
- **CLI/终端/安装流程的屏幕演示 -> `TerminalScene`（合成屏幕录制），不是操作系统级录制。** 详见 `.agents/skills/synthetic-screen-recording/SKILL.md`。更快、确定性、隐私安全。只有当演示是真实应用 UI 或需要不可预测的现场行为时，才使用真实录制（`screen_recorder`、`cap_recorder`、`playwright-recording`）。

### `remotion-composer/` 中可用的 Remotion 场景类型

权威列表及其剪辑 schema 见 `remotion-composer/SCENE_TYPES.md`。当前可通过 `cut.type` 使用的场景类型：`text_card`、`stat_card`、`callout`、`comparison`、`hero_title`、`terminal_scene`、`anime_scene`、`bar_chart`、`line_chart`、`pie_chart`、`kpi_grid`、`progress_bar`。覆盖层类型包括 `section_title`、`stat_reveal`、`hero_title`、`provider_chip`。

这些现成场景类型是**模板化**路径 — 快速可靠，但也是视频看起来雷同的原因。对于**重要作品，优先使用工坊模式**（手搓合成），而不是把这些类型当菜单来组装；把它们当作*机制参考手册*阅读，而非组装菜单。详见上文"合成创作模式"和 `skills/meta/bespoke-composition.md`。

**当 Remotion 不可用**且 `render_runtime="remotion"` 尚未锁定时，`video_compose` 可以在静态图上使用 FFmpeg Ken Burns 运动。这仍然有效，但视觉效果较差。在提案中说明这一权衡。当 `render_runtime="remotion"` 已锁定且 Remotion 不可用时，这是阻断 — 升级，不要静默切换。

当 `render_runtime="hyperframes"` 已锁定且 HyperFrames 不可用（Node < 22、缺少 `ffmpeg`/`npx`，或 `hyperframes doctor` 报告问题）时，这也是阻断。未经用户批准 + 记录 `render_runtime_selection` 决策，不要替换为 Remotion 或 FFmpeg。

路由是自动的 — `video_compose` 读取 `edit_decisions.render_runtime` 并分发到匹配的引擎（`_render_via_hyperframes`、`_remotion_render` 或 `_render_via_ffmpeg`）。但**智能体必须在提案阶段就知道 Remotion 和 HyperFrames 都存在**，这样才能有意识地设计视觉方案。不要对自然更适合 HTML/GSAP 表达的动态图形概念默认使用 Remotion，也不要对复用现有 React 场景堆栈的简报默认使用 HyperFrames。

## 能力发现

OpenMontage 使用两层进行能力选择：

- 选择器工具：能力级路由，如 `tts_selector` 和 `video_selector`
- 提供商工具：通过注册表发现的具体工具，调用特定后端

始终先检查注册表：

```bash
python -c "from tools.tool_registry import registry; import json; registry.discover(); print(json.dumps(registry.capability_catalog(), indent=2))"
python -c "from tools.tool_registry import registry; import json; registry.discover(); print(json.dumps(registry.provider_catalog(), indent=2))"
```

对于候选工具，检查：

- `capability`
- `provider`
- `usage_location`
- `supports`
- `fallback_tools`
- `related_skills`

当注册表能回答时，不要依赖记忆或旧文档。

## 工具族

**不要维护硬编码工具列表。** 始终在运行时查询注册表：

```bash
# 按能力分组查看所有工具（TTS、video_generation、image_generation 等）
python -c "from tools.tool_registry import registry; import json; registry.discover(); print(json.dumps(registry.capability_catalog(), indent=2))"

# 按提供商分组查看所有工具（elevenlabs、openai、ffmpeg 等）
python -c "from tools.tool_registry import registry; import json; registry.discover(); print(json.dumps(registry.provider_catalog(), indent=2))"
```

输出中需要关注的关键能力族：

- **tts** — 文本转语音提供商。通过 `tts_selector` 路由。
- **video_generation** — 视频生成提供商（云端、本地 GPU、素材库）。通过 `video_selector` 路由。
- **image_generation** — 图像生成提供商（云端、本地 GPU、素材库）。通过 `image_selector` 路由。
- **music_generation** — 音乐和音效生成。
- **video_post** — 合成、拼接、裁剪（基于 FFmpeg，始终本地）。
- **audio_processing** — 混音、增强（基于 FFmpeg，始终本地）。
- **analysis** — 转录、场景检测、帧采样。
- **avatar** — 数字人和唇形同步生成。
- **character_animation** — 本地角色规范、SVG 绑定、姿势库、动作时间线、预览和 QA。
- **enhancement** — 放大、背景移除、面部增强、色彩调色。

注册表中的每个工具都会声明 `best_for`、`install_instructions`、`runtime`（LOCAL、API、LOCAL_GPU、HYBRID）和 `status`。阅读这些字段 — 不要假设工具优势。

### 工具类命名约定

所有工具类都使用 **PascalCase，不带 "Tool" 后缀**。在 Python 中导入工具时：

| 模块 | 类名 | 不要 |
|--------|-----------|-----|
| `tools.audio.music_gen` | `MusicGen` | ~~MusicGenTool~~ |
| `tools.video.video_compose` | `VideoCompose` | ~~VideoComposeTool~~ |
| `tools.audio.audio_mixer` | `AudioMixer` | ~~AudioMixerTool~~ |
| `tools.tts.elevenlabs_tts` | `ElevenLabsTTS` | ~~ElevenLabsTTSTool~~ |
| `tools.analysis.transcriber` | `Transcriber` | ~~TranscriberTool~~ |
| `tools.subtitle.subtitle_gen` | `SubtitleGen` | ~~SubtitleGenTool~~ |

不确定时检查：`grep "^class " tools/<path>.py`

所有工具都通过 `.execute(params_dict)` 调用（返回带有 `.success`、`.data`、`.error` 的 `ToolResult`），不是 `.run()`。

### 选择器模式

三个选择器工具抽象了多提供商能力。**选择器自动从注册表发现提供商。** 添加新的提供商工具会自动使其通过选择器可用 — 无需修改选择器代码。

| 选择器 | 路由到 | 如何发现 |
|----------|-----------|-----------------|
| `tts_selector` | 所有 `capability="tts"` 的工具（ElevenLabs、Google TTS、OpenAI、Piper） | `registry.get_by_capability("tts")` |
| `image_selector` | 所有 `capability="image_generation"` 的工具（FLUX、Google Imagen、DALL-E、Recraft 等） | `registry.get_by_capability("image_generation")` |
| `video_selector` | 所有 `capability="video_generation"` 的工具 | `registry.get_by_capability("video_generation")` |

选择器基于：用户偏好 > 可用性 > 发现顺序 进行路由。它们在提供商之间透明地适配输入 schema。

## 面向用户的规划协议

在承诺执行之前，呈现：

1. 当简报仍开放时，给出 `4-5` 个概念方向。
2. 推荐的流水线。
3. 推荐的工具路径。
4. 实际可用的替代工具路径。
5. 成本估算和质量权衡。
6. **音乐计划** — 任何有音频的流水线都必须。见下文。
7. 按阶段列出的制作计划。
8. 资产生成前的审批关卡。

如果用户偏好特定厂商且该工具可用，直接展示。不要隐藏提供商选择。

### 音乐计划（必需）

音乐是任何视频的关键部分。**在提案/创意阶段就向用户说明音乐情况** — 不要默默将其推迟到资产阶段，在那里失败会变得昂贵。

按以下顺序检查音乐可用性并呈现选项：

1. **用户音乐库（`music_library/`）：** 检查该文件夹是否存在且包含音轨。如果是，列出可用音轨及其时长，让用户选择一首。
2. **音乐生成 API：** 通过注册表检查哪些音乐工具可用（`registry.get_by_capability("music_generation")`）。诚实地报告它们的状态 — 如果已知，包括配额状态。
3. **免版税来源：** 说明用户是否可以提供自己的音轨（例如来自 YouTube Audio Library、Jamendo 或其他免费来源）。提供 `music_library/` 拖放路径。

**始终向用户呈现明确选择：**
- 使用他们库中的音轨（哪一首？）
- 提供不同音轨（放入 `music_library/`）
- 通过 API 生成（如果可用 — 说明提供商和成本）
- 不使用音乐

**如果没有音乐来源：** 明确告诉用户。不要让这在资产阶段成为意外。

将音乐决策记录在提案/简报产物中，让资产导演知道该怎么做。

## 流水线资产预期

每个流水线清单的 `tools_available` 字段声明某个阶段可以使用哪些工具。对多提供商能力使用选择器 — 选择器会处理到任何可用工具的路由。阅读流水线清单以获取每个阶段的权威列表。

## 阶段智能体

每个阶段产生一个标准产物，成为下一阶段的契约。阶段导演技能教智能体 HOW 产生它。

| 阶段 | 导演技能 | 标准产物 | 核心质量标准 |
|------|---------------|------------------|------------------|
| `idea` | `*-director.md` | `brief` | 清晰的钩子、目标平台、时长、基调和用户意图 |
| `script` | `*-director.md` | `script` | 结构化段落、有效时长、连贯旁白 |
| `scene_plan` | `*-director.md` | `scene_plan` | 有序场景、时长、资产需求 |
| `assets` | `*-director.md` | `asset_manifest` | 来源、路径、模型/工具元数据、场景关联 |
| `edit` | `*-director.md` | `edit_decisions` | 具体剪辑、覆盖层、字幕/音乐决策 |
| `compose` | `*-director.md` | `render_report` | 输出路径、编码配置、验证说明 |

阶段契约规则：

- 已完成或等待人类的检查点必须包含该阶段的标准产物。
- 标准产物必须通过 `schemas/artifacts/` 中的 JSON Schema 验证。
- 非标准输出（如媒体文件）属于阶段特定目录。
- 工具应记录种子/模型版本以实现可复现性。

## 审核员协议

审核员是一个元技能（`skills/meta/reviewer.md`） — 仅提供建议，从不直接阻断进展。

- 每个阶段执行后、写入检查点前进行自我审核。
- 从流水线清单中为当前阶段加载 `review_focus` 项。
- 最多两轮审核。之后带着警告通过并继续。
- 发现分类：critical（必须修复）、suggestion（应该修复）、nitpick（锦上添花）。
- Critical 发现 -> 修复并重新审核。Suggestion -> 记录并继续。
- 将剧本 `quality_rules` 作为约束而非建议。

## 人类检查点协议

检查点协议元技能（`skills/meta/checkpoint-protocol.md`）教智能体何时暂停：

- 从流水线清单中按阶段读取 `human_approval_default`
- 创意阶段（`idea`、`script`、`scene_plan`）通常需要批准
- 技术阶段（`assets`、`edit`、`compose`）通常自动继续
- 当需要批准时：展示产物摘要、审核发现和成本快照
- 等待人类批准、要求修订或中止

## 通信协议

智能体通过标准 JSON 产物、检查点、流水线清单和工具注册表进行协调。

主要文件：

- 产物 schema：`schemas/artifacts/`
- 检查点 schema：`schemas/checkpoints/checkpoint.schema.json`
- 流水线清单 schema：`schemas/pipelines/pipeline_manifest.schema.json`
- 流水线清单：`pipeline_defs/`
- 风格剧本：`styles/*.yaml`（由 `schemas/styles/playbook.schema.json` 验证）
- 工具契约：`tools/base_tool.py`
- 工具注册表：`tools/tool_registry.py`
- 阶段导演技能：`skills/pipelines/<pipeline>/<stage>-director.md`
- 元技能：`skills/meta/*.md`

检查点规则：

- 检查点位于 `pipelines/<project_id>/checkpoint_<stage>.json`。
- `status` 可以是 `completed`、`failed`、`awaiting_human` 或 `in_progress`。
- `completed` 和 `awaiting_human` 检查点必须包含标准产物。
- 无效检查点或无效标准产物属于契约违规，应快速失败。

流水线清单规则：

- 流水线是 `pipeline_defs/` 中的声明式 YAML 清单。
- 阶段声明：`skill`（导演技能路径）、`produces`、`tools_available`、`review_focus`、`success_criteria`、`human_approval_default`。
- 添加新流水线需要清单 + 阶段导演技能。

工具规则：

- 每个生产工具必须继承自 `BaseTool`。
- 工具发现通过注册表进行，不是临时导入。
- 支持范围报告是能力、状态和资源需求的事实来源。

## 风格剧本

| 剧本 | 最适合 |
|----------|----------|
| `clean-professional` | 企业、教育、SaaS |
| `flat-motion-graphics` | 社交媒体、TikTok、初创公司 |
| `minimalist-diagram` | 技术深度解析、架构 |

## 层级映射

OpenMontage 有三个指令层级：

1. `tools/`
   存在什么、是否可用、成本、运行时、后备、相关技能。
2. `skills/`
   OpenMontage 希望如何在流水线中使用这些工具。
3. `.agents/skills/`
   原始厂商或技术知识。

阅读顺序：

1. 注册表 / 工具契约 — 发现有什么可用
2. 相关流水线或创意技能（第 2 层）— 知道在此上下文中 HOW 使用
3. 底层厂商技能（第 3 层）— **在调用任何生成工具前必须阅读**

**优先使用技能而非源代码来了解工具用法。** 技能的存在正是为了让你不需要在常见情况下了解实现细节。第 2 层告诉你 *what* 和 *when*。第 3 层告诉你 *how*。对于编写提示词、选择参数或理解使用模式，你应该阅读技能 — 而不是 `.py` 文件。

**例外：调试、审计和验证治理契约。** 当技能与工具不一致，或行为与技能声称不同时，阅读工具源码是合理的 — 这通常是发现静默可用性 bug 或陈旧文档字符串的唯一方法。拒绝查看实现的审计会漏掉最重要的 bug。如果你确实为了调试而阅读源码，考虑该发现是否应作为技能更新，以便下一个智能体不需要重复钻研。

**第 3 层不是可选的。** 每个生成工具（视频、图像、TTS、音乐）都有一个 `agent_skills` 字段，列出其第 3 层技能。在编写提示词前阅读它们。通用提示词和基于技能的提示词之间的差距，就是"可用"和"电影级"之间的差距。

示例：在调用 `kling_video` 之前，阅读其 `agent_skills` → `ai-video-gen` → 获取 Kling 特定的提示词结构、镜头方向语法和模型响应最佳的质量关键词。

### 按类别划分的第 3 层技能

`.agents/skills/` 目录很大。当你不是通过工具的 `agent_skills` 指针进入时，使用下表按*你想做什么*找到合适的文件：

| 类别 | 技能 |
|---|---|
| **合成运行时** | `remotion`、`remotion-best-practices`、`synthetic-screen-recording`（通过 Remotion TerminalScene 模拟终端/UI 演示） |
| **动画知识（通用）** | `gsap-core`、`gsap-timeline`、`gsap-plugins`（SplitText / MorphSVG / DrawSVG / MotionPath / Flip / CustomEase）、`gsap-utils`、`gsap-react`、`gsap-performance`、`gsap-scrolltrigger`、`gsap-frameworks`、`framer-motion`（迪士尼 12 原则）、`lottie-bodymovin`（Lottie 导出） |
| **角色动画** | `character-rigging`、`svg-character-animation`、`pose-library-design`、`canvas-procedural-animation`、`character-animation-qa` |
| **图像生成** | `bfl-api`、`flux-best-practices` |
| **视频生成** | `seedance-2-0`（首选高端默认 — 电影级、预告片、多镜头、同步音频、唇同步）、`ai-video-gen`、`ltx2` |
| **音频** | `elevenlabs`、`music`、`sound-effects`、`acestep`、`text-to-speech`、`setup-api-key` |
| **虚拟形象 / 唇同步** | `avatar-video`、`heygen`、`create-video`、`faceswap`、`video-translate`、`speech-to-text`、`agents` |
| **录制** | `playwright-recording`（浏览器流程）、`ffmpeg`（后期） |
| **可视化** | `beautiful-mermaid`、`d3-viz`、`manim-composer`、`manimce-best-practices`、`manimgl-best-practices` |
| **媒体编辑** | `video-edit`、`video-download`、`video-understand`、`video-toolkit`、`visual-style` |

**不确定时，先阅读该类别的元路由文件：**
- 选择动画运行时？ → `skills/meta/animation-runtime-selector.md` 在 Remotion 基础、GSAP 插件、framer-motion、Lottie、Manim、D3 之间路由。
- 选择屏幕录制模式（真实录制 vs 合成终端）？ → `pipeline_defs/screen-demo.yaml` + `skills/pipelines/screen-demo/idea-director.md`。

## 快速查询

| 问题 | 查看位置 |
|----------|---------------|
| 有哪些工具？ | `tools/tool_registry.py` 和 `registry.support_envelope()` |
| 某能力有哪些提供商？ | `registry.capability_catalog()` |
| 某厂商有哪些工具？ | `registry.provider_catalog()` |
| 工具实际如何工作？ | 注册表中的 `usage_location` |
| 流水线阶段应该如何表现？ | `skills/pipelines/<pipeline>/...` |
| 检查点/审核策略是什么？ | `skills/meta/` |

## 禁止事项

- **不要绕过流水线。** 永远不要编写临时脚本直接调用工具。所有制作都经过带有导演技能的流水线阶段。参见规则零。
- **不要未阅读第 3 层技能就调用生成工具。** 检查工具的 `agent_skills` 字段，阅读引用的技能，然后使用该指导编写提示词。
- **不要跳过阶段导演技能。** 在执行任何流水线阶段之前，阅读其导演技能。技能包含质量标准、工作流和审核标准。
- 不要使用已删除的遗留名称，如 `tts_cloud`、`tts_engine` 或 `video_gen`。
- 不要硬编码提供商名称、API key 名称或设置 URL。从注册表的 `install_instructions` 和 `dependencies` 字段读取。
- 不要在用户对制作计划批准前开始资产生成。
- 不要隐藏降级路径。明确记录替换和被阻断的选项。
- 不要孤立地展示单个不可用工具。始终展示完整能力图景："该能力有 X of Y 个提供商已配置。"
- 不要在起飞检查中跳过提供商菜单。用户必须看到他们已有的和可以解锁的。
- 不要在未事先告知用户并获得批准的情况下更改提供商、模型或渲染路径（当变更是重大时）。
