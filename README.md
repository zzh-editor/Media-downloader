# Media Downloader

跨平台素材下载工具 — 基于 yt-dlp + gallery-dl + XHS-Downloader + parse-video-py，覆盖 YouTube、Bilibili、Vimeo、ArtStation、小红书、抖音、TheRookies 等数百个站点。

自动处理清晰度选择（超过 1080p 询问用户）、时间节点切片下载、ArtStation 项目按用户名组织、TheRookies 比赛按作品批量组织。首次运行配置下载目录和 cookies 目录后即可使用。

在支持 Agent Skills 的 CLI 中，说「下载」+ URL 即可自动调用。

## 快速开始

```
npx skills@latest install https://github.com/zzh-editor/Media-downloader
```

基础下载：

```
用户：下载这个 https://youtu.be/xxx
Agent：列出格式 → 自动选择 1080p → 下载到 download_dir
```

## 支持的平台

| 平台 | 工具 | 说明 |
|------|------|------|
| YouTube / Bilibili / Vimeo / Twitter 等 | yt-dlp | 通用视频下载，支持用户上传 cookies |
| ArtStation / Pixiv / DeviantArt | gallery-dl | 图片画廊类下载 |
| 小红书（图文/视频） | XHS-Downloader | 无水印下载，API 或 CLI 模式 |
| 抖音（无水印） | parse-video-py | 解析无水印直链后下载 |
| TheRookies（比赛结果页） | BrowserClaw + yt-dlp + curl | 爬取比赛结果，按作品下载视频与 CloudFront 图片 |

## 工具路由

| URL 特征 | 工具 | 说明 |
|---------|------|------|
| artstation.com / artstation.cn | gallery-dl | 按用户名/项目名组织 |
| bilibili.com / b23.tv | yt-dlp | 需 `--impersonate chrome` |
| youtube.com / youtu.be | yt-dlp | 公开视频无需 cookies |
| vimeo.com | yt-dlp | 需登录 + `--extractor-args "vimeo:client=web"`，未登录提示登录 |
| xiaohongshu.com / xhslink.com / rednote.com | XHS-Downloader | 启动 API 服务后调用 |
| douyin.com / v.douyin.com | parse-video-py | 获取无水印直链 |
| therookies.co/contests / therookies.co/entries | BrowserClaw + yt-dlp + curl | 爬取比赛结果页或单作品页，DIFF 表格挑选后按作品下载 |
| 其他 | yt-dlp | 通用下载 |

## 首次配置

技能自动读取 `config.json`，按需设置：

**下载目录** — 所有素材统一保存到此目录，可通过 `-P` 临时覆盖。

**cookies 目录** — 存放用户上传的 cookies 文件。用 **Get cookies.txt LOCALLY** 扩展在各平台导出 cookies，保存为 `<cookies_dir>/<平台>.txt`（如 `youtube.txt`、`bilibili.txt`、`vimeo.txt`）。仅下载失效或高画质锁定时提示更新。

### 安装 Get cookies.txt LOCALLY 扩展

部分平台（YouTube 年龄限制、Bilibili 大会员高画质、Vimeo 私有/下载）需要登录态 cookies。cookies 不再自动从浏览器提取，改由用户用浏览器扩展手动导出。

**Chrome / Edge（及 Chromium 系）：**

1. 打开 [Chrome 应用商店 Get cookies.txt LOCALLY](https://chromewebstore.google.com/detail/get-cookiestxt-locally/cclelndahbckbenkjhflpdbgdldlbecc)（Edge 用户可在 Edge 加载项中搜索同名扩展）
2. 点击「添加至 Chrome」→ 安装完成后，工具栏出现绿底白锁图标

**Firefox：**

1. 打开 [Firefox Add-ons 的 Get cookies.txt LOCALLY](https://addons.mozilla.org/firefox/addon/get-cookies-txt-locally/)
2. 点击「添加到 Firefox」→ 安装完成后，工具栏出现绿底白锁图标

### 导出 cookies 并上传

```
1. 用浏览器登录目标平台（如 vimeo.com、bilibili.com）
2. 点击工具栏的 Get cookies.txt LOCALLY 图标
3. 点击页面中的 Export 按钮 → 下载到 cookies.txt
4. 将 cookies.txt 重命名为 <平台>.txt（如 vimeo.txt），放到 config.json 的 cookies_dir 目录
```

导出后 cookies 文件长期保留本地复用；仅当下载失效或高画质锁定时重新导出覆盖。

## TheRookies 比赛下载详解

TheRookies（Rookie Awards）是全球学生 CG 作品竞赛站，一场比赛的所有入围作品集中在一个 **results 页面**。下载流程分两层：**先爬取清单，再按清单逐个下载**。

### 页面结构

- `therookies.co/contests/{id}/results` — 比赛结果页，收录全部入围作品，每作品一个 `h3` 标题 + 链接
- `therookies.co/entries/{id}` — 单个作品页

### 作品内视频的四种形态

1. **iframe 嵌入**的 YouTube / Vimeo（`youtube.com/embed/{id}`、`player.vimeo.com/video/{id}`）
2. **原生 `<video>` 元素**直链（S3 `rookies-production.s3-accelerate.amazonaws.com` mp4，curl 直下无需 cookies）
3. **关联影片帖链接**（作品页内指向其他 `/entries/{id}` 的链接，跳转后才是完整影片，如 "Click here to see the full movie post"）
4. **纯图片作品**（CloudFront 图片，仅有图片时才提取）

### 爬取流程

```
1. 用 BrowserClaw 打开 results 页面（网站有 JS challenge，curl 直接抓只返回拦截页，必须走浏览器）
2. 在页面 evaluate 中提取比赛名 + 全部 entry 链接
3. 页内 fetch 批量抓取每个 entry 的 HTML，解析资源清单
4. 用 oEmbed 补每条视频真实标题，classify 自动分类成片/衍生/密码锁定
5. 对话中呈现 DIFF 表格交用户挑选
6. 按选择逐作品建目录下载
```

### 成片识别（关键）

一个作品往往混着成片与衍生内容（如 AZIMUTH 的 Vimeo 成片 + 28 个 YouTube making-of；SALAMANDER 的 YouTube Teaser 成片 + 密码锁定的 Vimeo + 多个 Showcase）。技能按视频标题自动打标：

- **`main`（成片）**：标题含 `short film` / `teaser` / `trailer` / `official` / `the movie` / `full movie` / 作品名核心词 等
- **`breakdown`（衍生）**：标题含 making of / breakdown / behind the scenes / showcase / progression / turnaround / lookdev / rig / character / render 等
- **`locked`（密码锁定）**：Vimeo oEmbed 返回无标题 → 需密码，除非作品页给出密码否则跳过

**下载优先级**：每个作品只下载 `main`；仅当无成片时才降级下载 `breakdown`；`locked` 一律跳过。

### DIFF 表格

每作品一行，成片单独标注，衍生与密码锁定合并为"衍生"列，纯图片作品列图片数：

| # | 作品 | 作者 | 成片 | 衍生（含密码锁定） |
|---|------|------|------|------|
| 1 | AZIMUTH Shortfilm | fmichez | Vimeo "AZIMUTH - Sci-Fi Short Film" | 衍生 ×28（making-of/breakdown） |
| 2 | The Character Dossier | Yanina Perez-Masud | 无成片（降级） | 原生视频 ×8（S3 mp4） |

### 图片最高质量技巧

CloudFront 图片 URL 含尺寸段 `/1400xAUTO/`、`/800xAUTO/` 等。把 `/{数字}xAUTO/` 替换为 `/3840xAUTO/` 即得原图（3840 是上限，更大尺寸段返回 400）。

### 目录结构

```
{download_dir}/
└── Rookie of the Year - 3D Animation/      ← 比赛名
    └── {作品标题} by {作者}/                ← 每作品一个文件夹
        ├── Video/                          ← 视频（成片优先）
        │   └── {作品标题}_01.mp4
        └── Images/                         ← 纯图片作品
            └── {作品标题}_01.jpg
```

## 时间切片

URL 后跟时间范围即可切片下载：

```
URL 10:30-15:00    下载 10:30 到 15:00
URL 10:30          从 10:30 下载到结尾
```

## 文件结构

```
media-downloader/
├── scripts/              # 环境检查等辅助脚本
├── cookies/              # 用户上传的各平台 cookies 文件
├── config.json           # 用户偏好（下载目录、cookies 目录、更新间隔）
├── SKILL.md              # Agent skill 定义
└── README.md
```

## License

[MIT](LICENSE)
