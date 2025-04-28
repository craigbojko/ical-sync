import os, datetime, requests
import recurring_ical_events
from icalendar import Calendar, Event
from google.oauth2 import service_account
from googleapiclient.discovery import build
from loadotenv import load_env
from typing import TypedDict, Any


# Load environment variables from ../.env
load_env(os.path.join(os.path.dirname(os.path.dirname(__file__)), '.env'))

ICS_URL = os.getenv("ICAL")
GOOGLE_CREDS_FILE = os.getenv("GOOGLE_CREDS_FILE")
PERSONAL_CAL_ID = "primary"

NUMBER_OF_DAYS_TO_SYNC = 14

CONFIG = {
    'DBBUG': False,
    'MAX_EVENTS': 100,
}

idx = 0
events_by_date = {}

class CalEvent(TypedDict):
    uid: str
    summary: str
    start: datetime.datetime
    end: datetime.datetime
    all_day: bool
    raw: Any

def compile_event(event) -> CalEvent:
    """
    Compile event details into a dictionary.
    """
    return {
        'uid': event.get('uid'),
        'summary': event.get('summary'),
        'start': convert_to_utc(event.decoded('DTSTART')),
        'end': convert_to_utc(event.decoded('DTEND')),
        'raw': event.to_ical().decode('utf-8'),
        'all_day': event.get('X-MICROSOFT-CDO-ALLDAYEVENT') == "TRUE"
    }

def track_event(event):
    """
    Track event details by date.
    """
    event_start = event.decoded('DTSTART')
    date_str    = event_start.strftime("%Y-%m-%d")
    
    if date_str not in events_by_date:
        events_by_date[date_str] = []
    events_by_date[date_str].append(compile_event(event))

def log(message, level="INFO"):
    """
    Log messages to the console.
    """
    print(f"[{level}] {message}")

def log_event(event):
    """
    Log event details to the console.
    """
    log(f"Event UID: {event['uid']}")
    log(f"Event summary: {event['summary']}")
    log(f"Event start: {event.get('start').isoformat()}, type: {type(event.decoded('DTSTART'))}")
    log(f"Event end: {event.get('end').isoformat()}, type: {type(event.decoded('DTEND'))}")
    log(f"Event all_day: {event['all_day']}")
    if CONFIG['DBBUG']: log(f"Event raw: {event.to_ical().decode('utf-8')}", level="DEBUG")

def convert_to_utc(dt: datetime.datetime) -> datetime.datetime:
    """
    Convert a datetime object to UTC.
    """
    if isinstance(dt, datetime.date) and not isinstance(dt, datetime.datetime):
        # Convert date to datetime at midnight
        dt = datetime.datetime.combine(dt, datetime.time.min, tzinfo=datetime.timezone.utc)
    elif dt.tzinfo is None:
        # Add UTC timezone if naive datetime
        dt = dt.replace(tzinfo=datetime.timezone.utc)
    else:
        # Convert to UTC if it has a different timezone
        dt = dt.astimezone(datetime.timezone.utc)
    return dt

# 1. Fetch ICS
resp = requests.get(ICS_URL)
resp.raise_for_status()
cal = Calendar.from_ical(resp.text)

log(f"Fetched {len(cal.subcomponents)} components from ICS")

now = datetime.datetime.now(datetime.timezone.utc)
start_range = now
end_range   = start_range + datetime.timedelta(days=NUMBER_OF_DAYS_TO_SYNC)
log(f"Current time: {now}")

recurring_ical_events = recurring_ical_events.of(cal).between(
    start_range,
    end_range
)

for event in recurring_ical_events:
    track_event(event)

for index, component in enumerate(cal.walk()):
    if CONFIG['MAX_EVENTS'] and index >= CONFIG['MAX_EVENTS']:
        log(f"DEBUG: Exiting after {index} events")
        break

    if component.name != "VEVENT":
        continue
    event: CalEvent = compile_event(component)
    
    # DEBUG: Print converted event details
    if CONFIG['DBBUG']: log_event(component)
    
    # Skip past events - ensure both are aware datetime objects
    if event.get('end') < now or event.get('all_day'):
        # print(f"Skipping event {uid} - End time {end} is before current time {now}")
        continue
    
    # Add to events_by_date for later verification
    track_event(event)


print(f"Events by date: {len(events_by_date)} dates")
for date, events in events_by_date.items():
    print(f"Date: {date}")
    for event in events:
        print("---")
        print(f"  - Summary: {event['summary']}, Start: {event['start']}, End: {event['end']}")
        # print(f"  - Raw:\n{event['raw']}")
        print(" ")

# Write to file
# with open("events_by_date.txt", "w") as f:
#     for date, events in events_by_date.items():
#         f.write(f"Date: {date}\n")
#         for event in events:
#             f.write(f"  - Summary: {event['summary']}, Start: {event['start']}, End: {event['end']}\n")
#             # f.write(f"  - Raw:\n{event['raw']}\n")
#             f.write("\n")
# print("Events written to events_by_date.txt")