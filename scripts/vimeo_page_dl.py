#!/usr/bin/env python3
"""Vimeo 下载器（浏览器抓签名播放列表方案）。

背景：Vimeo 网页版被 Cloudflare Turnstile 挡住 player.vimeo.com，yt-dlp/curl
直接访问全被 401。api.vimeo.com 的 JWT 方案只对 `privacy.download: true` 的视频
有效；公开可看但禁止下载的视频（`files`/`play` 返回空数组）拿不到直链。

可行路径：真实浏览器加载视频页时，播放器会向 CDN（不经 Turnstile）请求一份
带签名的 master playlist。用 CDP 抓到这个 URL，交给 yt-dlp 下载即可。
签名 URL 约 1 小时过期，抓完立刻下。

用法：
  python3 scripts/vimeo_page_dl.py --url https://vimeo.com/1233672899 -o /tmp/out.mp4
  python3 scripts/vimeo_page_dl.py --url https://vimeo.com/1233672899 --list
  python3 scripts/vimeo_page_dl.py --url 1233672899            # 输出到 download_dir/<标题>.mp4

退出码：0 成功 / 1 失败（抓不到播放列表、下载失败、音视频时长不一致）
"""
import argparse
import json
import os
import re
import shutil
import subprocess
import sys
import tempfile

SKILL_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
CONFIG = os.path.join(SKILL_DIR, "config.json")

# 在真实浏览器里跑：开一个临时标签页，抓 master playlist，然后关掉该标签页
BROWSER_SNIPPET = r"""
import json, time
url = {url!r}
cdp("Network.enable")
drain_events()
tid = new_tab(url)
wait_for_load()
masters, meta = set(), None
deadline = time.time() + {timeout}
while time.time() < deadline:
    for e in drain_events():
        if e.get("method") not in ("Network.requestWillBeSent", "Network.responseReceived"):
            continue
        p = e.get("params", {{}})
        u = (p.get("request") or p.get("response") or {{}}).get("url", "")
        if "playlist.m3u8" in u:
            masters.add(u)
    if masters and meta is None:
        meta = js("(()=>{{const el=document.getElementById('__NEXT_DATA__');"
                  "if(!el)return null;const c=JSON.parse(el.textContent).props.pageProps.clip;"
                  "return JSON.stringify({{name:c&&c.name,w:c&&c.width,h:c&&c.height,dur:c&&c.duration}});}})()")
    if masters and meta:
        break
    time.sleep(1)
close_tab(target=tid)
print("<<<VIMEO>>>" + json.dumps({{"masters": sorted(masters), "meta": meta}}))
"""


def sanitize_title(t):
    t = re.sub(r'[\\/:*?"<>|]', "-", t)
    t = re.sub(r"\s+", " ", t).strip()
    return re.sub(r"-{2,}", "-", t).strip("-. ")


def load_config():
    try:
        with open(CONFIG) as f:
            return json.load(f)
    except (OSError, ValueError):
        return {}


def capture_master(url, timeout=30):
    """在真实浏览器里打开视频页，返回 (master_playlist_url, meta)。"""
    snippet = BROWSER_SNIPPET.format(url=url, timeout=timeout)
    if not shutil.which("browser-harness"):
        print("ERROR: 未安装 browser-harness（uv tool install browser-harness）", file=sys.stderr)
        return None, None

    env = dict(os.environ)
    cdp_url = load_config().get("cdp_url")
    if cdp_url:
        env["BU_CDP_WS" if cdp_url.startswith("ws") else "BU_CDP_URL"] = cdp_url

    r = subprocess.run(["browser-harness"], input=snippet, capture_output=True,
                       text=True, env=env, timeout=timeout + 90)
    marker = "<<<VIMEO>>>"
    payload = next((ln[len(marker):] for ln in r.stdout.splitlines()
                    if ln.startswith(marker)), None)
    if not payload:
        print(f"ERROR: 浏览器未返回播放列表\n{r.stdout[-800:]}\n{r.stderr[-800:]}", file=sys.stderr)
        return None, None

    data = json.loads(payload)
    meta = json.loads(data["meta"]) if data.get("meta") else {}
    masters = data["masters"]
    if not masters:
        return None, meta
    # 优先带 pr= 的 master；退而取第一个
    master = next((u for u in masters if "pr=" in u), masters[0])
    return master, meta


def run(cmd, **kw):
    return subprocess.run(cmd, capture_output=True, text=True, **kw)


def probe(path):
    """返回 (容器时长, 视频流尺寸, 音频时长)，取不到的字段为 None。"""
    r = run(["ffprobe", "-v", "error", "-of", "json", "-show_entries",
             "format=duration:stream=codec_type,duration,width,height", path])
    if r.returncode != 0:
        return None, None, None
    d = json.loads(r.stdout or "{}")
    fmt = float(d.get("format", {}).get("duration") or 0) or None
    size = audio = None
    for s in d.get("streams", []):
        dur = float(s.get("duration") or 0) or None
        if s.get("codec_type") == "video" and s.get("width"):
            size = f"{s['width']}x{s['height']}"
        elif s.get("codec_type") == "audio":
            audio = dur
    return fmt, size, audio


def main():
    ap = argparse.ArgumentParser(description="Vimeo 下载器（浏览器抓签名播放列表）")
    ap.add_argument("--url", required=True, help="vimeo 视频 URL 或 id")
    ap.add_argument("-o", "--output", help="输出文件路径（缺省 download_dir/<标题>.mp4）")
    ap.add_argument("--list", action="store_true", help="只列清晰度不下载")
    ap.add_argument("--max-height", type=int, default=1080, help="最高分辨率，默认 1080")
    ap.add_argument("--no-proxy", action="store_true",
                    help="忽略本机 HTTP(S)_PROXY（代理挡 CDN 时用）")
    args = ap.parse_args()

    url = args.url
    if re.fullmatch(r"\d+", url):
        url = f"https://vimeo.com/{url}"

    master, meta = capture_master(url)
    if not master:
        print("ERROR: 没抓到签名播放列表（页面未加载出播放器，或视频需要密码/登录）",
              file=sys.stderr)
        return 1

    name = sanitize_title(meta.get("name") or "video")
    print(f"title: {name}  src: {meta.get('w')}x{meta.get('h')}  {meta.get('dur')}s")

    env = dict(os.environ)
    if args.no_proxy:
        for k in list(env):
            if k.lower() in ("http_proxy", "https_proxy", "all_proxy", "no_proxy"):
                env.pop(k)

    if args.list:
        r = run(["yt-dlp", "-F", master], env=env)
        print(r.stdout[-2000:] or r.stderr[-2000:])
        return 0

    out = args.output
    if not out:
        dl = os.path.expanduser(load_config().get("download_dir") or "~/Downloads")
        out = os.path.join(dl, f"{name}.mp4")
    if os.path.exists(out):
        # yt-dlp 遇到同名文件会直接跳过，导致后面校验的是旧文件
        print(f"ERROR: 输出文件已存在，换路径或先删掉：{out}", file=sys.stderr)
        return 1

    cmd = ["yt-dlp", master, "-f", "bv*+ba/b", "-S", f"res:{args.max_height}",
           "-o", out, "--newline"]
    r = run(cmd, env=env)
    if r.returncode != 0:
        print(f"ERROR: yt-dlp 下载失败\n{r.stderr[-1500:]}", file=sys.stderr)
        return 1

    fmt, size, audio = probe(out)
    if fmt is None:
        print(f"ERROR: 输出文件无法解析：{out}", file=sys.stderr)
        return 1
    if audio and fmt - audio > 1:
        os.remove(out)  # 坏文件删掉，重跑不会被"已存在"拦住
        print(f"ERROR: 音视频时长不一致（音频 {audio:.1f}s / 容器 {fmt:.1f}s，"
              f"约缺 {fmt - audio:.1f}s）——分片下载失败。重跑本脚本（会重新取签名 URL），"
              f"代理不稳时加 --no-proxy", file=sys.stderr)
        return 1
    print(f"OK -> {out}  {size}  {fmt:.1f}s  音频 {audio:.1f}s" if audio
          else f"OK -> {out}  {size}  {fmt:.1f}s（无音轨）")
    return 0


if __name__ == "__main__":
    sys.exit(main())
