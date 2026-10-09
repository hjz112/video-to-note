# 轻量版流程（平台字幕转写）

> 适用：只装了 yt-dlp、不想下载模型/编译 whisper.cpp 的环境。
> 转写来源是平台自带字幕（CC / 自动字幕），因此**只对有字幕的平台有效**。
> 完全版流程见 SKILL.md Step 2。

## 平台字幕可用性（先看这张表）

| 平台 | 字幕 | 判据与坑 |
|---|---|---|
| YouTube | ✅ 稳定 | 自动字幕覆盖率高；`--write-auto-subs` 即可 |
| B站 | ⚠️ 看视频 | 部分 UP 主传了 CC；**yt-dlp 的 warning 不能当判据**，必须登录态打 player API（见 long-video.md「B站字幕判据」节） |
| 抖音 | ❌ | 平台不提供字幕 → 走升级提示 |
| 小红书 / X | ❌ | 同上 |

## 抓取命令

```bash
yt-dlp --skip-download --write-subs --write-auto-subs \
    --sub-langs "zh.*,en.*" --sub-format "srt/vtt/best" \
    -o "<目标目录>/sub.%(ext)s" "<video_url>"
```

- `--skip-download` 不下视频/音频，几秒出结果。
- 输出可能是 `.srt` 或 `.vtt`（含 `sub.zh-Hans.vtt` 之类带语言后缀的文件名），先 `ls <目标目录>/sub.*` 看抓到了什么。
- 什么都没抓到 ≠ 平台没字幕：B站需登录态（cookies），见下方「B站专用判据」。

## B站专用判据（不要靠 yt-dlp 输出猜）

yt-dlp 对 B站 CC 字幕的支持不可靠：warning「no subtitles」可能只是没带登录态。
正确判据：带 SESSDATA cookie 请求 player API：

```bash
curl -s "https://api.bilibili.com/x/player/wbi/v2?bvid=<BV号>&cid=<cid>" \
    -H "Cookie: SESSDATA=<你的SESSDATA>" | python -m json.tool | grep -A3 subtitle
```

`subtitle.subtitles` 非空 → 有 CC，取其 `subtitle_url` 直接下载 JSON 字幕
（`curl <subtitle_url>` 返回 body 数组，`from`/`to`/`content` 字段）。
为空且无 AI 字幕入口 → 真没字幕，走升级提示。

## 字幕清洗为 transcript.txt

把 SRT/VTT/JSON 字幕整理成纯文本，供 Step 3 的 `collect.py` 直接使用
（它读产物目录下的 `transcript.txt`，缺失也只是置空不报错）：

```python
# 任意语言可用，纯标准库；用法：python clean_sub.py sub.zh-Hans.vtt transcript.txt
import re, sys
src, dst = sys.argv[1], sys.argv[2]
lines = open(src, encoding="utf-8").read().splitlines()
out, seen = [], set()
for ln in lines:
    s = ln.strip()
    if (not s or s == "WEBVTT" or re.match(r"^\d+$", s)
            or "-->" in s or s.startswith(("NOTE", "Kind:", "Language:"))):
        continue
    s = re.sub(r"<[^>]+>", "", s)          # 去 <c>/<v> 等标签
    s = re.sub(r"^\s*-\s*", "", s)          # 去滚动字幕行首连字符
    if s and s not in seen:                 # 自动字幕常见整行重复，去重
        seen.add(s); out.append(s)
open(dst, "w", encoding="utf-8").write("\n".join(out))
print(f"{len(out)} lines -> {dst}")
```

注意：自动字幕（auto-subs）没有标点、可能整行重复，去重后仍会有口语碎碎感，
写笔记时按 note-spec 的「压缩提炼」原则处理，不要搬运字幕原文。

## 无字幕平台的升级提示（标准话术）

检测到抖音/小红书/X 链接，或 B站确认无 CC 时，向用户说明：

> 轻量版依赖平台字幕，该平台不提供字幕，无法转写。两个选择：
> ① 升级完全版：安装 whisper.cpp + 下载模型（约 574MB 起，指引见 README），
>    之后全平台可用；
> ② 如果你能从别处拿到这个视频的文案/字幕，发给我，我直接按笔记规范整理。

**不要**对无字幕平台硬跑抓取命令然后报一堆 yt-dlp warning。

## 轻量版的产物边界

- 产出：`transcript.txt`（来自字幕）、`summary.md`、`sub.*.srt/vtt` 原始字幕
- 没有：视频文件、audio.wav、metadata.json（标题等元数据让 agent 从
  yt-dlp 的 `--print title` 或页面自行获取，collect.py 对缺失字段有容错）
- 交付时注明「本笔记基于平台字幕，非语音转写」，字幕覆盖不全的段落
  （字幕与语音不同步）在「存疑与不足」里标注
