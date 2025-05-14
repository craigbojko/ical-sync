import os, datetime, requests, hashlib
import recurring_ical_events
from icalendar import Calendar, Event
from google.oauth2 import service_account
from googleapiclient.discovery import build
from loadotenv import load_env
from typing import TypedDict, Any
from notion_client import Client

from notion.connect import NotionDatabaseConnector
from notion.driver import NotionDatabaseDriver

# Load environment variables from ../.env
# load_env(os.path.join(os.path.dirname(os.path.dirname(__file__)), "../.env"))
load_env(os.path.join(os.getcwd(), ".env"))

NOTION_API_KEY = os.getenv("NOTION_API_KEY")
ICS_URL = os.getenv("ICAL")
GOOGLE_CREDS_FILE = os.getenv("GOOGLE_CREDS_FILE")
PERSONAL_CAL_ID = "primary"

NUMBER_OF_DAYS_TO_SYNC = 14

CONFIG = {
    'DBBUG': False,
    'MAX_EVENTS': 100,
}

notion = Client(auth=NOTION_API_KEY)

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
    start = convert_to_utc(event.decoded('DTSTART'))
    start_date = start.strftime("%Y%m%d")
    uid = event.get('UID')
    composite_uid = hashlib.md5(f"{uid}_{start_date}".encode()).hexdigest()
    
    return {
        'uid': uid,
        'instance_uid': composite_uid,
        'summary': event.get('summary'),
        'start': start,
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
# resp = requests.get(ICS_URL)
# resp.raise_for_status()
# cal = Calendar.from_ical(resp.text)

# log(f"Fetched {len(cal.subcomponents)} components from ICS")

# now = datetime.datetime.now(datetime.timezone.utc)
# start_range = now
# end_range   = start_range + datetime.timedelta(days=NUMBER_OF_DAYS_TO_SYNC)
# log(f"Current time: {now}")

# recurring_ical_events = recurring_ical_events.of(cal).between(
#     start_range,
#     end_range
# )

# for event in recurring_ical_events:
#     track_event(event)

# for index, component in enumerate(cal.walk()):
#     if CONFIG['MAX_EVENTS'] and index >= CONFIG['MAX_EVENTS']:
#         log(f"DEBUG: Exiting after {index} events")
#         break

#     if component.name != "VEVENT":
#         continue
#     event: CalEvent = compile_event(component)
    
#     # DEBUG: Print converted event details
#     if CONFIG['DBBUG']: log_event(component)
    
#     # Skip past events - ensure both are aware datetime objects
#     if event.get('end') < now or event.get('all_day'):
#         # print(f"Skipping event {uid} - End time {end} is before current time {now}")
#         continue
    
#     # Add to events_by_date for later verification
#     track_event(event)


# print(f"Events by date: {len(events_by_date)} dates")
# for date, events in events_by_date.items():
#     print(f"Date: {date}")
#     for event in events:
#         print("---")
#         print(f"  - Summary: {event['summary']}, Start: {event['start']}, End: {event['end']}")
#         # print(f"  - Raw:\n{event['raw']}")
#         print(" ")

# Write to file
# with open("events_by_date.txt", "w") as f:
#     for date, events in events_by_date.items():
#         f.write(f"Date: {date}\n")
#         for event in events:
#             f.write(f"  - Summary: {event['summary']}, Start: {event['start']}, End: {event['end']}\n")
#             # f.write(f"  - Raw:\n{event['raw']}\n")
#             f.write("\n")
# print("Events written to events_by_date.txt")

# user = notion.users.me()
# print(f'Connected as:', user)

# calendar_database = notion.databases.query(
#     database_id=os.getenv("NOTION_DB_ID"),
# )
# print(f"Calendar database: ", calendar_database)

# Add an event to Notion calendar database
def sync_event_to_notion(event: CalEvent):
    """
    Sync an event to the Notion calendar database.
    If the event already exists (by UID), update it.
    If not, create a new event.
    """
    database_id = os.getenv("NOTION_DB_ID")
    
    # First, check if the event already exists by querying for its UID
    existing_pages = notion.databases.query(
        database_id=database_id,
        filter={
            "property": "InstanceUID",
            "rich_text": {
                "equals": event['instance_uid']
            }
        },
        # filter={
        #     "or": [
        #         {
        #             "property": "InstanceUID",
        #             "rich_text": {
        #                 "equals": event['instance_uid']
        #             }
        #         },
        #         {
        #             "property": "EventUID",
        #             "rich_text": {
        #                 "equals": event['uid']
        #             }
        #         }
        #     ]
        # }
    ).get('results', [])
    
    # Prepare properties to update or create
    properties = {
        "Name": {
            "title": [
                {
                    "text": {
                        "content": event['summary']
                    }
                }
            ]
        },
        "DueDate": {
            "date": {
                "start": event['start'].isoformat(),
                "end": event['end'].isoformat()
            }
        },
        "EventUID": {
            "rich_text": [
                {
                    "text": {
                        "content": event['uid']
                    }
                }
            ]
        },
        "InstanceUID": {
            "rich_text": [
                {
                    "text": {
                        "content": event['instance_uid']
                    }
                }
            ]
        },
    }
    
    if existing_pages:
        # Event exists, update it
        page_id = existing_pages[0]['id']
        log(f"Updating existing event in Notion: {event['summary']}")
        
        notion.pages.update(
            page_id=page_id,
            properties=properties
        )
        return page_id
    else:
        # Event doesn't exist, create it
        log(f"Creating new event in Notion: {event['summary']}")
        
        response = notion.pages.create(
            parent={
                "type": "database_id",
                "database_id": database_id
            },
            properties=properties
        )
        return response['id']

def sync_calendar_to_notion():
    """
    Sync calendar events to Notion.
    """
    # Fetch current events from Notion for comparison/cleanup
    database_id = os.getenv("NOTION_DB_ID")
    now = datetime.datetime.now(datetime.timezone.utc)
    
    # Fetch the calendar data and process events
    resp = requests.get(ICS_URL)
    resp.raise_for_status()
    cal = Calendar.from_ical(resp.text)
    
    log(f"Fetched {len(cal.subcomponents)} components from ICS")
    
    start_range = now
    end_range = start_range + datetime.timedelta(days=NUMBER_OF_DAYS_TO_SYNC)
    
    # Get all events including recurring instances
    events = recurring_ical_events.of(cal).between(start_range, end_range)
    
    synced_uids = []
    
    for event_component in events:
        if event_component.name != "VEVENT":
            continue
            
        event = compile_event(event_component)
        
        # Skip past events
        if event['end'] < now:
            log(f"Skipping past event: {event['summary']}")
            continue
            
        # Sync to Notion
        page_id = sync_event_to_notion(event)
        synced_uids.append(event['instance_uid'])
        log(f"Synced event: {event['summary']}")
    
    # Optional: Remove events from Notion that no longer exist in the calendar
    cleanup_orphaned_events(synced_uids, database_id)
    
    return len(synced_uids)

def cleanup_orphaned_events(synced_uids, database_id):
    """
    Remove events from Notion that are no longer in the calendar.
    """
    # Get all events in Notion with dates in our sync range
    now = datetime.datetime.now(datetime.timezone.utc)
    start_date = now.isoformat()
    end_date = (now + datetime.timedelta(days=NUMBER_OF_DAYS_TO_SYNC)).isoformat()
    
    notion_events = notion.databases.query(
        database_id=database_id,
        filter={
            "and": [
                {
                    "property": "DueDate",
                    "date": {
                        "on_or_after": start_date
                    }
                },
                {
                    "property": "DueDate",
                    "date": {
                        "before": end_date
                    }
                }
            ]
        }
    ).get('results', [])
    
    print(f"Found {len(notion_events)} events in Notion within the date range")
    
    for page in notion_events:
        uid_property = page.get('properties', {}).get('InstanceUID', {}).get('rich_text', [])
        if uid_property and uid_property[0].get('text', {}).get('content'):
            uid = uid_property[0]['text']['content']
            
            # If this UID wasn't in our synced events, archive/delete it
            if uid not in synced_uids:
                log(f"Archiving event that's no longer in calendar: {uid} | {page['id']}")
                # Option 1: Archive the page
                notion.pages.update(
                    page_id=page['id'],
                    archived=True
                )
                # Option 2: Delete the page (uncomment if you prefer deletion)
                ## Call notion api directly to delete the page
                # requests.delete(
                #     f"https://api.notion.com/v1/pages/{page['id']}",
                #     headers={
                #         "Authorization": f"Bearer {NOTION_API_KEY}",
                #     }
                # )
                # log(f"Deleted orphaned event: {uid}")


def main():
    """
    Main function to connect to Notion and create or query a calendar sync database.
    """
    # Initialize the Notion client
    notion = Client(auth=NOTION_API_KEY)

    # Create a NotionDatabaseConnector instance
    connector = NotionDatabaseConnector(notion)
    connection_details = connector.get_driver_database()
    print(f"Connection details: {connection_details}")
    
    driver = NotionDatabaseDriver(notion, connection_details['page_id'], connection_details['database_id'])
    sync_items = driver.get_sync_items()
    
    if len(sync_items) == 0:
        print("No sync items found in Notion database.")
        return

    driver.sync_items(sync_items)
    
    # Example usage
    # Replace the test code with a proper sync
    # sync_calendar_to_notion()

    # For testing purposes only - should be replaced with sync_calendar_to_notion() call
    # test_event = {
    #     'uid': 'test-event-123',
    #     'summary': 'Test Calendar Event',
    #     'start': datetime.datetime.now(datetime.timezone.utc) + datetime.timedelta(days=2),
    #     'end': datetime.datetime.now(datetime.timezone.utc) + datetime.timedelta(days=2, hours=1),
    #     'all_day': False,
    # }
    # sync_event_to_notion(test_event)



if __name__ == "__main__":
    # Run the main function
    # when the script is executed directly
    main()
