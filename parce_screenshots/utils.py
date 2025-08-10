import asyncio
import logging
import os

from typing import List
from tenacity import retry, stop_after_attempt, wait_fixed, retry_if_exception_type
from playwright.async_api import Error as PlaywrightError

from playwright.async_api import Page

from config_app import BASE_URL_PRO, BASE_URL_RU

from parce_screenshots.moduls.locators import TG_HIDE_LOCATOR, FLAG_LOCATOR


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


def all_folders_have_count_images(base_path: str, count_files_dir: int) -> bool:
    for folder in os.listdir(base_path):
        if folder == 'None':
            continue  # Пропустить папку с именем 'None'

        folder_path = os.path.join(base_path, folder)
        if not os.path.isdir(folder_path):
            continue

        images = [
            f for f in os.listdir(folder_path)
            if f.lower().endswith(('.png', '.jpg', '.jpeg'))
        ]
        if len(images) < count_files_dir:
            print(f"🔁 Folder '{folder}' has only {len(images)} images.")
            return False
    return True
