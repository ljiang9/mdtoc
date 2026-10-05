#!/usr/bin/env python3
"""mdtoc: 为 Markdown 文件生成并维护目录（Table of Contents）。

只做一件事：解析标题，生成 GitHub 风格的锚点目录，
在 <!-- toc --> ... <!-- /toc --> 标记之间写入/更新/校验。
纯标准库，离线可用。
"""
import argparse
import os
import re
import sys

VERSION = "0.1.0"
TOC_START = "<!-- toc -->"
TOC_END = "<!-- /toc -->"

HEADING_RE = re.compile(r"^(#{1,6})\s+(.*?)\s*#*\s*$")
FENCE_RE = re.compile(r"^\s*(```|~~~)")


def slugify(text):
    """GitHub 风格的锚点 slug（近似实现）。

    规则：小写；空格/下划线转连字符；去掉标点；CJK 原样保留；
    重复标题加 -1/-2 后缀。
    """
    s = text.strip().lower()
    s = re.sub(r"[\s_]+", "-", s)
    # 保留：字母数字、CJK、连字符
    s = "".join(ch for ch in s if ch.isalnum() or ch == "-" or "\u4e00" <= ch <= "\u9fff")
    s = re.sub(r"-{2,}", "-", s).strip("-")
    return s or "section"


def extract_headings(path):
    """解析 Markdown 文件，返回 [(level, text, slug)]。跳过代码块。"""
    headings = []
    counts = {}
    in_fence = False
    with open(path, encoding="utf-8") as f:
        for line in f:
            if FENCE_RE.match(line):
                in_fence = not in_fence
                continue
            if in_fence:
                continue
            m = HEADING_RE.match(line.rstrip("\n"))
            if not m:
                continue
            level = len(m.group(1))
            text = m.group(2).strip()
            if not text:
                continue
            base = slugify(text)
            n = counts.get(base, 0)
            counts[base] = n + 1
            slug = base if n == 0 else "%s-%d" % (base, n)
            headings.append((level, text, slug))
    return headings


def render_toc(headings, max_depth=6):
    """渲染为嵌套列表。"""
    lines = []
    for level, text, slug in headings:
        if level > max_depth:
            continue
        indent = "  " * (level - 1)
        lines.append("%s- [%s](#%s)" % (indent, text, slug))
    return "\n".join(lines) + ("\n" if lines else "")


def read_toc_block(lines):
    """找出标记之间的目录内容，返回 (start_idx, end_idx, current_toc) 或 None。"""
    start = end = None
    for i, line in enumerate(lines):
        if TOC_START in line and start is None:
            start = i
        elif TOC_END in line and start is not None:
            end = i
            break
    if start is None or end is None:
        return None
    return start, end, "".join(lines[start + 1:end])


def cmd_print(args):
    headings = extract_headings(args.file)
    toc = render_toc(headings, args.max_depth)
    if not toc:
        sys.stderr.write("error: 文件中没有找到标题：%s\n" % args.file)
        return 1
    sys.stdout.write(toc)
    return 0


def cmd_write(args):
    if not os.path.isfile(args.file):
        sys.stderr.write("error: 文件不存在：%s\n" % args.file)
        return 1
    with open(args.file, encoding="utf-8") as f:
        lines = f.readlines()
    headings = extract_headings(args.file)
    toc = render_toc(headings, args.max_depth)
    block = read_toc_block(lines)
    if block is None:
        sys.stderr.write(
            "error: 文件中没有找到 %s ... %s 标记。\n"
            "       用 --insert 在首个一级标题后自动插入标记后再试。\n" % (TOC_START, TOC_END))
        return 1
    start, end, _ = block
    new_lines = lines[:start + 1] + [toc] + lines[end:]
    with open(args.file, "w", encoding="utf-8") as f:
        f.writelines(new_lines)
    sys.stderr.write("已更新目录：%s（%d 个标题）\n" % (args.file, len(headings)))
    return 0


def cmd_insert(args):
    if not os.path.isfile(args.file):
        sys.stderr.write("error: 文件不存在：%s\n" % args.file)
        return 1
    with open(args.file, encoding="utf-8") as f:
        lines = f.readlines()
    if read_toc_block(lines) is not None:
        sys.stderr.write("标记已存在，无需插入。\n")
        return 0
    # 找到首个一级标题，在其后插入标记
    pos = None
    in_fence = False
    for i, line in enumerate(lines):
        if FENCE_RE.match(line):
            in_fence = not in_fence
            continue
        if in_fence:
            continue
        if re.match(r"^#\s+", line):
            pos = i
            break
    if pos is None:
        sys.stderr.write("error: 文件中没有一级标题，无法确定插入位置。\n")
        return 1
    new_lines = (lines[:pos + 1] + ["\n", TOC_START + "\n", TOC_END + "\n"]
                 + lines[pos + 1:])
    with open(args.file, "w", encoding="utf-8") as f:
        f.writelines(new_lines)
    sys.stderr.write("已在第 %d 行后插入目录标记。\n" % (pos + 1))
    return 0


def expected_toc(path, max_depth):
    headings = extract_headings(path)
    return render_toc(headings, max_depth)


def check_one(path, max_depth):
    with open(path, encoding="utf-8") as f:
        lines = f.readlines()
    block = read_toc_block(lines)
    if block is None:
        return False, "缺少目录标记"
    _, _, current = block
    want = expected_toc(path, max_depth)
    if current.strip() != want.strip():
        return False, "目录已过期"
    return True, "目录最新"


def cmd_check(args):
    targets = []
    if args.dir:
        if not os.path.isdir(args.dir):
            sys.stderr.write("error: 目录不存在：%s\n" % args.dir)
            return 1
        for root, _dirs, files in os.walk(args.dir):
            for fn in sorted(files):
                if fn.endswith(".md"):
                    targets.append(os.path.join(root, fn))
    else:
        if not os.path.isfile(args.file):
            sys.stderr.write("error: 文件不存在：%s\n" % args.file)
            return 1
        targets = [args.file]
    bad = 0
    for t in targets:
        ok, msg = check_one(t, args.max_depth)
        print("%s %s：%s" % ("✅" if ok else "❌", t, msg))
        if not ok:
            bad += 1
    return 1 if bad else 0


def main(argv=None):
    ap = argparse.ArgumentParser(prog="mdtoc", description="为 Markdown 生成/更新/校验目录（纯本地）")
    ap.add_argument("--version", action="version", version="mdtoc " + VERSION)
    ap.add_argument("--max-depth", type=int, default=6, help="目录最大标题层级（默认 6）")
    ap.add_argument("--dir", default=None, help="扫描目录下所有 .md（仅 --check 用）")
    ap.add_argument("--write", action="store_true", help="把目录写入标记之间")
    ap.add_argument("--insert", action="store_true", help="在首个一级标题后插入目录标记")
    ap.add_argument("--check", action="store_true", help="校验目录是否最新（CI 用）：过期则 exit 1")
    ap.add_argument("file", nargs="?", help="Markdown 文件")
    args = ap.parse_args(argv)

    if args.dir and not args.check:
        ap.error("--dir 只能与 --check 联用")
    if args.check:
        return cmd_check(args)
    if args.insert:
        if not args.file:
            ap.error("--insert 需要指定文件")
        return cmd_insert(args)
    if args.write:
        if not args.file:
            ap.error("--write 需要指定文件")
        return cmd_write(args)
    if not args.file:
        ap.error("需要指定要生成目录的 Markdown 文件")
    return cmd_print(args)


if __name__ == "__main__":
    sys.exit(main())
