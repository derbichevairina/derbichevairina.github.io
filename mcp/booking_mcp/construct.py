import os
from datetime import datetime, timezone

import httpx
from mcp.server import MCPServer

from booking_mcp.calcom import CalcomSlotsClient
from booking_mcp.server import build_booking_server

CALCOM_SCHEDULE_URL = os.environ.get("CALCOM_SCHEDULE_URL", "http://127.0.0.1:3000/api/trpc/slots/getSchedule")
EVENT_TYPE_ID = 1


def construct_booking_server() -> MCPServer:
    http = httpx.AsyncClient(timeout=20, headers={"User-Agent": "psyholog-irina.ru booking MCP"})
    slots_client = CalcomSlotsClient(http=http, schedule_url=CALCOM_SCHEDULE_URL, event_type_id=EVENT_TYPE_ID)
    return build_booking_server(slots_client=slots_client, now=lambda: datetime.now(timezone.utc))
