# synthetic log data generator
# make a rotating log file with 1mb max in size
# generate between 1 - ~100 log entries per second
from const import *
import logging
from logging.handlers import RotatingFileHandler
import numpy as np
from time import sleep, time
from random import choice
FMT = "{ip} {ident} {user} [{time}] \"{request} {url} HTTP/1.0\" {status} {size}"
logger = logging.getLogger("httplogger")
ch = RotatingFileHandler("test_logs.log", maxBytes=1 << 20, backupCount=2)
ch.setFormatter(logging.Formatter("%(msg)s"))
logger.addHandler(ch)
print("Starting to log, press CTRL+C to stop generating data")
ips = ["127.0.0.1", "8.8.4.8", "255.255.255.254", "10.11.12.13", "1.2.3.4"]
users = ["user1", "johnsmith", "mrdog", "yu"]
reqs = ["GET", "POST"]
urls = {"/": 1024, "/info": 2241, "/help": 4028, "/contact": 514,
        "/large": 55231, "/small": 223, "/small2": 110, "/large2": 44512}
print("Starting to log, press CTRL+C to stop generating data")
while True:
    mean = (np.sin(time())+1)*10
    cnts = np.random.normal(mean, mean*2, 10)
    for cnt in cnts:
        if cnt < 0:
            cnt = 0
        time_str = getTimeStr()
        for i in range(int(cnt)):
            url, sz = choice(list(urls.items()))
            d = {"ip": choice(ips), "size": sz, "ident": "-",
                 "user": choice(users), "request": choice(reqs), "url": url,
                 "status": 200, "time": time_str}
            logger.error(FMT.format(**d))
        sleep(0.1)
    sleep(0.5)
else:
    logger.error(FMT.format(**d))
