from __future__ import annotations

import os

from pathlib import Path
from PIL import Image


def _resize_all_images(folder_path: Path, width_px: int) -> None:
    """
    Пройтись по всем .png/.jpg/.jpeg в папке и привести их к фиксированной ширине (px),
    сохраняя пропорции. Перезапись *на месте* (in-place).
    """
    if width_px <= 0:
        return
    for name in sorted(os.listdir(folder_path)):
        if not name.lower().endswith((".png", ".jpg", ".jpeg")):
            continue
        p = folder_path / name
        try:
            with Image.open(p) as im:
                w, h = im.size
                if w == width_px:
                    continue
                scale = width_px / float(w)
                new_h = max(1, int(round(h * scale)))
                im = im.resize((width_px, new_h), Image.LANCZOS)
                # сохраняем с тем же форматом, максимально без потери видимого качества
                if p.suffix.lower() in (".jpg", ".jpeg"):
                    im.save(p, quality=95, optimize=True, progressive=True)
                else:
                    # для PNG — без потерь, с оптимизацией
                    im.save(p, optimize=True)
        except Exception as e:
            print(f"[WARN] Resize failed for {p.name}: {e}")
