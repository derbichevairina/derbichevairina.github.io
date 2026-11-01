from collections.abc import Callable
from datetime import date, datetime, time, timedelta, timezone
from urllib.parse import urlencode
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError

from mcp.server import MCPServer
from mcp.server.mcpserver.exceptions import ToolError
from mcp.types import ToolAnnotations
from pydantic import BaseModel, Field

from booking_mcp.calcom import CalcomSlotsClient
from booking_mcp.profile import PROFILE, SESSION_MINUTES, SITE, PsychologistProfile

DEFAULT_TIMEZONE = "Europe/Moscow"
MAX_DAYS_AHEAD = 60
ALTERNATIVES_COUNT = 6

WEEKDAYS = ["понедельник", "вторник", "среда", "четверг", "пятница", "суббота", "воскресенье"]
MONTHS = [
    "января", "февраля", "марта", "апреля", "мая", "июня",
    "июля", "августа", "сентября", "октября", "ноября", "декабря",
]

INSTRUCTIONS = """\
Booking an online session with Irina Derbicheva, a Russian-speaking clinical psychologist
(existential therapy and logotherapy, ACT as a supporting method). Adults only, individual, online only.

Use get_psychologist_profile to check that Irina fits the person's request before suggesting her.
Use list_free_slots to see her free times, in the person's timezone when you know it.
Use get_booking_link for the time the person picked and give them the link.

The booking itself is finished on her website: the person enters their name, email and consent to
personal data processing there. Never ask for their name, email, phone or health details in the chat
and never pass them to these tools. If the person is in danger or in acute crisis, point them to 112
or a local emergency service first; an online psychologist is not emergency help.
"""

READ_ONLY = {"read_only_hint": True, "destructive_hint": False, "idempotent_hint": True, "open_world_hint": False}


class FreeDay(BaseModel):
    date: str = Field(description="YYYY-MM-DD in the requested timezone")
    day: str = Field(description="The day in Russian, e.g. «среда, 4 ноября»")
    times: list[str] = Field(description="Start times HH:MM in the requested timezone")


class FreeSlots(BaseModel):
    timezone: str
    session_minutes: int
    days: list[FreeDay]
    next_step: str


class BookingLink(BaseModel):
    available: bool
    booking_url: str | None = Field(description="The site's booking page with this time selected; null if the time is taken")
    session: str | None = Field(description="The session in Russian, e.g. «среда, 4 ноября, 18:00–19:00 (Europe/Moscow)»")
    alternatives: list[str] = Field(description="Nearest free times in Russian when the asked time is taken")
    next_step: str


def resolve_timezone(name: str) -> ZoneInfo:
    try:
        return ZoneInfo(name)
    except (ZoneInfoNotFoundError, ValueError):
        raise ToolError(f"Unknown timezone {name!r}: use an IANA name such as Europe/Moscow or Asia/Tbilisi")


def format_day(day: date) -> str:
    return f"{WEEKDAYS[day.weekday()]}, {day.day} {MONTHS[day.month - 1]}"


def format_session(start: datetime, zone: ZoneInfo) -> str:
    local = start.astimezone(zone)
    end = local + timedelta(minutes=SESSION_MINUTES)
    return f"{format_day(local.date())}, {local:%H:%M}–{end:%H:%M} ({zone.key})"


def build_booking_link(start: datetime) -> str:
    # the picker on /zapis/ opens the contact form for this exact instant if it is still free
    utc = start.astimezone(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
    return f"{SITE}/zapis/?{urlencode({'slot': utc})}"


def group_by_local_day(starts: list[datetime], zone: ZoneInfo) -> list[FreeDay]:
    days: dict[date, list[str]] = {}
    for start in starts:
        local = start.astimezone(zone)
        days.setdefault(local.date(), []).append(f"{local:%H:%M}")
    return [FreeDay(date=day.isoformat(), day=format_day(day), times=times) for day, times in days.items()]


def build_booking_server(slots_client: CalcomSlotsClient, now: Callable[[], datetime]) -> MCPServer:
    server = MCPServer(
        name="psyholog-irina",
        title="Психолог Ирина Дербичева — запись",
        instructions=INSTRUCTIONS,
        website_url=SITE,
        version="1.0.0",
    )

    @server.tool(
        title="Профиль психолога",
        annotations=ToolAnnotations(title="Профиль психолога", **READ_ONLY),
    )
    def get_psychologist_profile() -> PsychologistProfile:
        """Who Irina Derbicheva is, which requests she works with and which not, format, session length, price and contacts."""
        return PROFILE

    @server.tool(
        title="Свободное время",
        annotations=ToolAnnotations(title="Свободное время", **READ_ONLY),
    )
    async def list_free_slots(
        timezone_name: str = Field(default=DEFAULT_TIMEZONE, description="The person's IANA timezone, e.g. Europe/Moscow"),
        days_ahead: int = Field(default=14, ge=1, le=MAX_DAYS_AHEAD, description="How many days from today to look ahead"),
    ) -> FreeSlots:
        """Irina's free 60-minute online session times, grouped by day in the given timezone."""
        zone = resolve_timezone(timezone_name)
        current = now()
        starts = await slots_client.get_free_slot_starts(current, current + timedelta(days=days_ahead))
        return FreeSlots(
            timezone=zone.key,
            session_minutes=SESSION_MINUTES,
            days=group_by_local_day(starts, zone),
            next_step="When the person picks a time, call get_booking_link with that date and time.",
        )

    @server.tool(
        title="Ссылка на запись",
        annotations=ToolAnnotations(title="Ссылка на запись", **READ_ONLY),
    )
    async def get_booking_link(
        date_local: str = Field(description="Session date YYYY-MM-DD in the given timezone"),
        time_local: str = Field(description="Session start HH:MM in the given timezone"),
        timezone_name: str = Field(default=DEFAULT_TIMEZONE, description="The person's IANA timezone"),
    ) -> BookingLink:
        """Check that a time is still free and return the link where the person finishes booking it on Irina's site; if it is taken, return the nearest free times."""
        zone = resolve_timezone(timezone_name)
        try:
            start = datetime.combine(date.fromisoformat(date_local), time.fromisoformat(time_local), zone)
        except ValueError:
            raise ToolError("date_local must be YYYY-MM-DD and time_local HH:MM")
        current = now()
        window_start = max(current, start - timedelta(days=7))
        starts = await slots_client.get_free_slot_starts(window_start, window_start + timedelta(days=21))
        if start in starts:
            return BookingLink(
                available=True,
                booking_url=build_booking_link(start),
                session=format_session(start, zone),
                alternatives=[],
                next_step="Give the person the link. On the page they enter name and email and confirm; the confirmation comes by email.",
            )
        nearest = sorted(sorted(starts, key=lambda free: abs(free - start))[:ALTERNATIVES_COUNT])
        return BookingLink(
            available=False,
            booking_url=None,
            session=None,
            alternatives=[format_session(free, zone) for free in nearest],
            next_step="This time is not free. Offer the alternatives, then call get_booking_link again for the chosen one.",
        )

    return server
