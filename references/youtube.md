# YouTube 下载与高清格式处理

SKILL.md 的「PO Token provider」「YouTube 专用处理」「下载后处理」三节内容在本文件。技能更新时上游若覆盖 SKILL.md，本文件不受影响。

---

## 一、PO Token provider（高清格式必需）

### 现象

YouTube 的 `web_creator` client 把 1080p 以上（含全部 4K）格式标记为 "require a GVS PO Token"。**没有 PO Token 时 yt-dlp 会静默跳过这些格式，`-F` 只剩 360p 和 18 号 mp4**，看起来像"视频最高只有 360p"，实际是缺 token。

PO Token 还决定 age-restricted 与 `The page needs to be reloaded` 两类报错能否通过。

### 检查是否已装

```bash
yt-dlp -v --skip-download "https://www.youtube.com/watch?v=<任意ID>" 2>&1 | grep "PO Token Providers"
```

看到 `bgutil:script-node-<版本> (external)` 且随后有 `Generating a gvs PO Token` 行 → 已就绪，跳过安装。

若只看到 `bgutil:http-<版本> (external)` 后跟 `WARNING ... Error reaching GET http://127.0.0.1:4416/ping`，说明装了插件但没起 HTTP server，忽略即可 —— script 模式会兜底。

### 安装（三步）

```bash
# 1. 插件（装进 yt_dlp_plugins）
pip install -U bgutil-ytdlp-pot-provider          # macOS 用 pip3 install --break-system-packages

# 2. provider 源码放官方默认位置 %USERPROFILE%\bgutil-ytdlp-pot-provider（~/bgutil-ytdlp-pot-provider）
git clone --single-branch --branch <与插件同版本号> --depth 1 \
  https://github.com/Brainicism/bgutil-ytdlp-pot-provider.git "$HOME/bgutil-ytdlp-pot-provider"
cd "$HOME/bgutil-ytdlp-pot-provider/server"

# 3. 编译（Node >= 22 或 Deno >= 2，任选其一）
npm ci && npx tsc            # Node
# deno install --allow-scripts=npm:canvas --frozen   # Deno
```

插件版本与 provider 源码的 tag 必须一致。查版本：`pip show bgutil-ytdlp-pot-provider`；换版本后在仓库里 `git fetch --tags && git checkout <版本号>` 再重编译。

### Windows 必须先预热一次

provider 用 script 模式时每次调用都要 spawn 一个 node 进程，yt-dlp 的超时上限是 15 秒；首次冷启动实测 21 秒会被判超时失败（`ERROR: Command '[...generate_once.js', '--version']' timed out after 15.0 seconds`）。

```powershell
node "$env:USERPROFILE\bgutil-ytdlp-pot-provider\server\build\generate_once.js" --version   # 首次 ~21s，失败正常
node "$env:USERPROFILE\bgutil-ytdlp-pot-provider\server\build\generate_once.js" --version   # 第二次 ~2s
```

预热后再跑 yt-dlp 即可。token 有 6 小时缓存，`TOKEN_TTL` 环境变量可调（单位小时）。

### HTTP server 模式（可选）

适合批量下载，省掉每次 spawn 的开销：

```bash
cd "$HOME/bgutil-ytdlp-pot-provider/server" && node build/main.js    # 默认 127.0.0.1:4416
```

非默认端口用 `--extractor-args "youtubepot-bgutilhttp:base_url=http://127.0.0.1:8080"`。插件会优先用 HTTP server。

provider 装在非默认位置时用 `--extractor-args "youtubepot-bgutilscript:server_home=<路径>/server"`。

### 兜底 client（装不了 provider 时）

`web_safari` / `mweb` / `web_embedded` 均不需要 PO Token，但最高 1080p 且为 m3u8/HLS 格式 —— 4K 视频会被砍到 1080p。仅当装不了 provider 时用。

```bash
yt-dlp --extractor-args "youtube:player_client=web_safari" -F "<URL>"    # 实测能拿 1080p 阶梯
```

### 与版本的关系

PO Token 不替代 yt-dlp 版本。stable 版落后两周以上仍会报 `age-restricted` / `The page needs to be reloaded`（反爬变更，非 cookies 问题），YouTube 场景用 nightly：`pip install -U --pre "yt-dlp[default]"`。

PO Token 也不绕过 IP 段风控。生成 token 后仍报 "Sign in to confirm you're not a bot"（常见于机房 IP），需额外传 cookies。

---

## 二、YouTube 专用处理

🔴 **CHECKPOINT**：先确认 PO Token provider 就绪（见本文件第一节）。没就绪时 `-F` 只会给出 360p/720p，会把 4K 视频误判成"最高画质就这些"。

1. **解析前确认 yt-dlp 版本够新**：stable 版对当前 YouTube 常直接报 `Sorry, this content is age-restricted` 或 `The page needs to be reloaded`（这类是反爬，不是 cookies 问题）。`yt-dlp --version` 落后两周以上就升 nightly：`pip install -U --pre "yt-dlp[default]"`
2. 公开视频无需 cookies；age-restricted / 已购内容需读 `<cookies_dir>/youtube.txt`
3. `yt-dlp -F "<URL>"` 列格式；>1080p 选项按清晰度策略询问
4. 下载（取每个视频的可用最高画质）：
   ```bash
   yt-dlp --cookies <cookies_dir>/youtube.txt -f "bv*+ba/b" --concurrent-fragments 4 \
     -P "<DOWNLOAD_DIR>" -o "%(title)s.%(ext)s" "<URL>"
   ```
   `-f "bv*+ba/b"` 自动取该视频最高档（4K 视频给 2160p，720p 视频给 720p），无需逐个查 `-S res:X`
5. 403 时加 `--impersonate chrome --cookies <cookies_dir>/youtube.txt`（实测能解决）
6. 下载产出多为 AV1 `.webm`，按第三节做后处理

---

## 三、AV1/WebM 下载后处理

🔴 **CHECKPOINT · 🛑 STOP：每次下载视频完成后必须检查文件格式。**

yt-dlp 在 YouTube 等平台默认优先下载 webm（VP9/AV1 编码），剪辑软件和系统播放器对 webm 容器的支持参差不齐。**下载完成后若输出为 .webm，先尝试无损转封装成 mp4**：

```bash
DOWNLOADED_FILE="<刚下载的文件路径>"
if [[ "$DOWNLOADED_FILE" == *.webm ]]; then
    MP4_FILE="${DOWNLOADED_FILE%.webm}.mp4"
    # -c copy 不重编码：秒级完成、画质无损、体积不变
    ffmpeg -i "$DOWNLOADED_FILE" -map 0 -c copy -movflags +faststart -y "$MP4_FILE" 2>&1
    if [ $? -eq 0 ]; then
        rm -f "$DOWNLOADED_FILE"
        echo "已转封装: $MP4_FILE"
    else
        echo "转封装失败，保留 webm 原文件: $DOWNLOADED_FILE"
    fi
fi
```

**直封 MP4 的兼容性**：AV1/VP9 视频流封进 MP4 后，DaVinci Resolve 18+、Premiere 2024+、VLC、PotPlayer 可正常播放与剪辑。**用户反馈打不开或导入失败时，才走重编码**（见下）。

**重编码（兜底，兼容性最大）**：有 NVIDIA 卡优先 NVENC（约 4x 实时），否则 libx264。

```bash
# NVENC（RTX 20 系及以上；Ampere 起支持 AV1 硬解，30 系起支持 NVENC H.264 硬编）
ffmpeg -hwaccel cuda -i "$DOWNLOADED_FILE" -c:v h264_nvenc -preset p7 -cq 19 -b:v 0 -c:a aac -b:a 192k "$MP4_FILE" -y
# 无 GPU
ffmpeg -i "$DOWNLOADED_FILE" -c:v libx264 -crf 18 -preset medium -c:a aac -b:a 192k "$MP4_FILE" -y
```

重编码代价：4K 视频体积常涨到原 webm 的 3-5 倍，72 分钟素材 libx264 可能跑数小时，NVENC 约 18 分钟。**参数说明**：`-cq 19`（NVENC）/ `-crf 18`（libx264）为视觉无损档；`-preset p7` 为 NVENC 最慢最高质量档；`-c:a aac -b:a 192k` 为剪辑标准音频。

**时间切片场景**：切片下载的 `.webm` 同样触发转封装，成功后删除 webm。

**已知例外**：若用户明确要求保留 webm（如用于 Web 嵌入），跳过处理。Vimeo JWT 方案直接输出 mp4，无需处理。
