# A simple log analyzer for datadog interview
# goals: 1, read rotating log files in a robust and performance aware fashion
# 2, calculate the amount of traffic and give alerts when thresholds are crossed
# 3, have reliable ways to produce outputs, in the form of console outputs and html
# 4, have a reasonable level of performance
# 5, design a good data structure with room for additional functionalities
# 6, perform tests using synthetic data
import os
from datetime import datetime
from dateutil import parser
import socket

class LogRecord(object):
    """
    Stores a series of timestamps and metadata from logs
    Has a maximum storage age of 2 min and can retrieve
    values in any intervals, e.g. 10 sec
    """
    def __init__(self,t,v,cutoff=120, limit=150):
        """
        limit -- storage limit in seconds
        cutoff -- max storage age in seconds
        limit is larger than cutoff to avoid having to truncate
        lists too often
        """
        #self.tag=tag #may be redundant
        self.times=[t]
        self.vals=[v]
        self.limit=limit
        self.cutoff=cutoff
        self.updated=t
        return
    def add(self,t,v):
        self.updated=t
        self.times.append(t)
        self.vals.append(v)
        if len(self.times)>self.limit:
            self.times=self.times[-self.cutoff:]
            self.vals=self.vals[-self.cutoff:]
        return
    def __str__(self):
        return """ Updated: {} - Times:...{} Data: ...{} """.format(self.updated,
                self.times[-3:], self.vals[-3:])
    def __repr__(self):
        return str(self)

class LogStore(object):
    def __init__(self):
        self.data={}
        self.traffic=[]
        self.times=[]
        return
    def add_record(self, s):
        #first, parse s assuming it follows the Common Log Format
        time=parser.parse(s[s.index("[")+1:s.index("]")].replace(":"," ",1))
        s2=s[s.index("\"")+1:s.rindex("\"")]
        #this parsing is simplistic but should work in almost all circumstances
        section=s2.split()[1].split("/")
        if len(section)>1:
            section=section[1]
        else:
            section="/"
        s=[i.strip() for i in s.split() if i!=""]
        try:
            ip=socket.inet_aton(s[0])
        except socket.error:
            raise ValueError("log ip has wrong format".format(s[0]))
        uid=s[1]
        user=s[2]
        sz = int(s[-1])
        code=int(s[-2])
        #this assumes the log format to be exact as the wiki page
        #store ip
        self.data.setdefault("ip",{}).setdefault(ip,LogRecord(time, sz))
        #store id
        self.data.setdefault("id",{}).setdefault(uid,LogRecord(time, sz))
        #store user
        self.data.setdefault("user",{}).setdefault(user,LogRecord(time, sz))
        #store section
        self.data.setdefault("section",{}).setdefault(section,LogRecord(time, sz))
        return
    def summarize_stats(self,cutoff_time):
        """
        Returns a summary of critical stats given a cutoff time
        Total traffic is calculated in the past 2 min while some 
        other stats are calculated in the past 10 sec
        """
        return
    def total_traffic(self):
        """
        Returns a running sum of total traffic in the last 2 mins.
        Does not take a time parameter--time specific traffic can be
        derived from the stats summary.
        """
        return


L=LogStore()
L.add_record("""127.0.0.1 user-identifier frank [10/Oct/2000:13:55:36 -0700] "GET /apache_pb.gif HTTP/1.0" 200 2326""")
print L.data
