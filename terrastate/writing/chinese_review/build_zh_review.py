#!/usr/bin/env python3
"""Build a XeLaTeX review source from MANUSCRIPT_ZH_FULL.md.

This converter is intentionally narrow: it supports exactly the Markdown
constructs used by the TerraState Chinese reading mirror. The English
submission source remains authoritative and is never modified.
"""

from __future__ import annotations

import re
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SOURCE = ROOT / "MANUSCRIPT_ZH_FULL.md"
OUTPUT = Path(__file__).resolve().parent / "main_zh.tex"


PREAMBLE = r"""\documentclass[11pt,a4paper,fontset=fandol]{ctexart}
\usepackage[a4paper,margin=24mm,headheight=15pt]{geometry}
\usepackage{amsmath,amssymb,booktabs,tabularx,array,graphicx}
\usepackage{enumitem}
\usepackage{microtype}
\usepackage{xcolor}
\usepackage{hyperref}
\usepackage{fancyhdr}
\usepackage{natbib}

\hypersetup{
  colorlinks=true,
  linkcolor=blue!45!black,
  citecolor=green!35!black,
  urlcolor=blue!55!black,
  pdftitle={TerraState 中文完整审阅版},
  pdfauthor={Internal review copy}
}
\setlength{\parindent}{2em}
\setlength{\parskip}{0.35em}
\linespread{1.18}
\emergencystretch=3em
\setlist{nosep,leftmargin=2.2em}
\renewcommand{\arraystretch}{1.22}
\setlength{\tabcolsep}{4pt}
\newcolumntype{Y}{>{\raggedright\arraybackslash}X}

\pagestyle{fancy}
\fancyhf{}
\lhead{\small TerraState 中文完整审阅版}
\rhead{\small 非投稿文件}
\cfoot{\thepage}

\title{\bfseries TerraState：面向天气驱动地表预测的\\可检验预测状态世界模型}
\author{中文审阅版（英文 \texttt{paper/main.tex} 为唯一投稿事实源）}
\date{2026 年 7 月 28 日}

\begin{document}
\maketitle

\begin{quote}\small
本 PDF 用于作者审阅中文叙事、公式、表格与证据边界，不是 AAAI 投稿文件。
章节顺序、公式含义、实验数字与主张强度同步自英文权威稿。当前只展示已经接入
正式稿的 Figure 1；未批准的 Figure 2/3 不以空框或占位图出现。
\end{quote}

\tableofcontents
\clearpage
"""


POSTAMBLE = r"""
\clearpage
\bibliographystyle{plainnat}
\bibliography{../paper/references}
\end{document}
"""


def escape_text(text: str) -> str:
    replacements = {
        "\\": r"\textbackslash{}",
        "&": r"\&",
        "%": r"\%",
        "#": r"\#",
        "_": r"\_",
        "{": r"\{",
        "}": r"\}",
        "~": r"\textasciitilde{}",
        "^": r"\textasciicircum{}",
    }
    return "".join(replacements.get(ch, ch) for ch in text)


def inline(text: str) -> str:
    """Convert inline Markdown while preserving TeX math."""
    out: list[str] = []
    i = 0
    n = len(text)
    while i < n:
        if text.startswith("![", i):
            match = re.match(r"!\[([^\]]*)\]\(([^)]+)\)", text[i:])
            if match:
                out.append(escape_text(match.group(1)))
                i += match.end()
                continue
        if text.startswith("[@", i):
            end = text.find("]", i)
            if end != -1:
                keys = re.findall(r"@([A-Za-z0-9_:-]+)", text[i : end + 1])
                if keys:
                    out.append(r"\cite{" + ",".join(keys) + "}")
                    i = end + 1
                    continue
        if text.startswith("**", i):
            end = text.find("**", i + 2)
            if end != -1:
                out.append(r"\textbf{" + inline(text[i + 2 : end]) + "}")
                i = end + 2
                continue
        if text[i] == "`":
            end = text.find("`", i + 1)
            if end != -1:
                out.append(r"\texttt{" + escape_text(text[i + 1 : end]) + "}")
                i = end + 1
                continue
        if text[i] == "$":
            end = text.find("$", i + 1)
            if end != -1:
                out.append(text[i : end + 1])
                i = end + 1
                continue
        if text[i] == "[":
            match = re.match(r"\[([^\]]+)\]\(([^)]+)\)", text[i:])
            if match:
                label, target = match.groups()
                if target.startswith("paper/"):
                    target = "../" + target
                out.append(r"\href{" + escape_text(target) + "}{" + inline(label) + "}")
                i += match.end()
                continue
        if text[i] == "*" and not text.startswith("**", i):
            end = text.find("*", i + 1)
            if end != -1:
                out.append(r"\emph{" + inline(text[i + 1 : end]) + "}")
                i = end + 1
                continue

        start = i
        while i < n and not (
            text.startswith("![", i)
            or text.startswith("[@", i)
            or text.startswith("**", i)
            or text[i] in "`$[*"
        ):
            i += 1
        if start == i:
            out.append(escape_text(text[i]))
            i += 1
        else:
            out.append(escape_text(text[start:i]))
    rendered = "".join(out)
    return rendered.replace(
        "PVT v2/Contextformer", r"PVT v2/\allowbreak Contextformer"
    )


def strip_heading_number(title: str) -> str:
    return re.sub(r"^\d+(?:\.\d+)*\.?\s*", "", title).strip()


def table_to_tex(lines: list[str]) -> str:
    rows = []
    for line in lines:
        cells = [cell.strip() for cell in line.strip().strip("|").split("|")]
        rows.append(cells)
    if len(rows) < 2:
        return ""
    rows.pop(1)  # Markdown alignment row.
    ncols = len(rows[0])
    spec = " ".join("Y" for _ in range(ncols))
    rendered = [
        r"\begin{center}",
        r"\small",
        rf"\begin{{tabularx}}{{\textwidth}}{{@{{}}{spec}@{{}}}}",
        r"\toprule",
        " & ".join(r"\textbf{" + inline(cell) + "}" for cell in rows[0]) + r" \\",
        r"\midrule",
    ]
    for row in rows[1:]:
        row = row + [""] * (ncols - len(row))
        rendered.append(" & ".join(inline(cell) for cell in row[:ncols]) + r" \\")
    rendered.extend([r"\bottomrule", r"\end{tabularx}", r"\end{center}"])
    return "\n".join(rendered)


def convert(lines: list[str]) -> str:
    output: list[str] = []
    paragraph: list[str] = []
    list_kind: str | None = None
    in_abstract = False
    skip_navigation = False
    skip_reference_note = False
    quote_lines: list[str] = []
    started = False

    def flush_paragraph() -> None:
        nonlocal paragraph
        if paragraph:
            output.append(inline(" ".join(part.strip() for part in paragraph)))
            output.append("")
            paragraph = []

    def close_list() -> None:
        nonlocal list_kind
        if list_kind:
            output.append(rf"\end{{{list_kind}}}")
            output.append("")
            list_kind = None

    def flush_quote() -> None:
        nonlocal quote_lines
        if quote_lines:
            output.append(r"\begin{quote}\small")
            output.append(inline(" ".join(quote_lines)))
            output.append(r"\end{quote}")
            output.append("")
            quote_lines = []

    i = 0
    while i < len(lines):
        raw = lines[i].rstrip()
        stripped = raw.strip()

        if not started:
            if stripped == "## 摘要":
                started = True
            else:
                i += 1
                continue

        if stripped.startswith("# "):
            i += 1
            continue
        if stripped == "## 快速导航":
            flush_paragraph()
            skip_navigation = True
            i += 1
            continue
        if skip_navigation:
            if stripped == "## 摘要":
                skip_navigation = False
            else:
                i += 1
                continue

        if stripped.startswith(">"):
            flush_paragraph()
            close_list()
            quote_lines.append(stripped.lstrip(">").strip())
            i += 1
            if i >= len(lines) or not lines[i].strip().startswith(">"):
                flush_quote()
            continue
        flush_quote()

        if stripped == "$$":
            flush_paragraph()
            close_list()
            math_lines = []
            i += 1
            while i < len(lines) and lines[i].strip() != "$$":
                math_lines.append(lines[i].rstrip())
                i += 1
            output.append(r"\begin{equation*}")
            output.extend(math_lines)
            output.append(r"\end{equation*}")
            output.append("")
            i += 1
            continue

        if stripped.startswith("!["):
            flush_paragraph()
            close_list()
            match = re.match(r"!\[([^\]]*)\]\(([^)]+)\)", stripped)
            if match:
                caption = re.sub(
                    r"^(?:Figure|图)\s*[12]\s*[:：]\s*", "", match.group(1)
                )
                image_target = match.group(2)
                if "terrastate_architecture_fig2" in image_target:
                    figure_pdf = (
                        "../paper/figures/terrastate_architecture_fig2.pdf"
                    )
                else:
                    figure_pdf = (
                        "../paper/figures/terrastate_method_overview.pdf"
                    )
                output.extend(
                    [
                        r"\begin{figure}[htbp]",
                        r"\centering",
                        r"\includegraphics[width=\textwidth]{" + figure_pdf + "}",
                        r"\caption{" + inline(caption) + "}",
                        r"\end{figure}",
                        "",
                    ]
                )
            i += 1
            continue

        if stripped.startswith("## "):
            flush_paragraph()
            close_list()
            title = stripped[3:].strip()
            if in_abstract:
                output.append(r"\end{abstract}")
                output.append("")
                in_abstract = False
            if title == "摘要":
                output.append(r"\addcontentsline{toc}{section}{摘要}")
                output.append(r"\begin{abstract}")
                in_abstract = True
            elif title == "参考文献":
                skip_reference_note = True
            elif title.startswith("中文审阅导航"):
                skip_reference_note = False
                output.append(r"\clearpage")
                output.append(r"\appendix")
                output.append(r"\section{中文审阅导航（非投稿正文）}")
            else:
                output.append(r"\section{" + inline(strip_heading_number(title)) + "}")
            output.append("")
            i += 1
            continue

        if skip_reference_note:
            i += 1
            continue

        if stripped.startswith("### "):
            flush_paragraph()
            close_list()
            title = strip_heading_number(stripped[4:].strip())
            if title.startswith("Table "):
                title = "表 " + title[len("Table ") :]
                output.append(r"\subsection*{" + inline(title) + "}")
            elif title.startswith(("Figure 1：", "Figure 2：")):
                # The embedded figure supplies its own caption.
                pass
            elif title.startswith("Figure "):
                title = "图 " + title[len("Figure ") :]
                output.append(r"\subsection*{" + inline(title) + "}")
            else:
                output.append(r"\subsection{" + inline(title) + "}")
            output.append("")
            i += 1
            continue

        if stripped.startswith("#### "):
            flush_paragraph()
            close_list()
            output.append(r"\subsubsection{" + inline(stripped[5:].strip()) + "}")
            output.append("")
            i += 1
            continue

        if stripped.startswith("|") and i + 1 < len(lines):
            next_line = lines[i + 1].strip()
            if re.match(r"^\|[\s:|-]+\|$", next_line):
                flush_paragraph()
                close_list()
                table_lines = [stripped, next_line]
                i += 2
                while i < len(lines) and lines[i].strip().startswith("|"):
                    table_lines.append(lines[i].strip())
                    i += 1
                output.append(table_to_tex(table_lines))
                output.append("")
                continue

        numbered = re.match(r"^(\d+)\.\s+(.*)", stripped)
        bullet = re.match(r"^-\s+(.*)", stripped)
        if numbered or bullet:
            flush_paragraph()
            wanted = "enumerate" if numbered else "itemize"
            if list_kind != wanted:
                close_list()
                output.append(rf"\begin{{{wanted}}}")
                list_kind = wanted
            content = numbered.group(2) if numbered else bullet.group(1)
            output.append(r"\item " + inline(content))
            i += 1
            continue
        close_list()

        if stripped == "---":
            flush_paragraph()
            output.append(r"\bigskip\hrule\bigskip")
            i += 1
            continue

        if not stripped:
            flush_paragraph()
            i += 1
            continue

        paragraph.append(raw)
        i += 1

    flush_quote()
    flush_paragraph()
    close_list()
    if in_abstract:
        output.append(r"\end{abstract}")
    return "\n".join(output)


def main() -> None:
    lines = SOURCE.read_text(encoding="utf-8").splitlines()
    body = convert(lines)
    OUTPUT.write_text(PREAMBLE + body + POSTAMBLE, encoding="utf-8")
    print(f"Wrote {OUTPUT}")


if __name__ == "__main__":
    main()
