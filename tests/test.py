from sms_sender import *
from FUTIL.my_logging import *
import time

my_logging(console_level = DEBUG, logfile_level = INFO, details = True)
sms_sender = SmsSender(gammu_config = "gammu.ini", pin_code = "1234",  mqtt_out_topic = "FSMS\INCOMING", mqtt_host = '192.168.10.155')
sms_sender.stop()
self = sms_sender


def run(f):
    while True:
        print(f())
        time.sleep(1)