import os
from time import sleep
import glob
from const import *
from data import *
import json

def Update(ls,fp=None,glob_str=GLOB_STR):
    """
    monitoring routine:
    1, create current time object, scan file patterns
    2, seek to the correct start time to scan the logs, this is
       the newer time between (current_time - storage age) and
       start of available log times
    3, from the start time, log all the way to current time,
       opening multiple files in rotating order if necessary
       stop when the log time is less than 1 update interval away
       or to the latest log entry
    4, return the current time and the
       LogStore objects after updating its values accordingly
    """
    cur_time=getNow()
    time=None
    fnames = glob.glob(GLOB_STR)
    fnames = sorted(fnames,reverse=True)
    if fp is None: 
        fin_ino=None #reset fname_in if it's outdated
    else:
        try:
            fin_ino=os.fstat(fp.fileno()).st_ino
            if os.fstat(fp.fileno()).st_size==0:
                fin_ino=None
        except IOError:
            fin_ino=None
    skipped_cnt=0
    startTime=None
    endTime=None
    for fname in fnames:
        cur_fp=None
        if fin_ino!=None:
            cur_ino=os.stat(fname).st_ino
            if fin_ino!=cur_ino:
                continue
                # seek to correct file indicated by fin_ino
            else:
                cur_fp=fp
                fin_ino=None
        if cur_fp==None:
            cur_fp=open(fname)
        for line in cur_fp.readlines():
            val=parseLogStr(line)
            if val is None: continue
            time=val[3]
            if (cur_time-time).total_seconds()<0:
                #if we seeked to the incorrect position, abort
                return cur_time,None
            if startTime==None:
                if (cur_time-time).total_seconds()<TIME_LIMIT_CUTOFF:
                    #start logging
                    ls.add_record(val)
                    startTime=time
                else: continue
            else:
                ls.add_record(val)
                if (cur_time-time).total_seconds()<=TIME_LIMIT_UPDATE:
                    endTime=time
                    break
    if time!=None and endTime is None:
        endTime=time
    if startTime!=None and endTime!=None and (endTime-startTime).total_seconds() > 1:
        return cur_time, cur_fp
    return cur_time,None

def Run(glob_str=GLOB_STR):
    """
    watches the log every so often and parses some info
    dumps into json file on disk for reading -- uses a tmp file in
    the cwd
    """
    FP=None
    LS=LogStore()
    CurTime=getNow()
    States={}
    def to_json(*rs):
        out=[]
        for eles in zip(*rs):
            inner=[]
            for ele in eles:
                inner.append({"v":ele,"f":None})
            out.append({"c":inner})
        return out
    while True:
        CurTime,FP=Update(LS,FP,glob_str)
        #grab traffic data in the past minute
        print("getting total traffic")
        s1,s2=LS.get(CurTime, TIME_LIMIT_TRAFFIC)
        traffic_json={"cols":[{"id":"","pattern":"","label":"Relative Time","type":"number"},
            {"id":"","pattern":"","label":"Hits", "type":"number"},
            {"id":"","pattern":"","label":"Bytes", "type":"number"},
            {"id":"","pattern":"","label":"Hits(delta)", "type":"number"},
            {"id":"","pattern":"","label":"Bytes(delta)", "type":"number"},
            ]}
        if len(s1)>3:
            grad1,grad2=np.gradient(s1), np.gradient(s2)
        else:
            #need to wait a bit for the update
            sleep(TIME_LIMIT_UPDATE)
            continue
        traffic_json["rows"]=to_json([-len(s1)+i+1 for i in range(len(s1))],
                s1.values.tolist(), s2.values.tolist(), grad1.tolist(), grad2.tolist())
        print("getting other data")
        #format traffic data for google chart, calculating gradients
        data=LS.summarize_stats(CurTime)
        print(data,len(s1), CurTime)
        #grab stats from the past 10 sec
        out={"traffic":traffic_json}
        out["time"]=CurTime.isoformat()
        out["top_stats_hits"]="<p></p>".join(data["section"]["top_hits"])
        out["top_stats_bytes"]="<p></p>".join(data["section"]["top_bytes"])
        out["grad_hits"]="Top up spike: {} hits <p> Top down spike: {} hits"\
                .format(max(grad1),min(grad1))
        out["grad_bytes"]="Top up spike: {} bytes <p> Top down spike: {} bytes"\
                .format(max(grad2),min(grad2))
        warnings_hits=States.setdefault("warnings_hits",[])
        warnings_bytes=States.setdefault("warnings_bytes",[])
        high_traffic_hits=States.setdefault("high_traffic_hits",False)
        high_traffic_bytes=States.setdefault("high_traffic_bytes",False)
        s1,s2=LS.get(CurTime, TIME_LIMIT_CUTOFF) #get traffic for past 2 minutes
        total_hits=s1.sum()
        total_bytes=s2.sum()
        if not high_traffic_hits and total_hits >= HIGH_HITS_CUTOFF:
            warnings_hits.append("High traffic generated an alert - hits = {value}, triggered at {time}"\
                    .format(time=CurTime.isoformat(), value=total_hits))
            high_traffic_hits=True
        elif high_traffic_hits and total_hits< HIGH_HITS_CUTOFF:
            warnings_hits.append("Traffic restored to normal level - hits = {value}, triggered at {time}"\
                    .format(time=CurTime.isoformat(), value=total_hits))
            high_traffic_hits=False
        if not high_traffic_bytes and total_bytes >= HIGH_BYTES_CUTOFF:
            warnings_bytes.append("High traffic generated an alert - bytes = {value}, triggered at {time}"\
                    .format(time=CurTime.isoformat(), value=total_bytes))
            high_traffic_bytes=True
        elif high_traffic_bytes and total_bytes< HIGH_BYTES_CUTOFF:
            warnings_bytes.append("Traffic restored to normal level - bytes = {value}, triggered at {time}"\
                    .format(time=CurTime.isoformat(), value=total_bytes))
            high_traffic_bytes=False
        States["warnings_hits"]=warnings_hits
        States["high_traffic_hits"]=high_traffic_hits
        States["warnings_bytes"]=warnings_bytes
        States["high_traffic_bytes"]=high_traffic_bytes
        # print total_hits, high_traffic_hits, warnings_hits
        out["warnings"]={"hits":"<p></p>".join(warnings_hits), "bytes":"<p></p>".join(warnings_bytes)}
        high_hits = States.setdefault("high_hits",0)
        high_hits_time = States.setdefault("high_hits_time",CurTime.isoformat())
        if total_hits>high_hits:
            high_hits=total_hits
            high_hits_time=CurTime.isoformat()
        high_bytes = States.setdefault("high_bytes",0)
        high_bytes_time = States.setdefault("high_bytes_time",CurTime.isoformat())
        if total_bytes>high_bytes:
            high_bytes=total_bytes
            high_bytes_time=CurTime.isoformat()
        low_hits = States.setdefault("low_hits",1E12)
        low_hits_time = States.setdefault("low_hits_time",CurTime.isoformat())
        if total_hits<low_hits:
            low_hits=total_hits
            low_hits_time=CurTime.isoformat()
        low_bytes = States.setdefault("low_bytes",1E12)
        low_bytes_time = States.setdefault("low_bytes_time",CurTime.isoformat())
        if total_bytes<low_bytes:
            low_bytes=total_bytes
            low_bytes_time=CurTime.isoformat()
        States["high_hits"]=high_hits
        States["high_hits_time"]=high_hits_time
        States["high_bytes"]=high_bytes
        States["high_bytes_time"]=high_bytes_time
        States["low_hits"]=low_hits
        States["low_hits_time"]=low_hits_time
        States["low_bytes"]=low_bytes
        States["low_bytes_time"]=low_bytes_time
        out["historic"]={"hits":"""Highest total hits: {} hits at {}
                <p></p> Lowest total hits: {} hits at {} 
                <p></p> Current interval hits: {} hits/120s, mean {:.2f}/s, std {:.2f}/s"""\
                        .format(high_hits, high_hits_time, low_hits, low_hits_time, 
                            s1.sum(), s1.mean(), s1.std()), 
            "bytes":"""Top total bytes: {} bytes at {}
                <p></p> Lowest total bytes: {} bytes at {} 
                <p></p> Current interval bytes: {} bytes/120s, mean {:.2f}/s, std {:.2f}/s"""\
                        .format(high_bytes, high_bytes_time, low_bytes, low_bytes_time, 
                            s2.sum(), s2.mean(), s2.std()),}
        LS.clean(CurTime)
        with open("tmp.json","w") as f:
            f.write(json.dumps(out))
        sleep(TIME_LIMIT_UPDATE)
    return
