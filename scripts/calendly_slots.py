#!/usr/bin/env python3
"""Publishes the nearest free Calendly slots as slots.json and slots.md.

Runs on the web server every half hour, so it stays on the standard library:
the box has python3.9 and no node. The files land outside the rsync target,
otherwise the next site deploy would delete them.

The endpoints below are the ones Calendly's own booking page calls. They need no
token but are undocumented, so they can change without notice; the documented
replacement is API v2 /event_type_available_times, which needs a personal access
token and answers seven days at a time.
"""
from __future__ import annotations

import json
import os
from datetime import datetime, timedelta, timezone
from pathlib import Path
from urllib.parse import urlencode
from urllib.request import Request, urlopen

PROFILE_SLUG = "derbichevairina"
EVENT_TYPE_SLUG = "full_session"
BOOKING_URL = "https://calendly.com/derbichevairina/full_session"
TELEGRAM_URL = "https://t.me/derbichevairina"
LOOKUP_URL = "https://calendly.com/api/booking/event_types/lookup"
OUTPUT_DIR = Path("/var/www/psyholog-slots")
DAYS_AHEAD = 7

# Calendly is asked for Moscow time and answers with a +03:00 offset on every timestamp,
# so a fixed offset is enough and no timezone database is needed. Moscow has no DST.
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
    # keeps the days that still have bookable spots, dropping the ones already in the past
    days = []
    for day in payload.get("days", []):
        spots = [
            spot["start_time"]
            for spot in day.get("spots", [])
            if spot.get("status") == "available"
            and datetime.fromisoformat(spot["start_time"]) > now
        ]
        if spots:
            days.append({"date": day["date"], "spots": spots})
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
            + f"Напишите в Telegram {TELEGRAM_URL} — Ирина подберёт время.\n"
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
    event_type = fetch_json(f"{LOOKUP_URL}?" + urlencode({
        "event_type_slug": EVENT_TYPE_SLUG,
        "profile_slug": PROFILE_SLUG,
    }))
    now = datetime.now(MOSCOW)
    calendar = fetch_json(
        f"https://calendly.com/api/booking/event_types/{event_type['uuid']}/calendar/range?"
        + urlencode({
            "timezone": TIMEZONE_NAME,
            "diagnostics": "false",
            "range_start": now.date().isoformat(),
            "range_end": (now.date() + timedelta(days=DAYS_AHEAD - 1)).isoformat(),
        })
    )

    days = available_days(calendar, now)
    duration = event_type["duration"]

    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    payload = build_json(days, now, duration)
    write_atomically(OUTPUT_DIR / "slots.json", json.dumps(payload, ensure_ascii=False, indent=2) + "\n")
    write_atomically(OUTPUT_DIR / "slots.md", render_markdown(days, now, duration))
    print(f"published {sum(len(day['spots']) for day in days)} slots over {len(days)} days")


if __name__ == "__main__":
    main()
