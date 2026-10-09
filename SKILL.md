---
name: video-to-note
description: 把抖音、B站、YouTube、小红书的视频链接转成结构化的知识库笔记。当用户提供视频链接并要求解析、总结、整理笔记、提取文案、转写内容或归档素材时使用。流程为规范化链接、调用 video-downloader-enhanced 下载并转写、汇总产物信息，最后按笔记规范生成 summary.md。
license: MIT
compatibility: Requires yt-dlp, ffmpeg, whisper.cpp (WHISPER_CPP_BIN / WHISPER_CPP_MODEL env vars) and Python 3.10+. Best with a video-downloader-enhanced skill present.
metadata:
  author: hjz112
  version: "1.1.0"
  repository: https://github.com/hjz112/video-to-note
---

# Video to Note

## Overview

把一条视频链接变成一份可归档的知识笔记。四步：

**规范化链接 → 下载并转写 → 汇总产物 → 生成笔记**

本 skill 负责编排流程；下载和转写交给 `video-downloader-enhanced`，
笔记格式由 `references/note-spec.md` 定义。职责分离的理由：
下载流程稳定、不该常改；笔记格式高度个人化、会频繁调整。

## 前置依赖

使用前确认本机已具备（缺一不可）：

| 依赖 | 检查方式 |
|---|---|
| `video-downloader-enhanced` skill | 目录 `~/.workbuddy/skills/video-downloader-enhanced` 存在 |
| `yt-dlp`、`ffmpeg` 在 PATH | `yt-dlp --version`、`ffmpeg -version` |
| whisper.cpp 已装且环境变量已配 | `WHISPER_CPP_BIN`、`WHISPER_CPP_MODEL` 有值 |

环境变量缺失时，让 `WHISPER_CPP_BIN` 指向 `whisper-cli`，
`WHISPER_CPP_MODEL` 指向一个 ggml 模型文件（如 `ggml-large-v3-turbo-q5_0.bin`）。
推荐把这两个环境变量持久化，新开终端即生效；当前 shell 里没有时，
在命令前显式 `export` 再跑。

## Step 1 — 规范化链接

```bash
# 路径相对 skill 根目录（即本 SKILL.md 所在目录）
python scripts/resolve.py "<用户给的链接或分享文案>"
```

脚本处理三种情形：抖音主页链接带 `modal_id`（取该视频）、
短链展开、整段分享文案抽链接。

拿到 `ok: true` 后用返回的 `video_url` 进入下一步。
`ok: false` 时把 `note` 字段的原因如实转述给用户，不要猜测硬编 URL。

**注意**：纯主页地址且无 `modal_id` 时本 skill 无法处理，
此时建议改用 `dy` 命令批量下载该博主作品。

## Step 2 — 下载并转写

```bash
cd ~/.workbuddy/skills/video-downloader-enhanced/scripts
python download_video.py "<规范化后的 video_url>" \
    --output-dir "<目标目录>" \
    --asr whisper_cpp \
    --asr-language <Chinese|English|auto>
```

要点：

- 语言按视频实际内容选；中文视频务必用 `Chinese`。
- 输出目录按你的 yt-dlp 配置（`-P`）保持一致；用户指定了目录就尊重其选择。
- 该命令产出：视频文件、`audio.wav`、`transcript.txt`、
  `transcript.srt`、`post_caption.txt`、`metadata.json`。
- 想跳过 ASR 加 `--asr none`；只要文案加 `--metadata-only`。
- 抖音风控：本工作流使用自定义 yt-dlp 插件（真实浏览器会话）绕过。
  若报 403，说明插件或浏览器会话异常，不要改用浏览器 cookie 硬试。
  （没有该插件的环境需自行解决抖音风控，其它平台不受影响。）
- **不要直接 `json.loads` 该命令的 stdout** —— 前面可能混入 yt-dlp 的
  WARNING 等非 JSON 行。产物信息一律走 Step 3 的 `collect.py` 读目录。
- 目录名由 skill 自动生成，形如 `YY_MM_DD_标题_平台_作者`；
  重名时追加视频 ID 后缀，所以不要预设固定路径，先跑再看。

## Step 3 — 汇总产物

```bash
python scripts/collect.py "<产物目录>" --transcript-chars 6000
```

输出标题、作者、日期、时长、互动数据、标签、文案、转写全文的 JSON。
写笔记前先跑它，避免自己翻 `metadata.json`（字段嵌套深、易漏）。

转写过长时脚本会截断；需要完整内容就把 `--transcript-chars` 调大或设 0。

## Step 4 — 生成笔记

读取 `references/note-spec.md`，按其规定的结构和原则，
在产物目录内写出 `summary.md`。

核心约束（完整版见规范文件）：

- 原视频链接放在标题下方，**不是**文末
- 压缩提炼，禁止整段搬运转写
- ASR 误识别按常识校正，拿不准的保留并标注
- 视频没说的不写，推断要标明
- 结尾给出标签

写完后向用户交付 `summary.md`、转写文本和视频文件。

## 扩展场景：多视频 / 超长视频（单条 > 1 小时）批量处理

默认流程（Step 1–4）在遇到「搜一批教程」或「数小时长视频」时会失效：
完整视频数 GB、provider 有 900 秒超时、十几万字转写会撑爆 Agent 上下文。

遇到这类请求时，**先读 [references/long-video.md](references/long-video.md)**，
其中包含：多视频搜索选片（B站 API）、长视频只下音轨 + 直接调 asr.py、
分块 + 并行子代理消化、以及 8 条实测踩坑经验（whisper 复读幻觉、B站字幕判据、
水印音轨识别、HLS 分片丢失补齐等）。

## 收尾

- 大文件默认保留，主动询问是否删除，不擅自清理。
- 向用户汇报：视频标题、作者、时长、笔记路径，以及核心结论摘要。

## 平台能力边界

| 平台 | 状态 |
|---|---|
| 抖音 | 可用（需自备绕风控的 yt-dlp 插件/方案） |
| B站 | 可用 |
| YouTube、小红书 | 已实现但未实测，可能需代理或登录 |
| 微信视频号 | 不支持。可先用小程序「kg百宝箱」下载，再走本地转写 |
