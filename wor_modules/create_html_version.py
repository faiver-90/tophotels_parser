from __future__ import annotations

import os
import re
import base64
import mimetypes
from html import escape
from pathlib import Path
from typing import Dict, Optional


from PIL import Image  # NEW: для изменения размеров изображений

from config_app import IMAGE_WIDTH_INCHES, CURRENT_MONTH, CURRENT_YEAR

# COM-экспорт Word -> HTML (опционально, только Windows + установлен Word)
try:
    import win32com.client as win32  # type: ignore

    _HAS_WORD = True
except Exception:
    _HAS_WORD = False
# =========================
# HTML (резервный чистый inline, как было у вас)
# =========================


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


def _build_inline_html(title_hotel: str, url_hotel: str,
                       mapping_paragraph: Dict[str, str], folder_path: Path) -> str:
    max_width_px = int(IMAGE_WIDTH_INCHES * 96)
    css = f"""
    body{{font-family:Arial,Helvetica,sans-serif; color:#111;}}
    .wrap{{max-width:{max_width_px + 40}px; margin:24px auto;}}
    h1, h2, h3{{margin:8px 0; text-align:center}}
    a{{color:#0645AD;}}
    /* список подписей */
    ul.caplist{{
        margin-top:20px;
        margin-bottom:20px;
        padding-left:26px;
    }}
    ul.caplist > li{{
        margin-top:8px;
        margin-bottom:8px;
        font-size:12pt;
        line-height:1.5;
    }}
    /* картинка */
    .imgbox{{
        margin-top:20px;
        margin-bottom:30px;
    }}
    img{{
        max-width:100%;
        height:auto;
        display:block;
        border:1px solid #ddd;
    }}
    """

    parts = []
    parts.append(
        f"<!doctype html><html><head><meta charset='utf-8'>"
        f"<meta name='viewport' content='width=device-width,initial-scale=1'>"
        f"<style>{css}</style></head><body><div class='wrap'>"
    )
    parts.append(f"<h2>Monthly Statistics Report {escape(CURRENT_MONTH)} {escape(CURRENT_YEAR)}</h2>")
    parts.append(f"<h1><a href='{escape(url_hotel)}' target='_blank'>{escape(title_hotel.upper())}</a></h1>")

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
            parts.append(f"<div class='imgbox'><img src='{data_uri}' alt=''></div>")
        except Exception as e:
            parts.append(f"<div style='color:#b00; font-size:12pt'>[Image error: {escape(str(e))}]</div>")

    parts.append("</div></body></html>")
    return "".join(parts)

# =========================
# NEW: Экспорт DOCX -> Word HTML и встраивание картинок
# =========================


def _export_docx_to_word_html_and_inline(docx_path: Path) -> Optional[Path]:
    """
    Экспортирует DOCX в 'Filtered HTML' через COM (Word), затем:
    - читает созданный HTML
    - находит <img src="..."> и подменяет src на data:URI (base64), читая файлы из ..._files/
    - сохраняет рядом *_word_inline.html
    Возвращает путь к inline-HTML или None, если COM недоступен или произошла ошибка.
    """
    if not _HAS_WORD:
        return None
    try:
        docx_path = Path(docx_path)
        html_path = docx_path.with_suffix(".htm")  # Word по умолчанию .htm
        assets_dir = docx_path.with_name(docx_path.stem + "_files")  # папка ресурсов

        word = win32.gencache.EnsureDispatch("Word.Application")
        word.Visible = False
        doc = word.Documents.Open(str(docx_path))
        # 10 = wdFormatFilteredHTML (более «чистый» HTML с mso-стилями, пригодный для Outlook)
        doc.SaveAs(str(html_path), FileFormat=10)
        doc.Close(False)
        word.Quit()

        # Заменим <img src="assets/..."> на data: URI
        html = html_path.read_text(encoding="utf-8", errors="ignore")

        def _to_data_uri(img_rel_src: str) -> str:
            img_path = assets_dir / Path(img_rel_src).name
            if not img_path.exists():
                # иногда Word пишет относительные пути с подпапками — попробуем как есть
                img_path = assets_dir / img_rel_src
                if not img_path.exists():
                    return img_rel_src  # оставим как есть
            mime, _ = mimetypes.guess_type(img_path.name)
            if not mime:
                mime = "application/octet-stream"
            b64 = base64.b64encode(img_path.read_bytes()).decode("ascii")
            return f"data:{mime};base64,{b64}"

        # грубая, но практичная замена src в тегах <img ...>
        html_inline = re.sub(
            r'(<img\b[^>]*\bsrc=")([^"]+)(")',
            lambda m: f"{m.group(1)}{_to_data_uri(m.group(2))}{m.group(3)}",
            html,
            flags=re.IGNORECASE,
        )

        out_inline = docx_path.with_name(docx_path.stem + "_word_inline.html")
        out_inline.write_text(html_inline, encoding="utf-8")

        # (опционально) можно удалить html и папку ресурсов; я оставлю их, чтобы можно было сравнить
        print(f"✔ Word Filtered HTML (inline) created: {out_inline}")
        return out_inline
    except Exception as e:
        print(f"[WARN] Word HTML export failed: {e}")
        return None