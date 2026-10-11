---
name: video-to-note
description: 把抖音、B站、YouTube、小红书的视频链接转成结构化的知识库笔记。分轻量版（仅 yt-dlp，用平台字幕转写，适合 B站/YouTube）和完全版（需 ffmpeg + whisper.cpp 本地 ASR，全平台可用）。当用户提供视频链接并要求解析、总结、整理笔记、提取文案、转写内容或归档素材时使用；只要视频文件不要笔记、或要批量下载博主主页全部作品时不要用本 skill（直接用 video-downloader-enhanced）。首次使用必须先执行 Step 0，向用户说明两版区别并确认选择。
license: MIT
agent_created: true
compatibility: Light mode needs yt-dlp only (platform subtitles). Full mode additionally needs ffmpeg, whisper.cpp (WHISPER_CPP_BIN / WHISPER_CPP_MODEL env vars) and Python 3.10+. Best with a video-downloader-enhanced skill present.
metadata:
  author: hjz112
  version: "1.3.0"
  repository: https://github.com/hjz112/video-to-note
---

# Video to Note

## Overview

把一条视频链接变成一份可归档的知识笔记。四步：

**规范化链接 → 下载/抓字幕并转写 → 汇总产物 → 生成笔记**

本 skill 分**轻量版**和**完全版**两种模式（见 Step 0）；负责编排流程，
下载和转写交给 `video-downloader-enhanced`，笔记格式由 `references/note-spec.md`
定义。职责分离的理由：下载流程稳定、不该常改；笔记格式高度个人化、会频繁调整。

## 适用边界（何时触发 / 何时不触发）

**触发**：用户给视频链接，并要求总结、做笔记、提取文案、转写、归档素材。

**不触发**，遇到时直接转给 `video-downloader-enhanced`，不要硬套本流程：

- 只要视频文件本身，不需要笔记或总结
- 批量下载某博主主页的全部作品（纯主页链接无 `modal_id` 同理，见 Step 1）
- 输入是音频、图片等非视频内容

## Step 0 — 版本选择（首次使用必做）

本 skill 有两个版本。**首次使用时必须**先跑环境探测，把区别讲给用户听并让用户选择；
选择在本会话内沿用，不必每次重问。

```bash
yt-dlp --version && ffmpeg -version
echo "BIN=$WHISPER_CPP_BIN"; echo "MODEL=$WHISPER_CPP_MODEL"
```

两版区别（原样讲给用户）：

| | 轻量版 | 完全版 |
|---|---|---|
| 依赖 | 仅 yt-dlp | yt-dlp + ffmpeg + whisper.cpp + 本地模型（574MB 起） |
| 转写来源 | 平台自带字幕（CC / 自动字幕） | 本地 whisper.cpp ASR，逐句转写 |
| B站 / YouTube | ✅ 直接抓字幕 | ✅ |
| 抖音 / 小红书 / X | ❌ 平台无字幕可抓，无法转写 | ✅ 全平台可用 |
| 安装成本 | 几分钟，无模型下载 | 需编译/安装 whisper.cpp + 下载模型 |
| 隐私 | 字幕来自平台 | 完全本地，无外部依赖 |

决策规则：

- 全依赖齐 → 展示上表，问用户「用轻量版还是完全版？」；用户没意见时默认完全版。
- 只有 yt-dlp → 告知当前只能跑轻量版（且仅限 B站/YouTube），
  问用户：先用轻量版，还是按「前置依赖」指引安装完全版。
- 链接属于无字幕平台（抖音等）且用户选了轻量版 → 明确说明该平台轻量版转写不了，
  建议升级完全版；不要硬跑。

## 前置依赖（完全版）

完全版需要确认（缺一不可）：

| 依赖 | 检查方式 |
|---|---|
| `video-downloader-enhanced` skill | 目录 `~/.workbuddy/skills/video-downloader-enhanced` 存在 |
| `yt-dlp`、`ffmpeg` 在 PATH | `yt-dlp --version`、`ffmpeg -version` |
| whisper.cpp 已装且环境变量已配 | `WHISPER_CPP_BIN`、`WHISPER_CPP_MODEL` 有值 |

环境变量缺失时，让 `WHISPER_CPP_BIN` 指向 `whisper-cli`，
`WHISPER_CPP_MODEL` 指向一个 ggml 模型文件。模型按部署场景选档：

| 场景 | 推荐模型 | 大小 | 说明 |
|---|---|---|---|
| 桌面 / 笔记本（默认） | `ggml-large-v3-turbo-q5_0.bin` | ~574MB | 速度/质量平衡最好，中文效果好 |
| 服务器 / 批处理 | `ggml-large-v3.bin` | ~3.1GB | 全量 1550M 参数 f16 无损，精度天花板，需 ~3.3GB 显存 |
| 省显存的服务器 | `ggml-large-v3-q5_0.bin` | ~1.1GB | 全参数 5bit 量化 |

模型下载优先级：HuggingFace → HF 镜像（域名换 `hf-mirror.com`）→ ModelScope
（modelscope.cn 搜 "whisper.cpp ggml"）；国内环境 HuggingFace 限速/连不上属常态。
推荐把环境变量持久化，新开终端即生效；当前 shell 里没有时，
在命令前显式 `export` 再跑。

轻量版只需 `yt-dlp` 在 PATH。

缺 `video-downloader-enhanced` skill 时的降级路径：轻量版不受影响（B站/YouTube
仍可用）；完全版优先引导用户安装该 skill（SkillHub 搜 `video-downloader-enhanced`）。
急用时可用下面的最小跑法替代 Step 2（产物缺 metadata 等字段，Step 3 的
collect.py 有容错，可直接跑）：

```bash
yt-dlp -x --audio-format wav -o "<目标目录>/audio.%(ext)s" "<video_url>"
"$WHISPER_CPP_BIN" -m "$WHISPER_CPP_MODEL" -l <语言> \
    -f "<目标目录>/audio.wav" -otxt -of "<目标目录>/transcript"
```

## Step 1 — 规范化链接（两版通用）

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

### 完全版

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

### 轻量版

**先读 [references/light-mode.md](references/light-mode.md)**，其中包含：
字幕抓取命令、B站/YouTube 字幕可用性判据、VTT/SRT 清洗为 `transcript.txt`
的脚本、以及无字幕平台的标准升级提示话术。核心命令：

```bash
yt-dlp --skip-download --write-subs --write-auto-subs \
    --sub-langs "zh.*,en.*" --sub-format "srt/vtt/best" \
    -o "<目标目录>/sub.%(ext)s" "<video_url>"
```

抓到字幕并清洗为 `transcript.txt` 后，直接跳到 Step 3（collect.py 对
缺失 metadata 等字段有容错）。

## Step 3 — 汇总产物（两版通用）

```bash
python scripts/collect.py "<产物目录>" --transcript-chars 6000
```

输出标题、作者、日期、时长、互动数据、标签、文案、转写全文的 JSON。
写笔记前先跑它，避免自己翻 `metadata.json`（字段嵌套深、易漏）。

转写过长时脚本会截断；需要完整内容就把 `--transcript-chars` 调大或设 0。

## Step 4 — 生成笔记（两版通用）

读取 `references/note-spec.md`，按其规定的结构和原则，
在产物目录内写出 `summary.md`。

核心约束（完整版见规范文件）：

- 原视频链接放在标题下方，**不是**文末
- 压缩提炼，禁止整段搬运转写
- ASR 误识别按常识校正，拿不准的保留并标注
- 视频没说的不写，推断要标明
- 结尾给出标签

写完后向用户交付 `summary.md`、转写文本和视频文件（轻量版无视频/音频文件，
交付 `summary.md` 与字幕即可，并注明来源是平台字幕）。

## 扩展场景：多视频 / 超长视频（单条 > 1 小时）批量处理

默认流程（Step 1–4）在遇到「搜一批教程」或「数小时长视频」时会失效：
完整视频数 GB、provider 有 900 秒超时、十几万字转写会撑爆 Agent 上下文。

遇到这类请求时，**先读 [references/long-video.md](references/long-video.md)**，
其中包含：多视频搜索选片（B站 API）、长视频只下音轨 + 直接调 asr.py、
分块 + 并行子代理消化、以及 8 条实测踩坑经验（whisper 复读幻觉、B站字幕判据、
水印音轨识别、HLS 分片丢失补齐等）。

## 故障排查（先重试，再对表）

下载 / 转写遇到网络波动或偶发失败：**先原样重试一次**，仍失败再按下表排查。
向用户报错时，把表中「原因」一列的话术如实转述，不要只丢一句「失败了」。

| 症状 | 原因 | 处理 |
|---|---|---|
| resolve.py 返回 `ok: false` | 链接不是单视频（主页链接 / 已删除 / 非视频） | 按 `note` 字段转述给用户，勿猜 URL |
| yt-dlp 报 403（抖音） | 绕风控插件或浏览器会话失效 | 按 Step 2 要点处理，勿改用 cookie 硬试 |
| B站字幕抓下来为空 | 未登录或该视频确实无字幕 | 按 long-video.md 的字幕可用性判据确认 |
| whisper 输出复读 / 大段乱码 | ASR 幻觉或音轨异常 | 见 long-video.md 踩坑清单（复读幻觉、水印音轨） |
| download_video.py 的 stdout 不是纯 JSON | 前面混入 yt-dlp WARNING 行 | 产物一律走 Step 3 的 collect.py 读目录，勿 json.loads |
| 转写为空但视频正常 | 音轨无有效人声（纯音乐等） | 如实告知用户，不要编造内容 |

## 收尾

- 大文件默认保留，主动询问是否删除，不擅自清理。
- 向用户汇报：视频标题、作者、时长、笔记路径、所用的版本模式，以及核心结论摘要。

## 平台能力边界

| 平台 | 完全版 | 轻量版 |
|---|---|---|
| 抖音 | 可用（需自备绕风控的 yt-dlp 插件/方案） | ❌ 无字幕，无法转写 |
| B站 | 可用 | ✅（字幕需登录态，判据见 long-video.md） |
| YouTube | 可用（可能需代理） | ✅ |
| 小红书 | 已实现但未实测（用法见下方说明） | ❌ 无字幕 |
| 微信视频号 | 不支持。可先用小程序「kg百宝箱」下载，再走本地转写 | ❌ |

边界补充说明：

- **YouTube 需代理**：不是平台不可用。给 yt-dlp 加 `--proxy <代理地址>` 或设置
  `HTTPS_PROXY` 环境变量后重试即可。
- **小红书（完全版）未实测**：首次使用先 `--metadata-only` 试跑验证可行性；
  成功再跑完整流程，失败则如实告知用户「该平台当前不可用」，不要反复重试硬刚。
