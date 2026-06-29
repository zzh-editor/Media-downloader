#!/usr/bin/env bash
set -e

echo "=== media-downloader 环境检查 ==="

check_tool() {
  if command -v "$1" >/dev/null 2>&1; then
    echo "  ✅ $1: $(command -v "$1")"
    return 0
  else
    echo "  ❌ $1: 未安装"
    return 1
  fi
}

MISSING=""
check_tool yt-dlp || MISSING="$MISSING yt-dlp"
check_tool gallery-dl || MISSING="$MISSING gallery-dl"
check_tool ffmpeg || MISSING="$MISSING ffmpeg"

if [ -n "$MISSING" ]; then
  echo ""
  echo "缺失工具:$MISSING"
  echo ""
  echo "安装命令:"
  echo "  brew install$MISSING"
  exit 1
fi

echo ""
echo "✅ 全部依赖就绪"
exit 0
