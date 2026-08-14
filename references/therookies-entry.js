// therookies entry 页解析脚本（Playwright MCP / 浏览器 evaluate 中运行）
// 用法：先跑 parse 包装（见文末），对 linkedEntries 再逐个 evaluate 合并视频。
// oEmbed 获取视频真实标题（CORS 可行）。Vimeo 密码保护视频 oEmbed 返回 title:null → "locked"（跳过）。
// 注意：用 evaluate 工具时若压换行，请用本目录的 therookies-entry.min.js（无注释单行版），
// 避免压缩后的行注释吞掉代码。min 版 selfId 默认 "48448"，运行时替换。原版仅作可读性参考。
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

// 成片分类：'main'=成片（优先下载）、'breakdown'=衍生（仅无成片时降级）、'locked'=Vimeo 密码锁定（跳过）、'other'=兜底
// classify(video, workTitle)：workTitle = 主作品 parseEntry 干净标题（页面 h1）。合并来的关联影片视频也用同一 workTitle。
// 衍生词表（contest 561 全 42 作品验证）：覆盖复数/下划线/连字符/驼峰/缩写，全部词边界匹配
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
  if (video.host === 'direct') return 'other';
  const t = (video.title || '').toLowerCase();
  const w = (workTitle || '').toLowerCase();
  if (!t) return 'locked';
  const tn = t.replace(/[^a-z0-9]+/g, ' ').trim().replace(/\b(making[ -]?of|behind[ -]?the[ -]?scenes)\b/g, ' breakdown ');
  for (const word of BREAKDOWN_WORDS) {
    if (new RegExp('(?<![a-z0-9])' + word + '(?![a-z0-9])').test(tn)) return 'breakdown';
  }
  if (/\b(short film|teaser|trailer|official|officielle|bande[ -]annonce|court[ -]m[eé]trage|the movie|full movie|full film|full|movie|film)\b/.test(tn)) return 'main';
  const core = w.replace(/\s*[-–|].+$/, '').replace(/\b(the|a|short film|film|movie|2025|2026)\b/g, '').replace(/[^a-z0-9]+/g, ' ').trim();
  if (core && core.length >= 3 && tn.includes(core)) return 'main';
  return 'other';
}

// 解析单个 entry 页：输入 document.documentElement.outerHTML，selfId = 当前 entry id
function parseEntry(html, selfId) {
  const doc = new DOMParser().parseFromString(html, 'text/html');
  // 标题 = og:title 剥 "The Rookies - " 前缀与尾部 ", by 用户名"（作者若在标题内则保留，勿再剥）
  const og = doc.querySelector('meta[property="og:title"]')?.content || '';
  let title = og.replace(/^The Rookies - /, '');
  let author = '';
  const byM = title.match(/, by (.+)$/);
  if (byM) {
    author = byM[1].split(', by ')[0];                       // 双 by 时只留显示名
    title = title.replace(/, by .+$/, '');
  }
  const avatar = doc.querySelector('.project-header img.avatar-media, .project-content img.avatar-media, main img.avatar-media')?.alt?.trim();
  if (avatar && author.toLowerCase() !== avatar.toLowerCase()) author = avatar;   // 头像 alt 才是显示名
  const videos = []; const images = []; const linkedEntries = [];
  const pc = doc.querySelector('.project-content');
  if (pc) {
    // iframe 前的最近 H3 章节标题（"THE MOVIE"/"THE MAKING-OF"）辅助判断成片
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
    // 原生 <video>（S3 直链 mp4）；保留完整 URL（可能带签名参数）
    for (const v of pc.querySelectorAll(':scope video')) {
      const src = v.currentSrc || v.getAttribute('src') || '';
      if (src) videos.push({ host: 'direct', url: src, section: '', title: null });
      for (const s of v.querySelectorAll('source')) {
        if (s.src) videos.push({ host: 'direct', url: s.src, section: '', title: null });
      }
    }
    // 关联影片帖链接（如 "Click here to see the full movie post"）
    for (const a of pc.querySelectorAll(':scope a[href*="/entries/"]')) {
      const m = a.href.match(/\/entries\/(\d+)/);
      if (m && m[1] !== String(selfId)) {
        linkedEntries.push({ id: m[1], label: (a.innerText || '').trim().slice(0, 60) || a.href });
      }
    }
    // 始终提取 CloudFront 图片，尺寸段换 3840xAUTO 拿原图
    for (const img of pc.querySelectorAll(':scope img')) {
      if (img.src && img.src.includes('cloudfront')) {
        images.push(img.src.replace(/\/([0-9]+)xAUTO\//, '/3840xAUTO/'));
      }
    }
  }
  return { title, author, videos, images, linkedEntries };
}

// 包装：当前 entry 页解析（evaluate 中把 selfId 换成当前 id）
// evaluate 用法：把本文件（或 min 版）全文作为 function 参数传入，
// 工具会自动包成 async () => {...}，文件末尾的 return 即解析结果。
return (async () => {
  const selfId = ""; /* 运行时替换为当前 entry id，如 "48448" */
  const r = parseEntry(document.documentElement.outerHTML, selfId);
  const results = [r];
  return results;
})();