#!/usr/bin/env python3
"""OpenMontage 中文配置向导

交互式配置 LLM、视频、音频、图像等 provider 的 API key。
运行后会生成/更新项目根目录的 .env 文件和 config.yaml。
"""

from __future__ import annotations

import os
import re
import sys
from pathlib import Path
from typing import Any

import yaml


ROOT = Path(__file__).resolve().parent.parent
ENV_PATH = ROOT / ".env"
CONFIG_PATH = ROOT / "config.yaml"


PROVIDERS = {
    "llm": {
        "title": "大语言模型 (LLM) - 用于 Agent 编排和创意决策",
        "options": [
            {"name": "Anthropic Claude", "key": "ANTHROPIC_API_KEY", "base_url_env": "ANTHROPIC_BASE_URL", "model": "claude-sonnet-4-6"},
            {"name": "OpenAI / 兼容端点", "key": "OPENAI_API_KEY", "base_url_env": "OPENAI_BASE_URL", "model": "gpt-4.1"},
            {"name": "DeepSeek", "key": "DEEPSEEK_API_KEY", "base_url_env": "DEEPSEEK_BASE_URL", "model": "deepseek-chat"},
            {"name": "通义千问 (Qwen)", "key": "QWEN_API_KEY", "base_url_env": "QWEN_BASE_URL", "model": "qwen-max"},
            {"name": "智谱 GLM", "key": "ZHIPU_API_KEY", "base_url_env": "ZHIPU_BASE_URL", "model": "glm-4-plus"},
            {"name": "Moonshot 月之暗面", "key": "MOONSHOT_API_KEY", "base_url_env": "MOONSHOT_BASE_URL", "model": "moonshot-v1-8k"},
            {"name": "百川", "key": "BAICHUAN_API_KEY", "base_url_env": "BAICHUAN_BASE_URL", "model": "Baichuan4"},
            {"name": "OpenRouter", "key": "OPENROUTER_API_KEY", "base_url_env": "OPENROUTER_BASE_URL", "model": "anthropic/claude-3.5-sonnet"},
            {"name": "AutoDL 模型广场（对话模型）", "key": "AUTODL_API_KEY", "base_url_env": "AUTODL_BASE_URL", "model": None, "model_env": "AUTODL_LLM_MODEL", "autodl_models": [
                "DeepSeek-V4-Pro",
                "GLM-5.2",
                "qwen3.7-max",
                "Kimi-K2.6",
                "gpt-5.5",
                "claude-opus-4-8",
                "MiniMax-M2.7",
                "gemini-3.1-pro-preview",
            ]},
            {"name": "Ollama (本地)", "key": None, "base_url_env": "OLLAMA_BASE_URL", "model": "qwen2.5:7b"},
            {"name": "跳过", "key": None, "base_url_env": None, "model": None},
        ],
    },
    "image": {
        "title": "图像生成 - 用于生成视频所需图片素材",
        "options": [
            {"name": "fal.ai (FLUX / Seedance / Recraft)", "key": "FAL_KEY", "model": "fal-ai/flux/dev"},
            {"name": "OpenAI DALL·E / GPT Image", "key": "OPENAI_API_KEY", "model": "gpt-image-1"},
            {"name": "AutoDL 模型广场（生图）", "key": "AUTODL_API_KEY", "model_env": "AUTODL_IMAGE_MODEL", "model_default": "gpt-image-2"},
            {"name": "Google Imagen (Vertex)", "key": "GOOGLE_API_KEY", "model": "imagen-3"},
            {"name": "通义万相 (Qwen Image)", "key": "QWEN_IMAGE_API_KEY", "model": "wanx-v1"},
            {"name": "智谱 CogView", "key": "ZHIPU_IMAGE_API_KEY", "model": "cogview-3"},
            {"name": "百度文心一格", "key": "BAIDU_IMAGE_API_KEY", "model": "ernie-vilg"},
            {"name": "跳过", "key": None, "model": None},
        ],
    },
    "video": {
        "title": "视频生成 - 用于生成动态视频片段",
        "options": [
            {"name": "fal.ai (Kling / Veo / MiniMax / Seedance)", "key": "FAL_KEY", "model": "fal-ai/kling-video/v1/standard"},
            {"name": "MiniMax 海螺", "key": "MINIMAX_API_KEY", "model": "video-01"},
            {"name": "可灵 Kling", "key": "KLING_API_KEY", "model": "kling-v1"},
            {"name": "通义万相视频", "key": "QWEN_VIDEO_API_KEY", "model": "wanx2.1-t2v-turbo"},
            {"name": "智谱 CogVideo", "key": "ZHIPU_VIDEO_API_KEY", "model": "cogvideox"},
            {"name": "Runway", "key": "RUNWAY_API_KEY", "model": "gen-4"},
            {"name": "HeyGen", "key": "HEYGEN_API_KEY", "model": "avatar"},
            {"name": "本地 LTX / CogVideo (需要 GPU)", "key": "VIDEO_GEN_LOCAL_ENABLED", "model": "wan2.1-1.3b", "value": "true"},
            {"name": "跳过", "key": None, "model": None},
        ],
    },
    "tts": {
        "title": "语音合成 (TTS) - 用于生成旁白",
        "options": [
            {"name": "ElevenLabs", "key": "ELEVENLABS_API_KEY", "model": "eleven_multilingual_v2"},
            {"name": "Google Cloud TTS", "key": "GOOGLE_API_KEY", "model": "Chirp3-HD"},
            {"name": "OpenAI TTS", "key": "OPENAI_API_KEY", "model": "tts-1"},
            {"name": "豆包 (Doubao)", "key": "DOUBAO_SPEECH_API_KEY", "model_env": "DOUBAO_SPEECH_VOICE_TYPE", "model_default": "zh_female_vv_uranus_bigtts"},
            {"name": "通义听悟 / 千问 TTS", "key": "QWEN_TTS_API_KEY", "model": "cosyvoice-v1"},
            {"name": "百度智能云 TTS", "key": "BAIDU_TTS_API_KEY", "model": "zh"},
            {"name": "Piper (本地免费)", "key": None, "model": "piper"},
            {"name": "跳过", "key": None, "model": None},
        ],
    },
    "music": {
        "title": "音乐生成 - 用于生成背景音乐",
        "options": [
            {"name": "Suno", "key": "SUNO_API_KEY", "model": "suno-v3"},
            {"name": "ElevenLabs Music", "key": "ELEVENLABS_API_KEY", "model": "elevenlabs-music"},
            {"name": "跳过", "key": None, "model": None},
        ],
    },
    "stock": {
        "title": "素材库 - 用于搜索免费视频/图片素材",
        "options": [
            {"name": "Pexels", "key": "PEXELS_API_KEY", "model": "pexels"},
            {"name": "Pixabay", "key": "PIXABAY_API_KEY", "model": "pixabay"},
            {"name": "Unsplash", "key": "UNSPLASH_ACCESS_KEY", "model": "unsplash"},
            {"name": "跳过", "key": None, "model": None},
        ],
    },
}


def print_header(text: str) -> None:
    print()
    print("=" * 60)
    print(text)
    print("=" * 60)


def ask(prompt: str, default: str = "") -> str:
    full_prompt = f"{prompt}"
    if default:
        full_prompt += f" [{default}]"
    full_prompt += ": "
    try:
        value = input(full_prompt).strip()
    except EOFError:
        value = ""
    return value if value else default


def ask_yes_no(prompt: str, default: bool = False) -> bool:
    suffix = "Y/n" if default else "y/N"
    value = ask(f"{prompt} ({suffix})", "y" if default else "n").lower()
    return value in {"y", "yes", "是"}


def choose(title: str, options: list[dict[str, Any]]) -> dict[str, Any]:
    print_header(title)
    for i, opt in enumerate(options, 1):
        print(f"  {i}. {opt['name']}")
    while True:
        choice = ask("请选择序号")
        if not choice.isdigit():
            print("请输入数字序号")
            continue
        idx = int(choice) - 1
        if 0 <= idx < len(options):
            return options[idx]
        print("序号无效，请重新输入")


def load_env() -> dict[str, str]:
    env: dict[str, str] = {}
    if not ENV_PATH.exists():
        return env
    with open(ENV_PATH, "r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line or line.startswith("#") or "=" not in line:
                continue
            key, _, value = line.partition("=")
            key = key.strip()
            value = value.strip()
            # Skip placeholder lines where value is itself a comment/description.
            if value.startswith("#"):
                continue
            env[key] = value
    return env


def save_env(env: dict[str, str]) -> None:
    with open(ENV_PATH, "w", encoding="utf-8") as f:
        f.write("# OpenMontage - 环境变量配置\n")
        f.write("# 由 config_wizard.py 自动生成\n\n")

        sections = {
            "大语言模型 (LLM)": ["ANTHROPIC_API_KEY", "ANTHROPIC_BASE_URL", "OPENAI_API_KEY", "OPENAI_BASE_URL",
                                "DEEPSEEK_API_KEY", "DEEPSEEK_BASE_URL", "QWEN_API_KEY", "QWEN_BASE_URL",
                                "ZHIPU_API_KEY", "ZHIPU_BASE_URL", "MOONSHOT_API_KEY", "MOONSHOT_BASE_URL",
                                "BAICHUAN_API_KEY", "BAICHUAN_BASE_URL", "OPENROUTER_API_KEY", "OPENROUTER_BASE_URL",
                                "AUTODL_API_KEY", "AUTODL_BASE_URL", "OLLAMA_BASE_URL"],
            "图像生成": ["FAL_KEY", "OPENAI_API_KEY", "AUTODL_API_KEY", "AUTODL_IMAGE_MODEL", "GOOGLE_API_KEY", "QWEN_IMAGE_API_KEY", "ZHIPU_IMAGE_API_KEY", "BAIDU_IMAGE_API_KEY"],
            "视频生成": ["FAL_KEY", "MINIMAX_API_KEY", "KLING_API_KEY", "QWEN_VIDEO_API_KEY", "ZHIPU_VIDEO_API_KEY",
                       "RUNWAY_API_KEY", "HEYGEN_API_KEY", "VIDEO_GEN_LOCAL_ENABLED", "VIDEO_GEN_LOCAL_MODEL",
                       "MODAL_LTX2_ENDPOINT_URL"],
            "语音合成": ["ELEVENLABS_API_KEY", "GOOGLE_API_KEY", "OPENAI_API_KEY", "DOUBAO_SPEECH_API_KEY",
                       "DOUBAO_SPEECH_VOICE_TYPE", "QWEN_TTS_API_KEY", "BAIDU_TTS_API_KEY"],
            "音乐生成": ["SUNO_API_KEY"],
            "素材库": ["PEXELS_API_KEY", "PIXABAY_API_KEY", "UNSPLASH_ACCESS_KEY"],
            "Google 服务账号": ["GOOGLE_APPLICATION_CREDENTIALS", "GOOGLE_CLOUD_PROJECT", "GOOGLE_CLOUD_LOCATION"],
            "分析与本地模型": ["HF_TOKEN", "WAV2LIP_PATH", "SADTALKER_PATH"],
        }

        written = set()
        for section, keys in sections.items():
            section_keys = [k for k in keys if k in env]
            if not section_keys:
                continue
            f.write(f"# --- {section} ---\n")
            for key in section_keys:
                f.write(f"{key}={env[key]}\n")
                written.add(key)
            f.write("\n")

        # 未分类的变量
        remaining = {k: v for k, v in env.items() if k not in written}
        if remaining:
            f.write("# --- 其他 ---\n")
            for key, value in remaining.items():
                f.write(f"{key}={value}\n")


def update_config_yaml(llm_provider: str, llm_model: str | None) -> None:
    config: dict[str, Any] = {}
    if CONFIG_PATH.exists():
        with open(CONFIG_PATH, "r", encoding="utf-8") as f:
            config = yaml.safe_load(f) or {}

    config.setdefault("llm", {})
    config["llm"]["provider"] = llm_provider
    if llm_model:
        config["llm"]["model"] = llm_model

    with open(CONFIG_PATH, "w", encoding="utf-8") as f:
        yaml.dump(config, f, allow_unicode=True, sort_keys=False, default_flow_style=False)


def provider_to_config(provider_name: str) -> tuple[str, str | None]:
    """Return (llm_provider, default_model) for config.yaml."""
    mapping = {
        "Anthropic Claude": ("anthropic", "claude-sonnet-4-6"),
        "OpenAI / 兼容端点": ("openai", "gpt-4.1"),
        "DeepSeek": ("openai", "deepseek-chat"),  # 使用 openai 兼容客户端
        "通义千问 (Qwen)": ("openai", "qwen-max"),
        "智谱 GLM": ("openai", "glm-4-plus"),
        "Moonshot 月之暗面": ("openai", "moonshot-v1-8k"),
        "百川": ("openai", "Baichuan4"),
        "OpenRouter": ("openrouter", None),
        "Ollama (本地)": ("ollama", "qwen2.5:7b"),
        "AutoDL 模型广场（对话模型）": ("autodl", None),
    }
    return mapping.get(provider_name, ("anthropic", None))


def run_wizard() -> int:
    print_header("OpenMontage 配置向导")
    print("本向导将帮助你配置各类 AI 服务商的 API key。")
    print("说明：\n  - 可直接按回车跳过不想配置的项目\n  - API key 会保存到项目根目录的 .env 文件中\n  - LLM 选择会同步写入 config.yaml")

    env = load_env()

    # LLM 配置
    llm_choice = choose(PROVIDERS["llm"]["title"], PROVIDERS["llm"]["options"])
    llm_provider_name = llm_choice["name"]

    if llm_choice.get("key"):
        key = ask(f"请输入 {llm_choice['name']} 的 API Key")
        if key:
            env[llm_choice["key"]] = key
            # 很多国内模型走 OpenAI 兼容端点，默认 base_url 非必填
            if llm_choice.get("base_url_env"):
                default_base = {
                    "DEEPSEEK_BASE_URL": "https://api.deepseek.com/v1",
                    "QWEN_BASE_URL": "https://dashscope.aliyuncs.com/compatible-mode/v1",
                    "ZHIPU_BASE_URL": "https://open.bigmodel.cn/api/paas/v4",
                    "MOONSHOT_BASE_URL": "https://api.moonshot.cn/v1",
                    "BAICHUAN_BASE_URL": "https://api.baichuan-ai.com/v1",
                    "OPENROUTER_BASE_URL": "https://openrouter.ai/api/v1",
                    "AUTODL_BASE_URL": "https://www.autodl.art/api/v1",
                }.get(llm_choice["base_url_env"], "")
                base_url = ask(f"请输入 API Base URL（可选）", default_base)
                if base_url:
                    env[llm_choice["base_url_env"]] = base_url

        # AutoDL 需要再选具体模型
        selected_model = llm_choice.get("model")
        if llm_choice["name"] == "AutoDL 模型广场（对话模型）":
            models = llm_choice.get("autodl_models", [])
            print_header("请选择 AutoDL 对话模型")
            for i, m in enumerate(models, 1):
                print(f"  {i}. {m}")
            while True:
                choice = ask("请选择序号", "1")
                if choice.isdigit():
                    idx = int(choice) - 1
                    if 0 <= idx < len(models):
                        selected_model = models[idx]
                        break
                print("序号无效，请重新输入")
            env["AUTODL_LLM_MODEL"] = selected_model

        provider, _ = provider_to_config(llm_choice["name"])
        update_config_yaml(provider, selected_model)
    elif llm_choice["name"] == "Ollama (本地)":
        base_url = ask("请输入 Ollama Base URL", "http://localhost:11434")
        env["OLLAMA_BASE_URL"] = base_url
        update_config_yaml("ollama", llm_choice["model"])

    # 图像、视频、TTS、音乐、素材库
    for category in ("image", "video", "tts", "music", "stock"):
        if not ask_yes_no(f"是否配置 {PROVIDERS[category]['title'].split(' - ')[0]}？"):
            continue
        choice = choose(PROVIDERS[category]["title"], PROVIDERS[category]["options"])
        if choice.get("key"):
            if choice.get("value"):
                env[choice["key"]] = choice["value"]
            else:
                key = ask(f"请输入 {choice['name']} 的 API Key")
                if key:
                    env[choice["key"]] = key
            if choice.get("model_env"):
                model = ask(f"请输入默认声音/模型", choice.get("model_default", ""))
                if model:
                    env[choice["model_env"]] = model
            elif choice.get("model"):
                print(f"  默认模型: {choice['model']}")

    # Google 服务账号（可选）
    if ask_yes_no("是否配置 Google 服务账号（用于 Vertex Imagen / Cloud TTS）？"):
        creds = ask("服务账号 JSON 文件路径")
        if creds:
            env["GOOGLE_APPLICATION_CREDENTIALS"] = creds
        project = ask("GCP 项目 ID")
        if project:
            env["GOOGLE_CLOUD_PROJECT"] = project
        location = ask("GCP 区域", "us-central1")
        if location:
            env["GOOGLE_CLOUD_LOCATION"] = location

    # HuggingFace token（可选）
    if ask_yes_no("是否配置 HuggingFace Token（用于说话人分离）？"):
        token = ask("HF_TOKEN")
        if token:
            env["HF_TOKEN"] = token

    save_env(env)

    print_header("配置完成")
    print(f"已保存到: {ENV_PATH}")
    print(f"LLM 配置已更新到: {CONFIG_PATH}")
    print("\n下一步：")
    print("  1. 用 `python3 -m openmontage_mcp.server` 启动 MCP 服务")
    print("  2. 或在 Claude Code / Cursor 中继续制作视频")
    print("  3. 运行 `python3 -m pytest tests/contracts/ -v` 验证基础工具")
    return 0


if __name__ == "__main__":
    raise SystemExit(run_wizard())
