import json
from datetime import datetime
from pathlib import Path

from calendly_slots import MOSCOW, available_days, build_json, render_markdown

FIXTURE = json.loads((Path(__file__).parent / "fixtures/calendly-range.json").read_text())
MORNING = datetime(2026, 9, 1, 9, 0, tzinfo=MOSCOW)


def test_keeps_only_days_with_bookable_spots():
    days = available_days(FIXTURE, MORNING)

    assert [day["date"] for day in days] == ["2026-09-01", "2026-09-02"]


def test_drops_spots_that_are_already_taken():
    days = available_days(FIXTURE, MORNING)

    assert days[1]["spots"] == ["2026-09-02T10:00:00+03:00"]


def test_drops_spots_that_already_started():
    days = available_days(FIXTURE, datetime(2026, 9, 1, 12, 0, tzinfo=MOSCOW))

    assert days[0]["spots"] == ["2026-09-01T18:00:00+03:00", "2026-09-01T18:30:00+03:00"]


def test_renders_every_slot_of_the_week():
    markdown = render_markdown(available_days(FIXTURE, MORNING), MORNING, 60)

    assert "- вторник, 1 сентября — 10:00, 18:00, 18:30" in markdown
    assert "- среда, 2 сентября — 10:00" in markdown


def test_says_so_when_the_week_is_empty():
    markdown = render_markdown([], MORNING, 60)

    assert "На ближайшую неделю свободных окон нет." in markdown
    assert "https://t.me/derbichevairina" in markdown


def test_names_the_timezone_and_the_refresh_time():
    markdown = render_markdown(available_days(FIXTURE, MORNING), MORNING, 60)

    assert "Время московское (UTC+3). Обновлено 1 сентября в 09:00." in markdown


def test_json_keeps_the_offset_so_a_client_can_convert():
    payload = build_json(available_days(FIXTURE, MORNING), MORNING, 60)

    assert payload["generated_at"] == "2026-09-01T09:00:00+03:00"
    assert payload["days"][0]["spots"][0] == "2026-09-01T10:00:00+03:00"
    assert payload["duration_minutes"] == 60
