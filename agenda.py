#!/home/joel/.venvs/taskscli/bin/python
import os
import sys

# Suppress tzlocal stderr warnings
import io
_original_stderr = sys.stderr
sys.stderr = io.StringIO()

import argparse
import datetime
import pickle
from google.oauth2.credentials import Credentials
from googleapiclient.discovery import build
import tzlocal

# Restore stderr after tzlocal import
sys.stderr = _original_stderr
# print("Python path:", sys.executable)

# Load environment variables
from dotenv import load_dotenv
load_dotenv()

# Combined scope for both Tasks and Calendar
SCOPES = [
    'https://www.googleapis.com/auth/tasks',
    'https://www.googleapis.com/auth/calendar'
]

# Paths to your client secrets and token pickle
CREDENTIALS_PATH = os.path.expanduser(os.getenv("GOOGLE_CREDENTIALS_PATH", "~/.venvs/taskscli/credentials.json"))
TOKEN_PATH = os.path.expanduser(os.getenv("GOOGLE_TOKEN_PATH", "~/.venvs/taskscli/token.pickle"))

# Suppress tzlocal warnings when getting timezone
sys.stderr = io.StringIO()
local_timezone = tzlocal.get_localzone().key
sys.stderr = _original_stderr

def get_service():
    # Load the pickled creds (access + refresh tokens)
    with open(TOKEN_PATH, 'rb') as f:
        creds = pickle.load(f)
    return build("calendar", "v3", credentials=creds)

def add_event(summary, start_time, day_offset=0, end_time=None, duration_hours=None, calendar_id="primary"):
    service = get_service()

    # Calculate start date
    start_date = datetime.date.today() + datetime.timedelta(days=day_offset)
    start_dt = datetime.datetime.fromisoformat(f"{start_date.isoformat()}T{start_time}")

    # Compute end datetime
    if end_time:
        # Parse end_time as HH:MM and use the same date as start
        end_dt = datetime.datetime.fromisoformat(f"{start_date.isoformat()}T{end_time}")
    elif duration_hours:
        end_dt = start_dt + datetime.timedelta(hours=duration_hours)
    else:
        end_dt = start_dt + datetime.timedelta(hours=1)

    event = {
        'summary': summary,
        'start': {
            'dateTime': start_dt.isoformat(),
            'timeZone': local_timezone
        },
        'end': {
            'dateTime': end_dt.isoformat(),
            'timeZone': local_timezone
        }
    }

    created = service.events().insert(calendarId=calendar_id, body=event).execute()
    print(f"✅ Created: {created.get('summary')} on {created['start']['dateTime']}")


def print_agenda(days):
    service = get_service()
    now = datetime.datetime.now(datetime.timezone.utc)
    future = now + datetime.timedelta(days=days)

    events = []
    # Query both your primary and the school import calendar
    for calendar_id in (
        "primary",
        os.getenv("SCHOOL_CALENDAR_ID", "2v5ivo6m0b3bko8oedcjr5i36orv3lpl@import.calendar.google.com")
    ):
        resp = service.events().list(
            calendarId=calendar_id,
            timeMin=now.isoformat(),
            timeMax=future.isoformat(),
            singleEvents=True,
            orderBy="startTime"
        ).execute()
        events.extend(resp.get("items", []))

    # Sort by start time
    events.sort(key=lambda e: e["start"].get("dateTime", e["start"].get("date")))

    if not events:
        print("✅ No upcoming events")
        return

    print(f"📅 Events in next {days} day(s):")
    today = datetime.date.today()
    tomorrow = today + datetime.timedelta(days=1)
    for ev in events:
        start = ev["start"].get("dateTime", ev["start"].get("date"))
        # Show local time nicely
        dt = datetime.datetime.fromisoformat(start)
        event_date = dt.date()
        if event_date == today:
            day_str = "Today"
        elif event_date == tomorrow:
            day_str = "Tomorrow"
        else:
            day_str = dt.strftime("%Y-%m-%d")
        timestr = dt.strftime("%H:%M") if "T" in start else ""
        print(f" • {day_str}{' ' + timestr if timestr else ''} — {ev.get('summary','No Title')}")

if __name__ == "__main__":
    p = argparse.ArgumentParser(description="Google Calendar CLI")
    subparsers = p.add_subparsers(dest="command")

    # Show agenda
    agenda_parser = subparsers.add_parser("list", help="Show calendar agenda")
    agenda_parser.add_argument("days", nargs="?", type=int, default=7)

    # Add event
    add_parser = subparsers.add_parser("add", help="Add an event")
    add_parser.add_argument("summary", help="Event title in quotes")
    add_parser.add_argument("start_time", help="Start time (HH:MM)")
    add_parser.add_argument("day_offset", nargs='?', type=int, default=0, help="Day offset (e.g., 0=today, 1=tomorrow)")
    add_parser.add_argument("--end_time", help="End time (HH:MM), must be same day as start")
    add_parser.add_argument("--duration", type=float, help="Duration in hours (e.g., 1.5 for 1h 30min)")

    args = p.parse_args()

    if args.command == "list":
        print_agenda(args.days)
    elif args.command == "add":
        add_event(args.summary, args.start_time, args.day_offset, args.end_time, args.duration)
    else:
        p.print_help()
