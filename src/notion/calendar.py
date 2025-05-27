# -*- coding: utf-8 -*-

import datetime
import requests
import recurring_ical_events

from notion_client import Client
from icalendar import Calendar

from entities.calendar_event import compile_event, CalendarEvent

class CalendarSync:
    """
    Class to interact with Notion's API for driving calendar sync.
    """
    NUMBER_OF_DAYS_TO_SYNC = 14
    MAX_EVENTS_PER_SYNC = 100

    def __init__(self, notion: Client, database_id: str, logger: callable = print):
        """
        Initialize the NotionDatabaseDriver.
        
        Args:
            notion: The Notion client
            database_id: The Notion database ID
            logger: Function that accepts a message argument for logging
        """
        self.notion = notion
        self.database_id = database_id
        self.logger = logger

    def set_ics_url(self, ics_url: str):
        """
        Set the ICS URL for the calendar.
        """
        self.ics_url = ics_url
        self.logger(f"ICS URL set to: {ics_url}")
        
    def set_number_of_days_to_sync(self, days: int):
        """
        Set the number of days to sync.
        """
        self.NUMBER_OF_DAYS_TO_SYNC = days
        self.logger(f"Number of days to sync set to: {days}")
        
    def set_max_events_per_sync(self, max_events: int):
        """
        Set the maximum number of events to sync per operation.
        """
        self.MAX_EVENTS_PER_SYNC = max_events
        self.logger(f"Maximum events per sync set to: {max_events}")

    def sync_calendar(self) -> int:
        """
        Sync calendar to the Notion database.
        """
        # Fetch the calendar data and process events
        resp = requests.get(self.ics_url)
        resp.raise_for_status()
        cal = Calendar.from_ical(resp.text)
        
        self.logger(f"Fetched {len(cal.subcomponents)} components from ICS")
        
        now = datetime.datetime.now(datetime.timezone.utc)
        start_range = now
        end_range = start_range + datetime.timedelta(days=self.NUMBER_OF_DAYS_TO_SYNC)
        
        # Get all events including recurring instances
        events = recurring_ical_events.of(cal).between(start_range, end_range)
        
        synced_uids = []
        
        for event_component in events:
            if event_component.name != "VEVENT":
                continue
                
            event = compile_event(event_component)
            
            # Skip past events
            if event['end'] < now:
                self.logger(f"Skipping past event: {event['summary']}")
                continue
                
            # Sync to Notion
            self.sync_event_to_notion(event)
            synced_uids.append(event['instance_uid'])
            self.logger(f"Synced event: {event['summary']}")

        # Optional: Remove events from Notion that no longer exist in the calendar
        self.cleanup_orphaned_events(synced_uids)
        
        return len(synced_uids)

    def sync_event_to_notion(self, event: CalendarEvent):
        """
        Sync an event to the Notion calendar database.
        If the event already exists (by UID), update it.
        If not, create a new event.
        """
        
        # First, check if the event already exists by querying for its UID
        existing_pages = self.notion.databases.query(
            database_id=self.database_id,
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
            "Due Date": {
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
        
        if existing_pages and len(existing_pages) > 0:
            # Event exists, update it
            event_page_id = existing_pages[0]['id']
            self.logger(f"Updating existing event in Notion: {event['summary']}")
            
            self.notion.pages.update(
                page_id=event_page_id,
                properties=properties
            )
            return event_page_id
        else:
            # Event doesn't exist, create it
            self.logger(f"Creating new event in Notion: {event['summary']}")
            
            response = self.notion.pages.create(
                parent={
                    "type": "database_id",
                    "database_id": self.database_id
                },
                properties=properties
            )
            return response['id']

    def cleanup_orphaned_events(self, synced_uids):
        """
        Remove events from Notion that are no longer in the calendar.
        """
        # Get all events in Notion with dates in our sync range
        now = datetime.datetime.now(datetime.timezone.utc)
        start_date = now.isoformat()
        end_date = (now + datetime.timedelta(days=self.NUMBER_OF_DAYS_TO_SYNC)).isoformat()
        
        notion_events = self.notion.databases.query(
            database_id=self.database_id,
            filter={
                "and": [
                    {
                        "property": "Due Date",
                        "date": {
                            "on_or_after": start_date
                        }
                    },
                    {
                        "property": "Due Date",
                        "date": {
                            "before": end_date
                        }
                    }
                ]
            }
        ).get('results', [])
        
        self.logger(f"Found {len(notion_events)} events in Notion within the date range")
        
        for page in notion_events:
            uid_property = page.get('properties', {}).get('InstanceUID', {}).get('rich_text', [])
            if uid_property and uid_property[0].get('text', {}).get('content'):
                uid = uid_property[0]['text']['content']
                
                # If this UID wasn't in our synced events, archive/delete it
                if uid not in synced_uids:
                    self.logger(f"Archiving event that's no longer in calendar: {uid} | {page['id']}")
                    # Option 1: Archive the page
                    self.notion.pages.update(
                        page_id=page['id'],
                        archived=True
                    )
