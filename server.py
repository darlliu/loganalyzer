#server for monitoring logfile and visualizing results
import os
import glob
from const import *
from data import *
from tqdm import tqdm
from flask import Flask
from flask import render_template
import json
import argparse
GLOB_STR="./test_logs.log*"

app = Flask(__name__)
app.secret_key= "ZDFSRQ#E!@#@#$DFGHDFGHERTQWEDDVXCVBA"
FP=None
LS=LogStore()
CurTime=getNow()
def Update(ls,fp=None):
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
        for line in tqdm(cur_fp.readlines(),fname):
            val=parseLogStr(line)
            if val is None: continue
            time=val[3]
            if startTime==None:
                td=cur_time-time
                if (td)<timedelta(seconds=0):
                    raise ValueError("Error in update logic, start time is later than current time!")
                elif td<timedelta(seconds=TIME_LIMIT_CUTOFF):
                    #start logging
                    ls.add_record(val)
                    startTime=time
                else: continue
            else:
                ls.add_record(val)
                if (cur_time-time)<=timedelta(microseconds=TIME_LIMIT_UPDATE):
                    endTime=time
                    break
    if time!=None and endTime is None:
        endTime=time
    if startTime!=None and endTime!=None and endTime-startTime > timedelta(seconds=1):
        return cur_time, cur_fp
    return cur_time,None

@app.route("/",methods=["GET"])
def Index():
    return render_template("index.html")

@app.route("/data",methods=["GET"])
def GetData():
    global FP,CurTime,LS
    CurTime,FP=Update(LS,FP)
    s1,s2=LS.get(CurTime)
    out={"traffic_hits":s1.to_json(),
        "traffic_bytes":s2.to_json()}
    return json.dumps(out)

if __name__ == '__main__':
    parser = argparse.ArgumentParser(description='Web Server')
    parser.add_argument('--port', type=int, help='Port number for deployment', default=8787)
    parser.add_argument('--debug', action='store_true', help='Run in debug mode')
    args = parser.parse_args()
    app.run(host='0.0.0.0',port=args.port,debug=args.debug)
