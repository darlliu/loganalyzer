# Author: Yu Liu
# A simple log analyzer that monitors traffic
# goals: 1, read rotating log files in a robust and performance aware fashion
# 2, calculate the amount of traffic and give alerts when thresholds are crossed
# 3, have reliable ways to produce outputs, in the form of console outputs and html
# 4, have a reasonable level of performance
# 5, design a good data structure with room for additional functionalities
# 6, perform tests using synthetic data
from const import *
import numpy as np
import pandas as pd

### Data classes


class LogRecord(object):
    """
    Stores a series of timestamps and metadata from logs
    Has a maximum storage age of (2 min) and can retrieve
    values in fixed intervals, e.g. (10 sec)
    """

    def __init__(self):
        self.times = []
        self.vals = []
        self.updated = None
        return

    def add(self, t, v):
        if self.updated != None and (t-self.updated).total_seconds() < 0:
            #we only allow incremental t, if t is older than last update
            #there is likely some issue with the log and we should skip
            return
        self.updated = t
        self.times.append(t)
        self.vals.append(v)
        self.clean(t)
        return

    def clean(self, t=None):
        if t is None:
            t = self.updated
        if self.times and (t-self.times[0]).total_seconds() > TIME_LIMIT_TOTAL:
            #remove records that are too old
            for idx, cur_t in enumerate(self.times):
                if (t-cur_t).total_seconds() <= TIME_LIMIT_CUTOFF:
                    break
            self.vals = self.vals[idx:]
            self.times = self.times[idx:]
        return

    def get(self, t, delta=TIME_LIMIT_INTERVAL):
        self.clean(t)
        if self.times and (self.times[0]-t).total_seconds() > 0:
            return pd.Series(), pd.Series()
        for idx, cur_t in enumerate(self.times):
            if (t-cur_t).total_seconds() <= delta:
                break
        else:
            #result is empty
            return pd.Series(), pd.Series()
        # print (t, start_i, end_i, len(self.times))
        ts, vs = self.times[idx:], self.vals[idx:]
        s = pd.Series([1 for i in ts], index=ts)
        s2 = pd.Series(vs, index=ts)
        return s.resample("1s").sum(),\
            s2.resample("1s").sum()

    def __str__(self):
        return """ Updated: {} - Times:...{} Data: ...{} """.format(self.updated,
                                                                    self.times[-3:], self.vals[-3:])

    def __repr__(self):
        return str(self)


class LogStore(LogRecord):
    def __init__(self):
        self.data = {}
        super(LogStore, self).__init__()
        return

    def add_record(self, val):
        ip, uid, user, time, method, section, code, sz = val
        #unpack directly here because we expect the argument to be correct at this point
        #store ip
        self.data.setdefault("ip", {}).setdefault(
            ip, LogRecord()).add(time, sz)
        #store id
        self.data.setdefault("id", {}).setdefault(
            uid, LogRecord()).add(time, sz)
        #store user
        self.data.setdefault("user", {}).setdefault(
            user, LogRecord()).add(time, sz)
        #store section
        self.data.setdefault("section", {}).setdefault(
            section, LogRecord()).add(time, sz)
        #add total traffic
        self.add(time, sz)
        return time

    def clean(self, t):
        "remove records that are too old to be useful"
        for key in self.data:
            for rec in list(self.data[key].keys()):
                if (t - self.data[key][rec].updated).total_seconds() > TIME_LIMIT_CUTOFF:
                    self.data[key].pop(rec)
        return

    def summarize_stats(self, cutoff_time):
        """
        Returns a summary of critical stats given a cutoff time
        Total traffic is calculated in the past 2 min while some 
        other stats are calculated in the past 10 sec
        """
        data = {key: {} for key in self.data}
        for key in self.data:
            for item, record in list(self.data[key].items()):
                vals = record.get(cutoff_time)
                data[key][item] = (vals[0].sum(), vals[1].sum())
        out = {}
        for k1 in data:
            max_hit = sorted(list(data[k1].values()),
                             key=lambda x: x[0])[-1][0]
            max_byte = sorted(list(data[k1].values()),
                              key=lambda x: x[1])[-1][1]
            top_hits = ["Section: /{}, traffic: {} (hits)".format(k, v[0])
                        for k, v in list(data[k1].items()) if v[0] == max_hit]
            top_bytes = ["Section: /{}, traffic: {} (bytes)".format(k, v[1])
                         for k, v in list(data[k1].items()) if v[1] == max_byte]
            #there could be multiple sections with the top hits/bytes
            out[k1] = {"top_hits": top_hits, "top_bytes": top_bytes}
        return out


if __name__ == "__main__":
    L = LogStore()
    time = L.add_record(parseLogStr(
        """127.0.0.1 user-identifier frank [10/Oct/2000:13:55:36 -0700] "GET /apache_pb.gif HTTP/1.0" 200 2326"""))
    time = L.add_record(parseLogStr(
        """127.0.0.1 user-identifier frank [10/Oct/2000:13:55:37 -0700] "GET /apache_pb.gif HTTP/1.0" 200 2326"""))
    time = L.add_record(parseLogStr(
        """127.0.0.1 user-identifier frank [10/Oct/2000:13:55:38 -0700] "GET /apache_pb.gif HTTP/1.0" 200 2326"""))
    time = L.add_record(parseLogStr(
        """127.0.0.1 user-identifier frank [10/Oct/2000:13:55:39 -0700] "GET /apache_pb.gif HTTP/1.0" 200 2326"""))
    time = L.add_record(parseLogStr(
        """127.0.0.1 user-identifier frank [10/Oct/2000:13:55:39 -0700] "GET /apache_pb.gif HTTP/1.0" 200 2326"""))
    time = L.add_record(parseLogStr(
        """127.0.0.1 user-identifier frank [10/Oct/2000:13:55:40 -0700] "GET /apache_pb.gif HTTP/1.0" 200 2326"""))
    print(L.summarize_stats(time))
    L.clean(getNow())
    print(L.data)
