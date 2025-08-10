import os
import ctypes
from pathlib import Path


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