#!/usr/bin/env bash
# research-collab 安装脚本（macOS / Linux）
#
# 用法：
#   ./install.sh              安装到 ~/.agents/skills/research-collab
#   ./install.sh --codex      再让 Codex 可见（软链到 ~/.codex/skills）
#   ./install.sh --force      覆盖已安装版本
#
# 说明：DSH 读取 ~/.agents/skills；Codex 读取 ~/.codex/skills。
#       用软链指向同一份文件，改一处两边同时生效。

set -euo pipefail

NAME="research-collab"
SRC="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
AGENTS_HOME="${DSH_AGENTS_HOME:-$HOME/.agents}"
DEST="$AGENTS_HOME/skills/$NAME"

CODEX=0
FORCE=0
for arg in "$@"; do
  case "$arg" in
    --codex) CODEX=1 ;;
    --force) FORCE=1 ;;
    *) echo "未知参数：$arg" >&2; exit 2 ;;
  esac
done

if [ ! -f "$SRC/SKILL.md" ]; then
  echo "找不到 SKILL.md；请在仓库根目录运行本脚本。" >&2
  exit 2
fi

if [ -e "$DEST" ] && [ "$FORCE" -eq 0 ]; then
  echo "已安装：$DEST"
  echo "要覆盖请加 --force"
  exit 1
fi

if [ -e "$DEST" ]; then
  echo "移除旧版本：$DEST"
  rm -rf "$DEST"
fi

mkdir -p "$DEST"
for item in SKILL.md README.md LICENSE references scripts templates examples; do
  if [ -e "$SRC/$item" ]; then
    cp -R "$SRC/$item" "$DEST/"
  fi
done

echo "已安装到 $DEST"

if [ "$CODEX" -eq 1 ]; then
  LINK="$HOME/.codex/skills/$NAME"
  mkdir -p "$HOME/.codex/skills"
  if [ -e "$LINK" ] || [ -L "$LINK" ]; then
    echo "已存在，跳过：$LINK（如需重建先手动删除）"
  else
    ln -s "$DEST" "$LINK"
    echo "已链接给 Codex：$LINK"
  fi
fi

echo
echo "验证安装："
echo "  python3 \"$DEST/scripts/init_workspace.py\" \"<项目目录>\" --title \"题目\""
