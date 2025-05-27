import datetime


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
