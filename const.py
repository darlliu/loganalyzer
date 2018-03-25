from datetime import datetime,timedelta
from dateutil import parser
from dateutil.tz import tzlocal
import re
import socket

### Consts
TIME_LIMIT_CUTOFF=120
TIME_LIMIT_TOTAL=150
# time limits in seconds
# total -- max storage age in seconds
# cutoff -- age to rotate/clean in seconds
# total is larger than cutoff to avoid having to truncate too often
TIME_LIMIT_INTERVAL=10
#interval for calculating stats, seconds
TIME_LIMIT_TRAFFIC=60
#interval for retrieving traffic data to plot, seconds
TIME_LIMIT_UPDATE=2
#update interval in seconds

HIGH_HITS_CUTOFF=10500
HIGH_BYTES_CUTOFF=137544295
#cutoffs for issueing warnings

GLOB_STR="./test_logs.log*"
PARSING_RE=re.compile("""^(\S+) (\S+) (\S+) \[([^\]]+)\] """+
        """"([A-Z]+) ([^ "]+) HTTP/[0-9.]+" ([0-9]{3}) ([0-9]+|-)*$""")

### Utility functions
def getNow():
    return datetime.now(tzlocal())

def getTimeStr(t=None):
    if t is None:
        t=datetime.now(tzlocal())
    return t.strftime("%d/%b/%Y:%H:%M:%S %z")

def parseLogStr(s):
    """
    simple parser for common log format, does not raise
    because it's used to detect malformatted lines as well
    """
    match=PARSING_RE.match(s)
    if match is None:
        return None
    ip, uid, user, time_str, method, url, code, sz=match.groups()
    try:
        ip=socket.inet_aton(ip)
    except socket.error:
        return None
    time=parser.parse(time_str.replace(":"," ",1))
    sz = int(sz)
    code=int(sz)
    section=url.split("/")
    if len(section)>1:
        section=section[1]
    else:
        section=""
    return ip,uid,user,time, method, section, code, sz
