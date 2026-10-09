# 视频转笔记任务（video-to-note）

用户输入：$ARGUMENTS

你现在要执行「视频链接 → 知识笔记」的完整流水线。输入 `$ARGUMENTS` 是视频链接，
或一整段包含链接的分享文案。如果 `$ARGUMENTS` 为空，向用户索要链接后再继续。

## 前置检查与版本选择（首次必做）

1. `yt-dlp --version` 可执行？（轻量版/完全版都需要）
2. `ffmpeg -version` 可执行，且环境变量 `WHISPER_CPP_BIN`（whisper-cli 路径）、
   `WHISPER_CPP_MODEL`（ggml 模型）已配置？（仅完全版需要）
3. **首次使用时必须向用户说明两版区别并让其选择**（本会话内沿用，不必每次重问）：
   - 轻量版：仅 yt-dlp，用平台字幕转写（B站/YouTube 可用；抖音/小红书/X 无字幕，不可用）
   - 完全版：+ ffmpeg + whisper.cpp 本地 ASR，全平台可用
   - 全依赖齐 → 问用户选哪个，未表态默认完全版；只有 yt-dlp → 告知只能跑轻量版
     并问是否先装完全版；链接属无字幕平台且选轻量版 → 说明后建议升级，不要硬跑
4. 若存在 `~/.workbuddy/skills/video-downloader-enhanced/scripts/download_video.py`
   且选了完全版则走完整流程；否则按下方「手动替代流程」执行
5. 轻量版的字幕抓取与清洗流程见本仓库 `references/light-mode.md`

## 流程

### Step 1 — 规范化链接

```bash
python <本仓库路径>/scripts/resolve.py "<用户输入>"
```

返回 JSON：`ok:true` 时用 `video_url` 继续；`ok:false` 时把 `note` 原因如实转述给用户，
**不要猜测硬编 URL**。

### Step 2 — 下载并转写

**有 video-downloader-enhanced 时**：

```bash
cd ~/.workbuddy/skills/video-downloader-enhanced/scripts
python download_video.py "<video_url>" --output-dir "<目标目录>" --asr whisper_cpp --asr-language Chinese
```

**手动替代流程**（无该 skill 时）：

```bash
yt-dlp --no-playlist -f "bestaudio/best" -x --audio-format m4a -o "<目录>/audio_src.%(ext)s" "<video_url>"
ffmpeg -i "<目录>/audio_src.m4a" -ar 16000 -ac 1 "<目录>/audio.wav"
"$WHISPER_CPP_BIN" -m "$WHISPER_CPP_MODEL" -f "<目录>/audio.wav" -l zh -osrt -otxt \
    -of "<目录>/transcript" --prompt "以下是普通话的句子，请使用简体中文输出。"
```

规则：

- 中文视频语言务必用 `Chinese` / `-l zh`
- 视频时长 > 1 小时：**不要下载完整视频**，只下音轨（见上面手动替代流程，它天然只下音轨）
- 不要预设产物路径，转写是否成功用 `ls` 判断
- 不要直接 `json.loads` 命令 stdout（可能混入 WARNING 行）

### Step 3 — 汇总产物

```bash
python <本仓库路径>/scripts/collect.py "<产物目录>" --transcript-chars 6000
```

得到标题/作者/时长/互动数据/文案/转写全文的 JSON，作为写笔记的素材。

### Step 4 — 生成笔记

按本仓库 `references/note-spec.md` 的结构写 `<产物目录>/summary.md`：

- 结构：标题 → 原视频链接（**标题下方，不是文末**）→ 基本信息表 → 一句话总结 → 核心内容 → 存疑与不足 → 标签
- 压缩提炼，禁止整段搬运转写
- ASR 误识别按常识校正，拿不准的保留并标 `(ASR存疑)`；推断标 `(推断)`
- 视频没说的不写；专有名词/英文缩写保留原名

### 转写稿超长时（> 3 万字）

不要把全文读进上下文。先跑复读幻觉检测（扫 SRT，连续相同文本 ≥5 次即记录时间点），
然后按时间窗把转写切块（每块 1–1.3 万字），每块单独总结后合并。
子代理 prompt 必须包含：输出格式（`### HH:MM:SS–HH:MM:SS 主题` + bullet）、
ASR 校正标注规则、字数上限、禁止写文件直接返回结果。

### 收尾

- 汇报：视频标题、作者、时长、summary.md 路径、核心结论摘要
- 大文件默认保留，询问用户是否删除，不擅自清理
