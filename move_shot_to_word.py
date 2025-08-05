from docx import Document
from docx.shared import Pt, Inches
from docx.enum.text import WD_ALIGN_PARAGRAPH
import os

# 📂 Текущая директория, где находится скрипт
SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))

# 📂 Папка с исходными скриншотами
SCREENSHOTS_DIR = os.path.join(SCRIPT_DIR, "screenshots")

# 📂 Папка, куда сохраняем отчёты
REPORTS_DIR = os.path.join(SCRIPT_DIR, "reports")
os.makedirs(REPORTS_DIR, exist_ok=True)

mapping_paragraph = {
    '01_top_element.png': '',
    '02_populars_element.png': 'Popularity of the hotel',
    '03_reviews.png': 'Rating and recommendations of hotel',
    '04_attendance.png': 'Hotel profile attendance by month: https://tophotels.pro/hotel/al27382/new_stat/attendance',
    '05_dynamic_rating.png': 'Dynamics of the rating & recommendation: https://tophotels.pro/hotel/al27382/new_stat/dynamics#month',
    '06_service_prices.png': 'Log of booking requests: https://tophotels.pro/hotel/al27382/booking/log',
    '07_rating_in_hurghada.png': 'Ranking beyond other hotels in Hurghada– by rating:  https://tophotels.pro/hotel/al27382/new_stat/rating-hotels',
    '08_activity.png': 'Last page activity: https://tophotels.pro/hotel/al27382/activity/index'
}


def create_formatted_doc():
    from datetime import datetime
    curr_month = datetime.now().month
    curr_year = datetime.now().year

    for folder_name in os.listdir(SCREENSHOTS_DIR):
        folder_path = os.path.join(SCREENSHOTS_DIR, folder_name)
        if not os.path.isdir(folder_path):
            continue

        doc = Document()

        # Title line
        title_1 = doc.add_paragraph()
        title_1.alignment = WD_ALIGN_PARAGRAPH.CENTER
        run_1 = title_1.add_run(f'Monthly Statistics Report {curr_month} {curr_year}')
        run_1.font.size = Pt(12)

        # Hotel name
        title_2 = doc.add_paragraph()
        title_2.alignment = WD_ALIGN_PARAGRAPH.CENTER
        run = title_2.add_run(folder_name.upper())
        run.bold = True
        run.font.size = Pt(20)

        for file_name in sorted(os.listdir(folder_path)):
            if not file_name.lower().endswith(('.png', '.jpg', '.jpeg')):
                continue

            if file_name in mapping_paragraph:
                p = doc.add_paragraph()
                p.alignment = WD_ALIGN_PARAGRAPH.LEFT
                run = p.add_run(mapping_paragraph[file_name])
                run.font.size = Pt(12)

            image_path = os.path.join(folder_path, file_name)
            try:
                doc.add_picture(image_path, width=Inches(6))
            except Exception as e:
                doc.add_paragraph(f"[Image error: {e}]")


        # Save report to 'reports'
        safe_name = folder_name.replace(" ", "_").replace("*", "")
        save_path = os.path.join(REPORTS_DIR, f"{safe_name}.docx")
        doc.save(save_path)
        print(f"✔ Report created: {save_path}")


if __name__ == "__main__":
    create_formatted_doc()
