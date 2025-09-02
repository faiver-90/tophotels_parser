from __future__ import annotations

import os
from pathlib import Path

from dotenv import load_dotenv

from word_modules.create_html_version import _build_inline_html
from word_modules.create_meta_data import create_meta_data
from word_modules.create_word_file import create_word_file
from word_modules.resize_all_images import _resize_all_images

try:
    import win32com.client as win32  # type: ignore

    _HAS_WORD = True
except Exception:
    _HAS_WORD = False

from config_app import SCREENSHOTS_DIR

load_dotenv()


def create_formatted_doc(target_image_width_px: int | None = None) -> None:
    """
    Генерирует DOCX и HTML-версии отчёта.
    Дополнительно: если задан target_image_width_px, сначала приводит каждую картинку
    в папке отеля к фиксированной ширине (px) с сохранением пропорций (in-place).
    """
    screenshots_dir = Path(SCREENSHOTS_DIR)

    for folder_name in os.listdir(screenshots_dir):
        if "_" not in folder_name:
            continue  # пропускаем «посторонние» папки
        hotel_id, title_hotel = folder_name.split("_", 1)
        folder_path = screenshots_dir / folder_name
        if not folder_path.is_dir():
            continue

        # 1) Привести картинки к фиксированной ширине, если задано
        if isinstance(target_image_width_px, int) and target_image_width_px > 0:
            _resize_all_images(folder_path, target_image_width_px)

        url_hotel, mapping_paragraph, reports_dir = create_meta_data(
            hotel_id, title_hotel
        )
        create_word_file(
            title_hotel, folder_path, url_hotel, mapping_paragraph, reports_dir
        )
        safe_name = title_hotel.replace(" ", "_").replace("*", "")

        html = _build_inline_html(
            title_hotel, url_hotel, mapping_paragraph, folder_path
        )
        html_path = reports_dir / f"{safe_name}_inline.html"
        html_path.write_text(html, encoding="utf-8")
        print(f"✔ Inline HTML (fallback) created: {html_path}")


if __name__ == "__main__":
    create_formatted_doc(target_image_width_px=1200)
