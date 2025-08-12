import asyncio
import logging

from playwright.async_api import async_playwright
from tqdm import tqdm

from config_app import HOTELS_IDS_FILE, SCREENSHOTS_DIR, MAX_ATTEMPTS_RUN, HEADLESS, MAX_FIRST_RUN
from auth_service import AuthService

from parce_screenshots.utils import (
    set_language_en,
    load_hotel_ids,
    get_title_hotel,
    all_folders_have_count_images,
)
from parce_screenshots.moduls.top_screen import top_screen
from parce_screenshots.moduls.review_screen import review_screen
from parce_screenshots.moduls.attendance import attendance
from parce_screenshots.moduls.dynamic_rating import dynamic_rating
from parce_screenshots.moduls.service_prices import service_prices
from parce_screenshots.moduls.rating_hotels_in_hurghada import rating_hotels_in_hurghada
from parce_screenshots.moduls.last_activity import last_activity


async def run():
    hotel_ids = load_hotel_ids(HOTELS_IDS_FILE)
    if not hotel_ids:
        logging.error("Файл пуст или содержит некорректные ID.")
        return

    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=HEADLESS)
        context = await browser.new_context(
            locale="en-US", viewport={"width": 1005, "height": 1000}
        )

        page = await context.new_page()
        try:
            await set_language_en(page)
            logging.info("Авторизация...")
            await AuthService(page).login()
            logging.info("Авторизация прошла.")
        except Exception:
            logging.exception("Ошибка при авторизации.")
            return

        for hotel_id in tqdm(hotel_ids, desc="Обработка отелей"):
            try:
                logging.info(f"⏳ Работаем с отелем {hotel_id}")
                title = await get_title_hotel(page, hotel_id)

                await top_screen(page, hotel_id, title)
                count_review = await review_screen(page, hotel_id, title)
                await attendance(page, hotel_id, title)
                await dynamic_rating(page, hotel_id, title)
                await service_prices(page, hotel_id, title)
                await rating_hotels_in_hurghada(page, count_review, hotel_id, title)
                await last_activity(page, hotel_id, title)
                logging.info(f"✅ Готово: {hotel_id} ({title})")
            except Exception:
                logging.exception(f"‼️ Ошибка при обработке отеля {hotel_id, title}")

        await browser.close()


async def run_create_report():
    for attempt in range(1, MAX_ATTEMPTS_RUN + 1):
        print(f"\n🌀 Attempt {attempt} of {MAX_ATTEMPTS_RUN}")
        await run()

        if attempt > MAX_FIRST_RUN and all_folders_have_count_images(SCREENSHOTS_DIR, 8):
            print("✅ All folders contain at least 8 images.")
            break
        else:
            print("⚠ Not all folders are complete or second lap. Retrying...\n")
            await asyncio.sleep(1)  # Можно убрать или увеличить паузу при необходимости
    else:
        print("❌ Max attempts reached. Some folders still have less than 8 images.")
