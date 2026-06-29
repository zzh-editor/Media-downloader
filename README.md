# Media Downloader

跨平台素材下载 Agent Skill — 基于 [yt-dlp](https://github.com/yt-dlp/yt-dlp) + [gallery-dl](https://github.com/mikf/gallery-dl)，覆盖 YouTube、Bilibili、Vimeo、ArtStation 等数百个站点。

## 触发词

在支持 Agent Skills 的 CLI（OpenCode、Claude Code、Cursor 等）中，以下场景自动调用：

```
下载这个视频 / 把这个下了 / 帮我下这个
下载链接 / 保存这个视频 / 下载 B 站
下这个 youtube / ArtStation 下载 / 把这个项目下了
下个视频 / 帮我下个东西
```

输入 URL 后 Agent 自动检测站点，选择合适工具，处理清晰度、Cookies、时间切片等需求。

## 安装

### OpenCode / Claude Code / Cursor 等

```bash
# 安装（自动注册到 skills 列表）
npx skills@latest install https://github.com/zzh-editor/Media-downloader

# 更新
npx skills@latest update https://github.com/zzh-editor/Media-downloader

# 查看已安装的 skills
npx skills@latest list
```

### 直接克隆（开发者）

```bash
git clone https://github.com/zzh-editor/Media-downloader.git
cd Media-downloader
```

> 需要 [yt-dlp](https://github.com/yt-dlp/yt-dlp)、[gallery-dl](https://github.com/mikf/gallery-dl)、[ffmpeg](https://github.com/FFmpeg/FFmpeg)，首次运行自动引导安装。

## 工作流程

```
用户发送链接
      │
      ▼
Agent 检测站点类型
      │
      ├── ArtStation ─────────────────→ gallery-dl 下载
      │
      ├── Bilibili / b23.tv ─────────→ yt-dlp（--impersonate chrome + cookies）
      │                                      │
      │                                      ▼
      │                              问字幕/弹幕选项 → 列出格式
      │                                      │
      │                                      ▼
      │                              若 >1080p → 问清晰度选择
      │
      ├── YouTube ───────────────────→ yt-dlp（cookies + 清晰度选择）
      │
      ├── Vimeo ─────────────────────→ yt-dlp 通用
      │
      └── 其他 ─────────────────────→ yt-dlp 通用
                                           │
                                           ▼
                                   检查 URL 是否含时间范围
                                           │
                                      ├── 含时间 → --download-sections 切片
                                      │
                                      └── 无时间 → 完整下载
```

## 核心能力

| 功能 | 说明 |
|------|------|
| YouTube 下载 | 清晰度选择（1080p / 4K / 8K）、时间切片、cookies 处理年龄限制 |
| Bilibili 下载 | 大会员/高画质解锁、AI 字幕下载、弹幕下载、AV1/HEVC/AVC 格式策略 |
| Vimeo 下载 | 公开视频无需特殊处理，cookies 支持未登录可下载 |
| ArtStation 下载 | gallery-dl 专用，按用户名/项目名自动组织文件结构 |
| 时间切片 | `URL HH:MM-SS` 语法，支持多区间叠加，依赖 ffmpeg |
| 清晰度选择 | 自动探测格式列表，≥1080p 时询问用户偏好 |
| Cookies 获取 | 支持标准浏览器 + 非标准 Chromium（Dia/Brave/Edge 等） |

## YouTube 下载

### 基础下载

```bash
yt-dlp --cookies-from-browser chrome -P "下载目录" -o "%(title)s.%(ext)s" "URL"
```

### 清晰度选择

Agent 自动运行 `yt-dlp -F "URL"` 列出格式，筛选 ≥1080p 的选项供用户选择：

| 选择 | 参数 |
|------|------|
| 1080p | `-S "res:1080"` |
| 4K / 2160p | `-S "res:2160"` |
| 8K / 4320p | `-S "res:4320"` |

若最大高度 ≤ 1080p，自动下载无需询问。

### 时间切片

```bash
# 下载 10:30 到 15:00
yt-dlp --download-sections "*10:30-15:00" "URL"

# 多区间叠加
yt-dlp --download-sections "*10:15-15:00" --download-sections "*30:00-35:00" "URL"

# 从 10:30 到结尾
yt-dlp --download-sections "*10:30-" "URL"
```

> 时间切片依赖 ffmpeg，会先检查 `command -v ffmpeg`。

## Bilibili 下载

### 基础命令

```bash
yt-dlp --impersonate chrome \
  --add-header "Origin:https://www.bilibili.com" \
  --add-header "Referer:https://www.bilibili.com" \
  --cookies-from-browser chrome \
  -P "下载目录" -o "%(title)s.%(ext)s" "URL"
```

### 清晰度策略

Bilibili 提供多种编码格式，优先级策略：

| 编码 | 格式代码 | 特点 | 适用场景 |
|------|---------|------|---------|
| AVC / H.264 | 30080+ | 兼容性最好 | 默认推荐 |
| HEVC / H.265 | 30064+ | 体积更小 | 画质敏感 |
| AV1 | 100026+ | 压缩率最高 | 网络差时可能超时 |

Agent 自动从 `-F` 输出解析可用格式，若 AV1 下载超时则自动回退到 AVC。

### 字幕 / 弹幕

| 选项 | 参数 |
|------|------|
| AI 字幕（中文） | `--write-subs --sub-lang ai-zh` |
| 弹幕 | `--write-subs --sub-lang danmaku` |

### Cookies 注意事项

Bilibili 大会员内容需要登录态。Agent 优先使用主力浏览器 Cookies，若缺失则引导用户在 Bilibili 登录后重试。

## Vimeo 下载

Vimeo 公开视频可直接下载，无需特殊处理：

```bash
yt-dlp -P "下载目录" -o "%(title)s.%(ext)s" "URL"
```

需要提取特定编码的视频时，同样使用 `-F` 列表 + `-S "res:X"` 清晰度策略。非公开 / 已购 Vimeo 内容需要 Cookies。

## ArtStation 下载

gallery-dl 专用，不支持 yt-dlp。

```bash
gallery-dl -d "下载目录" -f "{title}_{num:02d}.{extension}" "URL"
```

### 文件结构

默认目录模板 `{category}/{user[username]}/`，下载后结构为：

```
下载目录/
└── artstation/
    └── 用户名/
        └── 项目名_01.{ext}
        └── 项目名_02.{ext}
```

### 自定义字段

可用 `gallery-dl -K "URL"` 查看所有元数据字段。支持嵌套字段语法 `{dict[key]}`。

## Cookies 获取

Agent 按以下优先级获取 Cookies：

1. **标准浏览器**：`--cookies-from-browser chrome` / `firefox` / `safari`
2. **非标准 Chromium**：使用 `extract_cookies.py` 脚本提取
3. **无 Cookies**：跳过，影响高画质 / 年龄限制内容

### 支持的 Chromium 系浏览器

| 浏览器 | --cookies-from-browser 参数 | extract_cookies.py |
|--------|---------------------------|-------------------|
| Google Chrome | `chrome` | ✅ |
| Microsoft Edge | `edge` / `chromium` | ✅ |
| Brave | `brave` | ✅ |
| Dia | ❌ 无法直接支持 | ✅ |
| Chromium | `chromium` | ✅ |
| Vivaldi | `chromium` | ✅ |
| Opera | `chromium` | ✅ |

## 通用参数参考

### yt-dlp

| 参数 | 用途 |
|------|------|
| `-P <dir>` / `--paths <dir>` | 下载目录 |
| `-o "<template>"` | 输出文件名（`%(var)s` 语法） |
| `-S "res:1080"` | 限制并排序分辨率 |
| `-f "bv*+ba/b"` | 最佳视频 + 最佳音频 |
| `-F` | 列出格式 |
| `--cookies-from-browser chrome` | 浏览器 Cookies |
| `--impersonate chrome` | 浏览器指纹模拟（Bilibili 必需） |
| `--download-sections "*START-END"` | 时间切片（需 ffmpeg） |
| `--write-subs` | 下载字幕 |
| `--sub-lang ai-zh,danmaku` | 指定字幕语言 |

### gallery-dl

| 参数 | 用途 |
|------|------|
| `-d <dir>` / `--destination <dir>` | 下载目录（基础路径） |
| `-f "<template>"` | 文件名模板（`{var}` 语法） |
| `-K` / `--list-keywords` | 列出可用元数据字段 |
| `--cookies-from-browser chrome` | 浏览器 Cookies |

## 文件结构

```
Media-downloader/
├── scripts/
│   ├── check_env.sh           # 环境检查脚本
│   └── extract_cookies.py     # 非标准 Chromium cookie 提取
├── evals/                     # 评估数据
├── SKILL.md                   # Agent skill 定义（完整工作流）
├── test-prompts.json          # 测试用例
└── README.md
```

## 致谢

本技能核心依赖以下开源工具：

- [yt-dlp](https://github.com/yt-dlp/yt-dlp) — 视频下载核心引擎
- [gallery-dl](https://github.com/mikf/gallery-dl) — 图库下载引擎
- [FFmpeg](https://github.com/FFmpeg/FFmpeg) — 音视频处理与时间切片
- [curl_cffi](https://github.com/yifeikong/curl_cffi) — 浏览器指纹模拟（Bilibili 必需）

## License

[MIT](LICENSE)
