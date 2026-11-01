#!/usr/bin/env python3
"""Publishes the nearest free booking slots as slots.json and slots.md for agents and readers.

Runs on the web server every half hour, so it stays on the standard library:
the box has python3.9 and no node. The files land outside the rsync target,
otherwise the next site deploy would delete them.

The slots come from the self-hosted Cal.com on the same server, through the endpoint
the site's own booking picker calls (no token, undocumented, may change with Cal.com).
"""
from __future__ import annotations

import json
import os
from datetime import datetime, timedelta, timezone
from pathlib import Path
from urllib.parse import urlencode
from urllib.request import Request, urlopen

EVENT_TYPE_ID = 1
DURATION_MINUTES = 60
SCHEDULE_URL = "http://127.0.0.1:3000/api/trpc/slots/getSchedule"
BOOKING_URL = "https://psyholog-irina.ru/zapis/"
MAX_URL = "https://max.ru/u/f9LHodD0cOLjSTb7GhaDmaB-R57UI5gU6Ay_nZvGKr6fKqEEcqWUjn0GDBs"
TELEGRAM_URL = "https://t.me/derbichevairina"
OUTPUT_DIR = Path("/var/www/psyholog-slots")
DAYS_AHEAD = 7

# Cal.com is asked for Moscow days and answers in UTC; Moscow has no DST, so a fixed
# offset turns them into Moscow time without a timezone database.
MOSCOW = timezone(timedelta(hours=3))
TIMEZONE_NAME = "Europe/Moscow"

WEEKDAYS = [
    "понедельник", "вторник", "среда", "четверг",
    "пятница", "суббота", "воскресенье",
]
MONTHS = [
    "января", "февраля", "марта", "апреля", "мая", "июня",
    "июля", "августа", "сентября", "октября", "ноября", "декабря",
]


def available_days(payload: dict, now: datetime) -> list[dict]:
    # Cal.com's free slots by Moscow date, as Moscow-time ISO strings, without days that have none or past slots
    days = []
    for date, slots in sorted(payload["result"]["data"]["json"]["slots"].items()):
        starts = [datetime.fromisoformat(slot["time"].replace("Z", "+00:00")).astimezone(MOSCOW) for slot in slots]
        spots = [start.isoformat(timespec="seconds") for start in starts if start > now]
        if spots:
            days.append({"date": date, "spots": spots})
    return days


def format_day(day: dict) -> str:
    # "среда, 2 сентября — 10:00, 10:30"
    date = datetime.strptime(day["date"], "%Y-%m-%d").date()
    times = ", ".join(spot[11:16] for spot in day["spots"])
    return f"{WEEKDAYS[date.weekday()]}, {date.day} {MONTHS[date.month - 1]} — {times}"


def render_markdown(days: list[dict], generated_at: datetime, duration_minutes: int) -> str:
    header = (
        "# Свободные окна для записи\n\n"
        "Ирина Дербичева, психолог. Онлайн-сессия "
        f"{duration_minutes} минут.\n"
        f"Время московское (UTC+3). Обновлено {generated_at.day} "
        f"{MONTHS[generated_at.month - 1]} в {generated_at:%H:%M}.\n\n"
        "## Ближайшая неделя\n\n"
    )
    if not days:
        return (
            header
            + "На ближайшую неделю свободных окон нет.\n\n"
            + f"Напишите в MAX {MAX_URL} или Telegram {TELEGRAM_URL} — Ирина подберёт время.\n"
        )
    lines = "\n".join(f"- {format_day(day)}" for day in days)
    return header + lines + f"\n\nЗаписаться: {BOOKING_URL}\n"


def build_json(days: list[dict], generated_at: datetime, duration_minutes: int) -> dict:
    return {
        "generated_at": generated_at.isoformat(timespec="seconds"),
        "timezone": TIMEZONE_NAME,
        "days_ahead": DAYS_AHEAD,
        "duration_minutes": duration_minutes,
        "booking_url": BOOKING_URL,
        "days": days,
    }


def fetch_json(url: str) -> dict:
    request = Request(url, headers={"Accept": "application/json", "User-Agent": "psyholog-irina.ru slots"})
    with urlopen(request, timeout=20) as response:
        return json.load(response)


def write_atomically(path: Path, text: str) -> None:
    # a half-written file would be served to visitors, so swap it in with a rename
    temporary = path.with_suffix(path.suffix + ".tmp")
    temporary.write_text(text, encoding="utf-8")
    os.replace(temporary, path)


def main() -> None:
    now = datetime.now(MOSCOW)
    first_day = datetime.combine(now.date(), datetime.min.time(), MOSCOW)
    query = {"json": {
        "eventTypeId": EVENT_TYPE_ID,
        "startTime": first_day.isoformat(),
        "endTime": (first_day + timedelta(days=DAYS_AHEAD, seconds=-1)).isoformat(),
        "timeZone": TIMEZONE_NAME,
    }}
    days = available_days(fetch_json(f"{SCHEDULE_URL}?" + urlencode({"input": json.dumps(query)})), now)
    duration = DURATION_MINUTES

    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    payload = build_json(days, now, duration)
    write_atomically(OUTPUT_DIR / "slots.json", json.dumps(payload, ensure_ascii=False, indent=2) + "\n")
    write_atomically(OUTPUT_DIR / "slots.md", render_markdown(days, now, duration))
    print(f"published {sum(len(day['spots']) for day in days)} slots over {len(days)} days")


if __name__ == "__main__":
    main()
