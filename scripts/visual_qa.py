"""
scipilot-figure-skill :: visual_qa.py
=====================================
出图后的「程序自检」+「渲染预览」——自检闭环的机器那一层。

设计分工：
- **程序（本脚本）** 抓**确定性**问题：缺字乱码、文字越界裁切、刻度标签重叠。
- **AI 读图**（见 references/visual_review.md）抓**感知性**问题：图例压数据、
  子图标签是否对齐、配色灰度可分、整体观感。

两层串起来才是完整的「出图 → 渲 PNG → 程序自检 + AI 读图 → 回改 → 再看」闭环。

核心能力
--------
- ``render_preview(fig_or_path, out_png, dpi)`` —— 渲一张中分辨率 PNG，
  供 AI 用 Read 工具读图复核（矢量 PDF 没法直接"看像素重叠"，必须先栅格化）。
- ``audit_layout(fig)`` —— 返回 ``[(severity, msg), ...]``：
  * **缺字**（FAIL）：渲染时同时拦截 matplotlib 的 warnings 与 logging 两条
    告警通道，任一报 "missing from font" 即判定成图会出方框/乱码。
  * **文字越界裁切**（WARN）：Text 的 window_extent 超出画布边界。
  * **刻度标签重叠**（WARN）：相邻 tick label 的包围盒水平/垂直相交。

severity 约定与 check_figure.py 保持一致：INFO < WARN < FAIL。

Usage
-----
    from visual_qa import render_preview, audit_layout, print_report

    fig, ax = plt.subplots()
    ...
    png = render_preview(fig, "figs/_preview.png", dpi=150)  # 给 AI 读图
    issues = audit_layout(fig)
    print_report(issues)

CLI:
    python visual_qa.py demo                       # 跑一遍自检演示
    python visual_qa.py figs/fig1.png --preview out.png
"""
from __future__ import annotations

import argparse
import io
import logging
import os
import sys
import warnings

import matplotlib.pyplot as plt
import matplotlib.text as mtext


# Windows GBK 终端下 print 中文会 UnicodeEncodeError。用 reconfigure 而非替换
# sys.stdout：幂等、不创建新对象，多个脚本一起 import 时也不会关闭底层流。
if sys.platform == "win32":
    try:
        sys.stdout.reconfigure(encoding="utf-8")
    except (AttributeError, ValueError):
        pass

SEVERITY = {"INFO": 0, "WARN": 1, "FAIL": 2}
_GLYPH_MARKERS = ("missing from", "Glyph", "findfont")


def _ensure_parent(path: str) -> None:
    parent = os.path.dirname(os.path.abspath(path))
    if parent and not os.path.exists(parent):
        os.makedirs(parent, exist_ok=True)


class _GlyphLogHandler(logging.Handler):
    """拦截 matplotlib logger 里关于缺字 / 找不到字体的记录。"""

    def __init__(self):
        super().__init__()
        self.messages: list[str] = []

    def emit(self, record):
        msg = record.getMessage()
        if any(m in msg for m in _GLYPH_MARKERS):
            self.messages.append(msg)


def _draw_and_collect_glyph_warnings(fig) -> list[str]:
    """
    渲染一次 figure，同时从 warnings 和 logging 两条通道收集缺字告警。

    matplotlib 不同版本对缺字的上报方式不一：老版本走 warnings.warn，
    新版本走 logging。两边都挂上才不会漏。渲染顺便让 renderer 就绪，
    供后续 window_extent 测量使用。
    """
    handler = _GlyphLogHandler()
    mpl_logger = logging.getLogger("matplotlib")
    prev_level = mpl_logger.level
    mpl_logger.setLevel(logging.WARNING)
    mpl_logger.addHandler(handler)

    collected: list[str] = []
    try:
        with warnings.catch_warnings(record=True) as wlist:
            warnings.simplefilter("always")
            # 画到内存即可，不落盘；draw 也会触发缺字告警
            buf = io.BytesIO()
            fig.savefig(buf, format="png", dpi=100)
            buf.close()
            # savefig 临时改变 DPI；恢复当前画布渲染状态后再测量文字。
            fig.canvas.draw()
        for w in wlist:
            s = str(w.message)
            if any(m in s for m in _GLYPH_MARKERS):
                collected.append(s)
    finally:
        mpl_logger.removeHandler(handler)
        mpl_logger.setLevel(prev_level)

    collected.extend(handler.messages)
    # 去重并保持顺序
    seen, uniq = set(), []
    for m in collected:
        if m not in seen:
            seen.add(m)
            uniq.append(m)
    return uniq


def _visible_texts(fig) -> list:
    out = []
    for t in fig.findobj(mtext.Text):
        try:
            if t.get_visible() and t.get_text().strip():
                out.append(t)
        except Exception:
            continue
    return out


def audit_layout(fig, clip_tol_px: float = 2.0, overlap_tol_px: float = 1.0
                 ) -> list[tuple[str, str]]:
    """
    对一张 matplotlib Figure 做版面自检。返回 [(severity, msg), ...]。

    检测项：
        1. 缺字乱码（FAIL）—— 中文/特殊符号字体未命中。
        2. 文字越界裁切（WARN）—— 标题/轴标签/标注超出画布。
        3. 刻度标签重叠（WARN）—— x/y 轴相邻刻度包围盒相交。

    非破坏性：只渲染测量，不修改 fig 内容。
    """
    issues: list[tuple[str, str]] = []

    # ---- 1. 缺字（同时触发一次渲染，让 renderer 就绪）----
    glyph_msgs = _draw_and_collect_glyph_warnings(fig)
    if glyph_msgs:
        sample = " | ".join(glyph_msgs[:3])
        issues.append((
            "FAIL",
            f"检测到缺字，成图会出现方框/乱码：{sample[:240]}。"
            "中文图请先 setup_style(lang='zh') 配置 CJK 字体；"
            "若是负号方框，确认 axes.unicode_minus=False。"
        ))

    try:
        renderer = fig.canvas.get_renderer()
    except Exception:
        fig.canvas.draw()
        renderer = fig.canvas.get_renderer()

    W = float(fig.bbox.width)
    H = float(fig.bbox.height)

    # ---- 2. 文字越界裁切 ----
    # 刻度标签也可能越界。tight 裁边并非所有导出的默认设置，
    # 相邻刻度不重叠也不能证明文字在画布内。
    # 自动刻度可能含视区外的备用标签，这些标签不实际显示，不能算裁切。
    unrendered_tick_ids = set()
    for ax in fig.axes:
        for axis, limits in ((ax.xaxis, ax.get_xlim()),
                             (ax.yaxis, ax.get_ylim())):
            lo, hi = sorted(limits)
            tolerance = max(1.0, abs(lo), abs(hi)) * 1e-10
            for tick in axis.get_major_ticks() + axis.get_minor_ticks():
                if tick.get_loc() < lo - tolerance or tick.get_loc() > hi + tolerance:
                    unrendered_tick_ids.update((id(tick.label1), id(tick.label2)))

    clipped: list[str] = []
    for t in _visible_texts(fig):
        if id(t) in unrendered_tick_ids:
            continue
        try:
            bb = t.get_window_extent(renderer)
        except Exception:
            continue
        if (bb.x0 < -clip_tol_px or bb.y0 < -clip_tol_px
                or bb.x1 > W + clip_tol_px or bb.y1 > H + clip_tol_px):
            txt = t.get_text().strip().replace("\n", " ")
            if txt:
                clipped.append(txt[:24])
    if clipped:
        uniq = list(dict.fromkeys(clipped))[:6]
        issues.append((
            "WARN",
            f"以下文字可能超出画布被裁切：{uniq}。"
            "跑 finalize_figure(fig) 或导出时 bbox_inches='tight' 兜底；"
            "标题/标签过长可换行或缩短。"
        ))

    # ---- 3. 刻度标签重叠 ----
    overlap_axes = 0
    for ax in fig.axes:
        if ax.get_subplotspec() is None:
            continue
        if _ticklabels_overlap(ax.get_xticklabels(), renderer,
                               axis="x", tol=overlap_tol_px):
            overlap_axes += 1
            continue
        if _ticklabels_overlap(ax.get_yticklabels(), renderer,
                               axis="y", tol=overlap_tol_px):
            overlap_axes += 1
    if overlap_axes:
        issues.append((
            "WARN",
            f"{overlap_axes} 个子图存在刻度标签重叠。"
            "x 轴：ax.tick_params(axis='x', rotation=30) 或减少刻度/缩短标签；"
            "y 轴：增大子图高度或减少刻度数。"
        ))

    return issues


def _ticklabels_overlap(labels, renderer, axis: str, tol: float) -> bool:
    """相邻刻度标签包围盒是否相交。axis='x' 看水平、'y' 看垂直。"""
    boxes = []
    for l in labels:
        try:
            if l.get_visible() and l.get_text().strip():
                boxes.append(l.get_window_extent(renderer))
        except Exception:
            continue
    if len(boxes) < 2:
        return False
    if axis == "x":
        boxes.sort(key=lambda b: b.x0)
        return any(a.x1 - b.x0 > tol for a, b in zip(boxes, boxes[1:]))
    else:
        boxes.sort(key=lambda b: b.y0)
        return any(a.y1 - b.y0 > tol for a, b in zip(boxes, boxes[1:]))


def render_preview(fig_or_path, out_png: str = "_preview.png",
                   dpi: int = 150) -> str:
    """
    渲一张 PNG 预览供 AI 读图。

    Args:
        fig_or_path: matplotlib Figure 对象（自检闭环主路径），或一个已落盘
            的图片路径（位图直接返回；PDF 需可选的 PyMuPDF）。
        out_png: 输出 PNG 路径。
        dpi: 预览分辨率，默认 150（够 AI 看清文字/重叠，又不至于太大）。

    Returns:
        可供 Read 读取的 PNG 路径（位图来源时返回原路径）。
    """
    if hasattr(fig_or_path, "savefig"):
        _ensure_parent(out_png)
        fig_or_path.savefig(out_png, dpi=dpi, bbox_inches="tight")
        return out_png

    path = str(fig_or_path)
    if not os.path.exists(path):
        raise FileNotFoundError(path)
    ext = os.path.splitext(path)[1].lower().lstrip(".")
    if ext in {"png", "tif", "tiff", "jpg", "jpeg", "bmp"}:
        return path
    if ext == "pdf":
        try:
            import fitz  # PyMuPDF, 可选
        except ImportError as e:
            raise RuntimeError(
                "把 PDF 渲成预览需要 PyMuPDF（pip install pymupdf）。"
                "自检闭环更推荐直接把 matplotlib Figure 对象传给 render_preview，"
                "在导出前就完成读图复核。"
            ) from e
        doc = fitz.open(path)
        pix = doc[0].get_pixmap(dpi=dpi)
        _ensure_parent(out_png)
        pix.save(out_png)
        doc.close()
        return out_png
    raise RuntimeError(f"不支持从 .{ext} 生成预览；请传 Figure 对象或位图。")


def print_report(issues: list[tuple[str, str]]) -> str:
    """打印 audit_layout 的结果，返回 verdict（PASS/WARN/FAIL）。"""
    if not issues:
        print("  [PASS] 程序自检未发现缺字 / 裁切 / 刻度重叠。")
        print("  >>> 仍需 AI 读图复核感知性问题（见 visual_review.md）。")
        return "PASS"
    max_sev = max(SEVERITY[s] for s, _ in issues)
    verdict = {2: "FAIL", 1: "WARN", 0: "INFO"}[max_sev]
    for sev, msg in sorted(issues, key=lambda x: -SEVERITY[x[0]]):
        print(f"  [{sev}] {msg}")
    print(f"  >>> verdict: {verdict}（修完再渲一次 PNG 让 AI 读图复核）")
    return verdict


def _demo() -> int:
    """构造一张有版面问题的图，演示 audit_layout 能抓出来。"""
    import numpy as np
    rng = np.random.default_rng(1)

    fig, ax = plt.subplots(figsize=(3.0, 2.2))
    cats = [f"very_long_condition_name_{i}" for i in range(12)]
    ax.bar(range(12), rng.random(12))
    ax.set_xticks(range(12))
    ax.set_xticklabels(cats)  # 故意不旋转 -> x 轴刻度必然重叠
    ax.set_title("An intentionally overlong title that runs off the canvas edge")
    ax.set_ylabel("value")

    print("=== visual_qa demo：对一张刻意做坏版面的图自检 ===")
    issues = audit_layout(fig)
    print_report(issues)
    out = render_preview(fig, "./visual_qa_demo.png", dpi=120)
    print(f"\n预览已写出：{out}（可用 Read 工具读图复核）")
    print("注：缺字检测只在中文未配字体等情况下才会 FAIL；本 demo 主要展示裁切+重叠。")
    return 0


def _cli() -> int:
    p = argparse.ArgumentParser(description="scipilot-figure-skill visual QA")
    p.add_argument("target", nargs="?", help="图片路径；或 'demo'")
    p.add_argument("--preview", metavar="OUT.png",
                   help="把 target 渲成 PNG 预览到此路径")
    p.add_argument("--dpi", type=int, default=150)
    args = p.parse_args()

    if args.target == "demo" or args.target is None:
        return _demo()

    if args.preview:
        out = render_preview(args.target, args.preview, dpi=args.dpi)
        print(f"[visual_qa] 预览：{out}")
    else:
        # 对已落盘文件，audit_layout 需要 Figure 对象，这里只能提示
        print("[visual_qa] 对已落盘图片只支持 --preview 渲图；"
              "版面自检 audit_layout 请在画图脚本里对 Figure 对象调用。")
    return 0


if __name__ == "__main__":
    sys.exit(_cli())
