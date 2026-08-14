#!/usr/bin/env python3
"""Vimeo 下载器（JWT 方案）：绕开 Cloudflare Turnstile 挡死 yt-dlp 的场景。

背景：player.vimeo.com 被 CF Turnstile 人机验证挡住，yt-dlp / curl 全部 401/403。
但 Vimeo 网页版登录用户可通过页面内嵌 __NEXT_DATA__ 里的 viewerBootstrap.jwt，
调 api.vimeo.com 拿签名文件 URL 直接下载——完全绕过 Turnstile，泛平台。

用法（JWT 由浏览器 MCP evaluate 提取后传 stdin 或 --jwt）：
  echo "<JWT>" | python3 vimeo_jwt_dl.py --video 1199171757 -o /tmp/out.mp4
  python3 vimeo_jwt_dl.py --video 1199171757 --jwt "$JWT" -o /tmp/out.mp4
  python3 vimeo_jwt_dl.py --video 1199171757 --jwt "$JWT" --list   # 只列清晰度不下

也可自动从 __NEXT_DATA__ 提取 JWT（需 --html <文件>，由浏览器存的外层 HTML）：
  python3 vimeo_jwt_dl.py --video 1199171757 --html /tmp/page.html -o /tmp/out.mp4

退出码：0 成功 / 1 失败（含未登录 / 无可用文件）
"""
import argparse
import json
import re
import subprocess
import sys
import urllib.parse
import urllib.request

UA = ("Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/605.1.15 "
      "(KHTML, like Gecko) Version/18.0 Safari/605.1.15")
MAX_HEIGHT = 1080  # 默认最高清晰度（>1080 走清晰度策略询问，脚本只取 ≤1080）


def extract_jwt_from_html(html: str) -> str | None:
    """从页面 HTML 的 __NEXT_DATA__ 提取 viewerBootstrap.jwt。"""
    m = re.search(r'<script id="__NEXT_DATA__"[^>]*>(.*?)</script>', html, re.S)
    if not m:
        return None
    try:
        d = json.loads(m.group(1))
        return d["props"]["pageProps"]["viewerBootstrap"].get("jwt")
    except (KeyError, ValueError, TypeError):
        return None


def fetch_files(video_id: str, jwt: str) -> dict:
    url = f"https://api.vimeo.com/videos/{video_id}?fields=name,uri,privacy,files"
    req = urllib.request.Request(url, headers={
        "Authorization": "jwt " + jwt,
        "Accept": "application/vnd.vimeo.*+json;version=3.4",
        "User-Agent": UA,
    })
    with urllib.request.urlopen(req, timeout=30) as r:
        return json.loads(r.read())


def pick_best(files: list, max_height: int = MAX_HEIGHT) -> dict | None:
    best = None
    for f in files:
        h = f.get("height") or 0
        if h <= max_height and f.get("link"):
            if best is None or h > best.get("height", 0):
                best = f
    return best


def download(url: str, out: str) -> int:
    cmd = ["curl", "-sL",
           "-A", UA,
           "-H", "Referer: https://vimeo.com/",
           "-o", out, "-w", "%{http_code}", url]
    r = subprocess.run(cmd, capture_output=True, text=True)
    code = r.stdout.strip()
    if code != "200":
        return 1
    return 0


def main() -> int:
    ap = argparse.ArgumentParser(description="Vimeo JWT 下载器")
    ap.add_argument("--video", required=True, help="Vimeo video id 或完整 URL")
    ap.add_argument("--jwt", help="viewerBootstrap.jwt（网页登录 token）")
    ap.add_argument("--html", help="含 __NEXT_DATA__ 的页面 HTML 文件（自动提 JWT）")
    ap.add_argument("-o", "--output", help="输出文件路径（缺省 --list 模式）")
    ap.add_argument("--list", action="store_true", help="只列清晰度不下载")
    args = ap.parse_args()

    vid = args.video
    m = re.search(r"/(\d+)(?:[/?]|$)", vid)
    if m:
        vid = m.group(1)

    jwt = args.jwt
    if not jwt and args.html:
        jwt = extract_jwt_from_html(open(args.html, encoding="utf-8", errors="ignore").read())
    if not jwt:
        print("ERROR: 未提供 JWT。用浏览器 MCP 打开 Vimeo 视频页后 evaluate 提取：\n"
              "  JSON.parse(document.getElementById('__NEXT_DATA__').textContent)"
              ".props.pageProps.viewerBootstrap.jwt", file=sys.stderr)
        return 1

    try:
        d = fetch_files(vid, jwt)
    except Exception as e:
        print(f"ERROR: API 调用失败：{e}", file=sys.stderr)
        return 1

    if d.get("error"):
        print(f"ERROR: API 返回 {d['error']}", file=sys.stderr)
        return 1

    files = d.get("files", [])
    if not files:
        print("ERROR: 无可用文件（视频可能需要更高权限）", file=sys.stderr)
        return 1

    best = pick_best(files)
    if not best:
        print("ERROR: 无 ≤1080p 可下载文件", file=sys.stderr)
        return 1

    print(f"title: {d.get('name')}")
    print(f"pick: {best.get('width')}x{best.get('height')} {best.get('type')}")

    if args.list:
        for f in files:
            h = f.get("height") or 0
            mark = " <=1080p" if h <= MAX_HEIGHT and f.get("link") else ""
            print(f"  {f.get('width')}x{h} {f.get('type')}{mark}")
        return 0

    if not args.output:
        print("ERROR: 需要 -o 指定输出文件（或 --list）", file=sys.stderr)
        return 1

    if download(best["link"], args.output) == 0:
        print(f"OK -> {args.output}")
        return 0
    print("ERROR: 下载失败（HTTP 非 200）", file=sys.stderr)
    return 1


if __name__ == "__main__":
    sys.exit(main())