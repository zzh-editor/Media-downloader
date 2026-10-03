---
name: media-downloader
description: >
    基于 yt-dlp、gallery-dl、XHS-Downloader 和 parse-video-py 的跨平台、跨 agent 素材下载技能，
    覆盖 YouTube、Bilibili、Vimeo、ArtStation、小红书、抖音、TheRookies 等数百个站点。
    用户给出视频/图片链接请求下载时必须使用，包括"下载这个视频/把这个下了/帮我下这个/下载链接/保存这个视频/
    下载 B 站/下这个 youtube/ArtStation 下载/把这个项目下了/下个视频/帮我下个东西/下这个小红书/小红书这个笔记/
    下个抖音/抖音去水印/下载 therookies 这个比赛"。技能自动处理清晰度选择（>1080p 询问）、时间切片下载、
    ArtStation 按用户名/项目名组织、TheRookies 比赛按作品批量组织。
    依赖自动更新（每 7 天检查 yt-dlp/gallery-dl，下载失败时即时更新）。
    下载后 webm 自动转 mp4（兼容剪辑软件）。默认 1080p，更高分辨率弹窗询问。
    gallery-dl 用于图片画廊站（ArtStation、Pixiv、DeviantArt），XHS-Downloader 用于小红书，parse-video-py 用于抖音等无水印视频。
    therookies 结果页用 curl 直连，作品页/被 Cloudflare 拦截的页面用 browser-harness 直连用户真实浏览器
    解析（自带登录态，天然过 Cloudflare）；YouTube/Vimeo 视频走 yt-dlp（Vimeo 被 Turnstile 挡住时用 JWT 方案绕开），
    图片与内嵌视频用 curl/浏览器解析。cookies 优先从真实浏览器登录态直取（browser-harness CDP 导出转 Netscape），
    Get cookies.txt LOCALLY 扩展仅作兜底。任何时候用户提供 URL 并涉及下载行为，优先考虑此技能。
---

# media-downloader

基于 [yt-dlp](https://github.com/yt-dlp/yt-dlp) + [gallery-dl](https://github.com/mikf/gallery-dl) + [XHS-Downloader](https://github.com/JoeanAmier/XHS-Downloader) + [parse-video-py](https://github.com/wujunwei928/parse-video-py) 的跨平台、跨 agent 素材下载技能。配置存于 `<SKILL_DIR>/config.json` 跨会话持久化。

**浏览器后端原则**：浏览器解析统一用 **browser-harness**——一个直连**用户真实浏览器**（Dia / Chrome / Edge 等）的 CDP harness，自带登录态、天然过 Cloudflare（headless 浏览器过不了的痛点）。（macOS Safari MCP、Playwright MCP 均已弃用。）

## First Run Setup

🔴 **CHECKPOINT**：会话首次下载前确认下载目录、cookies 目录、浏览器后端。先读 `<SKILL_DIR>/config.json`：
- 存在且字段完整 → 直接用 `download_dir` / `cookies_dir`，跳过设置
- 否则用 `question` 逐一设置，写入 config.json

```
请设置素材下载目录（所有下载的素材将保存到这里）：
```

写入 `download_dir`。用户可通过 `-P` / `--paths` 临时覆盖。

```
cookies 由浏览器登录态直取（或 Get cookies.txt LOCALLY 扩展导出兜底），保存到哪个目录？
□ <SKILL_DIR>/cookies（推荐，随技能持久保存）
□ 自定义路径
```

写入 `cookies_dir`。

### browser-harness 检查（浏览器后端）

🔴 **CHECKPOINT**：需要浏览器解析（Cloudflare 拦截页、rookies entry 页、登录态/cookies 提取）时，先确认 browser-harness 可用且能连上用户浏览器：

```bash
command -v browser-harness && browser-harness --version
```

- 未安装 → 引导安装（Python 3.12 + uv）：

```bash
uv tool install --python 3.12 --upgrade --force browser-harness
browser-harness --doctor   # 诊断
```

- 已安装 → 测连接（**Dia 默认 CDP 端点在 127.0.0.1:9222，是纯 WebSocket**，不是标准 HTTP）：

```bash
BU_CDP_WS="ws://127.0.0.1:9222/devtools/browser" browser-harness <<'PY'
print(page_info())
PY
```

能打印 `{url, title, ...}` 即连接成功。否则按「浏览器连接引导」处理。

#### 浏览器连接引导（按优先级）

1. **已有 CDP 端点**（Dia 9222 默认 / 用户提供 / `--remote-debugging-port` 起的 Chrome）→ 直接用 `BU_CDP_WS`（WS 端点）或 `BU_CDP_URL`（HTTP 端点），可写入 `config.json` 的 `cdp_url` 跨会话复用
2. **Chrome 在跑但没开远程调试** → 引导用户手动开启一次：
   - 在 Chrome 打开 `chrome://inspect/#remote-debugging`
   - 勾选 "Allow remote debugging for this browser instance"
   - 首次连接时弹 "Allow remote debugging?" 弹窗点 Allow（Chrome 144+ 每次新连接都会弹，daemon 持单连接故只点一次）
3. **Chrome 没在跑** → browser-harness 会自动拉起 Chrome 并重试（用户只需点 Allow 弹窗）

> 实测：Dia 的 9222 是纯 WS 端点，HTTP `/json/version` 返回 404，必须用 `BU_CDP_WS=ws://127.0.0.1:9222/devtools/browser`。browser-harness 连上 Dia 后 `page_info()` 拿到实时页面，打开 therookies entry 页**无 Cloudflare 拦截**，`js()` 直接跑解析脚本返回完整数据。

### config.json 格式

```json
{
  "download_dir": "~/Downloads",
  "cookies_dir": "~/.config/opencode/skills/media-downloader/cookies",
  "cdp_url": "ws://127.0.0.1:9222/devtools/browser",
  "update_interval_days": 7,
  "last_update_check": "2026-08-02"
}
```

- `download_dir`：素材下载目录
- `cookies_dir`：用户 cookies 文件目录（见 Cookies 引导）
- `cdp_url`：browser-harness 连接的 CDP 端点（WS 或 HTTP；Dia 默认 `ws://127.0.0.1:9222/devtools/browser`，Chrome `--remote-debugging-port` 起的用 `http://127.0.0.1:9222`）
- `update_interval_days`：工具自动更新检查间隔天数，默认 7（见 工具自动更新）
- `last_update_check`：上次更新检查日期（ISO 格式，技能自动维护）

## 下载目录统一管理

所有平台的下载文件统一保存到 `config.json` 的 `download_dir`。工具路由：
- `yt-dlp` / `gallery-dl` → 用 `-P` / `-d` 直接指定 download_dir
- `XHS-Downloader` → 启动时 `--work_path` 指向 download_dir（小红书章节）
- `parse-video-py` → 下载时 `-o`/`-P` 指定 download_dir（抖音章节）

用户请求里指定 `--output <path>` / `-P <path>` / `--paths <path>` 时临时覆盖 download_dir，否则用 config 值。

## 依赖检查

首次运行或命令失败时检查工具可用性（或运行 `scripts/check_env.sh` 一键检查）：

```bash
command -v yt-dlp gallery-dl ffmpeg
# Windows (PowerShell): Get-Command yt-dlp, gallery-dl, ffmpeg -ErrorAction SilentlyContinue
```

缺失时按平台安装：

**macOS：**
```bash
brew install yt-dlp gallery-dl ffmpeg
```

**Windows（任选）：**
```powershell
winget install yt-dlp.yt-dlp Gyan.FFmpeg   # 或 scoop install yt-dlp gallery-dl ffmpeg；或 pip install yt-dlp gallery-dl
```

**Linux：**
```bash
sudo apt install yt-dlp ffmpeg && pipx install gallery-dl   # 或按发行版包管理器
```

### 工具自动更新

yt-dlp/gallery-dl 需频繁更新以对抗反爬。**每次下载会话开始时必须检查**，不跳过：

#### 执行逻辑（每次下载前强制运行）

1. 读 `config.json` 的 `last_update_check` 和 `update_interval_days`（默认 7）
2. 计算距今天数：`delta = today - last_update_check`
3. **delta >= update_interval_days → 执行更新**：

   **macOS：**
   ```bash
   brew upgrade yt-dlp gallery-dl 2>/dev/null || true
   pip3 install -U --break-system-packages yt-dlp 2>/dev/null || true
   cd /tmp/xhs-downloader && git pull && pip install -r requirements.txt 2>/dev/null || true
   cd /tmp/parse-video-py && git pull && pip install -r requirements.txt 2>/dev/null || true
   ```

   **Windows（PowerShell）：**
   ```powershell
   winget upgrade yt-dlp.yt-dlp Gyan.FFmpeg 2>$null
   pip install -U yt-dlp gallery-dl 2>$null
   cd C:\tmp\xhs-downloader; git pull; pip install -r requirements.txt 2>$null
   cd C:\tmp\parse-video-py; git pull; pip install -r requirements.txt 2>$null
   ```

   **Linux：**
   ```bash
   sudo apt update && sudo apt install -y yt-dlp 2>/dev/null || pip3 install -U --break-system-packages yt-dlp 2>/dev/null || true
   pip3 install -U --break-system-packages gallery-dl 2>/dev/null || true
   cd /tmp/xhs-downloader && git pull && pip install -r requirements.txt 2>/dev/null || true
   cd /tmp/parse-video-py && git pull && pip install -r requirements.txt 2>/dev/null || true
   ```

   更新后写回 `last_update_check` 为今天日期（ISO 格式）
4. **delta < update_interval_days → 跳过**（零开销）

> YouTube 场景更新 yt-dlp 时用 nightly 而非 stable：`pip install -U --pre "yt-dlp[default]"`。stable 版落后两周以上就常出现 `age-restricted` / `The page needs to be reloaded`（反爬变更，非 cookies 问题）。
>
> 升级 `bgutil-ytdlp-pot-provider` 插件后，provider 源码必须同步换到相同版本号的 tag 并重编译（`cd ~/bgutil-ytdlp-pot-provider && git fetch --tags && git checkout <版本号> && cd server && npm ci && npx tsc`），版本不一致会出现 token 生成失败。

#### 下载失败触发更新

以下错误出现时**无视间隔立即更新**对应工具，更新后重试下载（最多 1 次）：
- yt-dlp 报 "Please update" / "版本过旧" / HTTP 403（非登录问题）/ 412
- gallery-dl 报版本相关错误
- 任何 extractor 返回 "unsupported" / "not implemented"

更新失败则静默降级，用现有版本继续，不阻断下载。

### XHS-Downloader（小红书必需）

[GitHub](https://github.com/JoeanAmier/XHS-Downloader) 小红书图文/视频无水印下载。

```bash
git clone https://github.com/JoeanAmier/XHS-Downloader.git /tmp/xhs-downloader
pip install -r /tmp/xhs-downloader/requirements.txt
python /tmp/xhs-downloader/main.py --help 2>&1 | grep -q "usage" && echo "OK"   # 验证
# 已安装则更新：cd /tmp/xhs-downloader && git pull && pip install -r requirements.txt
```

### parse-video-py（抖音无水印必需）

[GitHub](https://github.com/wujunwei928/parse-video-py) 多平台无水印视频解析（抖音/小红书/快手/微博/B 站等 20+）。

```bash
git clone https://github.com/wujunwei928/parse-video-py.git /tmp/parse-video-py
cd /tmp/parse-video-py && pip install -r requirements.txt
python -c "import httpx, fastapi" && echo "OK"   # 验证
# 已安装则更新：cd /tmp/parse-video-py && git pull && pip install -r requirements.txt
```

### curl_cffi（Bilibili 必需）

`--impersonate chrome` 依赖 [curl_cffi](https://github.com/yifeikong/curl_cffi)，Homebrew/winget/scoop 装的 yt-dlp 不含它：

```bash
pip3 install --break-system-packages curl_cffi          # macOS；Windows 用 pip install curl_cffi
yt-dlp --list-impersonate-targets 2>&1 | grep -q chrome && echo "OK"   # 验证
```

### PO Token provider（YouTube 高清必需）

🔴 **CHECKPOINT**：缺 PO Token 时 `-F` 只会剩 360p 和 18 号 mp4，看起来像"视频最高只有 360p"。

安装、验证、Windows 15 秒超时的预热办法、HTTP server 模式、兜底 client：见 `references/youtube.md` 第一节。

## Cookies 获取引导

🔴 **CHECKPOINT**：cookies **优先从真实浏览器登录态直取**（browser-harness 连用户已登录的 Dia/Chrome），拿不到才用扩展导出，统一持久化为 cookies 文件复用。

**优先级**：
1. browser-harness 连用户真实浏览器 → `cdp("Network.getAllCookies")` 导出全部 cookie（含 HttpOnly/Secure），转 Netscape 写 `<cookies_dir>/<平台>.txt`
2. 目标平台未登录 → 引导用户在浏览器登录（或提示用 Get cookies.txt LOCALLY 扩展导出），存 `<cookies_dir>/<平台>.txt`
3. 留档复用；只在下载失效或高画质被锁定时提示更新

**文件约定**：每平台一文件，按 URL 域名匹配（`youtube.txt`/`bilibili.txt`/`vimeo.txt`/`artstation.txt`…），首行须为 `# Netscape HTTP Cookie File`。

**从真实浏览器提取（browser-harness）**：
1. 确保 browser-harness 已连上用户浏览器（见「browser-harness 检查」），确认目标平台已登录
2. 导出全部 cookie 存文件（CDP `Network.getAllCookies`，含 HttpOnly/Secure）：
   ```python
   import json
   cookies = cdp("Network.getAllCookies")
   json.dump(cookies["cookies"], open("/tmp/cookies.json", "w"))
   ```
3. 转 Netscape（按域过滤）：`python3 scripts/storage_state_to_netscape.py /tmp/cookies.json -o <cookies_dir>/<平台>.txt --domain <域名>`
4. 验证首行为 `# Netscape HTTP Cookie File`

> 转换脚本 `<SKILL_DIR>/scripts/storage_state_to_netscape.py` 同时接受 Playwright storageState 格式（`{"cookies":[...]}`）和 CDP cookie 数组（`[{...}]`）两种输入，自动检测。CDP 的 `expires` 是浮点秒、session cookie 为 -1（yt-dlp 会跳过但无关紧要），`domain` 以 `.` 开头即 domain cookie。实测：Dia 导出 3521 个真实 cookie（含 YouTube/B 站/小红书等已登录态），B 站 `SESSDATA`（HttpOnly）转换后 yt-dlp 正常拿到高画质格式列表。

**导出并上传（降级方案，用户操作）**：浏览器登录 → 装 Get cookies.txt LOCALLY 扩展 → Export → 保存到 `<cookies_dir>/<平台>.txt`，长期保留本地复用。

**技能使用**：下载时按 URL 判断平台 → 找 `<cookies_dir>/<平台>.txt`，存在则 yt-dlp/gallery-dl 加 `--cookies`，否则以公开内容最高画质下载。

**失效处理**：仅当 `-F` 显示高画质被锁定（Bilibili "premium member"、YouTube 年龄限制、Vimeo OAuth 401）或下载报登录/权限错误时，用 `question` 询问：

```
检测到高画质需登录或下载失效，请更新 <平台> 的 cookies。
□ 已更新，重新从浏览器登录态导出覆盖 cookies_dir/<平台>.txt 后重试
□ 跳过，用当前可用画质下载
```

- "已更新" → 优先浏览器重拉登录态覆盖（见上），否则引导重新导出覆盖 → 重试；再失败 → 提示"登录未生效，账号可能缺少该内容的购买权限或访问权限"，低画质下载
- "跳过" → 直接以公开内容最高画质下载

## 执行规范

下载命令优先用 `bash_stream`（流式进度，参数同 `bash`）；无此工具用 `bash` 兜底。

## 下载后处理：webm 容器处理

🔴 **CHECKPOINT · 🛑 STOP：每次下载视频完成后必须检查文件格式。**

`.webm` 默认先无损转封装成 MP4（`-c copy`，秒级、体积不变），老软件打不开才重编码 H.264。命令与参数：见 `references/youtube.md` 第三节。

## 浏览器访问约定

浏览器类操作（爬取、登录引导、验证）统一用 **browser-harness**（直连用户真实浏览器），按优先级降级：

```
1. 能 HTTP 直连抓取（无 JS challenge/登录要求）→ curl 抓 HTML + Python/正则解析，零浏览器依赖
   （如 therookies 结果页 /contests/{id}/results、ArtStation 页面，curl 即可拿完整 HTML）
2. 必须真实浏览器（JS/Cloudflare/登录，如 therookies 的 entry 页 /entries/{id}）→
   browser-harness 直连用户真实浏览器（自带登录态，天然过 Cloudflare）：
   - new_tab(url) / goto_url(url)        导航（首次导航用 new_tab）
   - wait_for_load()                     等页面加载
   - js("...")                           页内跑 JS（Runtime.evaluate，支持 async/await、非法 return 自动包装）
   - cdp("Domain.method", **params)      原始 CDP（Network.getAllCookies 等）
   - page_info()                         当前页 {url,title,viewport}
   - click_at_xy(x,y) / fill_input()     交互（AX 树取坐标，见 SKILL.md 头部）
   - capture_screenshot()                截图核对
- list_tabs() / switch_tab()          多标签页
    - close_tab(target=...)              关闭指定标签页（传 targetId）
    - new_tab(url)                        返回新标签页的 targetId
    调用方式：bash 跑 heredoc
     BU_CDP_WS="ws://127.0.0.1:9222/devtools/browser" browser-harness <<'PY'
     print(page_info())
     PY
   不要默认退回 curl 或让用户手动操作
```

**调用规范**：
- 每次浏览器操作先确认 CDP 端点：`cdp_url` 存于 config.json（Dia 默认 `ws://127.0.0.1:9222/devtools/browser`），作为 `BU_CDP_WS` 环境变量传给 `browser-harness`
- `js(expression)` 直接执行字符串表达式；表达式里有非法顶层 `return` 时自动包函数重试（与 rookies min.js 兼容，见实测）
- 导航后 `wait_for_load()`；SPA 异步渲染用 `wait_for_element(selector)` 等元素出现
- 多行 heredoc 结尾必须是独立的 `PY`（顶格），bash 执行

**标签页清理约定**：使用 browser-harness 批量解析页面时，必须管理临时标签页，避免污染用户浏览器：
1. 解析前 `list_tabs()` 快照现有标签页的 targetId 集合
2. 每次 `new_tab(url)` 记录返回的 targetId
3. 解析完成后对每个记录的 targetId 执行 `close_tab(target=targetId)`，只关闭本次打开的新标签页，不碰用户原有标签

```python
before = {t['targetId'] for t in list_tabs()}
tracked = []
for eid in entries:
    tid = new_tab(f"https://.../entries/{eid}")
    tracked.append(tid)
    # ... 解析逻辑 ...
for tid in tracked:
    close_tab(target=tid)
```

**Cloudflare**：browser-harness 连**用户真实浏览器**，已登录站点**天然过 CF**（实测 therookies entry 页无 "Just a moment…"）。仅当目标站需登录但浏览器未登录时，引导用户先登录再操作。

> **注意**：browser-harness 用你的真实浏览器 = 你的真实登录态 + 你的 IP。下载素材时的敏感操作（如登录墙、付款、下载有版权的私有内容）会真实发生在你浏览器里，涉及此场景先和用户确认。

### 标题标准化函数（所有平台通用）

下载的**文件夹/文件名必须与网页标题一致，禁止把空格替换成 `-`**。统一用 `sanitize_title`：

```python
def sanitize_title(t):
    t = re.sub(r'[\\/:*?"<>|]', '-', t)   # 只替换文件系统非法字符，保留空格
    t = re.sub(r'\s+', ' ', t).strip()
    t = re.sub(r'-{2,}', '-', t).strip('-. ')
    return t
```

命名直接用标题原文，单文件后追加 `_序号`。

## 核心路由逻辑

解析用户输入，按以下优先级处理：

### 1. 时间节点检测

URL 后跟时间范围（空格分隔）则切片下载：`URL 10:30-15:00`（区间）、`URL 1:20:30-1:45:00`（含小时）、`URL 10:30` / `URL 10:30-`（到结尾）、`URL 10:15-inf`（到末尾，负时间戳从结尾算）。**多区间重复传参**：`--download-sections "*10:30-15:00" --download-sections "*16:00-16:30"`。先 `command -v ffmpeg` 检查（依赖 ffmpeg）。切片输出自动加 `[起点-终点]` 后缀（如 `xxx [00-12-30-00-15-45].mp4`），不会覆盖完整版；区间超出时长自动截断到可用部分，不报错。

### 2. 站点路由

从 URL 判断站点 → 对应专用处理（优先看本站点「专用处理」章节，否则通用）：
- `artstation.com/.cn` → gallery-dl
- `bilibili.com`/`b23.tv` → yt-dlp（Bilibili 专用）
- `youtube.com`/`youtu.be`/`m.youtube.com` → yt-dlp
- `vimeo.com` → yt-dlp（Vimeo 专用，被 Turnstile 挡时用 JWT 方案）
- `xiaohongshu.com`/`xhslink.com`/`rednote.com` → XHS-Downloader
- `douyin.com`/`v.douyin.com` → parse-video-py
- `therookies.co/contests`/`therookies.co/entries` → TheRookies 专用流程
- 其他 → yt-dlp 通用下载

## ArtStation 专用处理

URL 示例：`https://www.artstation.com/artwork/Ov6Zwb`

```bash
gallery-dl -d "<DOWNLOAD_DIR>" -f "{title}_{num:02d}.{extension}" "<URL>"
```

- gallery-dl 用 `{field}` 格式（Python str.format 风格），不是 `%(field)s`；嵌套字段用 `{dict[key]}`
- 默认目录结构 `{category}/{user[username]}/`：`{download_dir}/artstation/{username}/{title}_01.ext`
- 文件名不符预期时：`gallery-dl -K "<URL>"` 列出可用字段，`gallery-dl --print '{user[username]}' --print '{title}' "<URL>"` 查具体值
- 不要 `artstation/` 前缀：`gallery-dl -d "<DOWNLOAD_DIR>" -o "directory={user[username]}" -f "{title}_{num:02d}.{extension}" "<URL>"`

## Bilibili 专用处理

1. **获取 cookies**：读 `<cookies_dir>/bilibili.txt`（见 Cookies 引导）；无该文件或未登录大会员则按失效处理
2. **列出格式**：`yt-dlp --impersonate chrome "$URL" -F`，检查高画质是否锁定
3. **下载**：

```bash
yt-dlp --impersonate chrome \
  --add-header "Origin:https://www.bilibili.com" \
  --add-header "Referer:https://www.bilibili.com" \
  -P "<DOWNLOAD_DIR>" -o "%(title)s.%(ext)s" -S "res:1080" "<URL>"
```

AV1 格式（ID 100xxx）可能连接超时，换 AVC/h264（300xx）或降分辨率。

## YouTube 专用处理

🔴 **CHECKPOINT**：先确认 PO Token provider 就绪（见 `references/youtube.md` 第一节）。没就绪时 `-F` 只会给出 360p/720p，会把 4K 视频误判成"最高画质就这些"。

yt-dlp 版本要求、cookies 判定、下载命令（`-f "bv*+ba/b"` 自动取最高档）、403 处理、AV1 `.webm` 后处理：见 `references/youtube.md` 第二、三节。

## Vimeo 专用处理

🔴 **CHECKPOINT**：Vimeo 网页版被 Cloudflare Turnstile 人机验证挡住 player.vimeo.com，**yt-dlp/curl 直接访问全被 401/403**（`Unable to download webpage: HTTP Error 401`），`--impersonate chrome --cookies` 无效（Turnstile 是 CF 层，非登录问题）。**不要无限重试 yt-dlp**，检测到 401/403 直接转 JWT 方案。

**方案一：JWT 方案（被 Turnstile 挡时主用，泛平台）**
登录用户的 Vimeo 视频页内嵌 `__NEXT_DATA__` 里有 `viewerBootstrap.jwt`（网页登录 token，约 1 小时有效）。用它对 `api.vimeo.com`（不走 Turnstile）拿签名文件 URL 下载：

```bash
# 1. 浏览器打开视频页提取 JWT（browser-harness 直连用户真实浏览器，自带登录态）：
#    BU_CDP_WS="ws://127.0.0.1:9222/devtools/browser" browser-harness <<'PY'
#    new_tab("https://vimeo.com/<id>")
#    wait_for_load()
#    jwt = js("JSON.parse(document.getElementById('__NEXT_DATA__').textContent).props.pageProps.viewerBootstrap.jwt")
#    print(jwt)
#    PY
#    # 或把页面 HTML 存文件用脚本提取：--html

# 2. 下载（选 ≤1080p；>1080p 按清晰度策略询问后改 --height）：
python3 scripts/vimeo_jwt_dl.py --video <ID> --jwt "$JWT" -o "<输出.mp4>"
python3 scripts/vimeo_jwt_dl.py --video <ID> --jwt "$JWT" --list   # 列清晰度
```

- `scripts/vimeo_jwt_dl.py` 支持 `--jwt <token>` 或 `--html <页面HTML文件>` 自动提取
- 实测：`Authorization: jwt <JWT>` 调 `api.vimeo.com/videos/{id}?fields=name,uri,privacy,files` 返回签名文件 URL（uhd/hd/sd 多档），curl 直接下载成功（1080p 40MB）
- JWT 过期（约 1h）重新提取即可
- **公开视频也可先试 yt-dlp**（部分视频 yt-dlp 能直接过，见方案二）；被 Turnstile 挡才转 JWT

**方案二：yt-dlp（公开视频快速通道，未被 Turnstile 挡时）**

```bash
yt-dlp --cookies <cookies_dir>/vimeo.txt --impersonate chrome --extractor-args "vimeo:client=web" -F "<URL>"   # 列格式
yt-dlp --cookies <cookies_dir>/vimeo.txt --impersonate chrome --extractor-args "vimeo:client=web" -P "<DOWNLOAD_DIR>" -o "%(title)s.%(ext)s" -S "res:1080" "<URL>"
```

密码锁定的 Vimeo（oEmbed `title: null`）跳过，除非页面给了密码用 `--video-password "<密码>"`。

## TheRookies 专用处理

URL 示例：`https://www.therookies.co/contests/549/results`

Rookie Awards 竞赛站。一个 **results 页面收录一场比赛的全部入围作品**，每个作品页（`/entries/{id}`）内可能嵌入：① YouTube/Vimeo iframe；② 原生 `<video>` 直链（S3 `rookies-production.s3-accelerate.amazonaws.com` mp4）；③ 指向其他 `/entries/{id}` 的超链接（如 "Click here to see the full movie post"，跳转后才是完整影片）；④ 只有图片（CloudFront）。

**流程分两层：先爬取清单，再按清单逐个下载**。爬取以视频为主、始终提取图片（用于 DIFF 表格一目了然）；**下载时视频优先——有视频的作品只下视频不下图，仅纯图片作品才下图片**。

**完整工作流**：
1. curl 直连 results 页拿完整 SSR HTML（无 JS challenge）→ Python/正则解析比赛名 + 全部 entry 链接
2. 快照当前浏览器标签页列表（`list_tabs()`）；逐作品用 browser-harness 打开 entry 页 `js()` 解析：YouTube/Vimeo iframe、原生 video 直链、关联影片 entry 的视频、全部 CloudFront 图片；追踪每个 `new_tab()` 返回的 targetId
3. 关闭所有追踪的临时标签页（`close_tab(target=targetId)`），不碰用户原有标签
4. 对每个 entry 的视频批量 fetch oEmbed 标题，`classify()` 分类为 main/breakdown/locked/other
5. 整理 DIFF 表格（四列分类 + 图片列）在对话呈现，交用户挑
6. 按选择逐作品建目录并下载

**页面访问分层**（见「浏览器访问约定」）：results 页 → curl 直连；entry 页 → browser-harness 直连用户真实浏览器（实测 Dia 无 Cloudflare 拦截）。

> 实测：`/contests/{id}/results` 用 curl 直连返回完整 SSR HTML（含全部作品）；`/entries/{id}` 有 Cloudflare challenge，但 browser-harness 连用户真实浏览器（Dia 9222）**直接放行**（无 "Just a moment…"）。标题实证（entry 48448）：`og:title` = `The Rookies - 3D Character Art | 2026 | Milla Khimich, by mimsculpt`，页面 `h1` = `3D Character Art | 2026 | Milla Khimich`。**作品标题本身就含作者/年份**，parseEntry 剥 `The Rookies - ` 前缀和 `, by 用户名` 后 = 页面 h1，无需再剥作者（属标题本体）。browser-harness 的 `js()` 跑 `references/therookies-entry.min.js` 直接返回完整解析结果（异步 min.js 与 illegal-return 自动包装兼容）。

### 单项目下载（直接给 entry 链接时）

用户给 `https://www.therookies.co/entries/{id}`（不经 results 页）时，无需比赛名：
1. browser-harness 打开 entry 链接；页内 `js()` 直接取 `document`（无需 fetch）：`parseEntry` 取 `og:title` → 标题/作者，`.project-content` 内全部 `iframe` + 原生 `<video>` → 视频，查指向其他 `/entries/` 的关联影片帖，同时取全部 `img` → 图片（尺寸段换 3840xAUTO）。再 `oEmbedTitle()` 补标题、`classify()` 分 `main`/`breakdown`/`locked`/`other`
2. 对话呈现（成片/衍生分列、有图列图数）交用户确认
3. 建 `{作品标题}` 目录（parseEntry 干净 og:title = 页面 h1），按「步骤 3：下载」——**只下成片，无成片才降级衍生，locked 跳过**；有视频只下视频不下图，纯图作品才下图片；单类型素材直接放主目录，仅用户显式要求连图一起下载才分 `Video/`、`Images/`

### 步骤 1：curl 抓取 results 页并提取比赛名 + entry 链接

```bash
curl -sL -A "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.0 Safari/605.1.15" \
  "https://www.therookies.co/contests/{id}/results" -o /tmp/rk_results.html
```

解析（顶栏标题即比赛名；`id="finalists"` 区块下每个 `.cardProject` 是一个作品）：

```python
import re, html
s = open('/tmp/rk_results.html').read()
tb = re.search(r'<title>(.*?)</title>', s).group(1)        # 比赛名
contest_title = tb.split(' Results | ')[-1].strip()
items = re.findall(   # 每个 .cardProject 的 h3 标题 + entry 链接
  r'<a[^>]*class="[^"]*cardProject[^"]*"[^>]*href="([^"]*entries/(\d+))"[^>]*>.*?<h3[^>]*>(.*?)</h3>', s, re.S)
links = []
for path, eid, title in items:
    t = html.unescape(re.sub(r'<[^>]+>', '', title)).strip()
    t = re.sub(r'\s+', ' ', t)
    links.append({'id': eid, 'title': t, 'url': 'https://www.therookies.co' + path})
```

`.cardProject` 的 `id` 形如 `entry-48448`，`href` 指向 `/entries/{id}`；h3 文本可能含换行，先 normalize 空白。

### 步骤 2：逐作品用浏览器解析每个 entry

对 links 里每个作品，用 browser-harness 导航到 entry 页，页内 `js()` 运行解析脚本（**`oEmbedTitle` / `classify` / `parseEntry` / 包装见 `references/therookies-entry.js`，用 `references/therookies-entry.min.js` 无注释版（browser-harness 的 `js()` 用 Runtime.evaluate，不压换行，但无注释版更稳）**）。**逐个导航、逐个解析，避免一次性返回大数组被截断**；对 `linkedEntries` 里每个 id 再 `js()` 对应 entry 页（复用 parse 包装，仅 `selfId` 换成该 id），把返回的 `videos` 合并进主作品并打 `via` 标记。

**标签页管理**：解析前快照现有标签页，追踪每个 `new_tab()` 返回的 targetId，解析完成后关闭所有追踪的标签页，不碰用户原有标签。

**browser-harness 调用模板**（entry 页解析 + 标签管理）：
```python
before = {t['targetId'] for t in list_tabs()}
tracked = []
results = []

for eid, title in entries:
    tid = new_tab(f"https://www.therookies.co/entries/{eid}")
    tracked.append(tid)
    wait_for_load()
    import time; time.sleep(3)
    expr = open("/path/to/therookies-entry.min.js").read().replace('"48448"', f'"{eid}"')
    r = js(expr)
    if r:
        results.append(r[0])

for tid in tracked:
    close_tab(target=tid)
```

`js()` 支持 async/await（Runtime.evaluate + awaitPromise）与非法顶层 `return` 自动包函数重试，min.js 末尾的 `return (async()=>{...})()` 直接兼容。

### 步骤 2b：oEmbed 补标题 + classify 分类

解析完成后，对每个 entry 的 videos 批量 fetch oEmbed 标题（并行 6 条），`classify(v, r.title)` 分类（`workTitle` = 主作品 parseEntry 干净标题，即页面 h1；合并来的视频也用同一 `r.title`，保证派生词表命中精准）。

**脚本逻辑（与 reference 一致）**：视频来源四种——① `.project-content` 内 `iframe`（YouTube `youtube.com/embed/{id}`、Vimeo `player.vimeo.com/video/{id}`）；② 原生 `<video>`（`currentSrc`/`src` 为 S3 直链 mp4）；③ 指向其他 `/entries/` 的超链接；④ CloudFront 图片。视频为主但图片始终提取。命名取 `og:title` 剥 `The Rookies - ` 前缀与尾部 `, by 用户名`（作者若在标题内则保留，勿再剥）。

**成片分类（contest 561 全 42 作品实测校准）**：
- `main`：标题含成片词（`short film`/`teaser`/`trailer`/`official`/`the movie`/`full movie`/`film`/`movie`/法语 `bande-annonce`/`court-métrage`），或含作品名核心词
- `breakdown`：标题命中衍生词表——making of/mof、breakdown/brkd、behind the scenes/bts、showcase、progression/process、turnaround/turn/turntable、lookdev、reel、rig/rigging、test、shot、character、environment、render、compositing/fx、lighting、blocking、demo、comparison、layout、pipeline、procedural、blendshape、expression、cycle、simulation、frame、storyboard 等（覆盖复数与 `_Turn_`/`TurnTable`/`MOF`/`lookDev` 变体，避免角色/镜头展示误判成片）
- `locked`：Vimeo oEmbed 返回 `title: null` → 需密码，页面没给就跳过
- `other`：兜底

**下载优先级**：每作品**只下载 `main`（成片）**；无 `main` 才降级下载 `breakdown`（衍生）；无 `breakdown` 降级 `other`；`locked` 一律跳过（除非页面给了密码）。有视频不下载图片（图片仅供 DIFF 展示）；纯图作品才下载全部图片。DIFF 表呈现时需完整展示全部四列分类，不可合并或省略。

### 图片最高质量技巧（CloudFront 图片通用）

CloudFront 图片 URL 含尺寸段 `/1400xAUTO/` 等。**把 `/{数字}xAUTO/` 替换为 `/3840xAUTO/` 拿到更高分辨率版本**。实测行为：
- `1400xAUTO`：始终可用（默认展示尺寸）
- `3840xAUTO`：原图分辨率高于 1400 时返回更高分辨率版本；原图不足 1400 时返回 400
- `2000xAUTO` / `4096xAUTO` / `5000xAUTO`：均返回 400

**下载时优先用 3840xAUTO，如果返回 400 则回退到 1400xAUTO**。parseEntry 脚本已自动替换为 3840xAUTO，无需额外处理。

### DIFF 表格格式（对话中呈现）

每作品一行，按 classify 四类分列，图片列标注 CloudFront 图片数：

| # | 作品 | 作者 | 成片(main) | 衍生(breakdown) | 锁定(locked) | 其他(other) | 图片 |
|---|------|------|-----------|----------------|-------------|-------------|------|
| 1 | The Lead that Bled | ... | Vimeo "The Lead that Bled - Short Film" | 衍生 ×6 | — | — | 图片 ×8 |
| 3 | SALAMANDER - Short Film | pumphik | YT "Salamander - Teaser 2025" | — | 密码锁定 ×1 | — | 图片 ×12 |
| 4 | The Character Dossier | Yanina Perez-Masud | — | — | — | S3 原生视频 ×8 | — |
| 5 | Product Design Portfolio | ... | — | — | — | — | 图片 ×53 |

作者列显示**显示名**（非用户名）。**默认只下载"成片(main)"列；无成片才降级下载衍生(breakdown)列；无衍生降级其他(other)；锁定(locked)跳过**。关联影片帖作品在资源列标注 `→ 关联影片帖标题`。有视频不下载图片（图列仅供展示附带图数）；仅用户明确要求时才连图并按 Video/Images 分类。纯图作品下载全部图片。

### 目录结构

主文件夹 = 比赛名，每个作品一个子文件夹（parseEntry 干净 og:title = 页面 h1）。资源文件用作品名命名，多资源追加 `_序号`。单类型素材直接放主目录；仅同一作品既下视频又下图片（用户显式要求）才建 `Video/`、`Images/`：

```
{download_dir}/
└── Rookie of the Year | 3D Animation/
    ├── {作品标题}/                         ← 仅视频：直接放主目录
    │   ├── {作品标题}_01.mp4
    ├── {混合作品标题}/                     ← 视频+图片并存：才分 Video/Images
    │   ├── Video/{混合作品标题}_01.mp4
    │   └── Images/{混合作品标题}_01.jpg
    └── {纯图片作品标题}/                   ← 仅图片：直接放主目录
        └── {纯图片作品标题}_01.jpg
```

目录/文件名统一用 **`sanitize_title`** 清洗（见「浏览器访问约定」）。`{比赛名}` 用结果页标题，`{作品标题}` 用 parseEntry 干净 og:title（剥 `The Rookies - ` 前缀、`by 用户名` 尾部；作者保留为标题本体）。**只替换 `/` `:` `|` 等非法字符为 `-`，保留空格，压缩连续 `-`**——不要学结果页 h3 那样把空格也转 `-`（会出现 `Finn-Bogaert---Environment-Art`）。关联影片帖视频（有 `via` 标记）仍用作品标题命名，序号顺延。

### 步骤 3：下载

🔴 **CHECKPOINT**：按作品下载时**先只下载成片（`main`）**；无成片才降级下载其余视频（`breakdown`/`other`，排除 `locked`）。`locked` 一律跳过，除非作品页正文明确给了密码（则传给 Vimeo/yt-dlp）。

**目标目录规则**：有视频 → 只下视频，直接存 `<作品目录>/` 主目录；纯图片 → 下全部图片存主目录；用户显式要求连图一起下载（仅此情况）→ 视频存 `Video/`、图片存 `Images/`。

**YouTube**（yt-dlp，公开视频无需 cookies；见 YouTube 专用处理）：
```bash
yt-dlp -P "<作品目录>/Video" -o "{作品标题}_01.%(ext)s" -S "res:1080" "<YouTube URL>"
```
多条时序号递增（`_01`、`_02`…）（混合作品 `-P` 指向 `Video`，仅视频作品指向 `<作品目录>`）。

**Vimeo**（优先 JWT 方案，被 Turnstile 挡时主用；未被挡可 yt-dlp；见 Vimeo 专用处理）：
```bash
# 每条 Vimeo 视频先试 yt-dlp（公开可过），401/403 转 JWT：
python3 scripts/vimeo_jwt_dl.py --video <ID> --jwt "$JWT" -o "<作品目录>/Video/{作品标题}_01.mp4"
```
密码锁定的 Vimeo（oEmbed `title: null`）不下载；页面给了密码用 `--video-password "<密码>"` 重试。

**原生 `<video>` 直链（S3 mp4）**（curl 直接下载，S3 直连无需 cookies；mp4/mov 无需转码；保留签名 URL）：
```bash
curl -sL -o "<作品目录>/Video/{作品标题}_01.mp4" "<S3 mp4 URL>"
```

**图片**（仅纯图作品，或用户显式要求混合作品连图时；CloudFront 直连无需 cookies）：
```bash
curl -sL -o "<作品目录>/Images/{作品标题}_01.jpg" "<3840xAUTO URL>"
```
图片较多用循环并行（控制并发如 `xargs -P 4`）；扩展名从 URL 取（.jpg/.png/.gif），序号递增。

## 小红书专用处理

URL 示例：`https://www.xiaohongshu.com/explore/xxx`、`https://xhslink.com/xxx`、`https://www.rednote.com/explore/xxx`

XHS-Downloader 支持图文笔记（图片）和视频笔记的无水印下载。

**依赖检查**：
```bash
ls /tmp/xhs-downloader/main.py >/dev/null 2>&1 || {
  git clone https://github.com/JoeanAmier/XHS-Downloader.git /tmp/xhs-downloader
  pip install -r /tmp/xhs-downloader/requirements.txt
}
```

### 方式 A：API 模式（推荐，可后台常驻）

🔴 **CHECKPOINT**：启动前先确认依赖就绪，再清理端口冲突。

```bash
test -f /tmp/xhs-downloader/main.py || { echo "ERROR: 先安装 XHS-Downloader"; exit 1; }
test -f <SKILL_DIR>/config.json || { echo "ERROR: 先完成 First Run Setup"; exit 1; }
kill $(lsof -t -i:5556) 2>/dev/null   # 清理端口占用
DOWNLOAD_DIR=$(python3 -c "import json; print(json.load(open('<SKILL_DIR>/config.json'))['download_dir'])")
python /tmp/xhs-downloader/main.py api --port 5556 --work_path "$DOWNLOAD_DIR" &   # --work_path→保存到 {download_dir}/Download/
for i in $(seq 1 10); do sleep 1; curl -s -o /dev/null -w "%{http_code}" http://127.0.0.1:5556/docs 2>/dev/null | grep -q 200 && echo "API Ready" && break; done
```

调用 API 下载（响应含标题、作者、标签和下载状态；`download:false` 仅取无水印地址不下）：
```bash
curl -s -X POST http://127.0.0.1:5556/xhs/detail -H "Content-Type: application/json" \
  -d '{"url": "<小红书链接>", "download": true}' | python3 -m json.tool
```

### 方式 B：CLI 模式（单次下载，自动使用统一下载目录）

```bash
DOWNLOAD_DIR=$(python3 -c "import json; print(json.load(open('<SKILL_DIR>/config.json'))['download_dir'])")
python /tmp/xhs-downloader/main.py --work_path "$DOWNLOAD_DIR" "<小红书链接>"
```

自动识别图文/视频，文件保存到 `{download_dir}/Download/`。

### 文件结构

下载路径 = `download_dir` + `folder_name`（默认 `Download`）：
```
{download_dir}/Download/{作品标题}_001.{ext} ...
```
- 开 `folder_mode` → `Download/{作品标题}/001.{ext}`
- 开 `author_archive` → `Download/{作者ID}_{作者昵称}/{作品标题}_001.{ext}`

### 仅下载指定图片

POST body 追加 `index` 数组字段：`{"url":"...","download":true,"index":[1,3,5]}`。

### Cookie 配置（可选，保证高画质）

2.2+ 版无需 Cookie 也可用，配 Cookie 更高画质。用 browser-harness 从真实浏览器直取 `web_session`（或用「cookies 直取」流程生成的 `<cookies_dir>/xiaohongshu.txt`），F12→网络→过滤 `web_session` 复制完整 Cookie 亦可，写入 `/tmp/xhs-downloader/settings.json` 的 `cookie` 字段，或 API 调用传 `cookie` 参数：
```json
{"url":"...","download":true,"cookie":"web_session=xxx; a1=xxx; ..."}
```

### 配置说明（改 `/tmp/xhs-downloader/settings.json`）

| 参数 | 含义 | 默认值 |
|------|------|--------|
| `image_format` | 图文格式 AUTO/PNG/WEBP/JPEG/HEIC | `WEBP` |
| `image_download` / `video_download` | 图文/视频下载开关 | `true` |
| `folder_mode` | 每作品独立文件夹 | `false` |
| `author_archive` | 按作者归档 | `false` |
| `download_record` | 防重复下载 | `true` |
| `name_format` | 命名模板 | `发布时间 作者昵称 作品标题` |

### 已知问题

- 旧链接可能被风控，要求最新分享链接（App 内点分享复制）
- 无水印视频下载后需处理文件，勿多次点击
- Releases 二进制首次运行需 `xattr -cr /path/to/main`（仅 Mac）

## 抖音无水印专用处理

URL 示例：`https://www.douyin.com/video/xxx`、`https://v.douyin.com/xxx/`

抖音视频用 yt-dlp 下载会带水印，本技能用 parse-video-py 拿无水印直链。

**依赖检查**：
```bash
ls /tmp/parse-video-py/main.py >/dev/null 2>&1 || {
  git clone https://github.com/wujunwei928/parse-video-py.git /tmp/parse-video-py
  cd /tmp/parse-video-py && pip install -r requirements.txt
}
```

### 解析流程

#### 步骤 1：启动解析服务

🔴 **CHECKPOINT**：先检查依赖是否存在，再清理端口冲突。

```bash
test -f /tmp/parse-video-py/main.py || { echo "ERROR: 先安装 parse-video-py"; exit 1; }
test -f <SKILL_DIR>/config.json || { echo "ERROR: 先完成 First Run Setup"; exit 1; }
kill $(lsof -t -i:8000) 2>/dev/null   # 清理端口
cd /tmp/parse-video-py && python main.py &
for i in $(seq 1 10); do sleep 1; STATUS=$(curl -s -o /dev/null -w "%{http_code}" http://127.0.0.1:8000/ 2>/dev/null); [ -n "$STATUS" ] && [ "$STATUS" -ge 200 ] && [ "$STATUS" -lt 500 ] && echo "Service Ready (HTTP $STATUS)" && break; done
```

#### 步骤 2：获取无水印视频直链

```bash
RESULT=$(curl -s --get --data-urlencode "url=<抖音分享链接>" \
  "http://127.0.0.1:8000/video/share/url/parse")
VIDEO_URL=$(echo "$RESULT" | python3 -c "import sys,json; print(json.load(sys.stdin)['data']['video_url'])")
TITLE=$(echo "$RESULT" | python3 -c "import sys,json; print(json.load(sys.stdin)['data']['title'])")
AUTHOR=$(echo "$RESULT" | python3 -c "import sys,json; print(json.load(sys.stdin)['data']['author']['nickname'])")
```

#### 步骤 3：下载无水印视频（保存到统一下载目录）

```bash
DOWNLOAD_DIR=$(python3 -c "import json; print(json.load(open('<SKILL_DIR>/config.json'))['download_dir'])")
TITLE=$(echo "$TITLE" | python3 -c "import sys,re;t=sys.stdin.read().strip();t=re.sub(r'[\\\\/:*?\"<>|]','-',t);t=re.sub(r'\\s+',' ',t).strip();print(re.sub(r'-{2,}','-',t).strip('-. ')[:50])")  # sanitize_title（同「浏览器访问约定」）
curl -L -o "${DOWNLOAD_DIR}/${TITLE}.mp4" "$VIDEO_URL"                            # 或
yt-dlp -P "$DOWNLOAD_DIR" -o "%(title)s.%(ext)s" "$VIDEO_URL"                     # yt-dlp 支持断点续传
```

### 图集（图文）处理

抖音图文笔记返回的 `image_list` 含全部图片地址（`live_photo_url` 字段表示含实况照片视频原件）：

```bash
RESULT=$(curl -s "http://127.0.0.1:8000/video/share/url/parse?url=<抖音图文链接>")
echo "$RESULT" | python3 -c "
import sys, json
data = json.load(sys.stdin)['data']
for i, img in enumerate(data.get('image_list', [])):
    print(f'{i+1}: {img.get(\"url\", \"\") if isinstance(img, dict) else img}')
"
```

### 其他平台（小红书、快手等）

parse-video-py 同样支持小红书、快手、微博、B 站：`curl -s "http://127.0.0.1:8000/video/share/url/parse?url=<链接>"`，从返回 JSON 提取对应字段即可。

### 注意

- **必须用 App 分享链接**（网页版未充分测试）；过快重复解析可能触发 IP 限频
- 建议服务持久化运行；解析失败重启：`kill $(lsof -t -i:8000); cd /tmp/parse-video-py && python main.py &`
- 进阶：`cd /tmp/parse-video-py && python main.py --mcp` 走 MCP 模式集成

## 清晰度选择策略

🔴 **CHECKPOINT · 🛑 STOP：每次下载视频前必须执行此检查，不可跳过。**

1. `yt-dlp -F "<URL>"` 提取所有视频格式的**高度值**（resolution/height 列）
2. 筛选 >= 1080p 的选项，去重升序
3. **决策**：
   - 最大高度 <= 1080 → 自动 `-S "res:1080"`，无需询问
   - **最大高度 > 1080 → 必须用 `question` 弹窗询问用户**，列出 >= 1080p 的所有选项（如 1080p / 1440p / 2160p），让用户选择
4. 选 1080p → `res:1080`；1440p → `res:1440`；4K/2160p → `res:2160`；8K/4320p → `res:4320`；具体值 → `res:<HEIGHT>`

`-S "res:X"` 含义：限制分辨率不超过 X，优先接近 X 的最佳格式。

**反模式**：不得在有 >1080p 选项时默认下载 1080p 而不询问用户。用户明确指定分辨率时可跳过询问。

## 通用参数参考

### yt-dlp
| 参数 | 用途 |
|------|------|
| `-P <dir>` / `--paths <dir>` | 下载目录 |
| `-o "<template>"` / `-S "res:1080"` | 输出文件名 / 限制并排序分辨率 |
| `-f "bv*+ba/b"` / `-F` | 最佳视频+音频 / 列出格式 |
| `--cookies <file>` | 使用 `<平台>.txt` cookies |
| `--impersonate chrome` | 浏览器指纹模拟 |
| `--download-sections "*START-END"` | 时间切片（需 ffmpeg） |

### gallery-dl
| 参数 | 用途 |
|------|------|
| `-d <dir>` / `-D <dir>` | 下载目录 / 精确目录（字面路径） |
| `-f "<template>"` | 文件名模板（`{field}` 语法） |
| `-K` / `--list-keywords` | 列出可用元数据字段及示例值 |
| `-o "directory=<template>"` | 目录路径模板 |
| `-s` / `--write-info-json` | 模拟运行 / 保存元数据 JSON |
| `--cookies <file>` | 使用 cookies |

### gallery-dl 模板变量
`{title}`、`{category}`、`{subcategory}`、`{num}`、`{extension}`、`{filename}`、`{count}`、`{user[key]}`（嵌套用 `[]`）

## ⚠️ 反例与黑名单

| 危险动作 | 正确做法 |
|---------|---------|
| 用 yt-dlp 下载 ArtStation | 用 gallery-dl |
| 用 gallery-dl 下载 YouTube/Bilibili | 用 yt-dlp |
| 不查 ffmpeg 就 `--download-sections` | 先 `command -v ffmpeg` |
| 下载 Bilibili 不加 `--impersonate chrome` | 加 `--impersonate chrome` + `--add-header Origin/Referer`（防 412） |
| 混用模板语法 `%(title)s` vs `{title}` | yt-dlp 用 `%(var)s`，gallery-dl 用 `{var}` |
| 用 `--cookies-from-browser`/解密脚本取 cookies | 优先浏览器登录态（browser-harness CDP 直取），否则 Get cookies.txt LOCALLY 导出 |
| 用 yt-dlp 下载小红书 / XHS-Downloader 下视频站 | 小红书用 XHS-Downloader，视频站用 yt-dlp |
| 用 yt-dlp 下载抖音（期望无水印） | 用 parse-video-py 拿无水印直链 |
| 不启动 parse-video-py/XHS 服务就调 API | 先启动服务（见各平台章节） |
| 旧代码不更新 | 每次下载会话开始时检查更新（见工具自动更新） |
| 下载 webm 不处理就交付 | 先检测格式：AV1 webm 用 `-c copy` 直封 MP4（无损秒级）；确需 H.264 才重编码（见下载后处理） |
| YouTube `-F` 只列 360p/18 号 mp4 就直接下载 | 缺 GVS PO Token 会静默跳过 1080p 以上格式，先装 PO Token provider（`references/youtube.md` 第一节）；`player_client=web_safari` 仅兜底（上限 1080p） |
| therookies 用 curl 抓 entry 页 | entry 页必须 browser-harness（真实浏览器过 CF）；results 页可 curl |
| therookies 逐个导航几十作品页并各返回大 JSON | results 页 curl 出全部链接；entry 页逐个解析、每次只返回单作品 |
| therookies 文件夹名把空格转 `-` 或抄 h3 标题 | parseEntry 干净 og:title（= h1）+ `sanitize_title`（保留空格，只替换 `/\:\|`） |
| therookies 纯图下载保留 `1400xAUTO` | 替换 `/3840xAUTO/` 拿原图 |
| Vimeo 无限重试 yt-dlp（被 Turnstile 401/403） | 检测到 401/403 直接转 JWT 方案（api.vimeo.com 拿签名 URL） |
| therookies 只查 iframe、忽略 `<video>` / 正文链接 | 同时 `querySelectorAll(':scope video')` + `a[href*="/entries/"]` |
| therookies 作者取单 by 用户名 | 取头像 `img.avatar-media` alt 作显示名 |
| therookies 下所有视频（含衍生） | `classify()` 分 main/breakdown/locked，只下 `main` 成片 |
| therookies 直接下密码锁定 Vimeo | 判 `locked` 跳过；页面有密码才 `--video-password` |
| therookies 一律建 Video/Images 子目录 | 单类型直接放主目录；仅用户显式要求连图才分 Video/Images |
| therookies 解析后不关闭临时标签页 | 快照 `list_tabs()` + 追踪 `new_tab()` targetId + 逐个 `close_tab(target=...)`，只清理本次打开的标签 |
| browser-harness 连不上浏览器 / `page_info()` 报错 | 确认 CDP 端点（Dia 9222 纯 WS 用 `BU_CDP_WS`）；Chrome 引导开 `chrome://inspect/#remote-debugging` + 勾选 Allow |

## 🔧 失败模式与恢复

| 触发条件 | 一线修复 | 仍失败兜底 |
|---------|---------|-----------|
| `yt-dlp` HTTP 403/412 | 加 `--impersonate chrome` | 加 `--add-header Origin/Referer`，仍失败让用户在浏览器手动访问 |
| YouTube `-F` 只有 360p，视频实有 1080p/4K | 装 PO Token provider（见 `references/youtube.md` 第一节） | 临时 `--extractor-args "youtube:player_client=web_safari"`，上限 1080p HLS |
| YouTube 报 `age-restricted` / `The page needs to be reloaded` | 升 nightly：`pip install -U --pre "yt-dlp[default]"`（反爬问题，非 cookies 问题） | 加 `--cookies` 后仍失败，确认账号对该内容有访问权限 |
| Windows 下 provider 报 `generate_once.js ... timed out after 15.0 seconds` | 手动先跑一次 `node build/generate_once.js --version` 预热（冷启动约 21s，第二次约 2s） | 改用 HTTP server 模式 `node build/main.js`，免每次 spawn |
| `yt-dlp` HTTP 404（Bilibili） | 确认 BV 号，换可用视频测试 | 可能是区域限制，提示确认视频可访问 |
| `command -v ffmpeg` 失败 | `brew install ffmpeg` | 不时间切片，引导下完整视频自行剪辑 |
| `gallery-dl -K` 空/报错 | 确认 URL 是否为项目/画师页格式 | 检查网络，提示浏览器打开确认链接 |
| `<cookies_dir>/<平台>.txt` 不存在 | 跳过 cookies 用公开画质 | 需高画质/登录时引导从真实浏览器登录态直取（browser-harness CDP） |
| 高画质被锁 / cookies 失效 | 提示更新 cookies 重试 | 确认账号有无权限，用公开画质 |
| Bilibili AV1（100xxx）超时 | 换 AVC/h264（300xx） | 降分辨率或换工具 |
| XHS-Downloader 空/报错 | `git pull` 更新 | 检查 Cookie 是否过期并更新 |
| parse-video-py 解析失败 | 用 App 分享链接；重启服务 | 切 yt-dlp 带水印版本 |
| parse-video-py 端口占用 | `kill $(lsof -t -i:8000)` 重启 | 改端口 `--port 8001` |
| 小红书含 `xsec_token` 解析失败 | 用 `xhslink.com` 短链 | 浏览器打开复制最新分享链 |
| therookies curl 提取不到 h3 | normalize 空白；`.cardProject` 容器 + `id="finalists"` 定位 | 页面结构已改则更新选择器 |
| therookies `js()` 返回空 | Cloudflare 未过 → 确认连的是真实浏览器（非 headless），重试或等页面渲染完 | 引导用户浏览器登录后重试 |
| therookies 图片 3840xAUTO 返回 400 | 原图实际分辨率不足 1400，回退到 1400xAUTO | 保留原有 1400xAUTO URL |
| therookies 作者显示为用户名 | 取头像 `.avatar-media` alt | 无头像回退 og:title |
| therookies 解析后浏览器残留大量空标签页 | 快照 `list_tabs()` 追踪 `new_tab()` targetId，结束后 `close_tab(target=...)` 逐条关闭 | 引导用户手动关闭空标签 |
| therookies oEmbed 拉标题失败 | 单条重试；用 iframe 前 H3 标题兜底 | 整批无标题模式（不分类全下载） |
| therookies Vimeo 401/403（Turnstile） | 转 JWT 方案（`scripts/vimeo_jwt_dl.py`） | 告知用户浏览器登录后提取 JWT |
| browser-harness 未安装 | `uv tool install --python 3.12 --upgrade --force browser-harness` + `--doctor` | 检查 uv/网络；用 Get cookies.txt LOCALLY + curl 兜底 |
| browser-harness 连不上 CDP（WS 握手失败） | 确认 Dia/Chrome 开了远程调试（9222）；Dia 用 `BU_CDP_WS`，Chrome 用 `BU_CDP_URL` | 引导用户开 `chrome://inspect/#remote-debugging` 勾选 Allow |
| browser-harness `js()` 语法/返回错 | 表达式须为合法 JS；min.js 用无注释版 | 改用单条简单表达式排查 |
| ffmpeg webm→mp4 转换失败 | 检查 ffmpeg 是否安装（`brew install ffmpeg`）；尝试只转视频流 `-vn` | 保留 webm 原文件，提示用户手动转换 |

## 场景示例

```
用户: "下载这个 https://youtu.be/xxx"
→ 列格式；max=1080p → 自动 1080p
用户: "把这个下了 https://youtu.be/xxx 10:30-15:00"
→ 查 ffmpeg → 时间切片
用户: "ArtStation 这个项目 https://www.artstation.com/artwork/Ov6Zwb"
→ gallery-dl → artstation/用户名/项目名_序号.ext
用户: "下个B站视频 https://www.bilibili.com/video/BV1GJ411x7"
→ 读 cookies_dir/bilibili.txt → 列格式 → 高画质锁定则更新 cookies → >1080p 问清晰度 → 下载
用户: "Vimeo 这个视频 https://vimeo.com/xxx"
→ 先试 yt-dlp；401/403（Turnstile）→ 浏览器取 JWT → vimeo_jwt_dl.py 下载
用户: "帮我下载 https://twitter.com/xxx/status/xxx"
→ yt-dlp 通用下载
用户: "下载这个小红书 https://www.xiaohongshu.com/explore/xxx"
→ 检查/安装 XHS-Downloader → 读 download_dir → 启动 API（--work_path）→ POST /xhs/detail → 存 Download/
用户: "下个抖音视频 https://v.douyin.com/xxx"
→ 检查/安装 parse-video-py → 启动 HTTP 服务 → GET /video/share/url/parse → 提取 video_url → curl/yt-dlp 下载
用户: "下载 https://www.therookies.co/contests/549/results 全部作品"
→ curl results 页解析比赛名 + entry 链接 → 逐作品 browser-harness（真实浏览器）js() 解析 → oEmbed 补标题 + classify → DIFF 表格交用户挑 → 建 {比赛名}/{作品名} 目录（og:title + sanitize_title 命名）→ 只下成片，无成片才降级，locked 跳过 → YouTube 用 yt-dlp、Vimeo 用 yt-dlp/JWT、原生 video 与图片用 curl
用户: "下载 https://www.therookies.co/entries/47874"
→ browser-harness 打开 entry → js() 跑 og:title + .project-content 视频/图片 → oEmbed 分类 → 对话呈现 → 建 {作品标题} 目录 → 只下成片
用户: "AZIMUTH 那个作品 Vimeo 有成片，28 个 YouTube 都是 making-of，只下成片"
→ classify 判 Vimeo 为 main、28 个 YouTube 为 breakdown → 只下那条 Vimeo 成片
```