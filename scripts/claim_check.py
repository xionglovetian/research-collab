#!/usr/bin/env python3
"""核对草稿中的数字是否全部可追溯到证据台账（research-collab skill）。

它拦的是写作环节最常见的事故：为了句子通顺，把数字写漂了、把估算写成实证、
把假设塞进摘要。

用法：
    python claim_check.py --draft 05_draft/v1_results.md --claims 04_results/claims.csv
    python claim_check.py --draft 05_draft/*.md --claims 04_results/claims.csv --tol 0.1
    python claim_check.py --draft 05_draft/v1_results.md --json

退出码：0 通过；1 存在未匹配数字或强度违规；2 输入错误。
"""

from __future__ import annotations

import argparse
import csv
import json
import re
import sys
from pathlib import Path

for _stream in (sys.stdout, sys.stderr):
    if hasattr(_stream, "reconfigure"):
        try:
            _stream.reconfigure(encoding="utf-8", errors="replace")
        except Exception:
            pass

NUM_RE = re.compile(r"(?<![0-9A-Za-z._^⁻])(\d+(?:\.\d+)?(?:[eE][+-]?\d+)?)(?![0-9A-Za-z._])")
SCI_RE = re.compile(r"(\d+(?:\.\d+)?)\s*[×xX*]\s*10\s*\^?\s*([+-]?\d+)")
STRONG_VERBS = ("证明", "表明", "证实", "揭示", "说明", "确立了", "建立了")
WEAK_MARKERS = ("估计", "假定", "假设", "推测", "预计", "预期", "估算", "大约", "约", "可能")


# ---------------------------------------------------------------- 台账

class Claim:
    __slots__ = ("id", "claim", "value", "unit", "strength", "source", "allowed_in", "note", "numbers")

    def __init__(self, row: dict[str, str]):
        self.id = (row.get("id") or "").strip()
        self.claim = (row.get("claim") or "").strip()
        self.value = (row.get("value") or "").strip()
        self.unit = (row.get("unit") or "").strip()
        self.strength = (row.get("strength") or "").strip().lower()
        self.source = (row.get("source") or "").strip()
        self.allowed_in = {
            s.strip().lower() for s in (row.get("allowed_in") or "").split(";") if s.strip()
        } or {"results", "discussion"}
        self.note = (row.get("note") or "").strip()
        self.numbers = _parse_value(self.value)


def _parse_value(raw: str) -> list[float]:
    """台账 value 可能是单值、区间（85–93）、带千分位。返回可接受数值列表。"""
    if not raw:
        return []
    cleaned = raw.replace(",", "").replace("，", "")
    parts = re.split(r"[–—~～\-至]", cleaned)
    out: list[float] = []
    for part in parts:
        part = part.strip().rstrip("%")
        if not part:
            continue
        try:
            out.append(float(part))
        except ValueError:
            continue
    return out


def load_claims(path: Path) -> list[Claim]:
    with open(path, "r", encoding="utf-8-sig", newline="") as fh:
        rows = list(csv.DictReader(fh))
    claims = [Claim(r) for r in rows]
    return [c for c in claims if c.id]


# ---------------------------------------------------------------- 草稿预处理

def strip_noise(text: str) -> str:
    if text.startswith("---"):
        end = text.find("\n---", 3)
        if end != -1:
            text = text[end + 4 :]
    text = re.sub(r"```.*?```", " ", text, flags=re.S)
    text = re.sub(r"`[^`]*`", " ", text)
    text = re.sub(r"https?://\S+", " ", text)
    text = re.sub(r"[（(]?\bC\d{1,3}\b[)）]?", " ", text)
    text = re.sub(r"\[\d+(?:\s*[-,–]\s*\d+)*\]", " ", text)
    text = re.sub(r"(图|表|Figure|Fig\.|Table)\s*\d+", " ", text)
    # 标题层级与章节序号不是观测值："### 3.2 结果"、"2.1 材料"
    text = re.sub(r"^\s{0,3}#{1,6}\s*", "", text, flags=re.M)
    text = re.sub(r"^\s*\d+(?:\.\d+)*[.、)]?\s", " ", text, flags=re.M)
    return text


def prepare(text: str, ignore_patterns: list[str] | None = None) -> str:
    """把正文整理成"只剩待核对数值"的形态，压掉误报来源。"""
    text = strip_noise(text)
    # 科学计数：1.2×10^5 / 1.2x10^5 / 10^5
    text = SCI_RE.sub(
        lambda m: format(float(m.group(1)) * (10 ** int(m.group(2))), ".10g"), text
    )
    text = re.sub(
        r"10\s*\^\s*([+-]?\d+)", lambda m: format(10.0 ** int(m.group(1)), ".10g"), text
    )
    # 区间统一拆成两端的独立数值：85–93 / 85-93 / 85~93
    text = re.sub(r"(?<=\d)\s*[–—~～-]\s*(?=\d)", " ", text)
    # 量纲指数不是观测值：kg·hm-2 / m^2 / s^-1 / cm3 已由词边界覆盖
    text = re.sub(r"(?<=[A-Za-z])\s*[-−^⁻]\s*\d+(?:\.\d+)?", " ", text)
    # 千分位
    text = re.sub(r"(?<=\d),(?=\d{3}(?!\d))", "", text)
    for pattern in ignore_patterns or []:
        try:
            text = re.sub(pattern, " ", text)
        except re.error as exc:
            print(f"[!] --ignore 正则无效，已跳过：{pattern}（{exc}）", file=sys.stderr)
    return text


def extract_numbers(text: str) -> list[tuple[float, str]]:
    found = []
    for m in NUM_RE.finditer(text):
        try:
            found.append((float(m.group(1)), m.group(1)))
        except ValueError:
            continue
    return found


def context_of(text: str, token: str, window: int = 28) -> str:
    idx = text.find(token)
    if idx == -1:
        return ""
    snippet = text[max(0, idx - window) : idx + len(token) + window]
    return re.sub(r"\s+", " ", snippet).strip()


# ---------------------------------------------------------------- 匹配

def close(a: float, b: float, tol: float) -> bool:
    if a == b:
        return True
    if abs(a - b) <= tol:
        return True
    return abs(a - b) <= 1e-9 * max(1.0, abs(b))


def match_number(value: float, claims: list[Claim], tol: float) -> tuple[Claim | None, str]:
    best: tuple[Claim | None, str, float] = (None, "", float("inf"))
    for c in claims:
        for num in c.numbers:
            # 只允许"台账存小数、正文写百分数"这一种单位换算（0.923 -> 92.3）。
            # 反向（台账 85、正文 0.85）是口径错误，应当被报出来而不是自动放过。
            for scale, note in ((1.0, ""), (100.0, "（按百分比换算）")):
                target = num * scale
                if close(value, target, tol):
                    diff = abs(value - target)
                    if diff < best[2]:
                        best = (c, note, diff)
    return best[0], best[1]


def is_abstract(draft: Path, raw_text: str) -> bool:
    head = raw_text[:600].lower()
    if re.search(r"^section:\s*abstract", head, flags=re.M):
        return True
    return "abstract" in draft.stem.lower() or "摘要" in draft.stem


def sentences(text: str) -> list[str]:
    return [s for s in re.split(r"(?<=[。！？!?；;\n])", text) if s.strip()]


def count_words(text: str) -> int:
    cjk = len(re.findall(r"[\u4e00-\u9fff]", text))
    latin = len(re.findall(r"[A-Za-z]+", text))
    return cjk + latin


# ---------------------------------------------------------------- 主流程

def check_draft(
    draft: Path,
    claims: list[Claim],
    tol: float,
    whitelist: bool,
    ignores: list[str] | None = None,
) -> dict:
    raw = draft.read_text(encoding="utf-8-sig", errors="replace")
    cleaned = prepare(raw, ignores)
    numbers = extract_numbers(cleaned)

    matched: list[dict] = []
    unmatched: list[dict] = []
    used_ids: set[str] = set()

    for value, token in numbers:
        if whitelist and re.fullmatch(r"\d{4}", token) and 1900 <= value <= 2100:
            continue
        claim, note = match_number(value, claims, tol)
        if claim is None:
            unmatched.append({"token": token, "value": value, "context": context_of(cleaned, token)})
        else:
            used_ids.add(claim.id)
            matched.append({"token": token, "id": claim.id, "note": note})

    violations: list[dict] = []
    sents = sentences(cleaned)
    abstract = is_abstract(draft, raw)
    for c in claims:
        if c.strength != "assumption":
            continue
        cited = c.id in raw or any(m["id"] == c.id for m in matched)
        if not cited:
            continue
        if abstract:
            violations.append(
                {
                    "id": c.id,
                    "kind": "assumption-in-abstract",
                    "detail": f"{c.id} 强度为 assumption，不得出现在摘要/结论中",
                }
            )
        for s in sents:
            involves = c.id in s or any(
                str(n) in s or format(n, "g") in s for n in c.numbers
            )
            if not involves:
                continue
            hit = [v for v in STRONG_VERBS if v in s]
            if hit and not any(w in s for w in WEAK_MARKERS):
                violations.append(
                    {
                        "id": c.id,
                        "kind": "strength-upgrade",
                        "detail": f"{c.id}（assumption）被写成「{hit[0]}」：{s.strip()[:80]}",
                    }
                )

    with_numbers = [c for c in claims if c.numbers]
    unused = [c for c in with_numbers if c.id not in used_ids]
    placeholders = re.findall(r"\[待补[:：][^\]]*\]", raw)

    declared: list[str] = []
    m = re.search(r"^claims_used:\s*\[(.*?)\]", raw, flags=re.M)
    if m:
        declared = [x.strip().strip("'\"") for x in m.group(1).split(",") if x.strip()]

    return {
        "draft": str(draft),
        "words": count_words(strip_noise(raw)),
        "numbers_found": len(numbers),
        "matched": matched,
        "unmatched": unmatched,
        "violations": violations,
        "unused": [{"id": c.id, "claim": c.claim} for c in unused],
        "placeholders": placeholders,
        "claims_declared": declared,
        "claims_declared_missing_from_ledger": sorted(set(declared) - {c.id for c in claims}),
        "ok": not unmatched and not violations,
    }


def render(result: dict) -> None:
    print(f"== 草稿核对：{result['draft']} ==")
    print(
        f"   字数约 {result['words']}，数值 {result['numbers_found']} 个，"
        f"占位符 {len(result['placeholders'])} 处"
    )
    if result["matched"]:
        scaled = [m for m in result["matched"] if m["note"]]
        line = f"[✓] 已追溯 {len(result['matched'])} 个数值"
        if scaled:
            line += f"（其中 {len(scaled)} 个经单位换算匹配，请确认口径）"
        print(line)

    if result["unmatched"]:
        print(f"[✗] 未匹配数值 {len(result['unmatched'])} 处 —— 疑似编造，必须逐条处理：")
        for item in result["unmatched"]:
            print(f"    · {item['token']}  …{item['context']}…")
        print("    处理方式只有两种：补进台账（它确实来自结果）或改写（它是编的）。")
    else:
        print("[✓] 所有数值均可追溯到台账")

    if result["violations"]:
        print(f"[!] 强度违规 {len(result['violations'])} 处：")
        for v in result["violations"]:
            print(f"    · [{v['kind']}] {v['detail']}")
    else:
        print("[✓] 无 claim 强度升级")

    if result["placeholders"]:
        print(f"[·] 待补占位符 {len(result['placeholders'])} 处（成稿前必须清零）：")
        for p in result["placeholders"]:
            print(f"    · {p}")

    if result["unused"]:
        print(f"[·] 台账未使用条目 {len(result['unused'])} 条（确认是否有发现漏写）：")
        for u in result["unused"][:10]:
            print(f"    · {u['id']} {u['claim'][:48]}")
        if len(result["unused"]) > 10:
            print(f"    · …另有 {len(result['unused']) - 10} 条")

    if result["claims_declared_missing_from_ledger"]:
        print(f"[✗] 文件头声明的 claim 编号不在台账中：{result['claims_declared_missing_from_ledger']}")

    print("结论：" + ("通过" if result["ok"] else "不通过"))


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="核对草稿数字与证据台账")
    parser.add_argument("--draft", nargs="+", required=True, help="一个或多个草稿 md 文件")
    parser.add_argument("--claims", required=True, help="证据台账 claims.csv")
    parser.add_argument("--tol", type=float, default=0.05, help="数值容差，默认 0.05（四舍五入）")
    parser.add_argument("--no-whitelist", action="store_true", help="不豁免 4 位年份")
    parser.add_argument(
        "--ignore",
        action="append",
        metavar="REGEX",
        help="忽略匹配该正则的片段（可多次），如 --ignore 'n\\s*=\\s*\\d+'",
    )
    parser.add_argument("--json", action="store_true", help="以 JSON 输出结果")
    args = parser.parse_args(argv)

    claims_path = Path(args.claims)
    if not claims_path.is_file():
        print(f"[x] 找不到台账：{claims_path}", file=sys.stderr)
        return 2
    claims = load_claims(claims_path)
    if not claims:
        print("[!] 台账为空（只有表头）。先按 references/evidence-ledger.md 建立条目。", file=sys.stderr)

    results = []
    for raw_draft in args.draft:
        draft = Path(raw_draft)
        if not draft.is_file():
            print(f"[x] 找不到草稿：{draft}", file=sys.stderr)
            return 2
        results.append(
            check_draft(draft, claims, args.tol, not args.no_whitelist, args.ignore)
        )

    if args.json:
        print(json.dumps({"claims": len(claims), "drafts": results}, ensure_ascii=False, indent=2))
    else:
        for res in results:
            render(res)
            print()
        failed = [r for r in results if not r["ok"]]
        print(f"总计 {len(results)} 个文件，通过 {len(results) - len(failed)}，不通过 {len(failed)}")

    return 0 if all(r["ok"] for r in results) else 1


if __name__ == "__main__":
    raise SystemExit(main())
