from __future__ import annotations

import os
import re
import base64
import mimetypes
from html import escape
from pathlib import Path
from typing import Dict

from config_app import IMAGE_WIDTH_INCHES, CURRENT_MONTH, CURRENT_YEAR


def _linkify(text: str) -> str:
    if not text:
        return ""
    return re.sub(
        r"(https?://[^\s)]+)", r'<a href="\1" target="_blank">\1</a>', escape(text)
    )


def _img_to_data_uri(path: Path) -> str:
    mime, _ = mimetypes.guess_type(path.name)
    if not mime:
        mime = "application/octet-stream"
    data = base64.b64encode(path.read_bytes()).decode("ascii")
    return f"data:{mime};base64,{data}"


def _build_inline_html(
    title_hotel: str,
    url_hotel: str,
    mapping_paragraph: Dict[str, str],
    folder_path: Path,
) -> str:
    max_width_px = int(IMAGE_WIDTH_INCHES * 96)
    css = f"""
    body{{font-family:Arial,Helvetica,sans-serif; color:#111;font-size: 13pt;}}
    .wrap{{max-width:{max_width_px + 40}px; margin:24px auto;}}
    h1, h2, h3{{margin:8px 0;}}
    a{{color:#0645AD;}}
    """

    parts = []
    parts.append(
        f"<!doctype html><html><head><meta charset='utf-8'>"
        f"<meta name='viewport' content='width=device-width,initial-scale=1'>"
        f"<style>{css}</style></head><body><div class='wrap'>"
    )
    parts.append(
        f"<h2 style='font-size:14pt; font-family:Arial,Helvetica,sans-serif;'>Hi, Name. <br>Monthly Statistics Report {escape(CURRENT_MONTH)} {escape(CURRENT_YEAR)}  <a href='{escape(url_hotel)}' target='_blank'>{escape(title_hotel.upper())}</a></h2>"
    )

    for file_name in sorted(os.listdir(folder_path)):
        if not file_name.lower().endswith((".png", ".jpg", ".jpeg")):
            continue

        # --- подпись как UL/LI с отступами сверху/снизу ---
        caption = mapping_paragraph.get(file_name)
        if caption is not None:
            if caption:
                parts.append(
                    f"<ul style='margin:20px 0; padding-left:26px; font-size:12pt; line-height:1.5; font-family:Arial,Helvetica,sans-serif;'>"
                )
                parts.append(
                    f"<li style='margin:8px 0; font-size:12pt; line-height:1.5; font-family:Arial,Helvetica,sans-serif;'>{_linkify(caption)}</li>"
                )
                parts.append("</ul>")

        # --- картинка ---
        img_path = folder_path / file_name
        try:
            data_uri = _img_to_data_uri(img_path)
            parts.append(
                f"<br><div class='imgbox'><img src='{data_uri}' alt=''></div><br>"
            )
        except Exception as e:
            parts.append(
                f"<div style='color:#b00; font-size:12pt'>[Image error: {escape(str(e))}]</div>"
            )

    # # --- подпись: таблица с логотипом и текстом ---
    # try:
    #     logo_path = Path("th_logo") / "logo_1.jpg"
    #     logo_data_uri = _img_to_data_uri(logo_path) if logo_path.exists() else ""
    # except Exception:
    #     logo_data_uri = ""
    #
    # img_html = (
    #     f"<img src='{logo_data_uri}' alt='TopHotels' "
    #     "style='display:block;border:0;outline:none;text-decoration:none;"
    #     "margin:0;padding:0;height:auto;max-width:186px;'>"
    #     if logo_data_uri
    #     else ""
    # )
    #
    # parts.append(f"""
    # <br>
    # <table border="0" cellspacing="0" cellpadding="0" width="600" style="border-collapse:collapse;">
    #   <tr>
    #     <td width="190" valign="top" style="padding:0 70px 0 30px;margin:0;">
    #           {img_html}
    #     </td>
    #     <td valign="top" style="padding:0;margin:0;font-family:'Segoe UI', Arial, sans-serif;font-size:10.5pt;line-height:14pt;color:#000;">
    #       <div style="margin:0;padding:0;font-family:'Segoe UI', Arial, sans-serif;font-size:10.5pt;line-height:14pt;color:#000;">
    #         <em>Best regards,</em>
    #       </div>
    #       <div style="height:6pt;line-height:6pt;font-size:0;">&nbsp;</div>
    #       <div style="margin:0;padding:0;font-family:'Segoe UI', Arial, sans-serif;font-size:10.5pt;line-height:14pt;font-weight:bold;color:#0f4761;">
    #         ISTAT
    #       </div>
    #       <div style="height:4pt;line-height:4pt;font-size:0;">&nbsp;</div>
    #       <div style="margin:0;padding:0;font-family:'Segoe UI', Arial, sans-serif;font-size:10.5pt;line-height:14pt;color:#000;">
    #         ACCOUNT MANAGER
    #       </div>
    #       <div style="height:4pt;line-height:4pt;font-size:0;">&nbsp;</div>
    #       <div style="margin:0;padding:0;font-family:'Segoe UI', Arial, sans-serif;font-size:10.5pt;line-height:14pt;color:#000;">
    #         Project TopHotels.ru
    #       </div>
    #       <div style="height:8pt;line-height:8pt;font-size:0;">&nbsp;</div>
    #       <div style="margin:0;padding:0;font-family:'Segoe UI', Arial, sans-serif;font-size:10.5pt;line-height:14pt;color:#000;">
    #         E-mail:
    #         <a href="mailto:istat@mediatravel.me" style="color:#0070c0;text-decoration:none;font-weight:bold;font-family:'Segoe UI', Arial, sans-serif;font-size:10.5pt;line-height:14pt;">
    #           istat@mediatravel.me
    #         </a>
    #       </div>
    #     </td>
    #   </tr>
    # </table>
    # """)
    #
    # # --- конец подписи ---

    parts.append("</div></body></html>")
    return "".join(parts)
