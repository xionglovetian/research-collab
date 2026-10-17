#!/usr/bin/env python3
"""直接调用豆包模型（火山引擎方舟 Ark，OpenAI 兼容接口）。

这是让豆包真正"调用本 skill"的唯一方式：豆包本体读不到文件、跑不了脚本，
但它的模型可以被程序调用。此时由 DSH 充当宿主——把 skill 的常驻纪律作为
system prompt、把 make_brief 生成的包作为 user message 发过去。

配置（环境变量）：
    ARK_API_KEY    必填。火山引擎方舟控制台的 API Key。
    ARK_MODEL      必填。模型 ID 或接入点 ID，如 doubao-pro-32k / ep-2024xxxx
    ARK_BASE_URL   可选。默认 https://ark.cn-beijing.volces.com/api/v3

仅用标准库，无第三方依赖。
"""

from __future__ import annotations

import json
import os
import re
import sys
import urllib.error
import urllib.request
from pathlib import Path

DEFAULT_BASE = "https://ark.cn-beijing.volces.com/api/v3"

FALLBACK_SYSTEM = """你是中文学术写作助手，负责把已经确定的证据写成通顺、克制、可发表的正文。
你不做研究判断，不补充事实。

三条铁律：
1. 不得新增任何数字、百分比、年份、样本量、文献或结论。只能用我给出的证据表里带编号的条目，并在引用处标注（C01）这样的编号。
2. 不得改变结论强度：标为「估计/假定」的只能写"估计/假定/可能"，不得写成"表明/证明"；不得把"相关"写成"因果"；不得从单一样本外推到整体。
3. 我给的证据不够时，写占位符 [待补:具体缺什么]，不要自己补、不要猜、不要用"约/近/超过"含糊过去。

写作要求：学术书面语，第三人称；每段一个论点，段首句即论点；不用空泛评价；不出现元话语。"""


class ArkError(RuntimeError):
    pass


def load_system_prompt() -> str:
    """优先用 integrations/doubao.md 里那段常驻纪律，没有就用内置精简版。"""
    skill_root = Path(__file__).resolve().parent.parent
    doc = skill_root / "integrations" / "doubao.md"
    if doc.is_file():
        text = doc.read_text(encoding="utf-8-sig", errors="replace")
        blocks = re.findall(r"```text\n(.*?)```", text, re.S)
        if blocks:
            return blocks[0].strip()
    return FALLBACK_SYSTEM


def call(
    user_prompt: str,
    *,
    api_key: str | None = None,
    model: str | None = None,
    base_url: str | None = None,
    temperature: float = 0.3,
    timeout: int = 180,
) -> str:
    api_key = api_key or os.environ.get("ARK_API_KEY", "").strip()
    model = model or os.environ.get("ARK_MODEL", "").strip()
    base_url = (base_url or os.environ.get("ARK_BASE_URL", DEFAULT_BASE)).rstrip("/")

    if not api_key:
        raise ArkError(
            "缺少 ARK_API_KEY。\n"
            "  1) 到火山引擎方舟控制台开通豆包模型并创建 API Key\n"
            "  2) 设置环境变量：$env:ARK_API_KEY=\"...\"\n"
            "     同时设置模型：$env:ARK_MODEL=\"doubao-pro-32k\" 或你的接入点 ID"
        )
    if not model:
        raise ArkError(
            "缺少 ARK_MODEL（模型 ID 或接入点 ep-xxxx）。\n"
            "  例：$env:ARK_MODEL=\"doubao-pro-32k\""
        )

    payload = {
        "model": model,
        "messages": [
            {"role": "system", "content": load_system_prompt()},
            {"role": "user", "content": user_prompt},
        ],
        "temperature": temperature,
    }
    req = urllib.request.Request(
        f"{base_url}/chat/completions",
        data=json.dumps(payload).encode("utf-8"),
        headers={
            "Content-Type": "application/json",
            "Authorization": f"Bearer {api_key}",
        },
        method="POST",
    )
    try:
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            data = json.loads(resp.read().decode("utf-8"))
    except urllib.error.HTTPError as exc:
        detail = exc.read().decode("utf-8", errors="replace")[:600]
        raise ArkError(f"调用失败 HTTP {exc.code}：{detail}") from exc
    except urllib.error.URLError as exc:
        raise ArkError(f"网络错误：{exc.reason}（检查网络或 ARK_BASE_URL）") from exc
    except json.JSONDecodeError as exc:
        raise ArkError(f"返回内容不是合法 JSON：{exc}") from exc

    try:
        return data["choices"][0]["message"]["content"]
    except (KeyError, IndexError, TypeError) as exc:
        raise ArkError(f"返回结构异常：{json.dumps(data, ensure_ascii=False)[:600]}") from exc


def main(argv: list[str] | None = None) -> int:
    for stream in (sys.stdout, sys.stderr):
        if hasattr(stream, "reconfigure"):
            try:
                stream.reconfigure(encoding="utf-8", errors="replace")
            except Exception:
                pass

    if not argv:
        print(__doc__)
        return 0
    prompt = " ".join(argv)
    try:
        print(call(prompt))
    except ArkError as exc:
        print(f"[x] {exc}", file=sys.stderr)
        return 5
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
