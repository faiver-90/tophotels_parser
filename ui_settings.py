from pathlib import Path
from html import escape

from fastapi import FastAPI, Request
from fastapi.responses import HTMLResponse, RedirectResponse
from dotenv import dotenv_values, set_key, unset_key

app = FastAPI()
ENV_PATH = Path(".env")  # путь к вашему .env

def load_env() -> dict:
    """
    Читает .env как dict.
    Комментарии/порядок не сохраняются (особенность python-dotenv).
    """
    if not ENV_PATH.exists():
        ENV_PATH.write_text("", encoding="utf-8")
    return dict(dotenv_values(ENV_PATH))

def render_form(env_vars: dict) -> str:
    """
    Простейшая HTML-форма: ключ/значение, удаление, добавление новой пары.
    """
    rows = []
    for key, value in env_vars.items():
        ek = escape(key)
        ev = "" if value is None else escape(str(value))
        rows.append(
            f"""
            <tr>
              <td style="white-space:nowrap;"><label for="{ek}">{ek}</label></td>
              <td style="width:100%;"><input id="{ek}" name="{ek}" value="{ev}" style="width:100%"></td>
              <td style="text-align:center;">
                <input type="checkbox" name="__del__{ek}" value="1" title="Удалить">
              </td>
            </tr>
            """
        )

    html = f"""
    <!doctype html>
    <html lang="ru">
    <head>
      <meta charset="utf-8">
      <title>.env editor</title>
      <meta name="viewport" content="width=device-width, initial-scale=1">
      <style>
        body {{ font-family: system-ui, -apple-system, Segoe UI, Roboto, Arial, sans-serif; margin: 24px; }}
        table {{ border-collapse: collapse; width: 100%; }}
        th, td {{ border: 1px solid #ddd; padding: 8px; }}
        th {{ background: #f7f7f7; text-align: left; }}
        input[type="text"], input[type="search"] {{ padding: 6px; }}
        .actions {{ display:flex; gap:12px; margin-top:12px; }}
      </style>
    </head>
    <body>
      <h1>.env editor</h1>

      <form method="post">
        <table>
          <thead>
            <tr>
              <th style="width:260px;">Key</th>
              <th>Value</th>
              <th style="width:80px; text-align:center;">Del</th>
            </tr>
          </thead>
          <tbody>
            {''.join(rows)}
            <tr>
              <td><input name="__new_key" placeholder="NEW_KEY" style="width:100%"></td>
              <td><input name="__new_value" placeholder="value" style="width:100%"></td>
              <td></td>
            </tr>
          </tbody>
        </table>

        <div class="actions">
          <button type="submit">Сохранить</button>
          <a href="/" style="align-self:center;">Сбросить изменения</a>
        </div>
      </form>
    </body>
    </html>
    """
    return html

@app.get("/", response_class=HTMLResponse)
def get_editor():
    env_vars = load_env()
    return render_form(env_vars)

@app.post("/", response_class=HTMLResponse)
async def post_editor(request: Request):
    """
    Обрабатывает:
    - обновление существующих ключей (значение берём из формы);
    - удаление (чекбокс "__del__KEY");
    - добавление новой пары (__new_key / __new_value).
    """
    form = await request.form()

    # 1) существующие ключи: удалить/обновить
    current = load_env()
    for key in list(current.keys()):
        # удаление
        if form.get(f"__del__{key}") == "1":
            unset_key(str(ENV_PATH), key)
            continue
        # обновление
        if key in form:
            value = form.get(key, "")
            # set_key сам обновляет/добавляет пару
            set_key(str(ENV_PATH), key, value if value is not None else "")

    # 2) добавить новую пару
    new_key = (form.get("__new_key") or "").strip()
    if new_key:
        new_value = form.get("__new_value", "")
        set_key(str(ENV_PATH), new_key, "" if new_value is None else str(new_value))

    # 3) редирект — PRG-паттерн
    return RedirectResponse(url="/", status_code=303)
