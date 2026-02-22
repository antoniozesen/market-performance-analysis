from __future__ import annotations

import html


def markdown_to_basic_html(markdown_text: str) -> str:
    lines = markdown_text.splitlines()
    out = [
        "<html><body style='font-family:Arial,sans-serif;line-height:1.45;color:#111;'>",
        "<div style='max-width:900px;margin:0 auto;'>",
    ]

    for line in lines:
        escaped = html.escape(line)
        if line.startswith("# "):
            out.append(f"<h1>{escaped[2:]}</h1>")
        elif line.startswith("## "):
            out.append(f"<h2 style='margin-top:18px;'>{escaped[3:]}</h2>")
        elif line.startswith("**") and line.endswith("**"):
            out.append(f"<p><strong>{escaped.strip('*')}</strong></p>")
        elif line.strip() == "":
            out.append("<br/>")
        else:
            out.append(f"<p>{_bold_assets(escaped)}</p>")

    out.append("</div></body></html>")
    return "\n".join(out)


def _bold_assets(text: str) -> str:
    return text.replace("**", "<strong>", 1).replace("**", "</strong>", 1) if "**" in text else text
