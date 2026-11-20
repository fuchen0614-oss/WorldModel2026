"""Calendar-only features: no observation values are consulted."""
import calendar
import math
from datetime import date

def annual_encoding(day):
    if not isinstance(day, date):
        day = date.fromisoformat(str(day)[:10])
    phase = 2 * math.pi * (day.timetuple().tm_yday - 1) / (366 if calendar.isleap(day.year) else 365)
    return (math.sin(phase), math.cos(phase))
