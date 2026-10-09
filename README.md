# video-to-note

把一条视频链接变成一份可归档的知识笔记 —— 为 AI Agent 设计的 Skill，兼容 **WorkBuddy / Claude Code / Codex CLI**。

```
规范化链接 → 下载/抓字幕并转写 → 汇总产物 → 生成 summary.md
```

## 两个版本：轻量版 vs 完全版

本 skill 内置两种模式。**安装后首次使用时，Agent 会主动展示下表并询问你选哪个**（选择在会话内沿用）：

| | 轻量版 | 完全版 |
|---|---|---|
| 依赖 | 仅 yt-dlp | yt-dlp + ffmpeg + whisper.cpp + 本地模型（574MB 起） |
| 转写来源 | 平台自带字幕（CC / 自动字幕） | 本地 whisper.cpp ASR，逐句转写 |
| B站 / YouTube | ✅ | ✅ |
| 抖音 / 小红书 / X | ❌ 平台无字幕，无法转写 | ✅ 全平台 |
| 安装成本 | 几分钟，无模型下载 | 需安装 whisper.cpp + 下载模型 |
| 适用建议 | 快速出稿、无 GPU、隐私敏感度低 | 播客/长视频/无字幕平台/高质量归档 |

选定后 Agent 按对应流程执行：轻量版见 [references/light-mode.md](references/light-mode.md)，完全版见 SKILL.md Step 2。

## 它解决什么问题

把「丢给我一个视频链接」这类请求变成**端到端自动流水线**：

- 支持**整段分享文案**作为输入（自动从中抽链接、展开短链）
- 自动下载、抽音轨、ASR 转写（whisper.cpp，CUDA 下约 20 倍实时）
- 自动汇总元数据（标题/作者/时长/互动数据/文案），Agent 不用翻深层 JSON
- 按[笔记规范](references/note-spec.md)产出单文件 `summary.md`：压缩提炼、ASR 校正标注、不臆造
- **超长视频（数小时级）也有完整方案**：只下音轨 → 分块 → 并行子代理消化，实测 5.7 小时音频 ≈ 16 分钟转写

## 目录结构

```
video-to-note/
├── SKILL.md                  # Skill 主文档：四步流程（符合 Agent Skills 规范）
├── references/
│   ├── note-spec.md          # 笔记格式规范（与下载流程解耦，方便个人化调整）
│   ├── light-mode.md         # 轻量版流程：平台字幕抓取 + 清洗 + 升级提示话术
│   └── long-video.md         # 长视频/多视频扩展流程 + 8 条踩坑经验（按需加载）
├── scripts/
│   ├── resolve.py            # 链接规范化：分享文案抽链接 / 短链展开 / modal_id 提取
│   └── collect.py            # 读取产物目录，输出写笔记所需全部信息的精简 JSON
└── adapters/
    └── codex-prompt.md       # Codex CLI 适配：复制到 ~/.codex/prompts/ 即用
```

## ⚡ 一键安装（推荐）

[skills.sh](https://skills.sh) 生态的通用安装器，一条命令装到任意支持的 Agent
（Claude Code、Codex、Cursor、OpenCode、Copilot 等），安装时交互选择目标：

```bash
npx skills add hjz112/video-to-note
```

## 平台兼容性

| 平台 | 安装方式 | 触发方式 |
|---|---|---|
| **WorkBuddy** | 克隆到 `~/.workbuddy/skills/video-to-note/` | 自然语言：「下载这个视频帮我总结」 |
| **Claude Code** | 克隆到 `~/.claude/skills/video-to-note/` | 自然语言，Skill 自动匹配（本仓库 SKILL.md 符合 Anthropic Agent Skills 规范） |
| **Codex CLI** | 见下方「Codex CLI 安装」 | 自定义 prompt：`/video-to-note <链接>` |

---

## 安装教程

### 第 0 步：装依赖（轻量版只需 yt-dlp，完全版三样全装）

```bash
# yt-dlp（轻量版/完全版都需要；三选一）
pip install -U yt-dlp          # pip
winget install yt-dlp          # Windows winget
brew install yt-dlp            # macOS

# ffmpeg（仅完全版：转写前抽音轨必需）
winget install ffmpeg          # Windows
brew install ffmpeg            # macOS

# whisper.cpp（仅完全版：ASR 引擎）
# 参考 https://github.com/ggml-org/whisper.cpp 编译或下载发行版，
# 然后设置两个环境变量：
export WHISPER_CPP_BIN="/path/to/whisper-cli"
export WHISPER_CPP_MODEL="/path/to/ggml-large-v3-turbo-q5_0.bin"
# Windows PowerShell:
# setx WHISPER_CPP_BIN "C:\whisper.cpp\bin\whisper-cli.exe"
# setx WHISPER_CPP_MODEL "C:\whisper.cpp\models\ggml-large-v3-turbo-q5_0.bin"
```

> **模型按部署场景选档**（同为 whisper large-v3 家族，区别在参数完整度与量化精度）：
>
> | 场景 | 模型 | 大小 | 说明 |
> |---|---|---|---|
> | 桌面 / 笔记本（默认） | `ggml-large-v3-turbo-q5_0.bin` | ~574MB | 速度/质量平衡最好，中文效果好 |
> | 服务器 / 批处理 | `ggml-large-v3.bin` | ~3.1GB | 全量 1550M 参数 f16 无损，精度天花板，需 ~3.3GB 显存 |
> | 省显存的服务器 | `ggml-large-v3-q5_0.bin` | ~1.1GB | 全参数 5bit 量化 |
>
> 下载（三选一，按连通性）：
>
> ```bash
> # 1) HuggingFace 直连
> #    https://huggingface.co/ggml-org/whisper.cpp/resolve/main/ggml-large-v3-turbo-q5_0.bin
>
> # 2) HF 国内镜像（HF 限速/连不上时）：把域名换成 hf-mirror.com 即可
> #    https://hf-mirror.com/ggml-org/whisper.cpp/resolve/main/ggml-large-v3-turbo-q5_0.bin
> #    或用 CLI：set HF_ENDPOINT=https://hf-mirror.com 后 huggingface-cli download
>
> # 3) ModelScope（魔搭，国内直连快）：到 modelscope.cn 搜索 "whisper.cpp ggml"，
> #    选含目标模型文件的仓库下载同款文件
> ```

**前置校验**（三条都通过即可用）：

```bash
yt-dlp --version && ffmpeg -version && echo $WHISPER_CPP_BIN
```

### WorkBuddy（原生 Skill）

```bash
git clone https://github.com/hjz112/video-to-note.git ~/.workbuddy/skills/video-to-note
```

重开对话即生效。直接说人话：「帮我下载并总结这个视频 <链接>」。

### Claude Code

本仓库的 `SKILL.md` + frontmatter（`name` / `description`）**符合 Anthropic Agent Skills 规范**，无需任何修改：

```bash
# 用户级（所有项目可用）
git clone https://github.com/hjz112/video-to-note.git ~/.claude/skills/video-to-note

# 或项目级（仅当前项目）
git clone https://github.com/hjz112/video-to-note.git <你的项目>/.claude/skills/video-to-note
```

Claude Code 会根据 SKILL.md 的 description 自动匹配视频类请求。
注意：本 skill 的 Step 2 依赖 `video-downloader-enhanced` 的 `download_video.py` /
`asr.py`（编排层与执行层分离的设计）。没有该 skill 时，可按 SKILL.md「扩展 B」一节
直接用 yt-dlp 命令 + `asr.py` 替代，或把 Step 2 的下载命令换成你自己的 yt-dlp 封装。

### Codex CLI

Codex 没有原生 skill 系统，用**自定义 prompt**（slash command）适配：

```bash
# 1. 克隆仓库到任意固定位置（建议放 skills 目录，和其它工具共用）
git clone https://github.com/hjz112/video-to-note.git ~/.codex/skills/video-to-note

# 2. 复制适配文件为自定义 prompt
mkdir -p ~/.codex/prompts
cp ~/.codex/skills/video-to-note/adapters/codex-prompt.md ~/.codex/prompts/video-to-note.md
```

使用：在 Codex 里输入 `/video-to-note <视频链接或分享文案>`，
Codex 会按 prompt 里的流程逐步执行。

### 手动使用（无 Agent，直接跑脚本）

两个脚本零第三方依赖（纯标准库），可以脱离 Agent 单独用：

```bash
# 1. 规范化链接（支持整段分享文案）
python scripts/resolve.py "8.51 复制打开抖音... https://v.douyin.com/xx/ 复制本条"

# 2. 下载 + 转写（需要先配好 yt-dlp / ffmpeg / whisper.cpp）
yt-dlp --no-playlist -f "bestaudio/best" -x --audio-format m4a \
    -o "out/audio_src.%(ext)s" "<视频链接>"
ffmpeg -i out/audio_src.m4a -ar 16000 -ac 1 out/audio.wav
whisper-cli -m $WHISPER_CPP_MODEL -f out/audio.wav -l zh -osrt -otxt

# 3. 写笔记：把 transcript.txt 按 references/note-spec.md 的规范整理成 summary.md
```

---

## 使用方法

### 日常单视频（默认路径）

对 Agent 说：

> 下载 https://www.bilibili.com/video/BVxxxx 并总结成笔记
> /video-to-note 8.51 复制打开抖音... https://v.douyin.com/xx/ 复制本条

产出（在产物目录内）：

| 文件 | 内容 |
|---|---|
| `summary.md` | **最终笔记**（按 note-spec 规范） |
| `transcript.txt` / `.srt` | 转写全文 / 带时间戳字幕 |
| `audio.wav` / 视频文件 | 原始素材 |
| `metadata.json` / `post_caption.txt` | 元数据 / 博主文案 |

### 超长视频（> 1 小时）

不要走默认路径（会下载数 GB 视频 + 转写稿撑爆上下文）。对 Agent 说：

> 这是个 4 小时的长视频，按长视频流程处理：<链接>

Agent 会按 SKILL.md「扩展」一节执行：只下音轨 → 抽 16k wav → whisper 转写
（CUDA 约 20 倍实时）→ 按时间窗切块 → 并行子代理消化 → 汇总成笔记。
详见 SKILL.md「扩展：多视频 / 超长视频批量处理」。

### 笔记格式个性化

`references/note-spec.md` 独立于流程，改它不会动下载逻辑：
结构（标题/基本信息表/一句话总结/核心内容/存疑与不足/标签）、写作原则
（校验优先、压缩而非搬运、不臆造、保留原名、标注存疑）、篇幅参考都在里面。

---

## 精华：踩坑经验（[references/long-video.md](references/long-video.md) 「D. 必踩的坑」节）

多次实测换来的，比流程本身更值钱：

- whisper 长音频「复读幻觉」的**检测脚本思路 + 修复参数**（`-mc 0` + `-bs 5`）
- B站 CC 字幕判据：yt-dlp warning **不能**当判据，必须登录态打 player API
- 搬运视频「整段只有水印音轨」的识别方法
- `--cookies-from-browser edge` 必败（App-Bound 加密），Chrome 的坑与 SESSDATA 兜底方案
- 沙箱批量删除保护误伤 yt-dlp HLS 分片的排查与手动补片方法（`frag N ↔ m3u8 URI[N-1]`）

## License

MIT
