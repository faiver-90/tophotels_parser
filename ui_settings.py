# ui_settings.py
from __future__ import annotations

import re
from pathlib import Path
from html import escape
from typing import List, Optional, Tuple

from fastapi import FastAPI, Request
from fastapi.responses import HTMLResponse, RedirectResponse

app = FastAPI()
ENV_PATH = Path(".env")

# ---------- Парсер .env с сохранением комментариев/порядка ----------

ASSIGN_RE = re.compile(
    r"""^\s*
        (?P<key>[A-Za-z_][A-Za-z0-9_]*)
        \s*=\s*
        (?P<value>.*?)
        \s*$
    """,
    re.X,
)

class Line:
    kind: str  # "pair" | "comment" | "blank" | "other"
    raw: str
    key: Optional[str]
    value: Optional[str]
    desc: List[str]  # комментарии, принадлежащие pair

    def __init__(self, kind: str, raw: str, key: str | None = None, value: str | None = None):
        self.kind = kind
        self.raw = raw
        self.key = key
        self.value = value
        self.desc = []

def parse_env_with_comments(path: Path) -> List[Line]:
    if not path.exists():
        path.write_text("", encoding="utf-8")
    lines = path.read_text(encoding="utf-8").splitlines()
    result: List[Line] = []
    pending_desc: List[str] = []

    for raw in lines:
        if not raw.strip():
            # пустая строка завершает блок комментариев
            result.append(Line("blank", raw))
            pending_desc = []
            continue

        if raw.lstrip().startswith("#"):
            # копим комментарии; пока не увидим пару, не сбрасываем
            pending_desc.append(raw)
            result.append(Line("comment", raw))
            continue

        m = ASSIGN_RE.match(raw)
        if m:
            key = m.group("key")
            value = m.group("value")
            node = Line("pair", raw, key=key, value=value)
            # прикрепляем комментарии ИЗВЕРХУ к этой паре (только ближайшие подряд)
            # назад пройдёмся и «перекрасим» эти строки как part of desc
            # (для сохранения файла не обязательно, но для UI удобно)
            node.desc = [c for c in pending_desc]
            pending_desc = []
            result.append(node)
        else:
            result.append(Line("other", raw))
            pending_desc = []

    return result

def reconstruct_env(lines: List[Line]) -> str:
    out: List[str] = []
    for i, ln in enumerate(lines):
        if ln.kind == "pair":
            # печатаем прикреплённое описание (заменим существующие верхние комментарии на ln.desc,
            # но при этом сами «comment»-строки останутся в потоке; чтобы не дублировать,
            # в простом варианте просто печатаем финальную пару с её desc)
            for d in ln.desc:
                out.append(d)
            # нормализуем строку пары: key=value (значение уже содержит кавычки, если вы их ввели)
            out.append(f"{ln.key}={ln.value}")
            # пропустим исходную «сырую» и старые комментарии — мы их заменили на ln.desc + пара
            # остальные виды строк печатаем как есть
        elif ln.kind in ("comment", "blank", "other"):
            # эти строки попадут только если они не были «поглощены» в ln.desc.
            # Чтобы не дублировать комментарии, отфильтруем: если это комментарий, который уже
            # присутствует как часть desc у следующей пары, мы его пропустим.
            # Простой приём: если это комментарий и следующий за ним line == pair и этот комментарий
            # содержится в pair.desc, пропустим.
            if ln.kind == "comment":
                next_ln = lines[i + 1] if i + 1 < len(lines) else None
                if next_ln and next_ln.kind == "pair" and ln.raw in next_ln.desc:
                    continue
            out.append(ln.raw)
        else:
            out.append(ln.raw)
    return "\n".join(out) + "\n"

def env_as_dict(lines: List[Line]) -> Tuple[dict, dict]:
    """
    Возвращает:
      - значения ключей как dict: key -> value (без снятия кавычек — показываем как в файле)
      - описания: key -> "многострочный текст"
    """
    data = {}
    desc = {}
    for ln in lines:
        if ln.kind == "pair" and ln.key is not None:
            data[ln.key] = ln.value or ""
            if ln.desc:
                # склеим без ведущих '# ' (только для UI)
                cleaned = []
                for d in ln.desc:
                    s = d.lstrip()
                    cleaned.append(s[1:].lstrip() if s.startswith("#") else d)
                desc[ln.key] = "\n".join(cleaned)
            else:
                desc[ln.key] = ""
    return data, desc

# ---------- Отрисовка UI ----------

def render_form(lines: List[Line]) -> str:
    data, descriptions = env_as_dict(lines)
    rows = []
    for key, value in data.items():
        ek = escape(key)
        ev = escape(value or "")
        dv = escape(descriptions.get(key, "") or "")
        rows.append(
            f"""
            <tr>
              <td style="white-space:nowrap;"><label for="{ek}">{ek}</label></td>
              <td style="width:45%;"><input id="{ek}" name="{ek}" value="{ev}" style="width:100%"></td>
              <td style="width:45%;"><textarea name="__desc__{ek}" rows="2" style="width:100%" placeholder="Описание (комментарии будут записаны строками с # перед ключом)">{dv}</textarea></td>
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
        th, td {{ border: 1px solid #ddd; padding: 8px; vertical-align: top; }}
        th {{ background: #f7f7f7; text-align: left; }}
        input[type="text"], input[type="search"], input[type="number"] {{ padding: 6px; }}
        textarea {{ padding: 6px; }}
        .actions {{ display:flex; gap:12px; margin-top:12px; }}
      </style>
    </head>
    <body>
      <h1>.env editor</h1>

      <form method="post">
        <table>
          <thead>
            <tr>
              <th style="width:200px;">Key</th>
              <th>Value</th>
              <th>Description (will be written as # ...)</th>
              <th style="width:60px; text-align:center;">Del</th>
            </tr>
          </thead>
          <tbody>
            {''.join(rows)}
            <tr>
              <td><input name="__new_key" placeholder="NEW_KEY" style="width:100%"></td>
              <td><input name="__new_value" placeholder="value (кавычки не обязательны)" style="width:100%"></td>
              <td><textarea name="__new_desc" rows="2" style="width:100%" placeholder="Описание новой переменной"></textarea></td>
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

# ---------- Эндпоинты ----------

@app.get("/", response_class=HTMLResponse)
def get_editor():
    lines = parse_env_with_comments(ENV_PATH)
    return render_form(lines)

@app.post("/", response_class=HTMLResponse)
async def post_editor(request: Request):
    """
    Обновляет значения, описания, поддерживает удаление и добавление.
    Комментарии пишутся как строки, начинающиеся с '#', непосредственно над KEY=VALUE.
    """
    form = await request.form()
    lines = parse_env_with_comments(ENV_PATH)

    # Соберём текущую карту: key -> индекс строки pair
    key_to_idx = {ln.key: i for i, ln in enumerate(lines) if ln.kind == "pair" and ln.key}

    # 1) обновление/удаление существующих ключей
    to_remove: set[str] = set()
    for key, idx in list(key_to_idx.items()):
        if form.get(f"__del__{key}") == "1":
            to_remove.add(key)
            continue

        if key in form:
            new_value = (form.get(key) or "").strip()
            # если значение без пробелов/спецсимволов, оставим как есть; иначе можно обернуть в одинарные кавычки
            # (оставляю простую стратегию: если содержит пробел или #, обернуть в одинарные кавычки)
            if (" " in new_value) or ("#" in new_value) or ("=" in new_value):
                if not (new_value.startswith("'") and new_value.endswith("'")) and not (
                    new_value.startswith('"') and new_value.endswith('"')
                ):
                    new_value = "'" + new_value.replace("'", "\\'") + "'"
            lines[idx].value = new_value
            # обновим описание
            desc_text = (form.get(f"__desc__{key}") or "").strip()
            if desc_text:
                # превратим в список строк-комментариев
                desc_lines = [("# " + s if not s.startswith("#") else s) for s in desc_text.splitlines()]
            else:
                desc_lines = []
            lines[idx].desc = desc_lines

    # фактическое удаление: убираем pair и прилегающие сверху комментарии, если они принадлежат этому ключу
    if to_remove:
        new_lines: List[Line] = []
        skip_indices = set()
        for key in to_remove:
            idx = key_to_idx[key]
            skip_indices.add(idx)
            # также пропустим комментарии, которые записаны в lines[idx].desc
            desc_set = set(lines[idx].desc)
            # пройдём назад и пропустим те comment-строки, которые совпадают
            j = idx - 1
            while j >= 0 and lines[j].kind == "comment" and lines[j].raw in desc_set:
                skip_indices.add(j)
                j -= 1
        for i, ln in enumerate(lines):
            if i not in skip_indices:
                new_lines.append(ln)
        lines = new_lines

    # 2) добавить новую пару
    new_key = (form.get("__new_key") or "").strip()
    if new_key:
        new_value = (form.get("__new_value") or "").strip()
        if (" " in new_value) or ("#" in new_value) or ("=" in new_value):
            if not (new_value.startswith("'") and new_value.endswith("'")) and not (
                new_value.startswith('"') and new_value.endswith('"')
            ):
                new_value = "'" + new_value.replace("'", "\\'") + "'"
        new_desc = (form.get("__new_desc") or "").strip()
        desc_lines = [("# " + s if not s.startswith("#") else s) for s in new_desc.splitlines()] if new_desc else []

        # добавляем в конец: сначала комментарии, затем пара
        ln = Line("pair", raw="", key=new_key, value=new_value)
        ln.desc = desc_lines
        lines.append(Line("blank", "")) if lines and lines[-1].kind != "blank" else None
        lines.append(ln)

    # 3) записываем обратно
    ENV_PATH.write_text(reconstruct_env(lines), encoding="utf-8")
    return RedirectResponse(url="/", status_code=303)
