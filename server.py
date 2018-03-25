#server for monitoring logfile and visualizing results
from flask import Flask, jsonify, render_template
import json
import argparse
from multiprocessing import Process
import atexit
from const import *
from watcher import Run

app = Flask(__name__)
app.secret_key = "ZDFSRQ#E!@#@#$DFGHDFGHERTQWEDDVXCVBA"


@app.route("/", methods=["GET"])
def Index():
    return render_template("index.html")


@app.route("/data", methods=["GET"])
def GetData():
    try:
        s = open("tmp.json", "r").read()
        js = json.loads(s)
    except:
        js = {}
    return jsonify(js)


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description='Web Server')
    parser.add_argument('--port', type=int,
                        help='Port number for deployment', default=8787)
    parser.add_argument('--debug', action='store_true',
                        help='Run in debug mode')
    parser.add_argument('--files', default=None,
                        help='Pattern for log files, leave empty for test_logs.log*')
    args = parser.parse_args()
    if args.files != None:
        GLOB_STR = str(args.files)
    p = Process(target=Run, args=(GLOB_STR,))
    p.start()
    atexit.register(lambda: p.terminate())
    app.run(host='0.0.0.0', port=args.port, debug=args.debug)
