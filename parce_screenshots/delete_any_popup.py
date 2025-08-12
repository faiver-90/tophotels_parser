from playwright.async_api import Page
import asyncio
from typing import Iterable

# ваши селекторы можно прокидывать наружу
from parce_screenshots.moduls.locators import POLL_OVERLAY_SELECTORS


async def nuke_poll_overlay(
        page: Page,
        selectors: Iterable[str] = POLL_OVERLAY_SELECTORS,
        retries: int = 2,
        delay_ms: int = 150,
) -> int:
    """
    Универсально убирает попап/затемнение:
    - снимает блокирующие стили с html/body,
    - удаляет узлы по селекторам,
    - удаляет вероятные оверлеи по эвристике,
    - делает то же во всех iframe.
    Возвращает суммарное число удалённых узлов.
    """
    sels = list(dict.fromkeys(selectors))  # без дублей, порядок сохраняем
    total_removed = 0

    js = r"""
    (sels) => {
      const cleanupDoc = (doc) => {
        let removed = 0;

        const unlock = (root) => {
          try {
            root.documentElement?.classList?.remove('modal-open','no-scroll','overflow-hidden','lock-scroll');
            root.body?.classList?.remove('modal-open','no-scroll','overflow-hidden','lock-scroll');
            root.documentElement?.style?.removeProperty('overflow');
            root.body?.style?.removeProperty('overflow');
            root.documentElement?.style?.removeProperty('position');
            root.body?.style?.removeProperty('position');
          } catch {}
        };

        const rmBySelectors = (root, sels) => {
          let cnt = 0;
          for (const sel of sels) {
            try {
              root.querySelectorAll(sel).forEach(el => { try { el.remove(); cnt++; } catch {} });
            } catch {}
          }
          return cnt;
        };

        const zNum = (z) => (z && z!=='auto' && !isNaN(parseInt(z,10))) ? parseInt(z,10) : 0;
        const isOverlay = (el, vw, vh) => {
          if (!(el instanceof root.defaultView.HTMLElement)) return false;
          const cs = root.defaultView.getComputedStyle(el);
          const pos = cs.position;
          const zi = zNum(cs.zIndex);
          const r  = el.getBoundingClientRect();
          const area = Math.max(0, r.width) * Math.max(0, r.height);
          const big = area >= 0.2 * vw * vh || (r.width >= 0.9 * vw && r.height >= 0.3 * vh);
          const fixedLike = pos === 'fixed' || pos === 'absolute' || pos === 'sticky';
          const bg = cs.backgroundColor;
          const backdrop = bg && bg !== 'transparent' && bg !== 'rgba(0, 0, 0, 0)';
          const modalRole = el.getAttribute('aria-modal') === 'true' || el.getAttribute('role') === 'dialog';
          return (big && fixedLike && (zi >= 1000 || backdrop)) || modalRole;
        };

        const rmHeuristics = (root) => {
          let cnt = 0;
          const vw = root.defaultView.innerWidth, vh = root.defaultView.innerHeight;
          root.querySelectorAll('body *').forEach(el => {
            try { if (isOverlay(el, vw, vh)) { el.remove(); cnt++; } } catch {}
          });
          // центр экрана — снять верхний фикс-предок
          try {
            const center = root.elementFromPoint(vw/2, vh/2);
            if (center && center !== root.body && center !== root.documentElement) {
              let cur = center;
              while (cur && cur !== root.body) {
                const cs = root.defaultView.getComputedStyle(cur);
                if (isOverlay(cur, vw, vh) || cs.position === 'fixed') { try { cur.remove(); cnt++; } catch {}; break; }
                cur = cur.parentElement;
              }
            }
          } catch {}
          return cnt;
        };

        unlock(doc);
        removed += rmBySelectors(doc, sels);
        removed += rmHeuristics(doc);

        // пройтись по iframe
        const iframes = doc.querySelectorAll('iframe');
        for (const iframe of iframes) {
          try {
            const idoc = iframe.contentDocument;
            if (!idoc) continue;
            unlock(idoc);
            removed += rmBySelectors(idoc, sels);
            removed += rmHeuristics(idoc);
          } catch {}
        }
        return removed;
      };

      try {
        return cleanupDoc(document);
      } catch {
        return 0;
      }
    }
    """

    for attempt in range(retries + 1):
        try:
            removed = await page.evaluate(js, sels)
            total_removed += int(removed or 0)
        except Exception:
            pass
        if attempt < retries and delay_ms:
            await asyncio.sleep(delay_ms / 1000)

    return total_removed
