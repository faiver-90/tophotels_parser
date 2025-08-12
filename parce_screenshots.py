import asyncio
import logging

from playwright.async_api import async_playwright
from tqdm import tqdm

from concurrent_runner import hotels_needing_retry, run_concurrent, CONCURRENCY
from config_app import (
    HOTELS_IDS_FILE,
    SCREENSHOTS_DIR,
    MAX_ATTEMPTS_RUN,
    HEADLESS,
    MAX_FIRST_RUN,
)
from auth_service import AuthService

from parce_screenshots_moduls.utils import (
    set_language_en,
    load_hotel_ids,
    get_title_hotel,
    all_folders_have_count_images,
)
from parce_screenshots_moduls.moduls.top_screen import top_screen
from parce_screenshots_moduls.moduls.review_screen import review_screen
from parce_screenshots_moduls.moduls.attendance import attendance
from parce_screenshots_moduls.moduls.dynamic_rating import dynamic_rating
from parce_screenshots_moduls.moduls.service_prices import service_prices
from parce_screenshots_moduls.moduls.rating_hotels_in_hurghada import (
    rating_hotels_in_hurghada,
)
from parce_screenshots_moduls.moduls.last_activity import last_activity
from utils import safe_step


# async def run():
#     hotel_ids = load_hotel_ids(HOTELS_IDS_FILE)
#     if not hotel_ids:
#         logging.error("Файл пуст или содержит некорректные ID.")
#         return
#
#     async with async_playwright() as p:
#         browser = await p.chromium.launch(headless=HEADLESS)
#         context = await browser.new_context(
#             locale="en-US", viewport={"width": 1005, "height": 1000}
#         )
#         page = await context.new_page()
#
#         try:
#             await set_language_en(page)
#             logging.info("Авторизация...")
#             await AuthService(page).login()
#             logging.info("Авторизация прошла.")
#         except Exception:
#             logging.exception("Ошибка при авторизации.")
#             return
#
#         # Обычный for + tqdm показывает прогресс, скорость и ETA
#         for hotel_id in tqdm(
#             hotel_ids, desc="Обработка отелей", unit="отель", dynamic_ncols=True
#         ):
#             try:
#                 tqdm.write(
#                     f"→ {hotel_id}"
#                 )  # опционально: вывести текущий ID поверх прогресс-бара
#                 title = await safe_step(get_title_hotel, page, hotel_id)
#
#                 await safe_step(top_screen, page, hotel_id, title)
#                 count_review = await safe_step(review_screen, page, hotel_id, title)
#                 await safe_step(attendance, page, hotel_id, title)
#                 await safe_step(dynamic_rating, page, hotel_id, title)
#                 await safe_step(service_prices, page, hotel_id, title)
#                 await safe_step(
#                     rating_hotels_in_hurghada, page, count_review, hotel_id, title
#                 )
#                 await safe_step(last_activity, page, hotel_id, title)
#
#                 logging.info(f"✅ Готово: {hotel_id} ({title})")
#             except Exception:
#                 logging.exception(
#                     f"‼️ Ошибка при обработке отеля {hotel_id} ({title or 'unknown'})"
#                 )
#
#         await browser.close()


async def run_create_report():
    hotel_ids_all = load_hotel_ids(HOTELS_IDS_FILE)

    for attempt in range(1, MAX_ATTEMPTS_RUN + 1):
        print(f"\n🌀 Attempt {attempt} of {MAX_ATTEMPTS_RUN}")

        # На повторных попытках докидываем ТОЛЬКО те ID, где не хватает картинок
        ids_for_run = (
            hotel_ids_all
            if attempt == 1
            else hotels_needing_retry(SCREENSHOTS_DIR, hotel_ids_all, required_files=8)
        )
        if not ids_for_run:
            print("✅ Всё уже собрано.")
            break

        if CONCURRENCY > 1:
            await run_concurrent(ids_for_run)  # ПАРАЛЛЕЛЬНО

        if attempt >= MAX_FIRST_RUN and all_folders_have_count_images(
            SCREENSHOTS_DIR, 8
        ):
            # После нужного количества кругов — проверяем ещё раз
            left = hotels_needing_retry(
                SCREENSHOTS_DIR, hotel_ids_all, required_files=8
            )
            if not left:
                print("✅ All folders contain at least 8 images.")
                break
        else:
            print("⚠ Ещё один круг…")
            await asyncio.sleep(1)
    else:
        print("❌ Max attempts reached. Some folders still have less than 8 images.")
