# Media Downloader

跨平台素材下载工具 — 基于 yt-dlp + gallery-dl + XHS-Downloader + parse-video-py，覆盖 YouTube、Bilibili、Vimeo、ArtStation、小红书、抖音等数百个站点。

自动处理清晰度选择（超过 1080p 询问用户）、时间节点切片下载、ArtStation 项目按用户名组织。首次运行配置下载目录和主力浏览器后即可使用。

在支持 Agent Skills 的 CLI 中，说「下载」+ URL 即可自动调用。

## 快速开始

```
npx skills@latest install https://github.com/zzh-editor/Media-downloader
```

### 基础下载：

```
用户：下载这个 https://youtu.be/xxx
Agent：列出格式 → 自动选择 1080p → 下载到 download_dir
```
### 时间切片

URL 后跟时间范围即可切片下载：

```
URL 10:30-15:00    下载 10:30 到 15:00
URL 10:30          从 10:30 下载到结尾
```

## 支持的平台

| 平台 | 工具 | 说明 |
|------|------|------|
| YouTube / Bilibili / Vimeo / Twitter 等 | yt-dlp | 通用视频下载，支持 cookies |
| ArtStation / Pixiv / DeviantArt | gallery-dl | 图片画廊类下载 |
| 小红书（图文/视频） | XHS-Downloader | 无水印下载，API 或 CLI 模式 |
| 抖音（无水印） | parse-video-py | 解析无水印直链后下载 |

## 工具路由

| URL 特征 | 工具 | 说明 |
|---------|------|------|
| artstation.com / artstation.cn | gallery-dl | 按用户名/项目名组织 |
| bilibili.com / b23.tv | yt-dlp | 需 `--impersonate chrome` |
| youtube.com / youtu.be | yt-dlp | 公开视频无需 cookies |
| vimeo.com | yt-dlp | 私有视频需 cookies |
| xiaohongshu.com / xhslink.com / rednote.com | XHS-Downloader | 启动 API 服务后调用 |
| douyin.com / v.douyin.com | parse-video-py | 获取无水印直链 |
| 其他 | yt-dlp | 通用下载 |

## 首次配置

技能自动读取 `config.json`，按需设置：

**下载目录** — 所有素材统一保存到此目录，可通过 `-P` 临时覆盖。

**主力浏览器** — 用于提取 cookies（Safari / Chrome / Edge / Firefox / Brave / 其他 Chromium 系），非标准 Chromium 浏览器需额外指定配置文件路径。


## 文件结构

```
media-downloader/
├── scripts/              # Cookie 提取等辅助脚本
├── config.json           # 用户偏好（下载目录、浏览器）
├── SKILL.md              # Agent skill 定义
└── README.md
```

## License

[MIT](LICENSE)
