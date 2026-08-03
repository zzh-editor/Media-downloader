---
name: media-downloader
description: >
   基于 yt-dlp、gallery-dl、XHS-Downloader 和 parse-video-py 的跨平台素材下载技能，
   覆盖 YouTube、Bilibili、Vimeo、ArtStation、小红书、抖音、TheRookies 等数百个站点。
   当用户给出视频/图片链接请求下载时，必须使用此技能——包括但不限于："下载这个视频"、"把这个下了"、
   "帮我下这个"、"下载链接"、"保存这个视频"、"下载 B 站"、"下这个 youtube"、"ArtStation 下载"、
   "把这个项目下了"、"下个视频"、"帮我下个东西"、"下这个小红书"、"小红书这个笔记"、"下个抖音"、
   "抖音去水印"、"下载 therookies 这个比赛"等。技能自动处理清晰度选择（超过1080p询问用户）、
   时间节点切片下载、ArtStation 项目按用户名/项目名组织、TheRookies 比赛按作品批量组织。
   gallery-dl 专门用于图片画廊类网站下载（ArtStation、Pixiv、DeviantArt 等）。
   XHS-Downloader 专门用于小红书图文/视频下载。
   parse-video-py 专门用于抖音等平台无水印视频解析。
   TheRookies（therookies.co）用 BrowserClaw 爬取比赛结果页或单个作品页，按作品下载 YouTube/Vimeo 视频，纯图片作品下载 CloudFront 图片。
   任何时候用户提供 URL 并涉及下载行为，优先考虑此技能。
---

# media-downloader

基于 [yt-dlp](https://github.com/yt-dlp/yt-dlp) + [gallery-dl](https://github.com/mikf/gallery-dl) + [XHS-Downloader](https://github.com/JoeanAmier/XHS-Downloader) + [parse-video-py](https://github.com/wujunwei928/parse-video-py) 的跨平台素材下载技能。

## First Run Setup

🔴 **CHECKPOINT**：在当前会话首次下载前，先确认下载目录和 cookies 目录。

技能使用 `<SKILL_DIR>/config.json` 跨会话持久化用户偏好。

### 读取已有配置

```
尝试读取 <SKILL_DIR>/config.json：

if 文件存在且字段完整:
    直接使用 download_dir 和 cookies_dir
    跳过步骤 1-2
else:
    进入步骤 1-2 询问并写入
```

### 步骤 1：设置下载目录

用 `question` 引导设置：

```
请设置素材下载目录（所有下载的素材将保存到这里）：
```

写入 `config.json` 的 `download_dir` 字段。用户可通过 `-P` 或 `--paths` 参数临时覆盖。

### 步骤 2：设置 cookies 目录

用 `question` 引导设置：

```
cookies 由你上传（用 Get cookies.txt LOCALLY 扩展导出），保存到哪个目录？
□ <SKILL_DIR>/cookies（推荐，随技能持久保存）
□ 自定义路径
```

写入 `config.json` 的 `cookies_dir` 字段。

### config.json 格式

```json
{
  "download_dir": "~/Downloads",
  "cookies_dir": "~/.config/opencode/skills/media-downloader/cookies",
  "update_interval_days": 7,
  "last_update_check": "2026-08-02"
}
```

- `download_dir`：素材下载目录
- `cookies_dir`：用户上传 cookies 文件的目录（见 Cookies 获取引导）
- `update_interval_days`：yt-dlp/gallery-dl 自动更新检查间隔天数，默认 7（见 工具自动更新）
- `last_update_check`：上次更新检查日期（ISO 格式，技能自动维护）
- 更新配置：直接修改此 JSON 文件，或要求技能重新设置

## 下载目录统一管理

所有平台的下载文件统一保存到 `config.json` 的 `download_dir` 字段指定的目录。

工具路由规则：

```
yt-dlp / gallery-dl
  → 用 -P / -d 参数直接指定 download_dir

XHS-Downloader
  → 启动时用 --work_path 指向 download_dir（见小红书专用处理）

parse-video-py
  → curl/yt-dlp 下载时 -o/-P 指定 download_dir（见抖音无水印专用处理）
```

允许用户通过脚本上下文或询问临时覆盖目录：

```
if 用户在请求中指定了 --output <path> 或 -P <path> 或 "--paths <path>":
    临时覆盖 download_dir
else:
    使用 config.json 的 download_dir
```

## 依赖检查

首次运行或命令失败时，检查三个工具的可用性：

```bash
command -v yt-dlp >/dev/null 2>&1 && echo "yt-dlp OK"
command -v gallery-dl >/dev/null 2>&1 && echo "gallery-dl OK"
command -v ffmpeg >/dev/null 2>&1 && echo "ffmpeg OK"
```

也支持使用技能附带的 `scripts/check_env.sh` 脚本一键检查（输出更详细的环境信息）。

缺失时提示用户安装。安装方式按平台：

**macOS：**
```bash
brew install yt-dlp gallery-dl ffmpeg
```

**Windows（任选其一）：**
```powershell
# winget（推荐）
winget install yt-dlp.yt-dlp
winget install Gyan.FFmpeg

# scoop
scoop install yt-dlp gallery-dl ffmpeg

# pip
pip install yt-dlp gallery-dl
```

Windows 依赖检查（PowerShell）：
```powershell
Get-Command yt-dlp, gallery-dl, ffmpeg -ErrorAction SilentlyContinue
```

### 工具自动更新

yt-dlp 需频繁更新以对抗平台反爬，gallery-dl 同理。为避免每次运行都检查更新带来的等待，采用**按天间隔检查**策略：

- `config.json` 记录 `last_update_check`（上次检查日期）与 `update_interval_days`（默认 7 天）
- 每次技能运行时读取 config：
  ```
  if 距 last_update_check 已超过 update_interval_days 天:
      执行一次自动更新并更新 last_update_check
  else:
      跳过（零开销）
  ```
- 自动更新命令（macOS / Windows 通用）：
  ```bash
  yt-dlp -U && gallery-dl --update
  ```
  若 yt-dlp 报"由包管理器管理"（brew 安装），改用：
  ```bash
  brew upgrade yt-dlp gallery-dl    # macOS
  # 或 pip install -U yt-dlp gallery-dl（Windows/pip 安装）
  ```
- 例外：若某次下载报"版本过旧/请更新"错误，无视间隔立即更新。

### XHS-Downloader（小红书必需）

[XHS-Downloader](https://github.com/JoeanAmier/XHS-Downloader) 是小红书图文/视频下载的社区标准工具，支持无水印下载。

**安装方式 A：Git 克隆（推荐，保持最新反爬兼容性）**

```bash
git clone https://github.com/JoeanAmier/XHS-Downloader.git /tmp/xhs-downloader
pip install -r /tmp/xhs-downloader/requirements.txt
```

**安装方式 B：已安装则更新**

```bash
cd /tmp/xhs-downloader && git pull && pip install -r requirements.txt
```

**验证：**

```bash
python /tmp/xhs-downloader/main.py --help 2>&1 | grep -q "usage" && echo "XHS-Downloader OK"
```

### parse-video-py（抖音无水印必需）

[parse-video-py](https://github.com/wujunwei928/parse-video-py) 是多平台无水印视频解析库，支持抖音、小红书、快手、微博、Bilibili 等 20+ 平台。

**安装方式 A：Git 克隆**

```bash
git clone https://github.com/wujunwei928/parse-video-py.git /tmp/parse-video-py
cd /tmp/parse-video-py && pip install -r requirements.txt
```

**安装方式 B：已安装则更新**

```bash
cd /tmp/parse-video-py && git pull && pip install -r requirements.txt
```

**验证：**

```bash
python -c "import httpx, fastapi; print('parse-video-py deps OK')" 2>&1 && echo "OK"
```

### curl_cffi（Bilibili 必需）

yt-dlp 的 `--impersonate chrome` 需要 [curl_cffi](https://github.com/yifeikong/curl_cffi) 库。Homebrew/winget/scoop 安装的 yt-dlp **不包含** curl_cffi，需额外安装：

**macOS：**
```bash
pip3 install --break-system-packages curl_cffi
```

**Windows：**
```powershell
pip install curl_cffi
```

**验证（跨平台）：**
```bash
yt-dlp --list-impersonate-targets 2>&1 | grep -q chrome && echo "OK"
```

## Cookies 获取引导

🔴 **CHECKPOINT**：cookies 不再自动从浏览器提取，由**用户通过 Get cookies.txt LOCALLY 浏览器扩展**导出各平台 cookies 文件，上传并保留在本地。技能只在**下载失效或高画质被锁定**时提示用户更新。

### cookies 文件约定

- 每平台一个文件，放在 `config.json` 的 `cookies_dir` 目录，命名为 `<平台>.txt`
- 支持：`youtube.txt`、`bilibili.txt`、`vimeo.txt`、`artstation.txt` 等（按 URL 域名匹配）
- 文件首行须为 `# Netscape HTTP Cookie File`（Get cookies.txt LOCALLY 导出的标准格式）

### 导出并上传（用户操作）

```
1. 用浏览器登录目标平台
2. 安装 Get cookies.txt LOCALLY 扩展，点击图标 → Export，导出 cookies.txt
3. 将文件保存到 <cookies_dir>/<平台>.txt
```

导出后 cookies 文件长期保留本地复用。

### 技能使用

```
下载时按 URL 判断平台 → 找 <cookies_dir>/<平台>.txt
if 文件存在:
    yt-dlp/gallery-dl 加 --cookies <cookies_dir>/<平台>.txt
else:
    无 cookies，直接以公开内容最高画质下载
```

### 平台 Cookies 失效处理

🔴 **CHECKPOINT**：仅当满足以下任一条件时才提示用户更新 cookies：
1. `-F` 显示高画质格式被锁定（如 Bilibili "you have to become a premium member"、YouTube 年龄限制、Vimeo OAuth 401）
2. 下载报登录/权限错误

用 `question` 询问：

```
检测到高画质需登录或下载失效，请更新 <平台> 的 cookies。
□ 已更新，重新导出并覆盖 cookies_dir/<平台>.txt 后重试
□ 跳过，用当前可用画质下载
```

- 选择"已更新" → 引导用户重新用 Get cookies.txt LOCALLY 导出覆盖该文件 → 重试
- 再次失败 → 提示"登录未生效，账号可能缺少该内容的购买权限或访问权限"，继续用低画质下载
- 选择"跳过" → 直接以公开内容可用的最高画质下载

## 执行规范

所有下载命令优先检查环境是否提供 `bash_stream` 工具（支持流式进度推送，参数同 `bash`）：

```
if agent has tool "bash_stream":
    用 bash_stream 执行下载命令（实时显示进度条）
else:
    用 bash 执行下载命令（完整输出兜底）
```

`bash_stream` 和 `bash` 的命令参数完全一致（command、timeout、workdir），只需切换工具名。

## 浏览器访问约定

所有需要浏览器访问的操作（页面爬取、登录引导、验证内容等）**一律默认调用 BrowserClaw**（用户的代理浏览器，已登录各平台账号）。**不要**退回到 curl 直接抓取或让用户手动操作。

```
if 环境提供 BrowserClaw 工具:
    用 BrowserClaw 打开页面并操作（tabs / navigate / snapshot / act / evaluate）
else:
    提示用户安装 BrowserClaw（macOS 或 Windows 均有对应安装方式），安装后重试
```

## 核心路由逻辑

解析用户输入，按以下优先级处理：

### 1. 时间节点检测

检查 URL 后面是否跟了时间范围（空格分隔）：

| 示例 | 含义 |
|------|------|
| `URL 10:30-15:00` | 下载 10:30 到 15:00 |
| `URL 1:20:30-1:45:00` | 含小时的格式 |
| `URL 10:30` | 从 10:30 下载到结尾 |
| `URL 10:30-` | 同上，从 10:30 到结尾 |

匹配到时间范围后：
- 首先检查 `command -v ffmpeg`（`--download-sections` 依赖 ffmpeg）
- 用 `--download-sections "*START-END"` 参数
- 可以叠加多个区间：`--download-sections "*10:15-15:00" --download-sections "*30:00-35:00"`

### 2. 站点路由

从 URL 判断站点：

```
URL 包含 "artstation.com" 或 "artstation.cn"
  → gallery-dl（见 ArtStation 专用逻辑）

URL 包含 "bilibili.com" 或 "b23.tv"
  → yt-dlp（见 Bilibili 专用逻辑）

URL 包含 "youtube.com"、"youtu.be"、"m.youtube.com"
  → yt-dlp（见 清晰度选择 + cookies）

URL 包含 "vimeo.com"
  → yt-dlp（见 Vimeo 专用逻辑）

URL 包含 "xiaohongshu.com" 或 "xhslink.com" 或 "rednote.com"
  → XHS-Downloader（见 小红书专用逻辑）

URL 包含 "douyin.com" 或 "v.douyin.com"
  → parse-video-py（见 抖音无水印专用逻辑）

URL 包含 "therookies.co/contests" 或 "therookies.co/entries"
  → TheRookies 专用流程（见 TheRookies 专用处理）

其他
  → yt-dlp 通用下载
```

## ArtStation 专用处理

URL 示例：`https://www.artstation.com/artwork/Ov6Zwb`

### 下载命令

```bash
gallery-dl -d "<DOWNLOAD_DIR>" -f "{title}_{num:02d}.{extension}" "<URL>"
```

**格式说明**：gallery-dl 使用 `{field}` 格式（Python str.format 风格），不是 `%(field)s`。
嵌套字段用 `{dict[key]}` 语法。

### 文件结构

默认目录模板为 `{category}/{user[username]}/`，所以下载后结构是：

```
{download_dir}/
└── artstation/
    └── {username}/
        └── {project_title}_01.{ext}
        └── {project_title}_02.{ext}
        └── ...
```

### 调试字段

如果文件名不符合预期，先用以下命令查看可用元数据字段：

```bash
gallery-dl -K "<URL>"      # 列出所有可用字段及示例值
gallery-dl --print '{user[username]}' --print '{title}' "<URL>"  # 查看具体字段值
```

然后用实际字段名调整 `-f` 模板。

### 目录结构自定义

如果不想保留 `artstation/` 类别前缀，可以先查看可用字段后用 `-o "directory={field}"` 自定义：

```bash
# 仅使用用户名作为上级目录
gallery-dl -d "<DOWNLOAD_DIR>" -o "directory={user[username]}" -f "{title}_{num:02d}.{extension}" "<URL>"
```

## Bilibili 专用处理

### 执行步骤

**Step 1：获取 cookies**

读取 `<cookies_dir>/bilibili.txt`（见 Cookies 获取引导）。无该文件或未登录大会员时，按平台 Cookies 失效处理引导用户更新。

**Step 2：列出可用格式**

```bash
yt-dlp --impersonate chrome "$URL" -F
```

从输出检查高画质格式是否锁定。如果大会员内容未登录，按平台 Cookies 失效处理。

**Step 3：下载视频**

```bash
yt-dlp --impersonate chrome \
  --add-header "Origin:https://www.bilibili.com" \
  --add-header "Referer:https://www.bilibili.com" \
  -P "<DOWNLOAD_DIR>" \
  -o "%(title)s.%(ext)s" \
  -S "res:1080" \
  "<URL>"
```

注意 Bilibili 的 AV1 编码格式（format ID 以 100 开头）在某些网络环境下连接超时。如遇超时，换用 AVC/h264 格式（format ID 以 300xx 开头）或指定低分辨率。

## YouTube 专用处理

### 执行步骤

**Step 1：获取 cookies（可选）**

公开视频不需要 cookies。仅年龄限制和已购内容需要：读取 `<cookies_dir>/youtube.txt`（见 Cookies 获取引导）。

**Step 2：列出格式并选择清晰度**

```bash
yt-dlp -F "<URL>"
```

见下方清晰度选择策略——若存在 >1080p 选项，询问用户选择。

**Step 3：下载视频**

```bash
yt-dlp -P "<DOWNLOAD_DIR>" -o "%(title)s.%(ext)s" -S "res:1080" "<URL>"
```

## Vimeo 专用处理

🔴 **CHECKPOINT**：Vimeo 下载必须登录（web 客户端）。未登录时 yt-dlp 报 `Failed to fetch macos OAuth token: HTTP Error 401`（上游 bug #17271）。**检测到未登录时不要降级，用 `question` 要求用户更新 `cookies_dir/vimeo.txt` 后重试**。

**Step 1：获取 cookies**（Vimeo 必需）

读取 `<cookies_dir>/vimeo.txt`（见 Cookies 获取引导）。未登录则按平台 Cookies 失效处理引导用户更新。

**Step 2：列出格式并选择清晰度**

```bash
yt-dlp --cookies <cookies_dir>/vimeo.txt --extractor-args "vimeo:client=web" -F "<URL>"
```

若报 `Failed to fetch macos OAuth token` → 提示用户更新 vimeo cookies 文件。见下方清晰度选择策略。

**Step 3：下载视频**

```bash
yt-dlp --cookies <cookies_dir>/vimeo.txt --extractor-args "vimeo:client=web" -P "<DOWNLOAD_DIR>" -o "%(title)s.%(ext)s" -S "res:1080" "<URL>"
```

## TheRookies 专用处理

URL 示例：`https://www.therookies.co/contests/549/results`

TheRookies 是 Rookie Awards 作品竞赛站，一个 **results 页面收录一场比赛的全部入围作品**，每个作品页（`/entries/{id}`）内可能以以下任一形式嵌入视频：

- iframe 嵌入的 YouTube/Vimeo 视频
- 原生 `<video>` 元素直链（S3 `rookies-production.s3-accelerate.amazonaws.com` mp4）
- 页面内指向其他 `/entries/{id}` 的超链接（如 "Click here to see the full movie post"），跳转后才是完整影片
- 只有图片（CloudFront）

因此下载流程分两层：**先爬取清单，再按清单逐个下载**。爬取时**以视频为主**：有视频（含原生 video、iframe、关联影片帖）优先列视频；真正只有图片的作品才提取图片。

### 完整工作流

```
1. 用 BrowserClaw 打开 results 页面（作为爬取 context）
2. 在页面 evaluate 中提取比赛名 + 全部 entry 链接（见下方脚本）
3. 批量 fetch 每个 entry 的 HTML，解析出每作品的资源清单（YouTube/Vimeo iframe、原生 video 直链、关联影片 entry 的视频，真正无视频的提取图片）
4. 将解析结果整理为 DIFF 表格（见下方表格格式），在对话中呈现，交用户判断下载哪些
5. 按表格选择，逐作品建立目录并下载
```

### 前提

🔴 **CHECKPOINT**：本流程强制使用 BrowserClaw（网站有 JS challenge，curl 直接抓只返回 5.6KB 拦截页；但在浏览器页内 `fetch` 同源页面可拿到完整服务端渲染 HTML）。在 results 页面 evaluate 中批量爬取，无需逐作品导航。

### 单项目下载（直接给 entry 链接时）

用户直接给出 `https://www.therookies.co/entries/{id}`（不经 results 页）时，无需比赛名，直接在该 entry 页执行解析：

1. BrowserClaw 打开该 entry 链接（作为 context）
2. 页内 evaluate 解析当前页面（直接取 `document`，无需 fetch）：用下方 `parseEntry` 逻辑取 `og:title` → 标题/作者，取 `.project-content` 内全部 `iframe` + 原生 `<video>` → 视频清单，检查是否有指向其他 `/entries/` 的关联影片帖链接；仅当这些都无视频时取 `.project-content` 内 `img` → 图片清单（尺寸段替换 3840xAUTO）。最后用 `oEmbedTitle()` 补每条视频真实标题、`classify()` 分类成片（`main`/`breakdown`/`locked`/`other`）
3. 对话中呈现该作品资源（**成片/衍生分列**、纯图列图片数），交用户确认
4. 建目录 `{作品标题} by {作者}/Video`（有视频）或 `/Images`（纯图片），按「步骤 3：下载」下载——**只下载成片，无成片才降级衍生，locked 跳过**

### 步骤 1：提取比赛名 + entry 链接

在 results 页面的 BrowserClaw evaluate 中运行：

```js
const h3s = [...document.querySelectorAll('h3')]
  .map(e => e.innerText.trim().replace(/\s+/g, ' '))
  .find(t => t.startsWith('Finalists '));
const contestTitle = h3s.replace(/^Finalists\s+/, '');  // 例: "Rookie of the Year | 3D Animation"

const links = []; const seen = new Set();
document.querySelectorAll('main a').forEach(a => {
  const h3 = a.querySelector('h3');
  if (h3) {
    const h = a.href;
    if (/therookies\.co\/entries\/\d+/.test(h) && !seen.has(h)) {
      seen.add(h);
      links.push({ title: h3.innerText.trim(), url: h });
    }
  }
});
return { contestTitle, count: links.length, links };
```

注意 h3 文本可能含换行符，必须先 normalize 空白再剥 `Finalists ` 前缀。

### 步骤 2：批量爬取并解析每个 entry

同一页面 evaluate 中运行（页内 fetch 同源、携带 cookies）。`parseEntry` 需接收当前 entry 的 id（用于过滤指向自身页面的关联链接）：

```js
async function rkFetch(url) {
  const r = await fetch(url, { credentials: 'include' });
  return r.ok ? await r.text() : null;
}
// oEmbed 获取视频真实标题（CORS 已验证可行）。YouTube 用 youtube.com/oembed，Vimeo 用 vimeo.com/api/oembed.json。
// Vimeo 密码保护视频 oEmbed 返回 title:null → 判定为"密码锁定"（locked），下载阶段跳过。
async function oEmbedTitle(v) {
  if (v.host !== 'youtube' && v.host !== 'vimeo') return null;   // 原生 S3 直链无 oEmbed
  const o = v.host === 'youtube'
    ? 'https://www.youtube.com/oembed?url=' + encodeURIComponent(v.url) + '&format=json'
    : 'https://vimeo.com/api/oembed.json?url=' + encodeURIComponent(v.url);
  try {
    const r = await fetch(o);
    if (!r.ok) return null;
    const d = await r.json();
    return d.title || null;
  } catch (e) { return null; }
}
// 成片分类：'main' = 作品成片（优先下载）；'breakdown' = making-of/breakdown/showcase 等衍生内容（仅无成片时降级下载）；'locked' = Vimeo 密码锁定（跳过）；'other' = 无法归类（当 secondary）
// 衍生特征词表（contest 561 全 42 作品验证）：须同时覆盖复数、下划线/连字符、驼峰、缩写
// （characters / _Turn_ / TurnTable / MOF=MakingOf / Brkd / lookDev / firstshot_blocking），全部用词边界断言匹配
const BREAKDOWN_WORDS = [
  'brkd', 'breakdown', 'breakdowns', 'making', 'mof', 'bts', 'wip', 'showcase', 'showcases',
  'progression', 'process', 'processes', 'progress', 'turnaround', 'turnarounds', 'turntable',
  'turntables', 'turn', 'lookdev', 'lookdevs', 'reel', 'reels', 'rig', 'rigs', 'rigging',
  'rigg', 'test', 'tests', 'testing', 'shot', 'shots', 'character', 'characters', 'environment',
  'environments', 'render', 'renders', 'rendering', 'compositing', 'comp', 'fx', 'lighting',
  'blocking', 'block', 'blocks', 'demo', 'demos', 'comparison', 'quad', 'orchestra', 'layout',
  'layouts', 'pipeline', 'cfx', 'procedural', 'blendshape', 'blendshapes', 'expression',
  'expressions', 'cycle', 'simulation', 'simulations', 'hair', 'clothes', 'cloth', 'frame',
  'frames', 'storyboard', 'blockout'
];
function classify(video, workTitle) {
  if (video.host === 'direct') return 'other';                    // 原生 S3 直链无标题，当兜底
  const t = (video.title || '').toLowerCase();
  const w = (workTitle || '').toLowerCase();
  if (!t) return 'locked';                       // oEmbed 无标题 → Vimeo 密码保护
  // 标题先归一化：非字母数字 → 空格，使 "_MOF_"、"-turn-"、驼峰 "lookDev" 也能按词命中
  const tn = t.replace(/[^a-z0-9]+/g, ' ').trim();
  // 短语归一化：making of / behind the scenes 的任意连写（makingof / behind-the-scenes）统一为 breakdown
  const tn2 = tn.replace(/\b(making[ -]?of|behind[ -]?the[ -]?scenes)\b/g, ' breakdown ');
  for (const word of BREAKDOWN_WORDS) {
    if (new RegExp('(?<![a-z0-9])' + word + '(?![a-z0-9])').test(tn2)) return 'breakdown';
  }
  // 成片特征词（含法语 bande-annonce / court-métrage，Rubika/ESMA 学生片常见）
  if (/\b(short film|teaser|trailer|official|officielle|bande[ -]annonce|court[ -]m[eé]trage|the movie|full movie|full film|full|movie|film)\b/.test(tn2)) return 'main';
  // 作品名核心词匹配：去标题分隔符与常见修饰词后，若核心词出现在视频标题里 → 成片
  const core = w.replace(/\s*[-–|].+$/, '').replace(/\b(the|a|short film|film|movie|2025|2026)\b/g, '').replace(/[^a-z0-9]+/g, ' ').trim();
  if (core && core.length >= 3 && tn2.includes(core)) return 'main';
  return 'other';
}
function parseEntry(html, selfId) {
  const doc = new DOMParser().parseFromString(html, 'text/html');
  const og = doc.querySelector('meta[property="og:title"]')?.content || '';
  let title = og.replace(/^The Rookies - /, '');
  let author = '';
  const byM = title.match(/, by (.+)$/);
  if (byM) {
    // og:title 可能含双 "by"（显示名 + 用户名，如 "..., by Yanina Perez-Masud, by thegraysays"），剥掉尾部 ", by \w+" 只留显示名
    author = byM[1].split(', by ')[0];
    title = title.replace(/, by .+$/, '');
  }
  // 作者显示名优先取自页面头像 alt（og:title 单 by 时 author 是用户名，如 "roberthmurillo"；头像 alt 才是 "Roberth Alexander Murillo Lugo"）
  const avatar = doc.querySelector('.project-header img.avatar-media, .project-content img.avatar-media, main img.avatar-media')?.alt?.trim();
  if (avatar && author.toLowerCase() !== avatar.toLowerCase()) author = avatar;
  const videos = []; const images = []; const linkedEntries = [];
  const pc = doc.querySelector('.project-content');
  if (pc) {
    // 收集 iframe 前最近的 H3 章节标题（如 "THE MOVIE"、"THE MAKING-OF"、"CHARACTER - HADENNA"），辅助判断成片
    const sections = [];
    const walker = document.createTreeWalker(pc, NodeFilter.SHOW_ELEMENT);
    let lastH3 = '';
    while (walker.nextNode()) {
      const n = walker.currentNode;
      if (n.tagName === 'H3') lastH3 = n.innerText.trim().replace(/\s+/g, ' ');
      if (n.tagName === 'IFRAME') sections.push({ node: n, section: lastH3 });
    }
    for (const { node: el, section } of sections) {
      const s = el.src || '';
      if (s.includes('youtube.com/embed/')) videos.push({ host: 'youtube', url: 'https://www.youtube.com/watch?v=' + s.split('/embed/')[1].split('?')[0], section, title: null });
      else if (s.includes('vimeo.com')) videos.push({ host: 'vimeo', url: s.split('?')[0], section, title: null });
    }
    // 2) 原生 <video> 元素（S3 直链 mp4，非 YouTube/Vimeo 内嵌）；保留完整 URL（可能带签名参数）
    for (const v of pc.querySelectorAll(':scope video')) {
      const src = v.currentSrc || v.getAttribute('src') || '';
      if (src) videos.push({ host: 'direct', url: src, section: '', title: null });
      for (const s of v.querySelectorAll('source')) {
        if (s.src) videos.push({ host: 'direct', url: s.src, section: '', title: null });
      }
    }
    // 3) 关联影片帖链接：.project-content 内指向其他 /entries/{id} 的超链接（如 "Click here to see the full movie post"）
    for (const a of pc.querySelectorAll(':scope a[href*="/entries/"]')) {
      const m = a.href.match(/\/entries\/(\d+)/);
      if (m && m[1] !== String(selfId)) {
        linkedEntries.push({ id: m[1], label: (a.innerText || '').trim().slice(0, 60) || a.href });
      }
    }
    // 4) 以上视频全无时才是纯图片作品，提取 CloudFront 图片
    if (videos.length === 0 && linkedEntries.length === 0) {
      for (const img of pc.querySelectorAll(':scope img')) {
        if (img.src && img.src.includes('cloudfront')) {
          images.push(img.src.replace(/\/([0-9]+)xAUTO\//, '/3840xAUTO/'));
        }
      }
    }
  }
  return { title, author, videos, images, linkedEntries };
}

// 遍历 links 批量解析；有关联影片帖的 entry 再 fetch 一次补全视频；最后用 oEmbed 补视频标题并分类成片
const results = [];
for (const l of links) {
  const id = l.url.match(/entries\/(\d+)/)?.[1] || '';
  const html = await rkFetch(l.url);
  if (!html) continue;
  const r = parseEntry(html, id);
  const subVideos = [];
  for (const le of r.linkedEntries) {
    const lh = await rkFetch('https://www.therookies.co/entries/' + le.id);
    if (lh) {
      const sub = parseEntry(lh, le.id);
      sub.videos.forEach(v => subVideos.push({ ...v, via: le.label }));
    }
  }
  r.videos.push(...subVideos);
  // oEmbed 逐条补标题（并发 6 个避免过载），再按标题分类成片
  for (let i = 0; i < r.videos.length; i += 6) {
    await Promise.all(r.videos.slice(i, i + 6).map(async v => { v.title = await oEmbedTitle(v); }));
  }
  for (const v of r.videos) v.role = classify(v, r.title);
  results.push(r);
}
return results;
```

**注意**：全部 42 个 entry 的返回数组较大，BrowserClaw evaluate 的返回可能被截断（上限约 5000 字符）。此时**不要重跑**，直接读取落盘文件 `~/.browseros/tool-output/*.txt` 拿完整结果。

**结构说明**：视频来源有四种——① `.project-content` 内 `iframe`（YouTube 形如 `youtube.com/embed/{id}`，Vimeo 形如 `player.vimeo.com/video/{id}`）；② 原生 `<video>` 元素（`currentSrc`/`src` 为 `rookies-production.s3-accelerate.amazonaws.com` 直链 mp4）；③ `.project-content` 内指向其他 `/entries/` 的超链接（纯图作品页可能用"here/click"文字链到完整影片帖）；④ 都没有才是纯图片作品。**爬取以视频为主；仅真正无视频、无关联影片帖的作品才提取图片**。若作品页有多个 `<video>`，用 `querySelectorAll(':scope video')` 一次性取全部。

**成片识别（关键）**：一个作品往往混着成片与衍生内容（如 AZIMUTH 的 Vimeo 成片 `AZIMUTH - Sci-Fi Short Film` + 28 个 YouTube making-of/breakdown；SALAMANDER 的 YouTube `Salamander - Teaser 2025` 成片 + 密码锁定的 Vimeo + 多个 Showcase/Progression）。脚本用 oEmbed 拉取每个视频真实标题，`classify()` 按以下规则打标（contest 561 全 42 作品实测校准）：
- **`main`（成片）**：标题含成片特征词（`short film`/`teaser`/`trailer`/`official`/`the movie`/`full movie`/`film`/`movie`/法语 `bande-annonce`/`court-métrage` 等），或含作品名核心词
- **`breakdown`（衍生）**：标题命中衍生词表——making of（含 `mof` 缩写、任意连写）、breakdown（含 `brkd`）、behind the scenes/bts、showcase、progression/process、turnaround/**turn**/turntable、lookdev、reel、rig/rigging、test、shot、character（含复数）、environment、render、compositing/fx、lighting、blocking、demo、comparison、layout、pipeline、procedural、blendshape、expression、cycle、simulation、frame、storyboard 等。**词表覆盖复数与变体**（`characters`、`_Turn_`、`TurnTable`、`MOF`、`lookDev`、`firstshot_blocking`），避免把"角色/镜头展示"误判成片
- **`locked`（密码锁定）**：Vimeo oEmbed 返回 `title: null` → 需密码，除非作品页正文给出密码否则跳过
- **`other`**：无法归类的兜底

**下载优先级**：每个作品**只下载 `main`（成片）**；仅当该作品**没有成片**（无 `main`）时才降级下载 `breakdown` 等其他视频；`locked` 一律跳过（除非页面给了密码）。DIFF 表格按此标注，方便用户只挑成片。

### 图片最高质量技巧（仅纯图片作品用）

CloudFront 图片 URL 含尺寸段 `/1400xAUTO/`、`/800xAUTO/` 等。**把 `/{数字}xAUTO/` 替换为 `/3840xAUTO/` 即得原图**（已验证 3840xAUTO 返回原始分辨率大图；5000xAUTO/4096xAUTO/2000xAUTO 等均返回 400，3840 是上限）。

### DIFF 表格格式（对话中呈现）

每作品一行，**成片单独标注**，衍生内容（making-of/breakdown/showcase 等）与密码锁定的视频合并为"衍生"列，交给用户判断下载哪些；**纯图片作品（无视频）列图片数量**：

| # | 作品 | 作者 | 成片 | 衍生（含密码锁定） |
|---|------|------|------|------|
| 1 | The Lead that Bled | ... | Vimeo "The Lead that Bled - Short Film" | 衍生 ×6 |
| 2 | AZIMUTH Shortfilm | fmichez | Vimeo "AZIMUTH - Sci-Fi Short Film" | 衍生 ×28（making-of/breakdown） |
| 3 | SALAMANDER - Short Film | pumphik | YouTube "Salamander - Teaser 2025" | Vimeo ×4（含 1 密码锁定、Showcase/Progression） |
| 4 | The Character Dossier | Yanina Perez-Masud | 无成片（降级） | 原生视频 ×8（S3 mp4） |
| 5 | Yanina ... | ... | — | 图片 ×53（纯图片） |
| ... | ... | ... | ... | ... |

作者列显示**显示名**（非用户名）。提交选择后按序号下载。**默认只下载"成片"列；无成片作品才降级下载衍生列**；密码锁定的 Vimeo 跳过。表格中对"关联影片帖"作品在资源列标注 `→ 关联影片帖标题`，让用户知道跳转后才能拿到完整影片。

### 目录结构

主文件夹 = 链接标题（比赛名），每个作品一个子文件夹，子文件夹内按资源类型分子目录，**资源文件一律用作品名命名，多资源追加 `_序号`**：

```
{download_dir}/
└── Rookie of the Year | 3D Animation/          ← 比赛名（results 页标题）
    └── {作品标题} by {作者}/                    ← 每作品一个文件夹
        ├── Video/                              ← 视频（有视频的作品）
        │   ├── {作品标题}_01.mp4
        │   └── {作品标题}_02.mp4
        └── Images/                             ← 图片（纯图片作品）
            ├── {作品标题}_01.jpg
            └── ...
```

目录名中如含 `/`、`:`、`|` 等非法字符需替换为 `-`（例如比赛名 `Rookie of the Year | 3D Animation` → `Rookie of the Year - 3D Animation`）。文件名的非法字符同样替换为 `-`。`{作品标题}` 用 parseEntry 解析出的干净标题（已剥 `The Rookies - ` 前缀和 `, by` 尾部）。若某视频来自关联影片帖（有 `via` 标记），文件名仍用作品标题命名，序号顺延。

### 步骤 3：下载

🔴 **CHECKPOINT**：按作品下载时，**先只下载成片（`role === 'main'`）**；若该作品无成片，才降级下载其余视频（`breakdown`/`other`，排除 `locked`）。`locked`（Vimeo 密码锁定）一律跳过——除非作品页正文里明确给出了密码（此时把密码传给 Vimeo 页/yt-dlp）。

**YouTube 视频**（用 yt-dlp，见 YouTube 专用处理；公开视频无需 cookies）。每条视频用作品名 + 递增序号命名：

```bash
yt-dlp -P "<作品目录>/Video" -o "{作品标题}_01.%(ext)s" -S "res:1080" "<YouTube URL>"
```

多条视频时按顺序把序号递增（`_01`、`_02`…）。

**Vimeo 视频**（见 Vimeo 专用处理——必须登录 Vimeo，未登录则提示用户登录后重试）。命名同上。密码锁定的 Vimeo（oEmbed `title: null`）不下载；若作品页正文给了密码，用 `--video-password "<密码>"` 重试。

**原生 `<video>` 直链（S3 mp4）**（用 curl 直接下载，S3 直连无需 cookies）：

```bash
curl -sL -o "<作品目录>/Video/{作品标题}_01.mp4" "<S3 mp4 URL>"
```

直链为 mp4/mov，无需转码；多条时递增序号。S3 直链可能带签名参数，保留完整 URL。

**图片（仅纯图片作品）**（用 curl 直接下载 3840xAUTO 原图，CloudFront 直连无需 cookies）：

```bash
curl -sL -o "<作品目录>/Images/{作品标题}_01.jpg" "<3840xAUTO URL>"
```

图片较多时可用循环并行下载（注意控制并发，如 `xargs -P 4`）。扩展名从 URL 取（`.jpg`/`.png`/`.gif`），序号递增。

## 小红书专用处理

URL 示例：`https://www.xiaohongshu.com/explore/xxx`、`https://xhslink.com/xxx`、`https://www.rednote.com/explore/xxx`

XHS-Downloader 支持图文笔记（图片）和视频笔记的无水印下载。

### 依赖检查

首次运行前确保已安装 XHS-Downloader：

```bash
ls /tmp/xhs-downloader/main.py >/dev/null 2>&1 || {
  git clone https://github.com/JoeanAmier/XHS-Downloader.git /tmp/xhs-downloader
  pip install -r /tmp/xhs-downloader/requirements.txt
}
```

### 方式 A：API 模式（推荐，可后台常驻）

🔴 **CHECKPOINT**：启动前先确认依赖就绪，再清理端口冲突。

```bash
# 0. 检查 main.py 是否存在
test -f /tmp/xhs-downloader/main.py || { echo "ERROR: XHS-Downloader 未安装，先运行依赖安装"; exit 1; }

# 1. 检查 config.json 是否存在
test -f <SKILL_DIR>/config.json || { echo "ERROR: config.json 不存在，请先完成 First Run Setup"; exit 1; }

# 2. 清理已有服务（防止端口占用）
kill $(lsof -t -i:5556) 2>/dev/null && echo "Killed existing XHS-API" || echo "Port 5556 free"

# 3. 读取下载目录
DOWNLOAD_DIR=$(python3 -c "import json; print(json.load(open('<SKILL_DIR>/config.json'))['download_dir'])")

# 4. 启动 API 服务（端口 5556），用 --work_path 指向统一下载目录
python /tmp/xhs-downloader/main.py api --port 5556 --work_path "$DOWNLOAD_DIR" &

# 5. 健康检查（轮询直到就绪，非硬等待）
for i in $(seq 1 10); do
  sleep 1
  curl -s -o /dev/null -w "%{http_code}" http://127.0.0.1:5556/docs 2>/dev/null | grep -q 200 && echo "API Ready" && break
done
```

`--work_path` 使得所有下载文件保存到 `{download_dir}/Download/` 下，而非 XHS-Downloader 的默认位置。

调用 API 下载：

```bash
curl -s -X POST http://127.0.0.1:5556/xhs/detail \
  -H "Content-Type: application/json" \
  -d '{"url": "<小红书链接>", "download": true}' | python3 -m json.tool
```

响应包含作品信息（标题、作者、标签等）和下载状态。

如果不需要实时下载，仅获取无水印地址：

```bash
curl -s -X POST http://127.0.0.1:5556/xhs/detail \
  -H "Content-Type: application/json" \
  -d '{"url": "<小红书链接>", "download": false}'
```

### 方式 B：CLI 模式（单次下载，自动使用统一下载目录）

```bash
DOWNLOAD_DIR=$(python3 -c "import json; print(json.load(open('<SKILL_DIR>/config.json'))['download_dir'])")
python /tmp/xhs-downloader/main.py --work_path "$DOWNLOAD_DIR" "<小红书链接>"
```

XHS-Downloader 会启动 TUI 界面并自动识别内容类型（图文/视频）开始下载。文件保存到 `{download_dir}/Download/`。

### 文件结构

下载路径由 `config.json` 的 `download_dir` + `folder_name`（默认 `Download`）拼接而成：

```
{download_dir}/
└── Download/              ← folder_name 控制
    ├── {作品标题}_001.{ext}
    ├── {作品标题}_002.{ext}
    └── ...
```

开启 `folder_mode` 后，每个作品保存在单独文件夹：

```
{download_dir}/
└── Download/
    └── {作品标题}/
        ├── 001.{ext}
        ├── 002.{ext}
        └── ...
```

开启 `author_archive` 后，按作者归档：

```
{download_dir}/
└── Download/
    └── {作者ID}_{作者昵称}/
        └── {作品标题}_001.{ext}
```

### 仅下载指定图片

如果图文笔记有很多张图，只想下载其中几张，在 CLI 模式下用 `index` 参数：

对 API 模式的 POST body 追加 `index` 字段：

```json
{
  "url": "<小红书链接>",
  "download": true,
  "index": [1, 3, 5]
}
```

### Cookie 配置（可选，推荐配置以保证高画质）

XHS-Downloader 2.2+ 版本无需 Cookie 也可正常工作，但配置 Cookie 可以获得更高画质。

1. 用 BrowserClaw 访问 https://www.xiaohongshu.com 并登录（可选）
2. F12 → 网络 → 过滤 `web_session` → 复制完整 Cookie
3. 编辑 `/tmp/xhs-downloader/settings.json` 写入 `cookie` 字段：

```json
{
  "cookie": "web_session=xxx; a1=xxx; ..."
}
```

或者在 API 调用时传 `cookie` 参数：

```json
{
  "url": "<小红书链接>",
  "download": true,
  "cookie": "web_session=xxx; a1=xxx; ..."
}
```

### 配置说明

主要配置修改 `/tmp/xhs-downloader/settings.json`：

| 参数 | 类型 | 含义 | 默认值 |
|------|------|------|--------|
| `image_format` | str | 图文下载格式：AUTO/PNG/WEBP/JPEG/HEIC | `WEBP` |
| `image_download` | bool | 图文作品下载开关 | `true` |
| `video_download` | bool | 视频作品下载开关 | `true` |
| `folder_mode` | bool | 每个作品独立文件夹 | `false` |
| `author_archive` | bool | 按作者归档 | `false` |
| `download_record` | bool | 记录已下载作品（防重复） | `true` |
| `name_format` | str | 文件命名模板 | `发布时间 作者昵称 作品标题` |

### 已知问题

- **URL 携带日期信息**：旧链接可能被风控，要求用户提供最新分享链接（在 App 中点击分享按钮复制）
- **无水印视频处理耗时**：下载后脚本需要处理文件，请勿多次点击
- **Mac 可执行文件签名**：如果使用 Releases 下载的二进制，首次运行需 `xattr -cr /path/to/main`

## 抖音无水印专用处理

URL 示例：`https://www.douyin.com/video/xxx`、`https://v.douyin.com/xxx/`

抖音（Douyin）的视频通过 yt-dlp 下载会携带水印。本技能使用 parse-video-py 获取无水印直链进行下载。

### 依赖检查

首次运行前确保已安装 parse-video-py：

```bash
ls /tmp/parse-video-py/main.py >/dev/null 2>&1 || {
  git clone https://github.com/wujunwei928/parse-video-py.git /tmp/parse-video-py
  cd /tmp/parse-video-py && pip install -r requirements.txt
}
```

### 解析流程

#### 步骤 1：启动解析服务

🔴 **CHECKPOINT**：启动前先检查依赖是否存在，再清理端口冲突。

```bash
# 0. 检查 main.py 是否存在
test -f /tmp/parse-video-py/main.py || { echo "ERROR: parse-video-py 未安装，先运行依赖安装"; exit 1; }

# 1. 检查 config.json 是否存在
test -f <SKILL_DIR>/config.json || { echo "ERROR: config.json 不存在，请先完成 First Run Setup"; exit 1; }

# 2. 清理已有服务
kill $(lsof -t -i:8000) 2>/dev/null && echo "Killed existing parse-video" || echo "Port 8000 free"

# 3. 启动 HTTP 服务（默认端口 8000）
cd /tmp/parse-video-py && python main.py &

# 4. 轮询健康检查（确认端口可达，非硬等待）
for i in $(seq 1 10); do
  sleep 1
  STATUS=$(curl -s -o /dev/null -w "%{http_code}" http://127.0.0.1:8000/ 2>/dev/null)
  # 只要不是连接错误（无 5xx）就算启动成功
  [ -n "$STATUS" ] && [ "$STATUS" -ge 200 ] && [ "$STATUS" -lt 500 ] && echo "Service Ready (HTTP $STATUS)" && break
done
```

#### 步骤 2：获取无水印视频直链

```bash
# 调用解析 API
RESULT=$(curl -s "http://127.0.0.1:8000/video/share/url/parse?url=<抖音分享链接>")

# 提取视频 URL
VIDEO_URL=$(echo "$RESULT" | python3 -c "import sys,json; print(json.load(sys.stdin)['data']['video_url'])")
TITLE=$(echo "$RESULT" | python3 -c "import sys,json; print(json.load(sys.stdin)['data']['title'])")
AUTHOR=$(echo "$RESULT" | python3 -c "import sys,json; print(json.load(sys.stdin)['data']['author']['nickname'])")

echo "标题: $TITLE"
echo "作者: $AUTHOR"
echo "无水印视频: $VIDEO_URL"
```

#### 步骤 3：下载无水印视频（保存到统一下载目录）

先从 `config.json` 读取下载目录：

```bash
DOWNLOAD_DIR=$(python3 -c "import json; print(json.load(open('<SKILL_DIR>/config.json'))['download_dir'])")
```

使用 curl 下载（无水印直链）：

```bash
curl -L -o "${DOWNLOAD_DIR}/${TITLE:0:50}.mp4" "$VIDEO_URL"
```

或使用 yt-dlp 以支持断点续传和进度显示（将无水印直链传给 yt-dlp）：

```bash
yt-dlp -P "$DOWNLOAD_DIR" -o "%(title)s.%(ext)s" "$VIDEO_URL"
```

### 图集（图文）处理

抖音图文笔记返回的 `image_list` 包含所有图片地址：

```bash
RESULT=$(curl -s "http://127.0.0.1:8000/video/share/url/parse?url=<抖音图文链接>")
echo "$RESULT" | python3 -c "
import sys, json
data = json.load(sys.stdin)['data']
for i, img in enumerate(data.get('image_list', [])):
    if isinstance(img, dict):
        print(f'{i+1}: {img.get(\"url\", \"\")}')
    else:
        print(f'{i+1}: {img}')
"
```

解析结果如包含 `live_photo_url` 字段，表示该图包含实况照片视频原件。

### 其他平台（小红书、快手等）

parse-video-py 同样支持小红书、快手、微博、Bilibili 等平台的解析：

```bash
# 小红书
curl -s "http://127.0.0.1:8000/video/share/url/parse?url=<小红书链接>"

# 快手
curl -s "http://127.0.0.1:8000/video/share/url/parse?url=<快手链接>"

# 微博
curl -s "http://127.0.0.1:8000/video/share/url/parse?url=<微博链接>"
```

从返回的 JSON 中提取对应字段即可获得无水印资源。

### MCP 模式（进阶）

parse-video-py 原生支持 MCP 协议，可作为 MCP 工具集成到 AI 编码助手中：

```bash
cd /tmp/parse-video-py && python main.py --mcp
```

### 注意

- **使用 App 分享链接**：网页版链接未做充分测试，必须使用 App 分享链接
- **频繁请求**：过快重复解析可能触发 IP 限频
- **服务保持**：将 HTTP 解析服务设为持久化后台服务
- **服务重启**：如遇解析失败，重启服务后重试：

```bash
kill $(lsof -t -i:8000) 2>/dev/null
cd /tmp/parse-video-py && python main.py &
```

## 清晰度选择策略

🔴 **CHECKPOINT**：发现格式中有 >1080p 选项时，必须询问用户。

先列出可用格式：

```bash
yt-dlp -F "<URL>"
```

从输出中解析所有视频格式的**高度值**（resolution/height 列），因为 yt-dlp 的列格式是固定的。

步骤：
1. 运行 `-F` 提取所有视频格式的高度
2. 筛选 >= 1080p 的选项，去重后升序排列
3. 决策：
   - 最大高度 <= 1080 → 自动用 `-S "res:1080"` 下载
   - 最大高度 > 1080 → 用 `question` 列出 >= 1080p 的所有选项让用户选
4. 用户选择后：
   - 选 1080p → `-S "res:1080"`
   - 选 4K / 2160p → `-S "res:2160"`
   - 选 8K / 4320p → `-S "res:4320"`
   - 选具体值 → `-S "res:<HEIGHT>"`

注意 `-S "res:X"` 的含义是"限制分辨率不超过 X，并优先接近 X 的最佳格式"，这正是需要的。

## 通用参数参考

### yt-dlp
| 参数 | 用途 |
|------|------|
| `-P <dir>` / `--paths <dir>` | 下载目录 |
| `-o "<template>"` | 输出文件名 |
| `-S "res:1080"` | 限制并排序分辨率 |
| `-f "bv*+ba/b"` | 最佳视频+最佳音频 |
| `-F` | 列出格式 |
| `--cookies <file>` | 使用 cookies 文件（用户上传的 `<平台>.txt`，见 Cookies 获取引导） |
| `--impersonate chrome` | 浏览器指纹模拟 |
| `--download-sections "*START-END"` | 时间切片（需 ffmpeg） |

### gallery-dl
| 参数 | 用途 |
|------|------|
| `-d <dir>` / `--destination <dir>` | 下载目录（基础路径） |
| `-f "<template>"` | 文件名模板（用 `{field}` 语法） |
| `-D <dir>` | 精确下载目录（字面路径，不支持模板） |
| `-K` / `--list-keywords` | 列出可用元数据字段及示例值 |
| `-o "directory=<template>"` | 目录路径模板 |
| `-o "filename=<template>"` | 文件名模板（同 `-f`） |
| `-s` | 模拟运行，不实际下载 |
| `--cookies <file>` | 使用 cookies 文件（用户上传的 `<平台>.txt`） |
| `--write-info-json` | 同时保存元数据 JSON |

### gallery-dl 输出模板变量
`{title}`、`{category}`、`{subcategory}`、`{num}`、`{extension}`、`{filename}`、`{count}`、`{user[key]}`（嵌套字段用 `[]`）

## ⚠️ 反例与黑名单

| # | 危险动作 | 后果 | 正确做法 |
|---|---------|------|---------|
| 1 | 用 yt-dlp 下载 ArtStation | 失败（yt-dlp 无 ArtStation extractor） | 必须用 gallery-dl |
| 2 | 用 gallery-dl 下载 YouTube/Bilibili | 失败（gallery-dl 不用于视频平台） | 必须用 yt-dlp |
| 3 | 不检查 ffmpeg 就用 `--download-sections` | 报错退出 | 先 `command -v ffmpeg` 检查 |
| 4 | 下载 Bilibili 时不加 `--impersonate chrome` | HTTP 412 错误 | 必须加 `--impersonate chrome` + `--add-header Origin/Referer` |
| 5 | 混用输出模板语法：`%(title)s` vs `{title}` | 文件名乱码或报错 | yt-dlp 用 `%(var)s`，gallery-dl 用 `{var}` |
| 6 | 跳过首次运行目录设置 | 文件下载到当前目录散落各处 | 必须先设 `DOWNLOAD_DIR` |
| 7 | 用 `--cookies-from-browser` 自动提取 cookies | 依赖本地浏览器登录态，跨平台不可复现 | 必须用用户上传的 `<cookies_dir>/<平台>.txt` 文件 |
| 8 | 下载高画质不检查账号状态 | 大会员内容下载失败 | 对 >1080p 选项标注需登录，提示用户更新 cookies 文件 |
| 9 | 用 `--cookies-from-browser chromium:` 或提取脚本读浏览器 cookies | Keychain 解密失败、依赖具体浏览器 | 用户用 Get cookies.txt LOCALLY 扩展导出后上传 |
| 10 | cookies 文件长期不更新导致失效 | 下载报权限错误 | 仅在下载失效或高画质锁定时提示用户重新导出覆盖 |
| 11 | 用 yt-dlp 下载小红书 | 需要 web_session cookie，经常 extractor 损坏 | 必须用 XHS-Downloader |
| 12 | 用 XHS-Downloader 下载 YouTube/Bilibili | 失败（XHS-Downloader 仅支持小红书） | 必须用 yt-dlp |
| 13 | 用 yt-dlp 下载抖音（期望无水印） | 视频带抖音水印 | 必须用 parse-video-py 获取无水印直链 |
| 14 | 不启动 parse-video-py 服务就调用 API | curl 返回 502/Connection refused | 先 `cd /tmp/parse-video-py && python main.py &` 启动服务 |
| 15 | XHS-Downloader 旧代码未更新 | 小红书反爬更新导致解析失败 | 定期 `git pull` 更新到最新版 |
| 16 | 用 curl 直接抓 therookies.co 页面 | 返回 5.6KB JS challenge 拦截页 | 必须用 BrowserClaw 在页内 `fetch`（同源携带 cookies） |
| 17 | 用浏览器逐个导航 42 个作品页爬取 | 极慢，且可能触发限流 | 在 results 页 evaluate 中批量 `fetch` 所有 entry HTML |
| 18 | 下载 therookies 纯图片作品的图片时保留原 `1400xAUTO` 尺寸段 | 拿到的是缩略图而非原图 | 替换为 `/3840xAUTO/` 拿原图 |
| 19 | 期望 yt-dlp 匿名下载 therookies 嵌入的 Vimeo 视频 | 报 `Failed to fetch macos OAuth token: HTTP Error 401`（上游 bug #17271） | 用 `--cookies + --extractor-args "vimeo:client=web"`；未登录则要求用户登录 Vimeo 后重试 |
| 20 | 解析时只查 `.project-content` 内的 `iframe`，忽略原生 `<video>` | 漏掉 S3 直链 mp4（如 Character Dossier），把有视频的作品当纯图 | 同时查 `querySelectorAll(':scope video')`（`currentSrc`/`src`）和 `video > source` |
| 21 | 纯图作品页忽略正文里的影片超链接 | 漏掉指向完整影片帖的 `a[href*="/entries/"]`（如 Allegaert "Click here"） | 检测 `.project-content` 内关联 entry 链接，`fetch` 后合并其视频 |
| 22 | 作者取 og:title 里单 by 的用户名 | 作者列显示用户名（`roberthmurillo`）而非显示名 | 优先取头像 `img.avatar-media` 的 alt 作显示名 |
| 23 | 下载文件用 yt-dlp 默认标题/图片原始文件名 | 文件不叫作品名 | 用 `{作品标题}_{序号}.{ext}` 命名 |
| 24 | 一个作品有多条视频时把全部（含 making-of/breakdown/showcase）都下载 | 下载大量衍生内容，成片淹没在几十个视频里 | 用 oEmbed 标题 + `classify()` 分 `main`/`breakdown`/`locked`/`other`；**只下载 `main` 成片，无成片才降级** |
| 25 | 直接下载 Vimeo 密码锁定视频（oEmbed `title: null`） | yt-dlp 下载失败或需要密码 | 判定为 `locked` 跳过；作品页给密码时才用 `--video-password` 下载 |

## 🔧 失败模式与恢复

| 触发条件 | 一线修复 | 仍失败兜底 |
|---------|---------|-----------|
| `yt-dlp` 返回 HTTP 403/412 | 加 `--impersonate chrome` 再试 | 加 `--add-header Origin` + `--add-header Referer`，仍失败则告知用户需在浏览器手动访问 |
| `yt-dlp` 返回 HTTP 404（Bilibili） | 确认 BV 号是否正确，换一个可用视频测试 | 可能是区域限制，提示用户确认视频可访问 |
| `command -v ffmpeg` 失败（时间切片需要） | 提示 `brew install ffmpeg` | 不用时间切片，引导用户下载完整视频后自行剪辑 |
| `gallery-dl -K` 返回空/报错 | 确认 URL 是否为 ArtStation 项目/画师页格式 | 检查网络，提示用户在浏览器打开确认链接有效 |
| `gallery-dl` 文件名包含非法字符 | gallery-dl 会自动替换，但如果报错改用 `-f "{hash_id}_{num}.{extension}"` | 用 `-f "{num}.{extension}"` 降级 |
| `<cookies_dir>/<平台>.txt` 不存在 | 跳过 cookies，用公开画质下载 | 需高画质/登录内容时提示用户用 Get cookies.txt LOCALLY 导出上传 |
| 格式列表 `-F` 无输出 | 检查 URL 是否可公开访问 | 提示用户确认链接，换 `-f "bv*+ba/b"` 无格式限制下载 |
| 高画质格式被锁定（需登录） | 提示用户更新该平台 cookies 文件后重试 | 仍失败则提示确认账号是否购买了该内容/有相应权限，用公开可用画质下载 |
| cookies 文件失效（下载报权限错误） | 引导用户重新用 Get cookies.txt LOCALLY 导出覆盖原文件 | 跳过 cookies 用公开画质下载 |
| Bilibili 下载 AV1 格式（format ID 100xxx）连接超时（`Connection timed out`） | 换用 AVC/h264 格式（format ID 300xx） | 指定低分辨率格式如 720p 或换第三方工具 |
| XHS-Downloader API 返回空/报错 | 检查 `/tmp/xhs-downloader` 是否最新，执行 `git pull` | 检查 Cookie 配置是否过期，必要时更新 Cookie |
| parse-video-py 解析抖音失败 | 确认使用 App 分享链接而非网页版链接；重启服务后重试 | 切换为 yt-dlp 带水印的版本下载 |
| parse-video-py 服务端口被占用 | `kill $(lsof -t -i:8000) 2>/dev/null` 后重启 | 修改端口号 `python main.py --port 8001` |
| 小红书链接含 `xsec_token` 但解析失败 | 尝试使用 `xhslink.com` 短链接格式 | 在浏览器中打开后复制最新分享链接 |
| 抖音图文/图集下载到的是图片而非视频 | 这是正常行为——抖音图文本来就只有图片 | 检查返回 JSON 的 `type` 字段确认内容类型 |
| therookies 结果页 evaluate 提取不到 h3 | 页面结构可能已改，h3 含换行或改为其它标签 | 先 normalize 空白（`replace(/\s+/g,' ')`）再剥 `Finalists ` 前缀 |
| therookies 作品页 fetch 返回空 | JS challenge 或网络波动 | 重试；或改为对该 entry 逐个导航抓取（BrowserClaw navigate + evaluate） |
| therookies 图片 3840xAUTO 返回 400 | 该图原尺寸不足 3840，尺寸段已超出上限 | 换用更小的尺寸段（1400xAUTO）或保留原 URL |
| therookies Vimeo 视频无法下载 | yt-dlp OAuth 401（未登录 web 客户端） | 用 `question` 要求用户更新 `cookies_dir/vimeo.txt` 后重试 |
| therookies 纯图作品漏检原生 `<video>`（如 Character Dossier 的 S3 mp4） | parseEntry 只查 iframe，没查 `<video>`/`<source>` | 解析时同时 `querySelectorAll(':scope video')` 取 `currentSrc`/`src`，判为 `direct` 视频 |
| therookies 作品作者显示为用户名（如 `roberthmurillo`）而非显示名 | og:title 单 by 时 by 后是用户名；显示名在头像 `img.avatar-media` 的 alt 里 | author 优先取 `.avatar-media` alt（"Roberth Alexander Murillo Lugo"），无头像时回退 og:title |
| therookies 纯图作品页里其实有完整影片超链接（如 Allegaert "Click here" → 另一 `/entries/`） | 只查 iframe/video 忽略正文链接 | 检测 `.project-content` 内 `a[href*="/entries/"]`（排除自身 id）记为 `linkedEntries`，再 fetch 补全其视频 |
| therookies 下载文件名不是作品名 | 用 yt-dlp 默认 `%(title)s` 或图片原始文件名 | 统一用 `{作品标题}_{序号}.{ext}` 命名，目录/文件非法字符替换为 `-` |
| therookies oEmbed 拉标题失败（网络/超时） | 单条重试 oEmbed；仍失败则用 iframe 前 H3 章节标题兜底（"THE MOVIE"→main） | 整批降级为无标题模式（不分类，全部下载，由用户自己判断） |
| therookies 成片标题不含作品名也不含特征词（classify 判为 `other`） | 对照 iframe 前 H3 章节标题补判：含 `movie`/`film`/`teaser` 的 H3 段落优先作 main | 按 `other` 处理放衍生列，呈现给用户时标注标题，由用户确认 |
| therookies Vimeo 密码锁定视频（oEmbed `title: null`）被当成纯图/漏掉 | 判定为 `locked` 保留在衍生列标注"密码锁定"，下载阶段跳过 | 作品页正文有密码则 `--video-password` 下载，无则告知用户需浏览器手动访问 |

## 场景示例

```
用户: "下载这个 https://youtu.be/xxx"
→ 列出格式，max=1080p → 自动下载 1080p

用户: "把这个下了 https://youtu.be/xxx 10:30-15:00"
→ 检查 ffmpeg → 时间切片下载

用户: "ArtStation 这个项目 https://www.artstation.com/artwork/Ov6Zwb"
→ gallery-dl → artstation/用户名/项目名_序号.扩展名

用户: "下个B站视频 https://www.bilibili.com/video/BV1GJ411x7"
→ 读取 cookies_dir/bilibili.txt → 列出格式 → 若高画质锁定则提示更新 cookies 重试 → 用户确认后重试 → 若>1080p问清晰度 → 下载

用户: "Vimeo 这个视频 https://vimeo.com/xxx"
→ 列出格式 → 若>1080p问清晰度 → 下载（公开视频无需 cookies）

用户: "帮我下载 https://twitter.com/xxx/status/xxx"
→ yt-dlp 通用下载

用户: "下载这个小红书 https://www.xiaohongshu.com/explore/xxx"
→ 检查 /tmp/xhs-downloader/main.py 是否存在 → 若不存在则克隆并安装依赖 → 从 config.json 读取 download_dir → 启动 API 服务（--work_path 指向 download_dir）→ 调用 POST /xhs/detail {url, download:true} → 保存到 {download_dir}/Download/

用户: "小红书这个笔记 https://xhslink.com/xxx"
→ XHS-Downloader API 模式 → 调用 POST /xhs/detail {url, download:true} → 返回作品信息 + 文件保存到 download_dir

用户: "下个抖音视频 https://v.douyin.com/xxx"
→ 检查 /tmp/parse-video-py/main.py 是否存在 → 若不存在则克隆并安装依赖 → 从 config.json 读取 download_dir → 启动 HTTP 服务 → 调用 GET /video/share/url/parse?url=抖音链接 → 提取 video_url → curl/yt-dlp 下载到 download_dir

用户: "抖音去水印 https://www.douyin.com/video/xxx"
→ parse-video-py 解析 → 获取无水印直链 → 下载到 download_dir

用户: "下载 https://www.therookies.co/contests/549/results 全部作品"
→ BrowserClaw 打开 results 页 → evaluate 提取比赛名 + entry 链接 → 批量 fetch + 解析每作品视频链接 → oEmbed 补标题 + classify 分 main/breakdown/locked → 对话中呈现 DIFF 表格（成片/衍生分列）交用户挑选 → 按所选作品建 {比赛名}/{作品名}/Video 目录 → **只下载成片，无成片才降级衍生**，locked 跳过 → YouTube 用 yt-dlp 下载、Vimeo 需登录

用户: "下载 https://www.therookies.co/entries/47874"
→ BrowserClaw 打开 entry 页 → evaluate 解析 og:title + .project-content 内视频/图片 → oEmbed 补标题分类成片 → 对话呈现（成片/衍生/密码锁定） → 建 {作品标题} by {作者}/Video 或 Images → 只下载成片，无成片才降级

用户: "这个作品只要成片，不要 breakdown"
→ 每个作品只下载 `role === 'main'` 的视频；无成片的作品提示用户（衍生内容也一并列出供选择）

用户: "AZIMUTH 那个作品 Vimeo 有成片，28 个 YouTube 都是 making-of，只下成片"
→ classify 会把 Vimeo 判为 main、28 个 YouTube 判为 breakdown → 只下载那条 Vimeo 成片
```

