# -*- coding: utf-8 -*-
"""把用户给的任意视频链接规范化成可直接下载的 URL。

处理的情形：
  1. 抖音主页链接带 modal_id  -> 取出 modal_id 作为视频 ID
  2. 抖音 / B站 / 小红书短链  -> 跟随重定向展开
  3. 一整段分享文案          -> 从中抽出链接再处理

用法：
    python resolve.py "https://www.douyin.com/user/MS4w...?modal_id=7669..."
    python resolve.py "8.51 复制打开抖音... https://v.douyin.com/xx/ 复制本条"

输出 JSON：
    {"ok": true, "platform": "douyin", "video_url": "...", "video_id": "...", "note": "..."}
"""
import json
import re
import sys
import urllib.request

try:
    sys.stdout.reconfigure(encoding="utf-8")
except Exception:
    pass

UA = ("Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
      "(KHTML, like Gecko) Chrome/131.0.0.0 Safari/537.36 Edg/131.0.0.0")

VIDEO_RE = re.compile(r"/(?:video|note|slides)/(\d{5,25})")
USER_RE = re.compile(r"/user/([A-Za-z0-9_\-]+)")
URL_IN_TEXT = re.compile(r"https?://[^\s\u4e00-\u9fa5，。、）】\"]+")

HOSTS = {
    "douyin.com": "douyin",
    "iesdouyin.com": "douyin",
    "bilibili.com": "bilibili",
    "b23.tv": "bilibili",
    "xiaohongshu.com": "xiaohongshu",
    "xhslink.com": "xiaohongshu",
    "xhslink.cn": "xiaohongshu",
    "youtube.com": "youtube",
    "youtu.be": "youtube",
}


def platform_of(url: str) -> str | None:
    host = re.sub(r"^https?://", "", url).split("/")[0].lower()
    for k, v in HOSTS.items():
        if host == k or host.endswith("." + k):
            return v
    return None


def expand(url: str, depth: int = 0) -> str:
    """展开短链，最多递归两层"""
    if depth > 2:
        return url
    try:
        req = urllib.request.Request(url, headers={"User-Agent": UA})
        with urllib.request.urlopen(req, timeout=20) as r:
            final = r.geturl()
            if VIDEO_RE.search(final) or USER_RE.search(final):
                return final
            body = r.read(300000).decode("utf-8", "ignore")
            for u in URL_IN_TEXT.findall(body):
                if VIDEO_RE.search(u) or USER_RE.search(u):
                    return u
            return final
    except Exception:
        return url


def resolve(raw: str) -> dict:
    text = raw.strip()
    out = {"ok": False, "input": text, "platform": None, "video_url": None,
           "video_id": None, "homepage": None, "note": None}

    urls = URL_IN_TEXT.findall(text)
    candidates = urls if urls else ([text] if text.startswith("http") else [])
    if not candidates:
        out["note"] = "没有在输入里找到链接"
        return out

    url = candidates[0]
    platform = platform_of(url)
    if not platform:
        platform = platform_of(expand(url))
        if not platform:
            out["note"] = f"不认识的平台: {url}"
            return out

    out["platform"] = platform

    # 主页链接：优先用 modal_id 指向的那个视频
    m_user = USER_RE.search(url)
    if m_user:
        out["homepage"] = m_user.group(1)
        m_modal = re.search(r"modal_id=(\d{5,25})", url)
        if m_modal:
            vid = m_modal.group(1)
            out.update(ok=True, video_id=vid,
                       video_url=f"https://www.douyin.com/video/{vid}",
                       note="链接是主页地址，已改用 modal_id 指向的具体视频")
            return out
        out["note"] = ("这是主页地址且没有 modal_id；本工作流只处理单个视频。"
                       "请给出具体视频的分享链接，主页批量下载请用 dy 命令")
        return out

    # 已经是视频链接
    m_vid = VIDEO_RE.search(url)
    if m_vid:
        out.update(ok=True, video_id=m_vid.group(1), video_url=url)
        return out

    # 短链，展开后再看
    final = expand(url)
    m_user = USER_RE.search(final)
    m_modal = re.search(r"modal_id=(\d{5,25})", final)
    if m_user and m_modal:
        out.update(ok=True, video_id=m_modal.group(1),
                   video_url=f"https://www.douyin.com/video/{m_modal.group(1)}",
                   homepage=m_user.group(1), note="短链展开后是主页+modal_id")
        return out
    m_vid = VIDEO_RE.search(final)
    if m_vid:
        out.update(ok=True, video_id=m_vid.group(1), video_url=final,
                   note="已展开短链")
        return out

    out["note"] = f"展开后仍没找到视频 ID，最终地址: {final}"
    return out


if __name__ == "__main__":
    if len(sys.argv) < 2:
        print(__doc__)
        sys.exit(1)
    print(json.dumps(resolve(sys.argv[1]), ensure_ascii=False, indent=2))
