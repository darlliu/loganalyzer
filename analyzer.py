# Author: Yu Liu
# A simple log analyzer that monitors traffic
# goals: 1, read rotating log files in a robust and performance aware fashion
# 2, calculate the amount of traffic and give alerts when thresholds are crossed
# 3, have reliable ways to produce outputs, in the form of console outputs and html
# 4, have a reasonable level of performance
# 5, design a good data structure with room for additional functionalities
# 6, perform tests using synthetic data
from const import *
import re
import numpy as np
import pandas as pd
import socket

PARSING_RE=re.compile("""^(\S+) (\S+) (\S+) \[([^\]]+)\] """+
        """"([A-Z]+) ([^ "]+) HTTP/[0-9.]+" ([0-9]{3}) ([0-9]+|-)*$""")


### Data classes
class LogRecord(object):
    """
    Stores a series of timestamps and metadata from logs
    Has a maximum storage age of 2 min and can retrieve
    values in any intervals, e.g. 10 sec
    """
    def __init__(self):
        self.times=[]
        self.vals=[]
        self.updated=None
        return
    def add(self,t,v):
        self.updated=t
        self.times.append(t)
        self.vals.append(v)
        if t-self.times[0]>timedelta(seconds=TIME_LIMIT_TOTAL):
            #remove records that are too old
            for idx, cur_t in enumerate(self.times):
                if t-cur_t<=timedelta(seconds=TIME_LIMIT_CUTOFF):
                    break
            self.vals=self.vals[idx:]
            self.times=self.times[idx:]
        return
    def get(self, t, delta=TIME_LIMIT_INTERVAL):
        for idx, cur_t in enumerate(self.times):
            if t-cur_t<=timedelta(seconds=delta):
                break
        t,v = self.times[idx:], self.vals[idx:]
        s=pd.Series([1 for i in t],index=t)
        s2=pd.Series(v,index=t)
        return s.groupby([pd.Grouper(freq="S")]).sum(),\
                s2.groupby([pd.Grouper(freq="S")]).sum()

    def __str__(self):
        return """ Updated: {} - Times:...{} Data: ...{} """.format(self.updated,
                self.times[-3:], self.vals[-3:])
    def __repr__(self):
        return str(self)

class LogStore(LogRecord):
    def __init__(self):
        self.data={}
        super(LogStore,self).__init__()
        return
    def add_record(self, s):
        #first, parse s assuming it follows the Common Log Format
        ip, uid, user, time_str, method, url, code, sz=PARSING_RE.match(s).groups()
        time=parser.parse(time_str.replace(":"," ",1))
        sz = int(sz)
        code=int(sz)
        try:
            ip=socket.inet_aton(ip)
        except socket.error:
            raise ValueError("log ip has wrong format".format(s[0]))
        section=url.split("/")
        if len(section)>1:
            section=section[1]
        else:
            section="/"
        #this parsing is simplistic but should work in almost all circumstances
        #store ip
        self.data.setdefault("ip",{}).setdefault(ip,LogRecord()).add(time,sz)
        #store id
        self.data.setdefault("id",{}).setdefault(uid,LogRecord()).add(time,sz)
        #store user
        self.data.setdefault("user",{}).setdefault(user,LogRecord()).add(time,sz)
        #store section
        self.data.setdefault("section",{}).setdefault(section,LogRecord()).add(time,sz)
        #add total traffic
        self.add(time,sz)
        return time

    def clean(self, t):
        "remove records that are too old to be useful"
        for key in self.data:
            for rec in self.data[key].keys():
                if t- self.data[key][rec].updated > timedelta(seconds=TIME_LIMIT_CUTOFF):
                    self.data[key].pop(rec)
        return

    def summarize_stats(self,cutoff_time):
        """
        Returns a summary of critical stats given a cutoff time
        Total traffic is calculated in the past 2 min while some 
        other stats are calculated in the past 10 sec
        """
        out = {key:{} for key in self.data}
        for key in self.data:
            for item, record in  self.data[key].items():
                vals=record.get(cutoff_time)
                out[key][item]={"total_hits":vals[0], "total_bytes":vals[1],}
        return out

    def total_traffic(self,t=None):
        """
        Returns some running stats of total traffic.
        """
        if t is None:
            t=getNow()
        hits,szs=self.get(t)
        out = {"hits":hits, "bytes":szs, "hits_gradient":np.gradient(hits),
                "bytes_gradient":np.gradient(szs)}
        return out

if __name__=="__main__":
    L=LogStore()
    time=L.add_record("""127.0.0.1 user-identifier frank [10/Oct/2000:13:55:36 -0700] "GET /apache_pb.gif HTTP/1.0" 200 2326""")
    time=L.add_record("""127.0.0.1 user-identifier frank [10/Oct/2000:13:55:37 -0700] "GET /apache_pb.gif HTTP/1.0" 200 2326""")
    time=L.add_record("""127.0.0.1 user-identifier frank [10/Oct/2000:13:55:38 -0700] "GET /apache_pb.gif HTTP/1.0" 200 2326""")
    time=L.add_record("""127.0.0.1 user-identifier frank [10/Oct/2000:13:55:39 -0700] "GET /apache_pb.gif HTTP/1.0" 200 2326""")
    time=L.add_record("""127.0.0.1 user-identifier frank [10/Oct/2000:13:55:39 -0700] "GET /apache_pb.gif HTTP/1.0" 200 2326""")
    time=L.add_record("""127.0.0.1 user-identifier frank [10/Oct/2000:13:55:40 -0700] "GET /apache_pb.gif HTTP/1.0" 200 2326""")
    print L.summarize_stats(time)
    print L.total_traffic(time)
    L.clean(getNow())
    print L.data