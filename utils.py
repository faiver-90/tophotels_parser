import logging
import os
import ctypes

import json
from pathlib import Path
import platform

from tenacity import RetryError

from config_app import SCREENSHOTS_DIR


# ----------------------- Desktop resolver -----------------------
def get_desktop_dir() -> Path:
    """
    Возвращает путь к папке 'Рабочий стол' для текущего пользователя.
    Для Windows пробует системный API (SHGetFolderPathW), затем OneDrive/USERPROFILE.
    Для Linux/macOS — ~/Desktop или ~/Рабочий стол, иначе ~.
    """
    home = Path.home()

    if os.name == "nt":
        # 1) Системный API: CSIDL_DESKTOPDIRECTORY = 0x0010
        try:
            buf = ctypes.create_unicode_buffer(260)
            if ctypes.windll.shell32.SHGetFolderPathW(None, 0x0010, None, 0, buf) == 0:
                p = Path(buf.value)
                if p.exists():
                    return p
        except Exception:
            pass

        # 2) OneDrive Desktop
        onedrive = os.environ.get("OneDrive")
        if onedrive:
            for cand in ("Desktop", "Рабочий стол"):
                p = Path(onedrive) / cand
                if p.exists():
                    return p

        # 3) USERPROFILE/HOMEPATH Desktop
        for env in ("USERPROFILE", "HOMEPATH"):
            base = os.environ.get(env)
            if base:
                for cand in ("Desktop", "Рабочий стол"):
                    p = Path(base) / cand
                    if p.exists():
                        return p

        # 4) Фолбэк
        return home / "Desktop"

    # *nix / macOS
    for cand in ("Desktop", "Рабочий стол"):
        p = home / cand
        if p.exists():
            return p
    return home


# -----------------------------------------------------------------


def normalize_windows_path(path_str: str) -> Path:
    """Преобразует обычный путь Windows в безопасный Path."""
    if not path_str:
        return None
    # Убираем кавычки, если есть
    cleaned = path_str.strip().strip('"').strip("'")
    # Заменяем обратные слэши на прямые
    cleaned = cleaned.replace("\\", "/")
    return Path(cleaned)


def get_hotel_folder(hotel_id: str | int, hotel_title: str) -> Path:
    """Возвращает Path к папке отеля и гарантирует её наличие."""
    folder = Path(SCREENSHOTS_DIR) / f"{hotel_id}_{hotel_title}"
    folder.mkdir(parents=True, exist_ok=True)
    return folder


def get_screenshot_path(hotel_id: str | int, hotel_title: str, filename: str) -> Path:
    """Путь к файлу скриншота в папке отеля."""
    return get_hotel_folder(hotel_id, hotel_title) / filename


def load_links(hotel_id: str | int, hotel_title: str) -> dict:
    """Читает links.json из папки отеля."""
    meta = get_hotel_folder(hotel_id, hotel_title) / "links.json"
    if meta.exists():
        try:
            return json.loads(meta.read_text(encoding="utf-8"))
        except Exception:
            return {}
    return {}


def save_to_jsonfile(hotel_id: str | int, hotel_title: str, key: str, value: str) -> None:
    """Сохраняет ссылку в links.json в папке отеля.
    Если ключ уже есть:
      - если значение одно, оно превращается в список
      - если список, в него добавляется новый элемент
    """
    folder = get_hotel_folder(hotel_id, hotel_title)
    meta = folder / "links.json"
    data = {}

    if meta.exists():
        try:
            data = json.loads(meta.read_text(encoding="utf-8"))
        except Exception:
            data = {}

    # добавляем значение по ключу
    if key not in data:
        data[key] = value
    else:
        # если уже список, добавляем
        if isinstance(data[key], list):
            data[key].append(value)
        else:
            # если было одно значение — превращаем в список
            data[key] = [data[key], value]

    meta.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")


async def safe_step(step_fn, *args, **kwargs):
    try:
        return await step_fn(*args, **kwargs)
    except RetryError as e:
        logging.error(f"{step_fn.__name__} упал по RetryError: {e}")
    except Exception as e:
        logging.exception(f"{step_fn.__name__} упал с ошибкой: {e}")


def sleep_system():
    system = platform.system()
    if system == "Windows":
        os.system("rundll32.exe powrprof.dll,SetSuspendState Sleep")
    elif system == "Linux":
        os.system("systemctl suspend")
    elif system == "Darwin":  # macOS
        os.system("pmset sleepnow")
    else:
        print("Неизвестная ОС, команда сна не выполнена")
