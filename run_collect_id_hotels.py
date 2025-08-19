import asyncio
import re
from pathlib import Path
from playwright.async_api import async_playwright, Page
from config_app import HEADLESS

savoy = ['al1799', 'al5054', 'al13549', 'al23213']
xperience = ['al12495', 'al66167', 'al70320', 'al247995']
parotel = ['al1802', 'al14258', 'al323704']
amphoras = ['al4115', 'al27559', 'al27677']
hotels_ids = [savoy, xperience, parotel, amphoras]

OUTPUT_TXT = Path("picked_hotel_ids.txt")

network_link = [
    "https://tophotels.ru/brand/baron-hotels"
]


async def _auto_scroll_to_bottom(page: Page, max_iters: int = 30):
    last_height = 0
    for _ in range(max_iters):
        current_height = await page.evaluate("() => document.body.scrollHeight")
        if current_height == last_height:
            break
        last_height = current_height
        await page.evaluate("() => window.scrollTo(0, document.body.scrollHeight)")
        await page.wait_for_timeout(800)


def _extract_ids_from_hrefs(hrefs: list[str]) -> list[str]:
    pat = re.compile(r"/hotel/(al\d+)\b")
    seen = set()
    result = []
    for href in hrefs:
        m = pat.search(href)
        if m:
            hid = m.group(1)
            if hid not in seen:
                seen.add(hid)
                result.append(hid)
    return result


async def _collect_ids_from_brand(page: Page, url: str) -> list[str]:
    await page.goto(url, wait_until="domcontentloaded")
    await page.wait_for_selector("a.lsfw-tbl__abs-link", timeout=10000)
    await _auto_scroll_to_bottom(page)
    hrefs = await page.eval_on_selector_all(
        "a.lsfw-tbl__abs-link",
        "els => els.map(e => e.href || e.getAttribute('href') || '')",
    )
    return _extract_ids_from_hrefs([h for h in hrefs if h])


def _flatten_manual_ids(groups: list[list[str]]) -> list[str]:
    # Флэттим список списков и фильтруем по формату al\d+
    pat = re.compile(r"^al\d+$")
    flat = []
    for g in groups:
        for x in g:
            if isinstance(x, str) and pat.match(x):
                flat.append(x)
    return flat


def _unique_preserve_order(*sequences: list[str]) -> list[str]:
    seen, out = set(), []
    for seq in sequences:
        for x in seq:
            if x not in seen:
                seen.add(x)
                out.append(x)
    return out


async def run_collect_id_from_link():
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=HEADLESS)
        page = await browser.new_page()

        # 1) Ручные ID
        manual_ids = _flatten_manual_ids(hotels_ids)

        # 2) Спаршенные ID
        scraped_ids: list[str] = []
        for link in network_link:
            ids = await _collect_ids_from_brand(page, link)
            print(f"[OK] {link} -> найдено {len(ids)} id")
            scraped_ids.extend(ids)

        # 3) Объединяем без дублей: сначала ручные, затем спаршенные
        final_ids = _unique_preserve_order(manual_ids, scraped_ids)

        # 4) Пишем построчно
        OUTPUT_TXT.write_text("\n".join(final_ids), encoding="utf-8")
        print(f"Сохранено {len(final_ids)} id в {OUTPUT_TXT.resolve()}")

        await browser.close()


if __name__ == '__main__':
    asyncio.run(run_collect_id_from_link())
