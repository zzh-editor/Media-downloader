# Media Downloader

跨平台素材下载工具 — 基于 [yt-dlp](https://github.com/yt-dlp/yt-dlp) + [gallery-dl](https://github.com/mikf/gallery-dl) + [XHS-Downloader](https://github.com/JoeanAmier/XHS-Downloader) + [parse-video-py](https://github.com/wujunwei928/parse-video-py)，覆盖 YouTube、Bilibili、Vimeo、ArtStation、小红书、抖音、TheRookies 等数百个站点。

自动处理清晰度选择（超过 1080p 询问用户）、时间节点切片下载、ArtStation 项目按用户名组织、TheRookies 比赛按作品批量组织。浏览器类操作（Cloudflare 拦截页、登录态提取）通过 [browser-harness](https://github.com/anomalyco/browser-harness) 直连用户真实浏览器，自带登录态、天然过 Cloudflare。

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
| YouTube / Bilibili / Vimeo / Twitter 等 | yt-dlp | 通用视频下载，支持 cookies 登录态 |
| ArtStation / Pixiv / DeviantArt | gallery-dl | 图片画廊类下载 |
| 小红书（图文/视频） | XHS-Downloader | 无水印下载，API 或 CLI 模式 |
| 抖音（无水印） | parse-video-py | 解析无水印直链后下载 |
| TheRookies（比赛结果页） | browser-harness + yt-dlp + curl | 爬取比赛结果，按作品下载视频与 CloudFront 图片 |

## 工具路由

| URL 特征 | 工具 | 说明 |
|---------|------|------|
| artstation.com / artstation.cn | gallery-dl | 按用户名/项目名组织 |
| bilibili.com / b23.tv | yt-dlp | 需 `--impersonate chrome` + Origin/Referer |
| youtube.com / youtu.be | yt-dlp | 公开视频无需 cookies |
| vimeo.com | yt-dlp / JWT 方案 | 被 Turnstile 挡时用 JWT 方案绕开 |
| xiaohongshu.com / xhslink.com / rednote.com | XHS-Downloader | 启动 API 服务后调用 |
| douyin.com / v.douyin.com | parse-video-py | 获取无水印直链 |
| therookies.co/contests / therookies.co/entries | browser-harness + yt-dlp + curl | 爬取比赛结果页或单作品页，DIFF 表格挑选后按作品下载 |
| 其他 | yt-dlp | 通用下载 |

## 首次配置

技能自动读取 `config.json`，按需设置：

**下载目录** — 所有素材统一保存到此目录，可通过 `-P` 临时覆盖。

**cookies 目录** — 存放 cookies 文件。cookies 优先从真实浏览器登录态自动提取（browser-harness CDP 直取），无需手动导出。仅当浏览器未登录目标平台时，使用 **Get cookies.txt LOCALLY** 扩展手动导出兜底。

### 浏览器后端（browser-harness）

浏览器类操作（TheRookies entry 页、Vimeo JWT 提取、cookies 导出）通过 browser-harness 直连用户真实浏览器（Dia / Chrome / Edge），自带登录态、天然过 Cloudflare。首次使用需：

1. 确保浏览器已开启远程调试（Dia 默认 9222，Chrome 需 `--remote-debugging-port=9222`）
2. browser-harness 会自动连接，首次连接时浏览器会弹出 "Allow remote debugging?" 确认，点 Allow 即可

```
browser-harness <<'PY'
print(page_info())
PY
```

### 手动导出 cookies（兜底方案）

部分平台（YouTube 年龄限制、Bilibili 大会员高画质、Vimeo 私有/下载）需要登录态 cookies。若浏览器自动提取失败，可手动导出：

**Chrome / Edge：** 安装 [Get cookies.txt LOCALLY](https://chromewebstore.google.com/detail/get-cookiestxt-locally/cclelndahbckbenkjhflpdbgdldlbecc) → 登录目标平台 → 点击扩展图标 → Export → 保存为 `<cookies_dir>/<平台>.txt`（如 `vimeo.txt`）。

**Firefox：** 安装 [Get cookies.txt LOCALLY](https://addons.mozilla.org/firefox/addon/get-cookies-txt-locally/) → 同上操作。

## TheRookies 比赛下载详解

TheRookies（Rookie Awards）是全球学生 CG 作品竞赛站，一个 **results 页面**收录一场比赛的全部入围作品。下载流程分两层：**先爬取清单，再按清单逐个下载**。

### 页面结构

- `therookies.co/contests/{id}/results` — 比赛结果页，curl 即可获取完整 SSR HTML（无 JS challenge）
- `therookies.co/entries/{id}` — 单个作品页，有 Cloudflare challenge，需 browser-harness 通过真实浏览器访问

### 作品内视频的四种形态

1. **iframe 嵌入**的 YouTube / Vimeo（`youtube.com/embed/{id}`、`player.vimeo.com/video/{id}`）
2. **原生 `<video>` 元素**直链（S3 `rookies-production.s3-accelerate.amazonaws.com` mp4，curl 直下无需 cookies）
3. **关联影片帖链接**（作品页内指向其他 `/entries/{id}` 的链接，跳转后才是完整影片）
4. **纯图片作品**（CloudFront 图片，仅有图片时才提取）

### 爬取流程

```
1. curl 直连 results 页 → 提取比赛名 + 全部 entry 链接
2. 快照浏览器标签页列表 → 逐 entry 用 browser-harness 打开 → js() 解析视频/图片/关联链接
3. 关闭所有临时打开的标签页（不碰用户原有标签）
4. 批量 fetch oEmbed 标题 → classify() 自动分类为 main/breakdown/locked/other
5. 对话中呈现 DIFF 表格交用户挑选
6. 按选择逐作品建目录下载
```

### 成片识别（关键）

一个作品往往混着成片与衍生内容。技能按视频标题自动打标：

- **`main`（成片）**：标题含 `short film` / `teaser` / `trailer` / `official` / `the movie` / `full movie` / 作品名核心词 等
- **`breakdown`（衍生）**：标题含 making of / breakdown / behind the scenes / showcase / progression / turnaround / lookdev / rig / render 等
- **`locked`（密码锁定）**：Vimeo oEmbed 返回无标题 → 需密码，除非作品页给出密码否则跳过
- **`other`**：兜底

**下载优先级**：每个作品只下载 `main`；无成片降级 `breakdown`；无衍生降级 `other`；`locked` 一律跳过。

### DIFF 表格

每作品一行，按 classify 四类分列，图片列标注 CloudFront 图片数：

| # | 作品 | 作者 | 成片(main) | 衍生(breakdown) | 锁定(locked) | 其他(other) | 图片 |
|---|------|------|-----------|----------------|-------------|-------------|------|
| 1 | AZIMUTH Shortfilm | fmichez | Vimeo "AZIMUTH - Sci-Fi Short Film" | 衍生 ×28 | — | — | 图片 ×8 |
| 2 | The Character Dossier | Yanina Perez-Masud | — | — | — | S3 原生视频 ×8 | — |
| 3 | Product Design Portfolio | ... | — | — | — | — | 图片 ×53 |

### 图片最高质量

CloudFront 图片 URL 含尺寸段 `/1400xAUTO/` 等。优先尝试替换为 `/3840xAUTO/` 获取更高分辨率版本。若返回 400（原图分辨率不足 1400），回退到 `/1400xAUTO/`。`2000/4096/5000xAUTO` 均不支持。

### 目录结构

```
{download_dir}/
└── Product & Industrial Design/          ← 比赛名
    ├── CAX/                              ← 纯图片：直接放主目录
    │   └── CAX_01.jpg
    ├── GASP - Care Your Life/            ← 仅视频：直接放主目录
    │   └── GASP - Care Your Life_01.mp4
    └── 混合作品标题/                      ← 视频+图片（用户显式要求时）
        ├── Video/混合作品标题_01.mp4
        └── Images/混合作品标题_01.jpg
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
├── scripts/                     # 辅助脚本
│   ├── check_env.sh             # 环境检查
│   ├── extract_cookies.py       # cookies 提取
│   ├── storage_state_to_netscape.py  # CDP cookie → Netscape 格式转换
│   └── vimeo_jwt_dl.py          # Vimeo JWT 方案下载
├── references/                  # 解析脚本
│   ├── therookies-entry.js      # TheRookies entry 页解析（完整版）
│   └── therookies-entry.min.js  # 无注释版（browser-harness js() 用）
├── evals/                       # 评估测试
├── plugins/                     # CLI 插件
├── config.json                  # 用户偏好（不提交）
├── SKILL.md                     # Agent skill 定义
└── README.md
```

## 致谢

本项目基于以下开源工具构建：

- [yt-dlp](https://github.com/yt-dlp/yt-dlp) — 通用视频下载
- [gallery-dl](https://github.com/mikf/gallery-dl) — 图片画廊下载
- [XHS-Downloader](https://github.com/JoeanAmier/XHS-Downloader) — 小红书无水印下载
- [parse-video-py](https://github.com/wujunwei928/parse-video-py) — 多平台无水印视频解析
- [browser-harness](https://github.com/anomalyco/browser-harness) — 浏览器自动化后端

## License

[MIT](LICENSE)