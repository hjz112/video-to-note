---
name: video-to-note
description: 把抖音、B站、YouTube、小红书的视频链接转成结构化的知识库笔记。当用户提供视频链接并要求解析、总结、整理笔记、提取文案、转写内容或归档素材时使用。流程为规范化链接、调用 video-downloader-enhanced 下载并转写、汇总产物信息，最后按笔记规范生成 summary.md。
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
python ~/.workbuddy/skills/video-to-note/scripts/resolve.py "<用户给的链接或分享文案>"
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
python ~/.workbuddy/skills/video-to-note/scripts/collect.py "<产物目录>" --transcript-chars 6000
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

## 扩展：多视频 / 超长视频（单条 > 1 小时）批量处理

单条链接的常规流程（Step 1–4）在遇到「搜一批教程」「5 小时以上的全流程」时会失效：
`video-downloader-enhanced` 的 B站 provider 会**下载完整视频**（1080p 的 5.7 小时 ≈ 数 GB，
且 provider 内 `_run_first_successful` 有 900 秒超时），同时十几万字转写稿灌进主上下文会
把 session 拖垮。改用下面这套流程。

### A. 多视频搜索（B站为例）

```bash
# 1) 拿候选 ID（注意：--flat-playlist 下 title/duration 全是 NA，只有 URL 可用）
yt-dlp --flat-playlist --dump-json "bilisearch30:关键词" | ...  # 抽出 av 号

# 2) 用 B站接口补题名/时长/播放（免登录、快、可批量，比逐条 yt-dlp --dump-json 省得多）
curl -s -H "User-Agent: Mozilla/5.0" \
  "https://api.bilibili.com/x/web-interface/view?aid=<aid>"
```

- `bvid=` 参数同样可用；拿到的 `data.stat.view/like` 用来排序选片。
- **不要**用 `--flat-playlist --print`，一样是 NA。
- 判断有无 CC 字幕：`https://api.bilibili.com/x/player/v2?bvid=<bv>&cid=<cid>`，
  看 `data.subtitle.subtitles`。**为空就只能 ASR**（国内教程类视频绝大多数为空）。
- 章节结构：`view` 接口的 `data.view_points` 常有值，但没有时不要硬找。

### B. 长视频只下音频（关键优化）

**先确认有没有现成字幕 —— 有就别跑 ASR。**
**唯一可靠判据：登录态请求 `api.bilibili.com/x/player/v2?bvid=&cid=`（Cookie 带 SESSDATA），
看 `data.subtitle.subtitles` 条数。** 未登录时该接口恒为空，不能下结论。

🔴 **yt-dlp 的 warning 不能当判据**（2026-10-07 实测修正）：`Subtitles are only available
when logged in` 是对未登录状态的**无差别提示**，出现≠该视频真有 CC。实测一条 5.7h 视频
warning 照报，登录后查 player API 仍 0 条（P2 短视频倒有 ai-zh AI 字幕）。
另：**超长视频（数小时级）B站不生成 AI 字幕**，疑似有时长上限。

登录态获取路径（按优先级）：
1. `--cookies-from-browser chrome`：先确认 Chrome **非无痕窗口**登过 —— 无痕 cookie 不落盘，
   「登好了」也可能查无 SESSDATA（实测两次踩坑）；
2. Edge 是 App-Bound 加密，`--cookies-from-browser edge` 报 DPAPI 失败，别试；
3. 兜底：让用户 F12 → Application → Cookies → bilibili.com 手动复制 SESSDATA 值
   （URL-encoded 原样直接拼进 Cookie 头即可用），1 分钟搞定。

确认没有字幕，再走下面这条：

**不要走 provider**，直接用 yt-dlp 抓音轨 + 直接调 `asr.py`：

```bash
PY="<你的 venv python，需要装 requests>"
SKILLS="<skills 目录，如 ~/.workbuddy/skills>"

# 1) 只下音轨（5.7 小时约 270MB，20 秒下完；视频本体则是数 GB）
yt-dlp --no-playlist -f "bestaudio/best" --audio-format m4a -x \
    -o "<dir>/audio_src.%(ext)s" "<url>"
```

```python
# 2) 直接调 run_asr，绕过 provider 的视频下载（run_asr 内部用 ffmpeg 抽 wav，任何媒体文件都能喂）
import sys; sys.path.insert(0, f"{SKILLS}/video-downloader-enhanced/scripts")
from asr import run_asr
run_asr(Path("audio_src.m4a"), Path(out_dir),
        backend="whisper_cpp", language="Chinese",
        prompt="以下是普通话的句子，请使用简体中文输出。")
```

- 产物目录自己定（`<dir>/audio.wav`、`transcript.txt`、`transcript.srt`）。
- **实测速度：whisper.cpp 走 CUDA（large-v3-turbo），约 20 倍实时——
  5.7 小时音频 ≈ 16 分钟**。长视频完全可行，不必回避。
- wav 体积注意：16k 单声道约 1.1 MB/分钟，5.7 小时 ≈ 650MB。

### C. 分块 + 并行子代理消化（保住主上下文）

十几万字转写**绝对不要直接 Read**。按时间窗切块，派子代理并行消化，只回收结论。

```bash
python chunk_srt.py "deep/d1_xxx=1800" "deep/d2_yyy=900"   # 按 SRT 时间戳切，1800s/块
```

- 切块粒度：**每块 1.0–1.3 万字**（≈ 30 分钟），一个子代理吃 2 块（约 2.6 万字）。
- 子代理 prompt 必须固化：① 输出格式（`### HH:MM:SS–HH:MM:SS 主题` + 数值型 bullet）；
  ② **ASR 同音字校正规则表**（按视频领域定制，如军事类：不炮→步炮、自活→自行火炮、
  坦尖→坦歼、银→营、田县师→填线师…）；③ 拿不准标 `(ASR存疑)`、推断标 `(推断)`；
  ④ 字数上限；⑤ **明确禁止写文件，结果直接返回**。
- 多个子代理在同一条消息里并行发（多个 Agent 调用），独立无依赖。
- 便宜的小文件（< 5 千字）自己 Read，不值得派代理。

### D. 必踩的坑

1. **`nohup ... &` 起的后台进程会被会话回收**（部分 agent 沙箱环境）——子进程被 SIGTERM、
   日志 0 字节、`.part` 文件卡住不动。**必须用环境提供的受管后台任务机制**（如
   Bash 工具的 `run_in_background: true`），完成时会收到通知。
2. **转写完成前不要预设产物路径**：whisper 失败时 `transcript.txt` 根本不会出现，
   靠 `ls` 判断状态，别靠猜。
3. **whisper 在长音频上会产生"复读幻觉"**：同一句字幕连续重复几十次，该段真实内容丢失。
   实测一条 54 分钟音频出现三段（14 次 / 53 次 / 6 次重复）。**必须写个检测脚本跑一遍**：
   扫 SRT，统计「连续相同文本 ≥5 次」的段落，在笔记的「存疑与不足」里明确列出
   **时间点 + 丢失了什么信息**。不检测就会把幻觉当成原话写进笔记。
   检测代码很简单：遍历 cue 文本，与上一条相同就累加，≥5 就记录。
   **修法（实测有效）**：把幻觉段单独抽出 16 kHz wav 重转写，加 `-mc 0`（禁跨段上下文）
   + `-bs 5` 束搜索——单加 `-mc 0` 复读即消失，通常是参数问题不是音频问题。
   注意 `--suppress-regex` **封不掉**中文水印词（多字词被拆成单 token，正则按 token 匹配不中）。
4. **转写稿会混入画面文字**：UP主加的字幕署名、视频平台的水印标语（如"某某剧场独家"）
   都会被识别成口播内容。看到与上下文无关的短句先怀疑是 OCR 噪音，别当他说的话。
   🔴 **搬运视频可能整段只有水印音轨**：水印 TTS 循环处 whisper 会连续转出各种水印署名
   （且每次不同）。判据：切多个 10s 采样块全部只出水印 + 视频该段无内嵌硬字幕
   = 该段真的没人说话，别硬抠，如实标注「无口播内容」。
5. **内嵌硬字幕是稀疏的**（实测一条只覆盖约 25% 时间轴），不能当完整字幕，只能当校对。
   定位法：黄字黑描边、位置固定，用黄色像素计数（下采样口径 ≥500 有字幕、噪声 ≤75）
   按连续区间分组、每组取最清晰一帧，拼成带时间戳的对比表再 OCR。
6. **B站 CC 字幕别靠猜**：直接打 `api.bilibili.com/x/player/v2?bvid=&cid=`（带 cookie）看
   `subtitle.subtitles` 条数；yt-dlp 只有 danmaku 不代表查过登录态。
   Cookie 注意：`--cookies-from-browser edge` 会报 DPAPI 解密失败（App-Bound 加密），
   Chrome 可读但要确认真的登了（无 SESSDATA 就是没登）。
7. **元数据别漏抓**：只下音轨的路径（上面的做法 B）不会生成 `metadata.json` /
   `post_caption.txt`。如果要写「基本信息」表格，补一次
   `yt-dlp --dump-single-json --skip-download <url>` 即可，别只填一半。
8. **yt-dlp 断点续传 + 受限沙箱 = 分片丢失**：HLS 下载大量 `.part-FragN` 分片时，
   沙箱的批量删除保护（threshold 触发）可能误删部分分片并杀死合并阶段。
   排查：用 ffprobe 验证合成文件时长 vs 元数据时长；补齐缺失分片可从 m3u8
   （`yt-dlp -g` 获取）按 `frag N ↔ m3u8 第 N 个 URI`（fMP4 时 EXT-X-MAP init 段
   对应 frag 1，frag 0 不需要）手动下载，按序拼接后 ffprobe 复验。

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
