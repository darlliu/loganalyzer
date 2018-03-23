from datetime import datetime,timedelta
from dateutil import parser
from dateutil.tz import tzlocal
TIME_LIMIT_CUTOFF=120
TIME_LIMIT_TOTAL=150
# time limits in seconds
# limit -- storage limit in seconds
# cutoff -- max storage age in seconds
# limit is larger than cutoff to avoid having to truncate too often
TIME_LIMIT_INTERVAL=10
#interval for calculating stats, seconds
TIME_LIMIT_UPDATE=1000
#update interval in ms

### Utility functions
def getNow():
    return datetime.now(tzlocal()

def getTimeStr(t=None):
    if t is None:
        t=datetime.now(tzlocal())
    return t.strftime("%d/%b/%Y:%H:%M:%S %z")

