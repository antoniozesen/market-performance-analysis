from __future__ import annotations

import html
from typing import Dict, Optional

import pandas as pd


def markdown_to_basic_html(
    markdown_text: str,
    summary_df: Optional[pd.DataFrame] = None,
    universe: Optional[Dict[str, Dict[str, str]]] = None,
) -> str:
    lines = markdown_text.splitlines()
    out = [
        "<html><body style='font-family:Arial,sans-serif;line-height:1.45;color:#111;'>",
        "<div style='max-width:960px;margin:0 auto;'>",
    ]

    for line in lines:
        if line.startswith("# "):
            out.append(f"<h1>{html.escape(line[2:])}</h1>")
        elif line.startswith("## "):
            out.append(f"<h2 style='margin-top:18px;border-bottom:1px solid #ddd;padding-bottom:4px;'>{html.escape(line[3:])}</h2>")
        elif line.startswith("- "):
            out.append(f"<p style='margin:4px 0 4px 14px;'>• {_inline_bold(line[2:])}</p>")
        elif line.strip() == "":
            out.append("<br/>")
        else:
            out.append(f"<p>{_inline_bold(line)}</p>")

    if summary_df is not None and not summary_df.empty:
        out.append("<h2 style='margin-top:22px;border-bottom:1px solid #ddd;padding-bottom:4px;'>PERFORMANCE SUMMARY</h2>")
        out.append(_performance_table_html(summary_df, universe or {}))

    out.append("</div></body></html>")
    return "\n".join(out)


def _inline_bold(text: str) -> str:
    escaped = html.escape(text)
    return escaped.replace("**", "<strong>", 1).replace("**", "</strong>", 1) if "**" in escaped else escaped


def _performance_table_html(summary_df: pd.DataFrame, universe: Dict[str, Dict[str, str]]) -> str:
    categories = [
        "INDICES",
        "EU SECTORS",
        "US SECTORS",
        "STYLE ETFs",
        "BOND ETFs",
        "CURRENCIES",
        "COMMODITIES",
    ]
    html_rows = [
        "<table style='width:100%;border-collapse:collapse;font-size:13px;'>",
        "<tr style='background:#0b3d91;color:#fff;'><th style='padding:8px;text-align:left;'>Asset</th><th style='padding:8px;text-align:right;'>Return %</th><th style='padding:8px;text-align:right;'>Vol %</th><th style='padding:8px;text-align:right;'>Max DD %</th></tr>",
    ]

    for cat in categories:
        labels = set((universe.get(cat) or {}).keys())
        subset = summary_df.loc[summary_df.index.intersection(labels)]
        if subset.empty:
            continue
        html_rows.append(f"<tr><td colspan='4' style='padding:7px;background:#efefef;font-weight:700;'>{html.escape(cat)}</td></tr>")
        for asset, row in subset.sort_values("Total Return %", ascending=False).iterrows():
            ret = float(row["Total Return %"])
            vol = float(row["Volatility %"])
            mdd = float(row["Max Drawdown %"])
            color = "#0a7a24" if ret >= 0 else "#b00020"
            html_rows.append(
                "<tr>"
                f"<td style='padding:6px;border-bottom:1px solid #eee;'><strong>{html.escape(asset)}</strong></td>"
                f"<td style='padding:6px;text-align:right;color:{color};border-bottom:1px solid #eee;'>{ret:.2f}%</td>"
                f"<td style='padding:6px;text-align:right;border-bottom:1px solid #eee;'>{vol:.2f}%</td>"
                f"<td style='padding:6px;text-align:right;border-bottom:1px solid #eee;'>{mdd:.2f}%</td>"
                "</tr>"
            )

    html_rows.append("</table>")
    return "\n".join(html_rows)
