import asyncio
import logging
import os
import time
from datetime import datetime
from typing import List

from playwright.async_api import async_playwright, Page
from main import AuthService

logging.basicConfig(
    level=logging.INFO,
    format='[%(asctime)s] %(levelname)s: %(message)s',
    handlers=[
        logging.FileHandler("script.log", mode='a', encoding='utf-8'),
        logging.StreamHandler()
    ]
)

BASE_URL_RU = 'https://tophotels.ru/en/'
BASE_URL_PRO = 'https://tophotels.pro/'
INPUT_FILE = 'ids.txt'
SCREENSHOT_DIR = 'screenshots'

TOP_ELEMENT_LOCATOR = '#container > div.topline'
POPULARS_LOCATOR = '#container > div.js-start-fixed-btn.grid > article > div.card-hotel-wrap > section.stata-bubble.stata-bubble--fz13-laptop.no-scrollbar'
REVIEW_LOCATOR = '#container > div.card-hotel-wrap.mt30 > section:nth-child(3) > div > section'
ATTENDANCE_LOCATOR = '#pg-container-stat > div:nth-child(1)'
ACTIVITY_LOCATOR = '#tab-pjax-index > div.js-bth__tbl.js-act-long-view'
RATING_HOTEL_IN_HURGHADA_LOCATOR = '.bth__scrolable-tbl .bth__table--bordering'
SERVICES_AND_PRICES_LOCATOR = '#hotelProfileApp > table:nth-child(5)'


def load_hotel_ids(file_path: str) -> List[str]:
    with open(file_path, 'r', encoding='utf-8') as f:
        return [
            line.strip()
            for line in f
            if line.strip().lower().startswith("al") and line.strip()[2:].isdigit()
        ]


async def get_title_hotel(page: Page, hotel_id):
    try:
        url = BASE_URL_RU + "hotel/" + hotel_id
        await page.goto(url, timeout=0)
        element = await page.query_selector('#container > div.topline > section.topline__info > a > h1')
        title = await element.text_content()
        return title.strip()[:-2].strip()
    except Exception as e:
        logging.exception("[get_title_hotel] Ошибка при выполнении")


async def top_screen(page: Page, hotel_id, hotel_title=None):
    try:
        'https://tophotels.ru/en/hotel/al27382'
        url = BASE_URL_RU + "hotel/" + hotel_id
        await page.goto(url, timeout=0)
        element = await page.query_selector(TOP_ELEMENT_LOCATOR)
        await element.screenshot(path=f"{SCREENSHOT_DIR}/{hotel_title}/01_top_element.png")
        element2 = await page.query_selector(POPULARS_LOCATOR)
        await element2.screenshot(path=f"{SCREENSHOT_DIR}/{hotel_title}/02_populars_element.png")
    except Exception as e:
        logging.exception(f"[top_screen] Ошибка при выполнении {url}")


async def review_screen(page: Page, hotel_id, hotel_title=None):
    try:
        'https://tophotels.ru/en/hotel/al27382/reviews'
        url = BASE_URL_RU + "hotel/" + hotel_id + '/reviews'
        await page.goto(url, timeout=0)
        element = await page.query_selector(REVIEW_LOCATOR)
        await element.screenshot(path=f'{SCREENSHOT_DIR}/{hotel_title or "default"}/03_reviews.png')

        count_review_locator = '#container > div.card-hotel-wrap.mt30 > section:nth-child(3) > div > section > ' \
                               'div.card-hotel-rating-list > ul:nth-child(4) > li:nth-child(1) > b'
        return await page.locator(count_review_locator).text_content()
    except Exception as e:
        logging.exception(f"[review_screen] Ошибка при выполнении {url}")


async def attendance(page: Page, hotel_id, hotel_title=None):
    try:
        'https://tophotels.pro/hotel/al27382/new_stat/attendance?filter%5Bperiod%5D=30'

        url = BASE_URL_PRO + "hotel/" + hotel_id + '/new_stat/attendance?filter%5Bperiod%5D=30'
        await page.goto(url, timeout=0)

        element = await page.query_selector(ATTENDANCE_LOCATOR)
        await element.screenshot(path=f'{SCREENSHOT_DIR}/{hotel_title or "default"}/04_attendance.png')
    except Exception as e:
        logging.exception(f"[attendance] Ошибка при выполнении {url}")


async def dynamic_rating(page: Page, hotel_id, hotel_title=None):
    current_year = datetime.now().year

    try:
        url = f"https://tophotels.pro/hotel/{hotel_id}/new_stat/dynamics#month"
        await page.goto(url)
        await page.wait_for_selector('#panel-month .bth__tbl', state="visible", timeout=10000)
        await page.wait_for_timeout(1000)

        # Поиск заголовка нужного года
        header_locator = page.locator(
            f"xpath=//div[@id='panel-month']//div[contains(@class, 'bth__row') and contains(., 'In total: {current_year}')]"
        )

        try:
            await header_locator.wait_for(timeout=5000)
        except:
            print(f"❌ Не найден блок 'In total: {current_year}' для отеля {hotel_id}")
            return

        header_index = await header_locator.evaluate(
            "node => Array.from(node.parentNode.children).indexOf(node)"
        )

        # Сбор всех строк таблицы
        all_rows = page.locator("#panel-month .bth__row")
        count = await all_rows.count()

        indexes = []
        for i in range(header_index + 1, count):
            row = all_rows.nth(i)
            html = await row.evaluate("e => e.outerHTML")
            if 'In total:' in html:
                break
            indexes.append(i)

        elements_to_shot = [all_rows.nth(i) for i in [header_index] + indexes]
        boxes = []

        for el in elements_to_shot:
            try:
                await el.scroll_into_view_if_needed(timeout=2000)
                box = await el.bounding_box()
                if box:
                    boxes.append(box)
            except Exception as e:
                print(f"⚠️ Пропущен элемент: {e}")

        if not boxes:
            print(f"❌ Не найдены строки для {current_year} в отеле {hotel_id}")
            return

        # Область скриншота
        min_x = min(box['x'] for box in boxes)
        min_y = min(box['y'] for box in boxes)
        max_x = max(box['x'] + box['width'] for box in boxes)
        max_y = max(box['y'] + box['height'] for box in boxes)

        clip_area = {
            "x": min_x,
            "y": min_y,
            "width": max_x - min_x,
            "height": max_y - min_y,
        }

        if clip_area["width"] <= 0 or clip_area["height"] <= 0:
            print(f"❌ Некорректная область скрина: {clip_area}")
            return

        os.makedirs(f"{SCREENSHOT_DIR}/{hotel_title or 'default'}", exist_ok=True)
        path = f'{SCREENSHOT_DIR}/{hotel_title or "default"}/05_dynamic_rating.png'

        await page.screenshot(path=path, clip=clip_area)

        print(f"✅ Скриншот сохранён: {path}")

    except Exception as e:
        logging.exception(f"[dynamic_rating] Ошибка при обработке отеля {hotel_id}: {e}, {url}")


async def service_prices(page: Page, hotel_id, hotel_title=None):
    'https://tophotels.pro/al/317844/stat/profile?group=day&vw=grouped'
    'проблема с ТГ на странице и ссылка не проходит в цикле'
    try:
        url = f'https://tophotels.pro/al/{hotel_id[2:]}/stat/profile?group=day&vw=grouped'
        await page.goto(url, timeout=0)

        locator = page.locator("section.js-block.thpro-tg-infoblock > i")

        try:
            if await locator.is_visible():
                await locator.click()
        except Exception as e:
            logging.exception(f'Клик на телеграм сломался, {e}')

        await asyncio.sleep(2)

        element = await page.query_selector(SERVICES_AND_PRICES_LOCATOR)
        old_viewport = page.viewport_size  # TODO посмотреть почему не меняется масштаб и падает
        await page.set_viewport_size({"width": 1400, "height": 1000})
        await element.screenshot(path=f'{SCREENSHOT_DIR}/{hotel_title or "default"}/06_service_prices.png')
        await page.set_viewport_size(old_viewport)
    except Exception as e:
        logging.exception(f"[service_prices] Ошибка при выполнении {url}")


async def rating_hotels_in_hurghada(page, count_review, hotel_id, hotel_title=None):
    'https://tophotels.pro/hotel/al52488/new_stat/rating-hotels'
    url = BASE_URL_PRO + f'hotel/{hotel_id}' + '/new_stat/rating-hotels'

    try:
        await page.goto(url, timeout=5000)

        page_content = await page.content()
        if "There is no data for the hotel" in page_content:
            logging.warning(f"[{hotel_id}] Нет данных по отелю ({hotel_title}) — 'There is no data for the hotel'")
            return
        if "To activate your business account, contact us" in page_content:
            element = page.query_selector('#tab-pjax-index > div > div.js-act-long-view')
            await element.screenshot(path=f'{SCREENSHOT_DIR}/{hotel_title or "default"}/07_rating_in_hurghada.png')
            return
        locator_10 = '#tab-pjax-index > div > div.js-act-long-view > div:nth-child(5) > table > tbody > ' \
                     'tr:nth-child(2) > td:nth-child(2) > a'
        locator_50 = '#tab-pjax-index > div > div.js-act-long-view > div:nth-child(5) > table > tbody > ' \
                     'tr:nth-child(3) > td:nth-child(2) > a'
        if 10 < int(count_review.replace(" ", "")) < 50:
            await page.click(locator_10)
        else:
            await page.click(locator_50)

        await page.wait_for_selector(RATING_HOTEL_IN_HURGHADA_LOCATOR)
        element = await page.query_selector(RATING_HOTEL_IN_HURGHADA_LOCATOR)

        if element:
            await element.screenshot(path=f'{SCREENSHOT_DIR}/{hotel_title or "default"}/07_rating_in_hurghada.png')
        else:
            print(f"[!] Таблица рейтинга не найдена у отеля {hotel_id} на странице {url}")
    except Exception as e:
        element = await page.query_selector('#tab-pjax-index > div > div.js-act-long-view')
        await element.screenshot(path=f'{SCREENSHOT_DIR}/{hotel_title or "default"}/07_rating_in_hurghada.png')
        logging.exception(f"[rating_hotels_in_hurghada] Ошибка при выполнении {url}")


async def last_activity(page: Page, hotel_id, hotel_title=None):
    try:
        'https://tophotels.pro/hotel/al27382/activity/index'
        url = BASE_URL_PRO + "hotel/" + hotel_id + '/activity/index'
        await page.goto(url, timeout=0)

        element = await page.query_selector(ACTIVITY_LOCATOR)

        old_viewport = page.viewport_size
        await page.set_viewport_size({"width": 1400, "height": 1000})
        await element.screenshot(path=f'{SCREENSHOT_DIR}/{hotel_title or "default"}/08_activity.png')
        await page.set_viewport_size(old_viewport)
    except Exception as e:
        logging.exception(f"[last_activity] Ошибка при выполнении {url}")


async def set_language_en(page: Page):
    try:
        await page.goto(BASE_URL_PRO)
        await page.click(
            'body > div.page > header > section > div.header__r-col.header__r-col--abs-right > div > div > button > i')
        await page.wait_for_selector('#pp-lang:not(.hidden)', timeout=30000)
        await page.click('#pp-lang li[data-key="en"]')
        await asyncio.sleep(3)
        # Ждём, пока пропадёт попап (появится класс hidden)
        # await page.wait_for_selector('#pplang.hidden', timeout=3000)
    except Exception as e:
        print(f"[set_language_en] Ошибка при выборе языка: {e}")


async def run():
    hotel_ids = load_hotel_ids(INPUT_FILE)
    if not hotel_ids:
        logging.error("Файл пуст или содержит некорректные ID.")
        return

    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=False)
        context = await browser.new_context(locale='en-US', viewport={"width": 1005, "height": 1000})
        page = await context.new_page()
        try:
            await set_language_en(page)
            logging.info("Авторизация...")
            await AuthService(page).login()
            logging.info("Авторизация прошла.")
        except Exception as e:
            logging.exception("Ошибка при авторизации.")
            return

        for hotel_id in hotel_ids:
            try:
                logging.info(f"⏳ Работаем с отелем {hotel_id}")
                title = await get_title_hotel(page, hotel_id)
                os.makedirs(f"{SCREENSHOT_DIR}/{title}", exist_ok=True)

                await top_screen(page, hotel_id, title)
                count_review = await review_screen(page, hotel_id, title)
                await attendance(page, hotel_id, title)
                await dynamic_rating(page, hotel_id, title)
                await service_prices(page, hotel_id, title)
                count_review = str(5)
                await rating_hotels_in_hurghada(page, count_review, hotel_id, title)
                # await last_activity(page, hotel_id, title)
                logging.info(f"✅ Готово: {hotel_id} ({title})")
            except Exception as e:
                logging.exception(f"‼️ Ошибка при обработке отеля {hotel_id, title}")

        await browser.close()


if __name__ == '__main__':
    asyncio.run(run())
