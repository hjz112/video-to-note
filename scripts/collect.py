# -*- coding: utf-8 -*-
"""读取 video-downloader-enhanced 的产物目录，输出一份精简信息（供写笔记用）。

用法：
    python collect.py "<产物目录>" [--transcript-chars 4000]

输出 JSON：平台 / 标题 / 作者 / 发布日期 / 时长 / 互动数据 / 标签 /
          文案 / 转写全文(可截断) / 文件清单。

设计目的：让 agent 不必自己翻 metadata.json（字段深、键多）就能拿到写笔记
所需的全部信息，省 token 也避免漏字段。
"""
import json
import os
import re
import sys
from pathlib import Path

try:
    sys.stdout.reconfigure(encoding="utf-8")
except Exception:
    pass


def pick(d, *keys, default=None):
    cur = d
    for k in keys:
        if not isinstance(cur, dict):
            return default
        cur = cur.get(k)
    return cur if cur is not None else default


def main(argv):
    if not argv:
        print(__doc__)
        return 1
    folder = Path(argv[0])
    limit = 4000
    if "--transcript-chars" in argv:
        i = argv.index("--transcript-chars")
        if i + 1 < len(argv):
            limit = int(argv[i + 1])

    if not folder.exists():
        print(json.dumps({"ok": False, "error": f"目录不存在: {folder}"},
                         ensure_ascii=False))
        return 1

    meta_path = folder / "metadata.json"
    meta = {}
    if meta_path.exists():
        meta = json.loads(meta_path.read_text(encoding="utf-8"))

    raw = meta.get("raw_ytdlp_metadata") or {}
    video = meta.get("video") or {}
    author = meta.get("author") or {}

    def read(name):
        p = folder / name
        return p.read_text(encoding="utf-8").strip() if p.exists() else None

    caption = read("post_caption.txt") or meta.get("caption")
    transcript = read("transcript.txt")

    # 文件清单
    files = []
    for p in sorted(folder.iterdir()):
        if p.is_file():
            files.append({"name": p.name, "size_mb": round(p.stat().st_size / 1e6, 2)})

    # 时长：优先顶层 video，再退到 raw
    duration = pick(video, "duration_seconds") or raw.get("duration")

    out = {
        "ok": True,
        "folder": str(folder),
        "platform": meta.get("platform"),
        "video_id": meta.get("id"),
        "source_url": meta.get("source_url"),
        "title": raw.get("title") or pick(author, "nickname") or folder.name,
        "author": pick(author, "nickname") or raw.get("uploader"),
        "upload_date": raw.get("upload_date"),
        "duration_seconds": duration,
        "resolution": pick(video, "resolution") or raw.get("resolution"),
        "stats": {
            "view": raw.get("view_count"),
            "like": raw.get("like_count"),
            "comment": raw.get("comment_count"),
            "repost": raw.get("repost_count"),
            "save": raw.get("save_count"),
        },
        "tags": raw.get("tags") or [],
        "caption": caption,
        "asr_status": pick(meta, "asr", "status"),
        "asr_backend": pick(meta, "asr", "backend"),
        "asr_language": pick(meta, "asr", "language"),
        "files": files,
    }

    if transcript is not None:
        full = transcript
        out["transcript_chars"] = len(full)
        out["transcript"] = full if limit <= 0 else full[:limit]
        if limit > 0 and len(full) > limit:
            out["transcript_truncated"] = True
        # 粗略分段，方便按主题定位
        out["transcript_line_count"] = len([x for x in full.splitlines() if x.strip()])
    else:
        out["transcript"] = None
        out["transcript_chars"] = 0

    print(json.dumps(out, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
