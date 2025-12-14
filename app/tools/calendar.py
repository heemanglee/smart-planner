"""Google Calendar tool for checking availability."""

import json
import logging
import os
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any

from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import build

from app.config import settings
from app.tools.base import BaseTool, ToolParameter

logger = logging.getLogger(__name__)

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
            "Returns existing events and free time slots from all accessible calendars."
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
                description="Calendar ID to check. Use 'all' to check all accessible calendars (default), or specify a specific calendar ID.",
                default="all",
            ),
        }

    async def execute(self, **kwargs: Any) -> dict[str, Any]:
        """Get calendar availability.

        Args:
            start_date: Start date (YYYY-MM-DD).
            end_date: End date (YYYY-MM-DD).
            calendar_id: Calendar ID (default: all - fetches from all calendars).

        Returns:
            Dict with events and free_slots.
        """
        start_date = kwargs["start_date"]
        end_date = kwargs["end_date"]
        calendar_id = kwargs.get("calendar_id", "all")

        try:
            service = get_calendar_service()

            # Parse dates and add timezone info
            # Using local timezone for proper time range
            from zoneinfo import ZoneInfo
            local_tz = ZoneInfo("Asia/Seoul")
            
            start_dt = datetime.fromisoformat(start_date).replace(
                hour=0, minute=0, second=0, tzinfo=local_tz
            )
            end_dt = (datetime.fromisoformat(end_date) + timedelta(days=1)).replace(
                hour=0, minute=0, second=0, tzinfo=local_tz
            )

            # Format as RFC 3339 for Google Calendar API
            time_min = start_dt.isoformat()
            time_max = end_dt.isoformat()

            logger.info(f"Fetching calendar events from {time_min} to {time_max}")
            logger.info(f"Using calendar_id: {calendar_id}")

            # Determine which calendars to fetch from
            if calendar_id == "all":
                # Get all accessible calendars
                calendar_list = service.calendarList().list().execute()
                calendars = calendar_list.get("items", [])
                calendar_ids = [(cal["id"], cal.get("summary", cal["id"])) for cal in calendars]
                logger.info(f"Found {len(calendar_ids)} calendars to check")
            else:
                calendar_ids = [(calendar_id, calendar_id)]

            # Fetch events from all selected calendars
            all_events = []
            for cal_id, cal_name in calendar_ids:
                try:
                    events_result = (
                        service.events()
                        .list(
                            calendarId=cal_id,
                            timeMin=time_min,
                            timeMax=time_max,
                            singleEvents=True,
                            orderBy="startTime",
                        )
                        .execute()
                    )
                    events = events_result.get("items", [])
                    logger.info(f"Calendar '{cal_name}': found {len(events)} events")
                    
                    # Add calendar info to each event
                    for event in events:
                        event["_calendar_name"] = cal_name
                    all_events.extend(events)
                except Exception as e:
                    logger.warning(f"Failed to fetch from calendar '{cal_name}': {e}")

            logger.info(f"Total events found: {len(all_events)}")

            # Format events
            formatted_events = []
            for event in all_events:
                start = event["start"].get("dateTime", event["start"].get("date"))
                end = event["end"].get("dateTime", event["end"].get("date"))
                formatted_events.append({
                    "summary": event.get("summary", "No title"),
                    "start": start,
                    "end": end,
                    "description": event.get("description", ""),
                    "location": event.get("location", ""),
                    "calendar": event.get("_calendar_name", ""),
                })

            # Sort events by start time
            formatted_events.sort(key=lambda x: x["start"])

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
            logger.error(f"Error fetching calendar events: {e}")
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