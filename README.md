# video-to-note

把一条视频链接变成一份可归档的知识笔记 —— 为 AI Agent（WorkBuddy / Claude Code 等）设计的 Skill。

```
规范化链接 → 下载并转写 (yt-dlp + whisper.cpp) → 汇总产物 → 生成 summary.md
```

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
├── SKILL.md               # Skill 主文档：四步流程 + 长视频/批量扩展 + 踩坑清单
├── references/
│   └── note-spec.md       # 笔记格式规范（与下载流程解耦，方便个人化调整）
└── scripts/
    ├── resolve.py         # 链接规范化：分享文案抽链接 / 短链展开 / modal_id 提取
    └── collect.py         # 读取产物目录，输出写笔记所需全部信息的精简 JSON
```

## 依赖

| 依赖 | 说明 |
|---|---|
| `yt-dlp` / `ffmpeg` | 下载与音轨处理 |
| [whisper.cpp](https://github.com/ggml-org/whisper.cpp) | ASR；`WHISPER_CPP_BIN` 指向 `whisper-cli`，`WHISPER_CPP_MODEL` 指向 ggml 模型（推荐 large-v3-turbo） |
| [video-downloader-enhanced](https://github.com/) skill | 下载/转写的执行层（本 skill 只做编排，见 SKILL.md 的职责分离说明） |
| Python 3.10+ | 脚本零第三方依赖（标准库实现） |

## 平台支持

| 平台 | 状态 |
|---|---|
| 抖音 | ✅（需自备绕风控的 yt-dlp 插件/方案） |
| B站 | ✅ |
| YouTube / 小红书 | 已实现，未充分实测 |
| 微信视频号 | ❌（可先小程序「kg百宝箱」下载后走本地转写） |

## 精华：踩坑经验（SKILL.md 「D. 必踩的坑」节）

这部分是多次实测换来的，比流程本身更值钱：

- whisper 长音频「复读幻觉」的**检测脚本思路 + 修复参数**（`-mc 0` + `-bs 5`）
- B站 CC 字幕判据：yt-dlp warning **不能**当判据，必须登录态打 player API
- 搬运视频「整段只有水印音轨」的识别方法
- `--cookies-from-browser edge` 必败（App-Bound 加密），Chrome 的坑与 SESSDATA 兜底方案
- 沙箱批量删除保护误伤 yt-dlp HLS 分片的排查与手动补片方法（`frag N ↔ m3u8 URI[N-1]`）

## 安装（WorkBuddy）

```bash
git clone https://github.com/hjz112/video-to-note.git ~/.workbuddy/skills/video-to-note
```

## License

MIT
