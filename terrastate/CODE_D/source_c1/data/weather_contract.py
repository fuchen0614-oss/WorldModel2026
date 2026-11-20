"""Daily weather contract; pure Python checks usable without training dependencies."""
from datetime import date, timedelta
import math

def aggregate_weather(dates, rows, aggregations=('mean','min','max')):
    days=[date.fromisoformat(str(d)[:10]) for d in dates]
    if not days or len(days)!=len(rows) or len(days)%5:
        raise ValueError('weather requires matching dates and complete five-day groups')
    for i in range(1,len(days)):
        if days[i]-days[i-1]!=timedelta(days=1):
            raise ValueError(f'non-daily, duplicate or unordered time: {days[i-1]} -> {days[i]}')
    width=len(rows[0]); counts=[]; result=[]
    if width!=8 or any(len(row)!=width for row in rows):
        raise ValueError('expected eight daily weather variables')
    if any(math.isinf(float(x)) for row in rows for x in row):
        raise ValueError('infinite weather value: refuse corrupt inputs')
    if any(a not in ('mean','min','max','std') for a in aggregations):
        raise ValueError('unknown weather aggregation')
    for start in range(0,len(rows),5):
        values=[[float(rows[t][v]) for t in range(start,start+5) if math.isfinite(float(rows[t][v]))] for v in range(width)]
        count=[len(v) for v in values]
        # Match the original normalized-statistics NaN->0 convention; counts retain missingness.
        means=[sum(v)/len(v) if v else 0.0 for v in values]
        stats={'mean':means,'min':[min(v) if v else 0.0 for v in values],'max':[max(v) if v else 0.0 for v in values],
               'std':[math.sqrt(sum((x-m)**2 for x in v)/len(v)) if v else 0.0 for v,m in zip(values,means)]}
        result.append([x for key in aggregations for x in stats[key]])
        counts.append(count)
    return result,counts,[str(d) for d in days[4::5]]
