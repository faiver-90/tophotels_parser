from __future__ import annotations

import os
import re
from pathlib import Path
from typing import Dict

from docx import Document
from docx.enum.text import WD_ALIGN_PARAGRAPH
from docx.oxml import OxmlElement
from docx.oxml.ns import qn
from docx.shared import Inches, Pt, RGBColor, Cm
from dotenv import load_dotenv

from config_app import SCREENSHOTS_DIR, curr_month, curr_year, BASE_URL_TH, BASE_URL_PRO
from utils import get_desktop_dir, normalize_windows_path, load_links

# =========================
# Константы и настройки
# =========================

# Шрифты/размеры
FONT_NAME = "Arial"
FONT_SIZE_TITLE = 14  # заголовок "Monthly Statistics Report ..."
FONT_SIZE_HOTEL_LINK = 18  # кликабельное название отеля
FONT_SIZE_CAPTION = 12  # подписи к скринам

# Размер картинок
IMAGE_WIDTH_INCHES = 6

# Разрыв страницы перед этими файлами
PAGE_BREAK_FILES = {"07_rating_in_hurghada.png", "08_activity.png", "04_attendance.png"}

# Регэксп для URL (не захватываем завершающие скобки/знаки препинания)
URL_RE = re.compile(r"(https?://[^\s)]+)")

load_dotenv()


# =========================
# Вспомогательные функции
# =========================


def add_header_image(
    doc: Document,
    image_path: str | Path,
    width_inches: float = 2.0,
    top_margin_cm: float = 1.0,
    bottom_margin_cm: float = 0.5,
) -> None:
    """
    Вставляет картинку в верхний колонтитул во всех секциях документа
    и задаёт отступы сверху и снизу.

    Args:
        doc: Объект Document (python-docx).
        image_path: Путь к картинке.
        width_inches: Ширина картинки в дюймах.
        top_margin_cm: Отступ от колонтитула до текста сверху.
        bottom_margin_cm: Отступ снизу колонтитула (визуальный).
    """
    image_path = Path(image_path)

    if not image_path.exists():
        raise FileNotFoundError(f"Файл {image_path} не найден.")

    for section in doc.sections:
        section.header_distance = Cm(top_margin_cm)  # Отступ сверху
        header = section.header
        paragraph = (
            header.paragraphs[0] if header.paragraphs else header.add_paragraph()
        )
        paragraph.alignment = WD_ALIGN_PARAGRAPH.CENTER

        run = paragraph.add_run()
        run.add_picture(str(image_path), width=Inches(width_inches))

        # Визуальный отступ снизу — пустой абзац
        if bottom_margin_cm > 0:
            empty_p = header.add_paragraph()
            empty_p.paragraph_format.space_before = Pt(0)
            empty_p.paragraph_format.space_after = Cm(bottom_margin_cm)


def ensure_normal_style_arial(doc: Document) -> None:
    """
    Применяет Arial к стилю Normal и фиксирует eastAsia/ascii/hAnsi,
    чтобы Word не подменял шрифты.
    """
    style = doc.styles["Normal"]
    style.font.name = FONT_NAME
    rPr = style._element.rPr

    rPr.rFonts.set(qn("w:ascii"), FONT_NAME)
    rPr.rFonts.set(qn("w:hAnsi"), FONT_NAME)
    rPr.rFonts.set(qn("w:eastAsia"), FONT_NAME)


def set_run_arial(run, size_pt: int) -> None:
    """
    Применяет Arial и точный размер к обычному run (не гиперссылке).
    """
    run.font.name = FONT_NAME
    run.font.size = Pt(size_pt)
    rPr = run._element.rPr
    rPr.rFonts.set(qn("w:ascii"), FONT_NAME)
    rPr.rFonts.set(qn("w:hAnsi"), FONT_NAME)
    rPr.rFonts.set(qn("w:eastAsia"), FONT_NAME)


def add_hyperlink(
    paragraph,
    text: str,
    url: str,
    *,
    font_name: str = FONT_NAME,
    font_size_pt: int = FONT_SIZE_CAPTION,
    bold: bool = False,
    underline: bool = True,
    color: str = "0000FF",
):
    """
    Создаёт кликабельную гиперссылку без применения стиля 'Hyperlink'
    (чтобы Word не сбрасывал размер до 11/12 pt).

    Возвращает созданный python-docx Run (на случай, если нужно донастроить).
    """
    part = paragraph.part
    r_id = part.relate_to(
        url,
        "http://schemas.openxmlformats.org/officeDocument/2006/relationships/hyperlink",
        is_external=True,
    )

    # <w:hyperlink r:id="...">
    hyperlink = OxmlElement("w:hyperlink")
    hyperlink.set(qn("r:id"), r_id)

    # создаём обычный run и сразу задаём вид
    run = paragraph.add_run(text)
    run.font.name = font_name
    run.font.size = Pt(font_size_pt)
    run.font.bold = bold
    run.font.underline = underline
    if color:
        run.font.color.rgb = RGBColor.from_string(color)

    rPr = run._element.rPr
    rPr.rFonts.set(qn("w:ascii"), font_name)
    rPr.rFonts.set(qn("w:hAnsi"), font_name)
    rPr.rFonts.set(qn("w:eastAsia"), font_name)

    # перемещаем run внутрь <w:hyperlink>
    hyperlink.append(run._element)
    paragraph._p.append(hyperlink)
    return run


def add_text_with_links(
    paragraph, text: str, *, font_size_pt: int = FONT_SIZE_CAPTION
) -> None:
    """
    Разбивает строку на сегменты: обычный текст и URL.
    Обычный текст вставляет как run, URL — как кликабельные гиперссылки.
    """
    pos = 0
    for m in URL_RE.finditer(text or ""):
        # текст до ссылки
        if m.start() > pos:
            prefix = text[pos : m.start()]
            if prefix:
                set_run_arial(paragraph.add_run(prefix), size_pt=font_size_pt)

        url = m.group(1)
        add_hyperlink(paragraph, url, url, font_size_pt=font_size_pt)
        pos = m.end()

    # хвост после последней ссылки
    if pos < len(text or ""):
        tail = text[pos:]
        if tail:
            set_run_arial(paragraph.add_run(tail), size_pt=font_size_pt)


def build_mapping(hotel_id: int, *, rating_url: str | None = None, city) -> Dict[str, str]:
    base = BASE_URL_PRO + "hotel/" + str(hotel_id)
    rating_url = rating_url or f"{base}/new_stat/rating-hotels"
    return {
        "01_top_element.png": "",
        "02_populars_element.png": "Popularity of the hotel",
        "03_reviews.png": "Rating and recommendations of hotel",
        "04_attendance.png": f"Hotel profile attendance by month: {base}/new_stat/attendance",
        "05_dynamic_rating.png": f"Dynamics of the rating & recommendation: {base}/new_stat/dynamics#month",
        "06_service_prices.png": f"Log of booking requests: {base}/stat/profile?group=week&vw=grouped",
        "07_rating_in_hurghada.png": f"Ranking beyond other hotels in {city} – by rating: {rating_url}",
        "08_activity.png": f"Last page activity: {base}/activity/index",
    }


def build_reports_dir(curr_year: str, curr_month: str) -> Path:
    """
    Строит директорию для отчётов:
    либо из ENV PATH_FOR_REPORTS, либо на рабочем столе.
    """
    raw_path = os.getenv("PATH_FOR_REPORTS")
    base_dir = normalize_windows_path(raw_path) if raw_path else get_desktop_dir()
    reports = Path(base_dir) / "TopHotels Reports" / f"{curr_year}" / f"{curr_month}"
    reports.mkdir(parents=True, exist_ok=True)
    return reports


# =========================
# Основная логика
# =========================


def create_formatted_doc() -> None:
    reports_dir = build_reports_dir(curr_year, curr_month)
    screenshots_dir = Path(SCREENSHOTS_DIR)

    for folder_name in os.listdir(screenshots_dir):
        hotel_id, title_hotel = folder_name.split("_", 1)
        folder_path = screenshots_dir / folder_name
        if not folder_path.is_dir():
            continue

        json_file = load_links(hotel_id, title_hotel)
        city = json_file.get('city', 'City')

        rating_url = json_file.get("rating_url")
        url_hotel = f"{BASE_URL_TH}hotel/{hotel_id}"
        mapping_paragraph = build_mapping(hotel_id, rating_url=rating_url, city=city)

        doc = Document()
        add_header_image(
            doc, "th_logo/logo_1.jpg", width_inches=1.5, bottom_margin_cm=0.2
        )

        ensure_normal_style_arial(doc)

        # Заголовок файла
        title_1 = doc.add_paragraph()
        title_1.alignment = WD_ALIGN_PARAGRAPH.CENTER
        run_1 = title_1.add_run(f"Monthly Statistics Report {curr_month} {curr_year}")
        set_run_arial(run_1, size_pt=FONT_SIZE_TITLE)

        # Название отеля — кликабельное, строго 18 pt
        title_2 = doc.add_paragraph()
        title_2.alignment = WD_ALIGN_PARAGRAPH.CENTER
        add_hyperlink(
            title_2,
            title_hotel.upper(),
            url_hotel,
            font_size_pt=FONT_SIZE_HOTEL_LINK,
            bold=True,
        )

        # Тело: подписи и картинки
        for file_name in sorted(os.listdir(folder_path)):
            if not file_name.lower().endswith((".png", ".jpg", ".jpeg")):
                continue

            if file_name in PAGE_BREAK_FILES:
                doc.add_page_break()

            caption = mapping_paragraph.get(file_name)
            if caption is not None:
                p = doc.add_paragraph()
                p.alignment = WD_ALIGN_PARAGRAPH.LEFT
                if caption:
                    add_text_with_links(p, caption, font_size_pt=FONT_SIZE_CAPTION)

            image_path = folder_path / file_name
            try:
                doc.add_picture(str(image_path), width=Inches(IMAGE_WIDTH_INCHES))
            except Exception as e:
                err_p = doc.add_paragraph(f"[Image error: {e}]")
                for r in err_p.runs:
                    set_run_arial(r, size_pt=FONT_SIZE_CAPTION)

        # Сохранение
        safe_name = title_hotel.replace(" ", "_").replace("*", "")
        save_path = reports_dir / f"{safe_name}.docx"
        doc.save(save_path)
        print(f"✔ Report created: {save_path}")


if __name__ == "__main__":
    create_formatted_doc()
