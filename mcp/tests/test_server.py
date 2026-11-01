import json
from datetime import datetime, timezone
from pathlib import Path

import httpx
import pytest
from mcp import Client

from booking_mcp.calcom import CalcomSlotsClient
from booking_mcp.server import build_booking_server

FIXTURE = json.loads((Path(__file__).parents[2] / "tests/fixtures/calcom-slots.json").read_text())
MORNING_UTC = datetime(2026, 9, 1, 5, 0, tzinfo=timezone.utc)

pytestmark = pytest.mark.anyio


@pytest.fixture
def anyio_backend():
    return "asyncio"


def calcom_client_answering(payload: dict, seen_requests: list[httpx.Request] | None = None) -> CalcomSlotsClient:
    def answer(request: httpx.Request) -> httpx.Response:
        if seen_requests is not None:
            seen_requests.append(request)
        return httpx.Response(200, json=payload)

    http = httpx.AsyncClient(transport=httpx.MockTransport(answer))
    return CalcomSlotsClient(http=http, schedule_url="http://calcom.test/api/trpc/slots/getSchedule", event_type_id=1)


def booking_server():
    return build_booking_server(slots_client=calcom_client_answering(FIXTURE), now=lambda: MORNING_UTC)


async def test_every_tool_is_titled_and_read_only():
    async with Client(booking_server()) as client:
        tools = (await client.list_tools()).tools

    assert sorted(tool.name for tool in tools) == ["get_booking_link", "get_psychologist_profile", "list_free_slots"]
    for tool in tools:
        assert tool.title
        assert tool.annotations.title
        assert tool.annotations.read_only_hint is True
        assert tool.annotations.destructive_hint is False


async def test_calcom_client_asks_for_the_consultation_event_and_skips_empty_days():
    seen_requests: list[httpx.Request] = []
    slots_client = calcom_client_answering(FIXTURE, seen_requests)

    starts = await slots_client.get_free_slot_starts(MORNING_UTC, datetime(2026, 9, 3, tzinfo=timezone.utc))

    assert starts == [
        datetime(2026, 9, 1, 7, 0, tzinfo=timezone.utc),
        datetime(2026, 9, 1, 15, 0, tzinfo=timezone.utc),
        datetime(2026, 9, 1, 15, 30, tzinfo=timezone.utc),
        datetime(2026, 9, 2, 7, 0, tzinfo=timezone.utc),
    ]
    assert json.loads(seen_requests[0].url.params["input"])["json"]["eventTypeId"] == 1


async def test_free_slots_are_shown_in_the_persons_timezone():
    async with Client(booking_server()) as client:
        result = await client.call_tool("list_free_slots", {"timezone_name": "Asia/Tbilisi"})

    days = result.structured_content["days"]
    assert days[0] == {"date": "2026-09-01", "day": "вторник, 1 сентября", "times": ["11:00", "19:00", "19:30"]}
    assert days[1]["times"] == ["11:00"]


async def test_unknown_timezone_is_a_tool_error():
    async with Client(booking_server()) as client:
        result = await client.call_tool("list_free_slots", {"timezone_name": "Mars/Olympus"})

    assert result.is_error
    assert "Unknown timezone" in result.content[0].text


async def test_free_time_gets_a_link_to_the_booking_page():
    async with Client(booking_server()) as client:
        result = await client.call_tool("get_booking_link", {"date_local": "2026-09-01", "time_local": "18:00"})

    link = result.structured_content
    assert link["available"] is True
    assert link["booking_url"] == "https://psyholog-irina.ru/zapis/?slot=2026-09-01T15%3A00%3A00Z"
    assert link["session"] == "вторник, 1 сентября, 18:00–19:00 (Europe/Moscow)"


async def test_taken_time_offers_the_nearest_free_times():
    async with Client(booking_server()) as client:
        result = await client.call_tool("get_booking_link", {"date_local": "2026-09-01", "time_local": "17:00"})

    link = result.structured_content
    assert link["available"] is False
    assert link["booking_url"] is None
    assert link["alternatives"][:2] == [
        "вторник, 1 сентября, 10:00–11:00 (Europe/Moscow)",
        "вторник, 1 сентября, 18:00–19:00 (Europe/Moscow)",
    ]


async def test_profile_names_who_irina_does_not_work_with():
    async with Client(booking_server()) as client:
        result = await client.call_tool("get_psychologist_profile", {})

    profile = result.structured_content
    assert profile["name"] == "Ирина Дербичева"
    assert "Дети и подростки" in profile["does_not_work_with"]
    assert profile["booking_page"] == "https://psyholog-irina.ru/zapis/"
