"""Google Calendar tool for checking availability."""

import json
import os
from datetime import datetime, timedelta
from pathlib import Path
from typing import Any

from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import build

from app.config import settings
from app.tools.base import BaseTool, ToolParameter

SCOPES = ["https://www.googleapis.com/auth/calendar.readonly"]
TOKEN_PATH = Path("token.json")
CREDENTIALS_PATH = Path("credentials.json")


def get_calendar_service():
    """Get authenticated Google Calendar service."""
    creds = None

    if TOKEN_PATH.exists():
        creds = Credentials.from_authorized_user_file(str(TOKEN_PATH), SCOPES)

    if not creds or not creds.valid:
        if creds and creds.expired and creds.refresh_token:
            creds.refresh(Request())
        else:
            if not CREDENTIALS_PATH.exists():
                # Create credentials from settings
                if settings.google_client_id and settings.google_client_secret:
                    creds_data = {
                        "installed": {
                            "client_id": settings.google_client_id,
                            "client_secret": settings.google_client_secret,
                            "auth_uri": "https://accounts.google.com/o/oauth2/auth",
                            "token_uri": "https://oauth2.googleapis.com/token",
                            "redirect_uris": ["http://localhost"],
                        }
                    }
                    with open(CREDENTIALS_PATH, "w") as f:
                        json.dump(creds_data, f)
                else:
                    raise ValueError(
                        "Google Calendar credentials not configured. "
                        "Set GOOGLE_CLIENT_ID and GOOGLE_CLIENT_SECRET in .env"
                    )

            flow = InstalledAppFlow.from_client_secrets_file(
                str(CREDENTIALS_PATH), SCOPES
            )
            creds = flow.run_local_server(port=0)

        with open(TOKEN_PATH, "w") as token:
            token.write(creds.to_json())

    return build("calendar", "v3", credentials=creds)


class GetCalendarAvailabilityTool(BaseTool):
    """Tool for getting calendar availability."""

    @property
    def name(self) -> str:
        return "get_calendar_availability"

    @property
    def description(self) -> str:
        return (
            "Get calendar events and available time slots for a given date range. "
            "Returns existing events and free time slots."
        )

    @property
    def parameters(self) -> dict[str, ToolParameter]:
        return {
            "start_date": ToolParameter(
                type="string",
                description="Start date in YYYY-MM-DD format",
            ),
            "end_date": ToolParameter(
                type="string",
                description="End date in YYYY-MM-DD format",
            ),
            "calendar_id": ToolParameter(
                type="string",
                description="Calendar ID to check (default: primary)",
                default="primary",
            ),
        }

    async def execute(self, **kwargs: Any) -> dict[str, Any]:
        """Get calendar availability.

        Args:
            start_date: Start date (YYYY-MM-DD).
            end_date: End date (YYYY-MM-DD).
            calendar_id: Calendar ID (default: primary).

        Returns:
            Dict with events and free_slots.
        """
        start_date = kwargs["start_date"]
        end_date = kwargs["end_date"]
        calendar_id = kwargs.get("calendar_id", "primary")

        try:
            service = get_calendar_service()

            # Parse dates
            start_dt = datetime.fromisoformat(start_date)
            end_dt = datetime.fromisoformat(end_date) + timedelta(days=1)

            time_min = start_dt.isoformat() + "Z"
            time_max = end_dt.isoformat() + "Z"

            # Get events
            events_result = (
                service.events()
                .list(
                    calendarId=calendar_id,
                    timeMin=time_min,
                    timeMax=time_max,
                    singleEvents=True,
                    orderBy="startTime",
                )
                .execute()
            )

            events = events_result.get("items", [])

            # Format events
            formatted_events = []
            for event in events:
                start = event["start"].get("dateTime", event["start"].get("date"))
                end = event["end"].get("dateTime", event["end"].get("date"))
                formatted_events.append({
                    "summary": event.get("summary", "No title"),
                    "start": start,
                    "end": end,
                    "location": event.get("location", ""),
                })

            # Calculate free slots (simplified: 9AM-6PM working hours)
            free_slots = self._calculate_free_slots(
                formatted_events, start_dt, end_dt
            )

            return {
                "success": True,
                "events": formatted_events,
                "free_slots": free_slots,
                "period": {"start": start_date, "end": end_date},
            }

        except Exception as e:
            return {
                "success": False,
                "error": str(e),
                "events": [],
                "free_slots": [],
            }

    def _calculate_free_slots(
        self,
        events: list[dict],
        start_dt: datetime,
        end_dt: datetime,
    ) -> list[dict]:
        """Calculate free time slots between events."""
        free_slots = []
        current = start_dt

        while current < end_dt:
            # Working hours: 9AM to 6PM
            day_start = current.replace(hour=9, minute=0, second=0)
            day_end = current.replace(hour=18, minute=0, second=0)

            # Get events for this day
            day_events = [
                e for e in events
                if e["start"].startswith(current.strftime("%Y-%m-%d"))
            ]

            if not day_events:
                free_slots.append({
                    "date": current.strftime("%Y-%m-%d"),
                    "start": "09:00",
                    "end": "18:00",
                    "duration_hours": 9,
                })
            else:
                # Simplified: just note the day has events
                free_slots.append({
                    "date": current.strftime("%Y-%m-%d"),
                    "events_count": len(day_events),
                    "note": "Partial availability - check events for details",
                })

            current += timedelta(days=1)

        return free_slots