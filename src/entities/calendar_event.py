import datetime
import hashlib
from typing import Any, TypedDict
from helpers.time import convert_to_utc

class CalendarEvent(TypedDict):
    """
    Class to represent a calendar event.
    """

    uid: str
    instance_uid: str
    summary: str
    start: datetime.datetime
    end: datetime.datetime
    all_day: bool
    raw: Any

def compile_event(event) -> CalendarEvent:
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

