"""
Рекурсивная загрузка локальной папки на Google Диск.
Поддерживаются 2 режима авторизации:
- OAuth (ваш аккаунт, квота вашего Диска) — AUTH_MODE=oauth
- Service Account (только при расшаренной папке или Shared Drive) — AUTH_MODE=sa

Все параметры берутся из .env:
    AUTH_MODE=oauth
    LOCAL_FOLDER=D:/web_develop/tophotels/tophotels_moduls/TopHotels Reports
    PARENT_ID=root
    SA_JSON=service_account_google_drive.json
"""

import os
import json
import time
import mimetypes
from typing import Optional, Dict

from dotenv import load_dotenv
from googleapiclient.discovery import build
from googleapiclient.http import MediaFileUpload
from googleapiclient.errors import HttpError

# --- OAuth ---
from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow

SCOPES = ["https://www.googleapis.com/auth/drive"]

# Загружаем переменные из .env
load_dotenv()

AUTH_MODE    = os.getenv("AUTH_MODE", "oauth").strip().lower()  # oauth | sa
LOCAL_FOLDER = os.path.normpath(os.getenv("LOCAL_FOLDER", "").strip())
PARENT_ID    = os.getenv("PARENT_ID", "root").strip() or "root"
SA_JSON      = os.getenv("SA_JSON", "service_account_google_drive.json").strip()


# ---------------- Авторизация ----------------
def get_service_oauth():
    """Авторизация под вашим Google-аккаунтом (OAuth)."""
    creds = None
    if os.path.exists("token.json"):
        creds = Credentials.from_authorized_user_file("token.json", SCOPES)

    if not creds or not creds.valid:
        if creds and creds.expired and creds.refresh_token:
            creds.refresh(Request())
        else:
            if not os.path.exists("credentials.json"):
                raise FileNotFoundError("Нет credentials.json (OAuth client ID Desktop).")
            flow = InstalledAppFlow.from_client_secrets_file("credentials.json", SCOPES)
            creds = flow.run_local_server(port=0)
        with open("token.json", "w", encoding="utf-8") as f:
            f.write(creds.to_json())

    return build("drive", "v3", credentials=creds, cache_discovery=False)


def get_service_sa():
    """Авторизация через сервис-аккаунт (используется только при AUTH_MODE=sa)."""
    from google.oauth2 import service_account
    if not os.path.exists(SA_JSON):
        raise FileNotFoundError(f"Не найден файл сервис-аккаунта: {SA_JSON}")
    creds = service_account.Credentials.from_service_account_file(SA_JSON, scopes=SCOPES)
    return build("drive", "v3", credentials=creds, cache_discovery=False)


# ---------------- Вспомогательные функции ----------------
def find_or_create_folder(service, name: str, parent_id: str) -> str:
    """Ищет или создаёт подпапку в Google Drive."""
    q = (
        f"name = {json.dumps(name)} and "
        "mimeType = 'application/vnd.google-apps.folder' and "
        f"'{parent_id}' in parents and trashed = false"
    )
    resp = service.files().list(q=q, fields="files(id, name)", pageSize=1).execute()
    files = resp.get("files", [])
    if files:
        return files[0]["id"]

    file_metadata = {"name": name, "mimeType": "application/vnd.google-apps.folder", "parents": [parent_id]}
    created = service.files().create(body=file_metadata, fields="id").execute()
    return created["id"]


def safe_media_upload(path: str) -> MediaFileUpload:
    """Формируем MediaFileUpload с корректным mime и резюмируемой загрузкой."""
    mime, _ = mimetypes.guess_type(path)
    return MediaFileUpload(
        path,
        mimetype=mime or "application/octet-stream",
        chunksize=10 * 1024 * 1024,  # 10 MB
        resumable=True,
    )


def upload_file_with_retry(service, path: str, parent_id: str, max_retries: int = 5) -> str:
    """Загрузка файла с повторами и логированием."""
    body = {"name": os.path.basename(path), "parents": [parent_id]}
    media = safe_media_upload(path)

    attempt = 0
    while attempt <= max_retries:
        try:
            print(f"[UPLOAD] {path} -> parent={parent_id}")
            request = service.files().create(body=body, media_body=media, fields="id")
            response = None
            while response is None:
                status, response = request.next_chunk()
                if status:
                    print(f"  progress: {int(status.progress() * 100)}%")
            file_id = response["id"]
            print(f"  OK: id={file_id}")
            return file_id

        except HttpError as e:
            code = getattr(e.resp, "status", None)
            content = getattr(e, "content", b"") or b""
            print(f"  HttpError {code}: {content[:300]!r}")
            if code in (429, 500, 502, 503, 504):
                sleep = min(2 ** attempt, 30)
                print(f"  retry in {sleep}s...")
                time.sleep(sleep)
                attempt += 1
                continue
            raise
        except Exception as e:
            print(f"  ERROR: {type(e).__name__}: {e}")
            raise


def upload_folder_recursive(service, local_root: str, parent_id: str) -> None:
    """Рекурсивная загрузка локальной папки."""
    local_root = os.path.abspath(local_root)
    folder_cache: Dict[str, str] = {"": parent_id}

    for current_dir, subdirs, files in os.walk(local_root):
        rel_dir = os.path.relpath(current_dir, start=local_root)
        if rel_dir == ".":
            rel_dir = ""

        parent_rel = rel_dir
        parent_disk_id = folder_cache.get(parent_rel)
        if parent_disk_id is None:
            parts = [] if not rel_dir else rel_dir.split(os.sep)
            path_so_far = ""
            parent = parent_id
            for p in parts:
                path_so_far = os.path.join(path_so_far, p) if path_so_far else p
                if path_so_far not in folder_cache:
                    folder_id = find_or_create_folder(service, p, parent)
                    folder_cache[path_so_far] = folder_id
                    parent = folder_id
                else:
                    parent = folder_cache[path_so_far]
            parent_disk_id = parent

        for sd in subdirs:
            sub_rel = os.path.join(rel_dir, sd) if rel_dir else sd
            if sub_rel not in folder_cache:
                folder_id = find_or_create_folder(service, sd, parent_disk_id)
                folder_cache[sub_rel] = folder_id

        for f in files:
            local_path = os.path.join(current_dir, f)
            upload_file_with_retry(service, local_path, parent_disk_id)


# ---------------- main ----------------
if __name__ == "__main__":
    if not LOCAL_FOLDER or not os.path.isdir(LOCAL_FOLDER):
        raise NotADirectoryError(f"Папка не найдена: {LOCAL_FOLDER}")

    if AUTH_MODE == "oauth":
        service = get_service_oauth()
    elif AUTH_MODE == "sa":
        service = get_service_sa()
    else:
        raise ValueError("AUTH_MODE должен быть 'oauth' или 'sa'")

    upload_folder_recursive(service, LOCAL_FOLDER, PARENT_ID)
    print("Готово.")
