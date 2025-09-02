import re
from typing import Optional
from playwright.async_api import Page
from parce_screenshots_moduls.moduls.locators import POLL_OVERLAY_SELECTORS

# Блоки, которые нельзя трогать
KEEP_SELECTORS = [
    "section.stata-bubble",
]


async def _click_if_present(
    page: Page, root: Optional[any], sel: str, timeout: int = 800
) -> bool:
    """Пытаемся кликнуть по селектору внутри root (или на странице), игнорируем ошибки."""
    try:
        scope = root if root else page
        btn = scope.locator(sel)
        if await btn.count():
            await btn.first.click(timeout=timeout, delay=50)
            return True
    except Exception:
        pass
    return False


async def _is_overlay_candidate(page: Page, el_handle) -> bool:
    """JS-проверка: реально ли это оверлей, который мешает скрину."""
    return await el_handle.evaluate("""
      (el) => {
        const cs = getComputedStyle(el);
        const r  = el.getBoundingClientRect();
        const vw = window.innerWidth, vh = window.innerHeight;
        const area = Math.max(0, r.width) * Math.max(0, r.height);
        const coversMuch = (r.width >= vw * 0.5) || (r.height >= vh * 0.5) || (area >= vw * vh * 0.25);
        const posOverlay = ['fixed','sticky'].includes(cs.position) || (cs.position === 'absolute' && coversMuch);
        const zi = parseInt(cs.zIndex || '0', 10);
        const occludes = zi > 100 || posOverlay;
        const blocksClicks = cs.pointerEvents !== 'none' && occludes;
        return occludes || blocksClicks;
      }
    """)


async def _intersects_keep(page: Page, el_handle) -> bool:
    """Не трогаем элемент, если он сам или его предки/потомки пересекаются с keep-элементами."""
    js = f"""
      (el) => {{
        const keepSel = {KEEP_SELECTORS!r};
        for (const sel of keepSel) {{
          try {{
            if (el.matches(sel) || el.closest(sel)) return true;
            if (el.querySelector && el.querySelector(sel)) return true;
          }} catch (e) {{}}
        }}
        return false;
      }}
    """
    try:
        return await el_handle.evaluate(js)
    except Exception:
        return False


async def _hide_element(el_handle) -> bool:
    """Скрыть без удаления — безопаснее для layout."""
    try:
        await el_handle.evaluate("""
          (el) => {
            el.style.setProperty('opacity', '0', 'important');
            el.style.setProperty('visibility', 'hidden', 'important');
            el.style.setProperty('pointer-events', 'none', 'important');
            el.style.setProperty('transform', 'none', 'important');
            el.style.setProperty('z-index', '-1', 'important');
          }
        """)
        return True
    except Exception:
        return False


async def _remove_element(el_handle) -> bool:
    try:
        await el_handle.evaluate("(el) => el.remove()")
        return True
    except Exception:
        return False


# Быстрый предикат: селектор явно «попапный» -> можно не гонять дорогую _is_overlay_candidate
_POPUP_HINT_RE = re.compile(
    r"popup|modal|overlay|backdrop|aria-modal|role=['\"]dialog['\"]", re.I
)


def _looks_like_overlay_selector(sel: str) -> bool:
    return bool(_POPUP_HINT_RE.search(sel))


async def _any_overlays_present(page: Page) -> bool:
    """Один быстрый вызов в JS: есть ли хоть один элемент из списка селекторов."""
    try:
        return await page.evaluate(
            """
            (sels) => {
              for (const s of sels) {
                try {
                  if (document.querySelector(s)) return true;
                } catch (e) {}
              }
              return false;
            }
            """,
            POLL_OVERLAY_SELECTORS,
        )
    except Exception:
        return True  # на всякий случай не прерываем очистку


async def nuke_poll_overlay(
    page: Page,
    *,
    retries: int = 2,  # меньше по умолчанию
    delay_ms: int = 120,  # короче пауза
    per_selector_limit: int = 5,  # не обрабатываем сотни совпадений на широкий селектор
) -> None:
    """
    «Бережная» очистка с ранним выходом и ограничением обработки.
    Алгоритм попытки:
      0) Если на странице нет ни одного кандидата — выходим сразу.
      1) Отмечаем KEEP.
      2) По каждому селектору:
         - обработать не более per_selector_limit совпадений;
         - сперва клик по крестику (внутри и как отдельный селектор),
         - затем скрыть CSS,
         - в крайнем случае удалить,
         - после любой успешной операции — быстро проверить, остались ли оверлеи; если нет — выйти.
    Между попытками — короткая пауза, но только если действительно что-то поменяли.
    """

    async def _mark_keep():
        await page.evaluate(
            """
          (list) => {
            for (const sel of list) {
              try {
                document.querySelectorAll(sel).forEach(el => el.classList.add('keep-me'));
              } catch (e) {}
            }
          }
        """,
            KEEP_SELECTORS,
        )

    # Early exit перед первой попыткой
    if not await _any_overlays_present(page):
        return

    for attempt in range(1, retries + 1):
        await _mark_keep()
        changed_anything = False

        for sel in POLL_OVERLAY_SELECTORS:
            try:
                loc = page.locator(sel)
                cnt = await loc.count()
            except Exception:
                cnt = 0

            if cnt == 0:
                continue

            # ограничим слишком широкие выборки
            to_process = min(cnt, per_selector_limit)

            for i in range(to_process):
                try:
                    el = loc.nth(i)
                    handle = await el.element_handle()
                    if not handle:
                        continue

                    # Не трогаем KEEP
                    if await _intersects_keep(page, handle):
                        continue

                    # Явная кнопка закрытия по самому селектору
                    if sel.endswith("__btn-cross") or "btn-cross" in sel:
                        if await _click_if_present(page, None, sel):
                            changed_anything = True
                            # если всё исчезло — сразу выходим
                            if not await _any_overlays_present(page):
                                return
                        continue

                    # Крестик внутри кандидата
                    if await _click_if_present(page, el, ".lsfw-popup__btn-cross"):
                        changed_anything = True
                        if not await _any_overlays_present(page):
                            return
                        continue

                    # Узкий «попапный» селектор — можно не делать дорогую проверку
                    looks_overlay = _looks_like_overlay_selector(sel)
                    if not looks_overlay:
                        # Для широких селекторов страхуемся проверкой «оверлейности»
                        if not await _is_overlay_candidate(page, handle):
                            continue

                    # Спрятать
                    if await _hide_element(handle):
                        changed_anything = True
                        if not await _any_overlays_present(page):
                            return
                        continue

                    # Удалить
                    if await _remove_element(handle):
                        changed_anything = True
                        if not await _any_overlays_present(page):
                            return

                except Exception:
                    continue  # точечные сбои игнорируем

        if not changed_anything:
            break

        # короткая пауза только если реально что-то делали
        try:
            await page.wait_for_timeout(delay_ms)
        except Exception:
            pass
