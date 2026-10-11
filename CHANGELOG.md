# 更新日志

所有显著变更记录在本文件。格式参考 [Keep a Changelog](https://keepachangelog.com/zh-CN/1.1.0/)。

## [1.3.0] - 2026-10-11

基于 SkillHub TRACE 评估（4.6/5）针对性改进：

- **触发边界明确化**：frontmatter description 增加不触发场景说明（只要文件不要笔记 / 批量主页下载 → 转用 video-downloader-enhanced）
- **新增「适用边界」章节**：何时触发 / 何时不触发，一页说清
- **降低开箱门槛**：前置依赖新增降级路径 —— 缺 download skill 时用最小 yt-dlp + whisper-cli 组合也能跑（collect.py 已有容错）
- **新增「故障排查」章节**：6 行症状速查表 + 先重试再对表的规范
- **平台能力边界补充**：YouTube 代理具体做法（`--proxy` / `HTTPS_PROXY`）、小红书未实测的验证方法（`--metadata-only` 试跑）

## [1.2.0] - 2026-10-09

- **轻量版 / 完全版双模式**：安装后首次使用时 Agent 主动展示对比表并询问选择
  - 轻量版：仅 yt-dlp，抓平台自带字幕，几分钟开箱即用
  - 完全版：yt-dlp + ffmpeg + whisper.cpp 本地 ASR，全平台可用
- **新增 Step 0 依赖自检**：首次使用必须先执行，自动探测缺失依赖并给出安装指引
- **长视频指南拆分**至 `references/long-video.md`（按需加载，缩短主文档上下文开销）

## [1.1.0] - 2026-10

- 符合 Agent Skills 规范的 frontmatter（license / compatibility / metadata）
- 长视频扩展流程与踩坑经验文档化
- 模型下载增加 HF 镜像与 ModelScope 回退（大陆用户友好）
- 新增 Codex CLI 适配（`adapters/codex-prompt.md`）
- 一键安装：`npx skills add hjz112/video-to-note`
