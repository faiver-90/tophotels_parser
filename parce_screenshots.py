import asyncio
import logging
import os
from PIL import Image
from datetime import datetime
from typing import List
from tenacity import retry, stop_after_attempt, wait_fixed, retry_if_exception_type
from playwright.async_api import Error as PlaywrightError

from playwright.async_api import async_playwright, Page
from tqdm import tqdm

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
INPUT_FILE = 'ids_shot_4_image.txt'
SCREENSHOT_DIR = 'screenshots'

TOP_ELEMENT_LOCATOR = '#container > div.topline'
POPULARS_LOCATOR = '#container > div.js-start-fixed-btn.grid > article > div.card-hotel-wrap > section.stata-bubble.stata-bubble--fz13-laptop.no-scrollbar'
REVIEW_LOCATOR = '#container > div.card-hotel-wrap.mt30 > section:nth-child(3) > div > section'
ATTENDANCE_LOCATOR = '#pg-container-stat > div:nth-child(1)'
ACTIVITY_LOCATOR = '#tab-pjax-index > div.js-bth__tbl.js-act-long-view'
RATING_HOTEL_IN_HURGHADA_LOCATOR = '.bth__scrolable-tbl .bth__table--bordering'
SERVICES_AND_PRICES_LOCATOR = '#hotelProfileApp > table:nth-child(5)'
TG_HIDE_LOCATOR = "section.js-block.thpro-tg-infoblock > i"
ALL_TABLE_RATING_OVEREVIEW_LOCATOR = '#tab-pjax-index > div > div.js-act-long-view'

FLAG_LOCATOR = 'body > div.page > header > section > div.header__r-col.header__r-col--abs-right > div > div > button > i'


def load_hotel_ids(file_path: str) -> List[str]:
    with open(file_path, 'r', encoding='utf-8') as f:
        return [
            line.strip()
            for line in f
            if line.strip().lower().startswith("al") and line.strip()[2:].isdigit()
        ]


@retry(
    stop=stop_after_attempt(3),
    wait=wait_fixed(2),
    retry=retry_if_exception_type(PlaywrightError)
)
async def get_title_hotel(page: Page, hotel_id):
    try:
        url = BASE_URL_RU + "hotel/" + hotel_id
        await page.goto(url, timeout=0)
        await page.wait_for_selector('#container > div.topline > section.topline__info > a > h1',
                                     state="visible",
                                     timeout=30000)
        element = await page.query_selector('#container > div.topline > section.topline__info > a > h1')
        if element is None:
            raise PlaywrightError("title_hotel не найден")
        title = await element.text_content()
        return title.strip()[:-2].strip()
    except Exception as e:
        logging.exception("[get_title_hotel] Ошибка при выполнении")


@retry(
    stop=stop_after_attempt(3),
    wait=wait_fixed(2),
    retry=retry_if_exception_type(PlaywrightError)
)
async def top_screen(page: Page, hotel_id, hotel_title=None):
    try:
        'https://tophotels.ru/en/hotel/al27382'
        url = BASE_URL_RU + "hotel/" + hotel_id
        await page.goto(url, timeout=0)

        await page.wait_for_selector(TOP_ELEMENT_LOCATOR,
                                     state="visible",
                                     timeout=30000)
        await page.wait_for_selector(POPULARS_LOCATOR,
                                     state="visible",
                                     timeout=30000)

        element = await page.query_selector(TOP_ELEMENT_LOCATOR)

        if element is None:
            raise PlaywrightError("TOP_ELEMENT_LOCATOR не найден")

        await element.screenshot(path=f"{SCREENSHOT_DIR}/{hotel_title}/01_top_element.png")
        element2 = await page.query_selector(POPULARS_LOCATOR)
        await element2.screenshot(path=f"{SCREENSHOT_DIR}/{hotel_title}/02_populars_element.png")
    except Exception as e:
        logging.exception(f"[top_screen] Ошибка при выполнении {url}")


@retry(
    stop=stop_after_attempt(3),
    wait=wait_fixed(2),
    retry=retry_if_exception_type(PlaywrightError)
)
async def review_screen(page: Page, hotel_id, hotel_title=None):
    try:
        'https://tophotels.ru/en/hotel/al27382/reviews'
        url = BASE_URL_RU + "hotel/" + hotel_id + '/reviews'
        await page.goto(url, timeout=0)
        await page.wait_for_selector(REVIEW_LOCATOR,
                                     state="visible",
                                     timeout=30000)

        element = await page.query_selector(REVIEW_LOCATOR)
        await element.screenshot(path=f'{SCREENSHOT_DIR}/{hotel_title or "default"}/03_reviews.png')

        count_review_locator = '#container > div.card-hotel-wrap.mt30 > section:nth-child(3) > div > section > ' \
                               'div.card-hotel-rating-list > ul:nth-child(4) > li:nth-child(1) > b'
        return await page.locator(count_review_locator).text_content()
    except Exception as e:
        logging.exception(f"[review_screen] Ошибка при выполнении {url}")


@retry(
    stop=stop_after_attempt(3),
    wait=wait_fixed(2),
    retry=retry_if_exception_type(PlaywrightError)
)
async def attendance(page: Page, hotel_id, hotel_title=None):
    url = BASE_URL_PRO + "hotel/" + hotel_id + '/new_stat/attendance?filter%5Bperiod%5D=30'
    incorrect_data_selector = '#cstm-filter-frm > article > div.js-filter-info.filter-new__info-wrap'
    activation_required_selector = '#pg-container-stat > div > table'
    attempts = 3

    try:
        for attempt in range(attempts):
            await page.goto(url, timeout=0)

            # Ждём основной контент
            await page.wait_for_selector(ATTENDANCE_LOCATOR, state="visible", timeout=30000)

            # 1Проверка: "неверные данные"
            if await page.is_visible(incorrect_data_selector):
                text = await page.inner_text(incorrect_data_selector)
                if "At the moment, the service may show incorrect data" in text:
                    logging.warning(
                        f"[attendance] Предупреждение о данных на {hotel_id}. Попытка {attempt + 1} из {attempts}")
                    await asyncio.sleep(2)
                    continue  # пробуем ещё раз

            # Проверка: "требуется активация"
            page_content = await page.content()
            if "Attention! For this report you need an additional activation." in page_content:
                logging.warning(f"[attendance] Требуется активация отчёта для {hotel_id}")
                try:
                    element = await page.query_selector(activation_required_selector)
                    if element:
                        path = f'{SCREENSHOT_DIR}/{hotel_title or "default"}/04_attendance.png'
                        await element.screenshot(path=path)
                        logging.info(f"[attendance] Скриншот таблицы при требуемой активации сохранён: {path}")
                    else:
                        logging.warning(f"[attendance] Таблица при активации не найдена на {hotel_id}")
                except Exception as e:
                    logging.exception(f"[attendance] Ошибка при скриншоте таблицы активации: {e}")
                return

            # Всё нормально — делаем обычный скриншот
            element = await page.query_selector(ATTENDANCE_LOCATOR)
            await element.screenshot(path=f'{SCREENSHOT_DIR}/{hotel_title or "default"}/04_attendance.png')
            return

        # Ошибка "неверные данные" осталась после всех попыток
        if await page.is_visible(incorrect_data_selector):
            error_element = await page.query_selector(incorrect_data_selector)
            await error_element.screenshot(path=f'{SCREENSHOT_DIR}/{hotel_title or "default"}/04_attendance.png')
            logging.warning(f"[attendance] После {attempts} попыток ошибка осталась. Сделан скрин ошибки.")
    except Exception as e:
        logging.exception(f"[attendance] Ошибка при выполнении {url}")


@retry(
    stop=stop_after_attempt(3),
    wait=wait_fixed(2),
    retry=retry_if_exception_type(PlaywrightError)
)
async def dynamic_rating(page: Page, hotel_id, hotel_title=None):
    current_year = datetime.now().year

    try:
        url = BASE_URL_PRO + 'hotel/' + f"{hotel_id}/new_stat/dynamics#month"
        print(url)
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
    except Exception as e:
        logging.exception(f"[dynamic_rating] Ошибка при обработке отеля {hotel_id}: {e}, {url}")


@retry(
    stop=stop_after_attempt(3),
    wait=wait_fixed(2),
    retry=retry_if_exception_type(PlaywrightError)
)
async def hide_tg(page: Page):
    locator = page.locator(TG_HIDE_LOCATOR)

    try:
        if await locator.is_visible():
            await locator.click()
    except Exception as e:
        logging.exception(f'Клик на телеграм сломался, {e}')


@retry(
    stop=stop_after_attempt(3),
    wait=wait_fixed(2),
    retry=retry_if_exception_type(PlaywrightError)
)
async def service_prices(page: Page, hotel_id, hotel_title=None):
    'https://tophotels.pro/al/317844/stat/profile?group=day&vw=grouped'
    try:
        url = BASE_URL_PRO + f'al/{hotel_id[2:]}/stat/profile?group=day&vw=grouped'
        print(url)
        await page.goto(url, timeout=0)

        await hide_tg(page)

        await asyncio.sleep(2)

        await page.wait_for_selector(SERVICES_AND_PRICES_LOCATOR,
                                     state="visible",
                                     timeout=30000)

        element = await page.query_selector(SERVICES_AND_PRICES_LOCATOR)

        old_viewport = page.viewport_size  # TODO посмотреть почему не меняется масштаб и падает
        await page.set_viewport_size({"width": 1400, "height": 1000})
        await element.screenshot(path=f'{SCREENSHOT_DIR}/{hotel_title or "default"}/06_service_prices.png')
        await page.set_viewport_size(old_viewport)
    except Exception as e:
        logging.exception(f"[service_prices] Ошибка при выполнении {url}")


@retry(
    stop=stop_after_attempt(3),
    wait=wait_fixed(2),
    retry=retry_if_exception_type(PlaywrightError)
)
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
            try:
                await page.wait_for_selector(ALL_TABLE_RATING_OVEREVIEW_LOCATOR, timeout=30000)
                element = await page.query_selector(ALL_TABLE_RATING_OVEREVIEW_LOCATOR)

                if element is None:
                    raise PlaywrightError("Элемент ALL_TABLE_RATING_OVEREVIEW_LOCATOR не найден")

                await element.screenshot(path=f'{SCREENSHOT_DIR}/{hotel_title or "default"}/07_rating_in_hurghada.png')
                return
            except PlaywrightError as e:
                logging.exception(f"❌ Не удалось найти элемент активности для отеля {hotel_id}: {e}")
                return

        locator_10 = '#tab-pjax-index > div > div.js-act-long-view > div:nth-child(5) > table > tbody > ' \
                     'tr:nth-child(2) > td:nth-child(2) > a'
        locator_50 = '#tab-pjax-index > div > div.js-act-long-view > div:nth-child(5) > table > tbody > ' \
                     'tr:nth-child(3) > td:nth-child(2) > a'
        if 10 < int(count_review.replace(" ", "")) < 50:
            await page.click(locator_10)
        else:
            await page.click(locator_50)

        await page.wait_for_selector(RATING_HOTEL_IN_HURGHADA_LOCATOR,
                                     state="visible",
                                     timeout=30000)

        await page.wait_for_selector(RATING_HOTEL_IN_HURGHADA_LOCATOR)
        element = await page.query_selector(RATING_HOTEL_IN_HURGHADA_LOCATOR)

        if element:
            await element.screenshot(path=f'{SCREENSHOT_DIR}/{hotel_title or "default"}/07_rating_in_hurghada.png')
        else:
            print(f"[!] Таблица рейтинга не найдена у отеля {hotel_id} на странице {url}")
    except Exception as e:
        element = await page.query_selector(ALL_TABLE_RATING_OVEREVIEW_LOCATOR)
        if element is None:
            raise PlaywrightError(f"[{hotel_id}] Элемент не найден даже в except — повторяем попытку")
        await element.screenshot(path=f'{SCREENSHOT_DIR}/{hotel_title or "default"}/07_rating_in_hurghada.png')
        logging.exception(f"[rating_hotels_in_hurghada] Ошибка при выполнении {url}")


@retry(
    stop=stop_after_attempt(3),
    wait=wait_fixed(2),
    retry=retry_if_exception_type(PlaywrightError)
)
async def last_activity(page: Page, hotel_id, hotel_title=None):
    try:
        url = BASE_URL_PRO + "hotel/" + hotel_id + '/activity/index'
        await page.goto(url, timeout=0)

        await page.wait_for_selector(ACTIVITY_LOCATOR, state="visible", timeout=30000)

        element = await page.query_selector(ACTIVITY_LOCATOR)
        if element is None:
            raise PlaywrightError("Элемент ACTIVITY_LOCATOR не найден")

        old_viewport = page.viewport_size
        await page.set_viewport_size({"width": 1400, "height": 1000})

        screenshot_dir = os.path.join(SCREENSHOT_DIR, hotel_title or "default")
        os.makedirs(screenshot_dir, exist_ok=True)

        full_path = os.path.join(screenshot_dir, "08_activity.png")

        # Сделать скриншот элемента
        await element.screenshot(path=full_path)

        # Обрезать нижнюю половину (оставить верхнюю)
        with Image.open(full_path) as img:
            width, height = img.size
            top_half = img.crop((0, 0, width, height // 2))  # (left, upper, right, lower)
            top_half.save(full_path)

        await page.set_viewport_size(old_viewport)

    except Exception as e:
        logging.exception(f"[last_activity] Ошибка при выполнении {url}")


@retry(
    stop=stop_after_attempt(3),
    wait=wait_fixed(2),
    retry=retry_if_exception_type(PlaywrightError)
)
async def set_language_en(page: Page):
    try:
        await page.goto(BASE_URL_PRO)

        await page.wait_for_selector(
            FLAG_LOCATOR,
            state="visible",
            timeout=30000)

        await page.click(FLAG_LOCATOR)

        await page.wait_for_selector('#pp-lang:not(.hidden)',
                                     state="visible",
                                     timeout=30000)

        await page.wait_for_selector('#pp-lang:not(.hidden)', timeout=30000)
        await page.click('#pp-lang li[data-key="en"]')
        await asyncio.sleep(3)
    except Exception as e:
        logging.exception(f"[set_language_en] Ошибка при выборе языка: {e}")


async def run():
    hotel_ids = load_hotel_ids(INPUT_FILE)
    if not hotel_ids:
        logging.error("Файл пуст или содержит некорректные ID.")
        return

    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
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

        for hotel_id in tqdm(hotel_ids, desc="Обработка отелей"):
            try:
                logging.info(f"⏳ Работаем с отелем {hotel_id}")
                title = await get_title_hotel(page, hotel_id)
                os.makedirs(f"{SCREENSHOT_DIR}/{title}", exist_ok=True)

                # await top_screen(page, hotel_id, title)
                # count_review = await review_screen(page, hotel_id, title)
                # await attendance(page, hotel_id, title)
                # await dynamic_rating(page, hotel_id, title)
                # await service_prices(page, hotel_id, title)
                # await rating_hotels_in_hurghada(page, count_review, hotel_id, title)
                await last_activity(page, hotel_id, title)
                logging.info(f"✅ Готово: {hotel_id} ({title})")
            except Exception as e:
                logging.exception(f"‼️ Ошибка при обработке отеля {hotel_id, title}")

        await browser.close()


async def main():
    for i in range(2):
        await run()


if __name__ == '__main__':
    asyncio.run(main())
