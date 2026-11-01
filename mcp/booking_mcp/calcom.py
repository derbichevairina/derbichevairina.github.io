import json
from datetime import datetime, timezone

import httpx


class CalcomSlotsClient:
    # free slots of Irina's consultation event type, from the same Cal.com endpoint the site's picker calls
    def __init__(self, http: httpx.AsyncClient, schedule_url: str, event_type_id: int):
        self.http = http
        self.schedule_url = schedule_url
        self.event_type_id = event_type_id

    async def get_free_slot_starts(self, start: datetime, end: datetime) -> list[datetime]:
        # free slot starts in UTC within [start, end), earliest first
        query = {"json": {
            "eventTypeId": self.event_type_id,
            "startTime": start.astimezone(timezone.utc).isoformat(),
            "endTime": end.astimezone(timezone.utc).isoformat(),
            "timeZone": "UTC",
        }}
        response = await self.http.get(self.schedule_url, params={"input": json.dumps(query)})
        response.raise_for_status()
        slots_by_date = response.json()["result"]["data"]["json"]["slots"]
        starts = [
            datetime.fromisoformat(slot["time"].replace("Z", "+00:00"))
            for slots in slots_by_date.values()
            for slot in slots
        ]
        return sorted(slot_start for slot_start in starts if start <= slot_start < end)
