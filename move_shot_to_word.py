from docx import Document
from docx.shared import Pt, Inches
from docx.enum.text import WD_ALIGN_PARAGRAPH
import os

BASE_DIR = "D:\\web_develop\\parcers\\questions\\screenshots"


def create_formatted_doc(base_dir):
    for folder_name in os.listdir(base_dir):
        folder_path = os.path.join(base_dir, folder_name)
        if not os.path.isdir(folder_path):
            continue

        doc = Document()

        # Заголовок
        title = doc.add_paragraph()
        title.alignment = WD_ALIGN_PARAGRAPH.CENTER
        run = title.add_run(folder_name.upper())
        run.bold = True
        run.font.size = Pt(20)

        doc.add_paragraph()  # пустая строка

        for file_name in sorted(os.listdir(folder_path)):
            if not file_name.lower().endswith(('.png', '.jpg', '.jpeg')):
                continue

            # Имя файла по центру
            p = doc.add_paragraph()
            p.alignment = WD_ALIGN_PARAGRAPH.CENTER
            run = p.add_run(file_name)
            run.font.size = Pt(12)

            # Картинка
            image_path = os.path.join(folder_path, file_name)
            try:
                doc.add_picture(image_path, width=Inches(6))
            except Exception as e:
                doc.add_paragraph(f"[Ошибка изображения: {e}]")

            doc.add_paragraph()  # отступ

        # Сохранить файл с названием папки
        safe_name = folder_name.replace(" ", "_").replace("*", "")
        save_path = os.path.join(base_dir, f"{safe_name}.docx")
        doc.save(save_path)
        print(f"Создан файл: {save_path}")


if __name__ == "__main__":
    create_formatted_doc(BASE_DIR)
