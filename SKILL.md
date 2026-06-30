---
name: media-downloader
description: >
   基于 yt-dlp 和 gallery-dl 的素材下载技能，覆盖 YouTube、Bilibili、Vimeo、ArtStation 等数百个站点。
   当用户给出视频/图片链接请求下载时，必须使用此技能——包括但不限于："下载这个视频"、"把这个下了"、
   "帮我下这个"、"下载链接"、"保存这个视频"、"下载 B 站"、"下这个 youtube"、"ArtStation 下载"、
   "把这个项目下了"、"下个视频"、"帮我下个东西"等。技能自动处理清晰度选择（超过1080p询问用户）、
   时间节点切片下载、ArtStation 项目按用户名/项目名组织。
   gallery-dl 专门用于图片画廊类网站下载（ArtStation、Pixiv、DeviantArt 等）。
   任何时候用户提供 URL 并涉及下载行为，优先考虑此技能。
---

# media-downloader

基于 [yt-dlp](https://github.com/yt-dlp/yt-dlp) + [gallery-dl](https://github.com/mikf/gallery-dl) 的跨平台素材下载技能。

## First Run Setup

🔴 **CHECKPOINT**：在当前会话首次下载前，先确认下载目录和主力浏览器。

技能使用 `<SKILL_DIR>/config.json` 跨会话持久化用户偏好。

### 读取已有配置

```
尝试读取 <SKILL_DIR>/config.json：

if 文件存在且字段完整:
    直接使用 download_dir 和 browser
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

### 步骤 2：设置主力浏览器

用 `question` 引导设置：

```
你的主力浏览器是什么？（用于自动提取 cookies，请选择日常登录了各视频平台的浏览器）
□ Safari
□ Chrome
□ Edge
□ Firefox
□ Brave
□ 其他 Chromium 系（如 Dia、Thorium 等）
```

如果选择"其他 Chromium 系"，追加询问：

```
浏览器名称：
配置文件路径（如 ~/Library/Application Support/Dia/User Data/Default）：
```

写入 `config.json` 的 `browser` 字段。如果用户需要更换浏览器，可重新运行本步骤或直接编辑 `config.json`。

### config.json 格式

```json
{
  "download_dir": "~/Downloads",
  "browser": "safari",
  "browser_profile": "~/Library/Application Support/Dia/User Data/Default"
}
```

- `browser`：标准浏览器名（safari/chrome/edge/firefox/brave）或自定义浏览器名（dia/thorium 等）
- `browser_profile`：仅非标准 Chromium 浏览器需要
- 更新配置：直接修改此 JSON 文件，或要求技能重新设置

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

### cryptography（Chromium 非标准浏览器 cookie 提取）

macOS 上使用非标准 Chromium 浏览器（Dia、Thorium 等）的 cookie 提取脚本需要 `cryptography` 库：

```bash
pip3 install --break-system-packages cryptography
```

**验证：**
```bash
python3 -c "from cryptography.hazmat.primitives.ciphers.aead import AESGCM; print('OK')"
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

### Cookies 获取路由

从 config.json 读取 `browser` 和 `browser_profile` 字段，按以下规则路由：

```
browser = safari / chrome / edge / firefox / brave
  → 方式 A：yt-dlp --cookies-from-browser <browser> ...

browser 为其他值（如 dia、thorium 等自定义非标准 Chromium 浏览器）
  → 方式 B：extract_cookies.py → yt-dlp --cookies /tmp/cookies.txt ...
```

方式 A 的 `<browser>` 从 config.json 的 `browser` 字段直接读取。
方式 B 的 `browser_profile` 从 config.json 的 `browser_profile` 字段读取。

### 方式 A：标准浏览器

主力浏览器为 Chrome/Firefox/Safari/Edge/Brave 等标准浏览器时，直接用：

```bash
yt-dlp --cookies-from-browser <browser> ...
```

yt-dlp 原生支持列表：brave, chrome, chromium, edge, firefox, opera, safari, vivaldi, whale

### 方式 B：macOS 非标准 Chromium 浏览器

当主力浏览器为"其他 Chromium 系"（如 Dia、Thorium），**禁止使用** `--cookies-from-browser chromium:"<PROFILE>"`，因为 yt-dlp 会使用标准 Chromium 的 Keychain 密钥（"Chromium Safe Storage"）解密，而非该浏览器的专用密钥（如 Dia → "Dia Safe Storage"），导致大部分登录态的 cookies 解密失败。

必须使用技能附带的 cookie 提取脚本：

```bash
python3 <SKILL_DIR>/scripts/extract_cookies.py \
  "<PROFILE_PATH>" --browser <浏览器名> \
  --domain <平台域名> > /tmp/cookies.txt

# 验证 cookies 格式（首行须为 Netscape header）
head -1 /tmp/cookies.txt | grep -q "Netscape HTTP Cookie File" && echo "OK"

# 然后用 cookies.txt 调用
yt-dlp --cookies /tmp/cookies.txt ...
```

支持 `--browser` 参数：`Dia`、`Chrome`、`Chromium`、`Brave`、`Edge`。这确保了使用正确的 macOS Keychain 服务名（如 Dia → `Dia Safe Storage`）进行 PBKDF2 密钥派生和 AES-CBC 解密。

`<SKILL_DIR>` 为该技能所在目录（`~/.config/opencode/skills/media-downloader`），通过 `command` 获取。

### 平台 Cookies 缺失处理

🔴 **CHECKPOINT**：当 `-F` 输出显示高画质格式被锁定（如 Bilibili 显示 "you have to become a premium member" 或 YouTube 年龄限制），说明该平台未在主力浏览器中登录。

用 `question` 询问用户：

```
检测到高画质需登录（该平台尚未在浏览器中登录）。
请在主力浏览器中登录该平台后重试。
□ 已登录，重新获取 cookies 重试
□ 跳过，用当前可用画质下载
```

- 选择"已登录" → 重新获取 cookies（标准浏览器用 `--cookies-from-browser`，非标准用提取脚本）
- 如果再次失败 → 提示"登录未生效，建议确认账号是否已购买该内容/有相应权限"，继续用低画质下载
- 选择"跳过" → 直接以公开内容可用的最高画质下载

### cookies.txt（非交互式兜底）

手动导出 cookies.txt 仅在上述方式完全不可用时才考虑，不属于标准交互流程。参考 `--cookies cookies.txt` 参数用法。

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

### 基础命令

```bash
yt-dlp --impersonate chrome \
  --add-header "Origin:https://www.bilibili.com" \
  --add-header "Referer:https://www.bilibili.com" \
  -P "<DOWNLOAD_DIR>" \
  -o "%(title)s.%(ext)s" \
  "<URL>"
```

cookies 按 Cookies 获取引导章节的策略提取。无 cookies 或未登录大会员时，按平台 Cookies 缺失处理流程引导用户登录后重试。

注意 Bilibili 的 AV1 编码格式（format ID 以 100 开头）在某些网络环境下连接超时。如遇超时，换用 AVC/h264 格式（format ID 以 300 开头）即可。

## YouTube 专用处理

### 基础命令

```bash
yt-dlp -P "<DOWNLOAD_DIR>" -o "%(title)s.%(ext)s" "<URL>"
```

cookies 按 Cookies 获取引导章节的策略，从主力浏览器提取（用于处理年龄限制和已购内容）。

### 清晰度处理

见下方清晰度选择策略。

## Vimeo 专用处理

### 基础命令

Vimeo 公开视频无需特殊处理，与通用下载一致：

```bash
yt-dlp -P "<DOWNLOAD_DIR>" -o "%(title)s.%(ext)s" "<URL>"
```

私有/付费视频需要 cookies，按 Cookies 获取引导章节从主力浏览器提取。

### 清晰度处理

见下方清晰度选择策略，与 YouTube 共用逻辑。

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
| `--cookies-from-browser chrome` | 浏览器 cookies |
| `--impersonate chrome` | 浏览器指纹模拟 |
| `--download-sections "*START-END"` | 时间切片（需 ffmpeg） |
| `--write-subs` | 下载字幕 |
| `--sub-lang ai-zh,danmaku` | 指定字幕语言 |
| `--cookies-from-browser chrome` | 浏览器 cookies（标准浏览器用） |
| `--cookies /tmp/cookies.txt` | 使用 cookies.txt（非标准浏览器用 extract_cookies.py 后） |

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
| `--cookies-from-browser chrome` | 浏览器 cookies |
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
| 7 | 将 `--cookies-from-browser` 视为必选项而不检查 | cookies 不可用时命令中断 | 先检查浏览器可用性，无 cookies 时跳过此参数 |
| 8 | 下载高画质不检查账号状态 | 大会员内容下载失败 | 对 >1080p 选项标注需登录，提示用户自行登录 |
| 9 | 用非标准 Chromium 浏览器（Dia）时用 `--cookies-from-browser chromium:` | cookies 解密失败（Keychain 服务名不匹配） | 使用 `extract_cookies.py` 脚本提取 cookies |
| 10 | 不设主力浏览器，每次都猜 cookies 来源 | 反复失败或选了未登录的浏览器 | First Run 时让用户指定主力浏览器并保存偏好 |

## 🔧 失败模式与恢复

| 触发条件 | 一线修复 | 仍失败兜底 |
|---------|---------|-----------|
| `yt-dlp` 返回 HTTP 403/412 | 加 `--impersonate chrome` 再试 | 加 `--add-header Origin` + `--add-header Referer`，仍失败则告知用户需在浏览器手动访问 |
| `yt-dlp` 返回 HTTP 404（Bilibili） | 确认 BV 号是否正确，换一个可用视频测试 | 可能是区域限制，提示用户确认视频可访问 |
| `command -v ffmpeg` 失败（时间切片需要） | 提示 `brew install ffmpeg` | 不用时间切片，引导用户下载完整视频后自行剪辑 |
| `gallery-dl -K` 返回空/报错 | 确认 URL 是否为 ArtStation 项目/画师页格式 | 检查网络，提示用户在浏览器打开确认链接有效 |
| `gallery-dl` 文件名包含非法字符 | gallery-dl 会自动替换，但如果报错改用 `-f "{hash_id}_{num}.{extension}"` | 用 `-f "{num}.{extension}"` 降级 |
| `--cookies-from-browser` 找不到浏览器 | 提示 `--cookies-from-browser firefox/safari` 或完全跳过此参数 | 无 cookies 继续下载，仅影响高画质/年龄限制内容 |
| 格式列表 `-F` 无输出 | 检查 URL 是否可公开访问 | 提示用户确认链接，换 `-f "bv*+ba/b"` 无格式限制下载 |
| 高画质格式被锁定（需登录） | 引导用户在主力浏览器中登录该平台后重试 | 仍失败则提示确认账号是否购买了该内容/有相应权限，用公开可用画质下载 |
| Chromium 非标准浏览器（Dia） `--cookies-from-browser` 解密失败（`AES-CBC` 警告） | 使用 `extract_cookies.py` 脚本指定 `--browser Dia` 提取 | 手动导出 cookies.txt 或跳过 cookies |
| Bilibili 下载 AV1 格式（format ID 100xxx）连接超时（`Connection timed out`） | 换用 AVC/h264 格式（format ID 300xx） | 指定低分辨率格式如 720p 或换第三方工具 |

## 场景示例

```
用户: "下载这个 https://youtu.be/xxx"
→ 列出格式，max=1080p → 自动下载 1080p

用户: "把这个下了 https://youtu.be/xxx 10:30-15:00"
→ 检查 ffmpeg → 时间切片下载

用户: "ArtStation 这个项目 https://www.artstation.com/artwork/Ov6Zwb"
→ gallery-dl → artstation/用户名/项目名_序号.扩展名

用户: "下个B站视频 https://www.bilibili.com/video/BV1GJ411x7"
→ 获取 cookies（标准浏览器用 --cookies-from-browser，非标准 Chromium 用 extract_cookies.py） → 列出格式 → 若高画质锁定则提示登录重试 → 用户确认后重试 → 若>1080p问清晰度 → 下载

用户: "Vimeo 这个视频 https://vimeo.com/xxx"
→ 列出格式 → 若>1080p问清晰度 → 下载（公开视频无需 cookies）

用户: "帮我下载 https://twitter.com/xxx/status/xxx"
→ yt-dlp 通用下载
```

