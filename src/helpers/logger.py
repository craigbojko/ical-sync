
def log(message, level="INFO"):
    """
    Log messages to the console.
    """
    print(f"[{level}] {message}")

def log_event(event, debug=False):
    """
    Log event details to the console.
    """
    log(f"Event UID: {event['uid']}")
    log(f"Event summary: {event['summary']}")
    log(f"Event start: {event.get('start').isoformat()}, type: {type(event.decoded('DTSTART'))}")
    log(f"Event end: {event.get('end').isoformat()}, type: {type(event.decoded('DTEND'))}")
    log(f"Event all_day: {event['all_day']}")
    if debug:
        log(f"Event raw: {event.to_ical().decode('utf-8')}", level="DEBUG")
