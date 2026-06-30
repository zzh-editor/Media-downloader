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

> 需要 [yt-dlp](https://github.com/yt-dlp/yt-dlp)、[gallery-dl](https://github.com/mikf/gallery-dl)、[ffmpeg](https://github.com/FFmpeg/FFmpeg)，首次运行自动引导安装。

## 下载方式

所有下载任务只用一句话描述需求 + 链接，Agent 自动处理后续。

### 视频下载

```
用户：下载这个视频 https://youtu.be/xxx
Agent：检测到 YouTube 视频
       运行格式探测 → 最大 1080p → 自动下载 1080p
```

```
用户：下载这个视频 https://youtu.be/xxx
Agent：检测到 YouTube 视频
       运行格式探测 → 发现 4K / 2160p 选项
       询问：可选清晰度 1080p / 2160p / 4320p
       用户选择 2160p → 下载 4K
```

```
用户：下载B站这个视频 https://www.bilibili.com/video/BV1JqT56fEGS
Agent：检测到 Bilibili 视频 → 检查 Cookies
       运行格式探测 → 从可用编码中选择 AVC（兼容性最好）
       若该视频需要大会员/登录 → 提示登录后重试
       下载 1080p AVC
```

```
用户：帮我下这个视频 https://vimeo.com/xxx
Agent：检测到 Vimeo 视频 → 公开内容无需 Cookies
       运行格式探测 → 下载最佳清晰度
```

> Bilibili 需要额外参数 `--impersonate chrome` + `--add-header Origin/Referer` 模拟浏览器指纹。大会员内容需要登录态 Cookies。

> 清晰度选择逻辑：Agent 先运行 `yt-dlp -F "URL"` 列出格式，筛选 ≥1080p 的选项；若最大高度 ≤1080p 则自动下载，不做询问。

### 视频时间切片下载

```
用户：把这个下了 https://youtu.be/xxx 1:30-5:00
Agent：检测到时间切片需求 → 检查 ffmpeg
       下载 1:30 到 5:00 的视频片段
```

```
用户：下B站这个 https://www.bilibili.com/video/BVxxx 10:30-15:00
Agent：检测到 Bilibili → 时间切片需求 → 检查 ffmpeg
       下载 10:30 到 15:00 的片段
```

时间范围紧跟在 URL 后面，空格分隔，支持格式：

| 语法 | 含义 |
|------|------|
| `URL 10:30-15:00` | 下载 10:30 到 15:00 |
| `URL 01:20:30-01:45:00` | 含小时的格式 |
| `URL 10:30` | 从 10:30 下载到结尾 |
| `URL 10:30-` | 同上，从 10:30 到结尾 |
| `URL 10:15-15:00 30:00-35:00` | 多区间叠加 |

### 图片下载

gallery-dl 处理图片类平台，ArtStation 最为常用。

**下载单个项目：**

```
用户：下载这个 ArtStation 项目 https://www.artstation.com/artwork/Ov6Zwb
Agent：检测到 ArtStation → 用 gallery-dl
       下载全部文件到 artstation/用户名/项目名_01.png
```

项目内所有文件保存为：

```
下载目录/
└── artstation/
    └── 用户名/
        └── 项目名_01.{ext}
        └── 项目名_02.{ext}
```

**下载画师所有作品：**

```
用户：下载这位画师的所有作品 https://www.artstation.com/artist/xxx
Agent：检测到 ArtStation 画师主页 → 用 gallery-dl
       遍历所有项目 → 按用户名组织目录
```

ArtStation 之外的图片站（如 Pixiv、DeviantArt、Twitter 图片等）同样由 gallery-dl 处理，Agent 自动识别 URL 选择合适工具。

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
                                      ├── 含时间 → 切片下载（需 ffmpeg）
                                      │
                                      └── 无时间 → 完整下载
```

## 核心能力

| 功能 | 说明 |
|------|------|
| 视频下载 | YouTube / Bilibili / Vimeo 等主流视频站，自动选择最佳清晰度 |
| 视频时间切片 | `URL 10:30-15:00` 语法，支持多区间叠加，依赖 ffmpeg |
| 图片下载 | ArtStation 等图库站，支持画师主页与单个项目 |
| 清晰度选择 | 自动探测格式列表，≥1080p 时询问用户偏好 |
| Cookies 获取 | 支持标准浏览器 + 非标准 Chromium（Dia/Brave/Edge 等） |

## Cookies 获取

Agent 按以下优先级获取 Cookies：

1. **标准浏览器**：`--cookies-from-browser chrome` / `firefox` / `safari`
2. **非标准 Chromium**：使用 `scripts/extract_cookies.py` 脚本提取
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

## 支持网站一览

### yt-dlp 视频平台（精选）

| 站点 | URL 识别 |
|------|---------|
| YouTube | `youtube.com` / `youtu.be` |
| Bilibili | `bilibili.com` / `b23.tv` |
| Vimeo | `vimeo.com` |
| Twitter / X | `twitter.com` / `x.com` |
| Instagram | `instagram.com` |
| TikTok | `tiktok.com` |
| Facebook | `facebook.com` |
| Twitch | `twitch.tv` |
| Dailymotion | `dailymotion.com` |
| Niconico | `nicovideo.jp` |
| SoundCloud | `soundcloud.com` |
| Bandcamp | `bandcamp.com` |
| Reddit | `reddit.com` |
| Tumblr | `tumblr.com` |
| 抖音 / Douyin | `douyin.com` |
| 快手 | `kuaishou.com` / `kuaishou.cn` |
| 微博 | `weibo.com` |
| Youku | `youku.com` |
| Pornhub | `pornhub.com` |
| NicoNico | `nicovideo.jp` |

> 完整列表 → [yt-dlp supported sites](https://github.com/yt-dlp/yt-dlp/blob/master/supportedsites.md)

### gallery-dl 图库平台（精选）

| 站点 | URL 识别 |
|------|---------|
| ArtStation | `artstation.com` |
| Pixiv | `pixiv.net` |
| DeviantArt | `deviantart.com` |
| Twitter / X | `twitter.com` / `x.com` |
| Instagram | `instagram.com` |
| Flickr | `flickr.com` |
| 500px | `500px.com` |
| Behance | `behance.net` |
| Dribbble | `dribbble.com` |
| Ko-fi | `ko-fi.com` |
| Patreon | `patreon.com` |
| Pinterest | `pinterest.com` |
| Imgur | `imgur.com` |
| Reddit | `reddit.com` |
| Danbooru | `danbooru.donmai.us` |
| Sankaku | `sankakucomplex.com` |
| Gelbooru | `gelbooru.com` |
| Rule34 | `rule34.xxx` |
| Zerochan | `zerochan.net` |
| Newgrounds | `newgrounds.com` |

> 完整列表 → [gallery-dl supported sites](https://github.com/mikf/gallery-dl/blob/master/docs/supportedsites.md)

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
