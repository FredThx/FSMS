import time, datetime, json

from tinydb import TinyDB
from tinydb_serialization import SerializationMiddleware
from tinydb_serialization.serializers import DateTimeSerializer
from tinydb.storages import JSONStorage

import logging
import gammu
import threading
import paho.mqtt.publish as publish

class SmsSender:
    '''Une file d'attente pour envoyer des sms via gammu
    '''
    def __init__(self, gammu_config, pin_code = None, mqtt_out_topic = None, mqtt_host = None, mqtt_port = 1883, delay = 1, nb_trys_max = 5):
        '''Initialisation
        gammu_config : a gammu file config
        delay : time between two sms
        '''
        logging.info("Start gammu state machine ....")
        self.state_machine = gammu.StateMachine()
        self.state_machine.ReadConfig(Filename=gammu_config)
        self.state_machine.Init()
        logging.info("Gammu state machine is initialised.")
        self.delay = delay
        self.pin_code = pin_code
        self.nb_trys_max = nb_trys_max
        self.queue = []
        self.set_datetime()
        #db
        serialization = SerializationMiddleware(JSONStorage)
        serialization.register_serializer(DateTimeSerializer(), 'TinyDate')
        db = TinyDB('db_sms.json', storage=serialization)
        self.inbox = db.table('inbox')
        #mqtt
        self.mqtt_out_topic = mqtt_out_topic
        self.mqtt_host = mqtt_host
        self.mqtt_port = mqtt_port
        #Incoming callback
        #self.state_machine.SetIncomingCallback(self.on_incoming)
        #thread always_run
        self.thread_is_running = True
        self.thread = threading.Thread(target=self.always_run)
        self.thread.start()
        logging.debug(f"SmsSender created : {self}")

    def always_run(self):
        '''backbround function
        '''
        while self.thread_is_running:
            self.send_all()
            logging.debug("Queue is empty.")
            try:
                self.recept_all()
                self._status = self._get_status()
            except gammu.GSMError  as e:
                self._status = f"Error : {e}"
                logging.error(self._status)
            time.sleep(self.delay)
    
    def stop(self):
        self.thread_is_running = False
    
    def send(self, message, callback = None):
        '''Add a message to the queue and sent messages
        callback is function with one argument
        '''
        self.queue.append((message, callback, 0))

    def set_pin(self, pin = None):
        '''If needed, unlock the sim with pin code
        '''
        pin = pin or self.pin_code
        try:
            if pin and self.state_machine.GetSecurityStatus():
                    self.state_machine.EnterSecurityCode("PIN",pin)
        except gammu.ERR_TIMEOUT as e:
            logging.error(f"Error during PIN indentification : {e}")

    def send_all(self):
        '''Send all messages in th queue
        '''
        while self.queue:
            logging.debug(f"Queue lenght : {len(self.queue)}.")
            message, callback, trys = self.queue.pop(0)
            logging.debug(f"Try n°{trys} for {message}.")
            try:
                rep = self.state_machine.SendSMS(message)
            except gammu.GSMError as e:
                if trys < self.nb_trys_max:
                    self.queue.append((message, callback, trys+1))
                    logging.warning(f"SMS error (try{trys}/{self.nb_trys_max}): {message} => {e}")
                    rep = None
                else:
                    logging.error(f"SMS not send : {message} => {rep}")
                    rep = e
                self.set_pin()
            else:
                logging.debug(f"SMS send : {message} => {rep}")
            if rep and callback:
                callback(rep)
            time.sleep(self.delay)

    def get_status(self):
        ''' Return the (cached) status of the phone : a dict
        '''
        return self._status

    def _get_status(self):
        '''Return a dict
        '''
        status = {}
        status['device'] = self.state_machine.GetConfig().get('Device')
        status['connection'] = self.state_machine.GetConfig().get('Connection')
        status['datetime'] = self.state_machine.GetDateTime()
        status['firmware'] = self.state_machine.GetFirmware()
        status['imei'] = self.state_machine.GetIMEI()
        status.update(self.state_machine.GetNetworkInfo())
        status['imsi'] = self.state_machine.GetSIMIMSI()
        status['smsc'] = self.state_machine.GetSMSC()
        status['sms_status'] = self.state_machine.GetSMSStatus()
        status['sms_folders'] = self.state_machine.GetSMSFolders()
        status['security'] = self.state_machine.GetSecurityStatus() or "OK"
        status['signal_quality'] = self.state_machine.GetSignalQuality()
        return status

    def get_inbox(self):
        return self.inbox.all()

    def _get_inbox(self, only_unread = False):
        '''Return all inbox sms
        '''
        #sim_used = self.state_machine.GetSMSStatus().get('SIMUsed')
        sim_size = self.state_machine.GetSMSStatus().get('SIMSize')
        inbox = []
        for location in range(1,sim_size+1):
            try:
                #logging.debug(f"sms = self.state_machine.GetSMS(0,{location})[0]")
                sms = self.state_machine.GetSMS(0,location)[0]
                #logging.debug(f"sms = {sms}")
                del sms['UDH']
                #Attention, la lecture du sms rend le sms lu
                if not only_unread or sms.get('State')=='UnRead':
                    inbox.append(sms)
            except gammu.ERR_EMPTY:
                pass
        return inbox

    def recept_all(self):
        '''read sms inbox 
            - store messages on disk
            - send mqtt message
        '''
        logging.debug("Check for new messages...")
        new_messages = self._get_inbox(only_unread = True) or []
        for message in new_messages:
            logging.info(f"New message arrived : {message}")
            self.inbox.insert(message)
            self.send_mqtt(json.dumps(message, default = self.json_serial))

    def check_status(self):
        '''read something from the phone (for on_incoming)
        DEPRECATED
        '''
        try:
            self.state_machine.GetBatteryCharge()
        except gammu.GSMError  as e:
            logging.error(e)

    def on_incoming(self, state_machine, callback_type, data):
        '''When an new message is incoming to the phone
        notes : must be register by self.state_machine.SetIncomingCallback(self.incoming)
                and the phone must be read by any command.
        DEPRECATED
        '''
        logging.info(f"Received incoming event type {callback_type}, data: {data}")
        if callback_type != "SMS":
            logging.warning("Unsupported event!")
        if "Number" not in data:
            data = state_machine.GetSMS(data["Folder"], data["Location"])[0]
        message = data
        self.inbox.insert(message)
        self.send_mqtt(json.dumps(message, default = self.json_serial))      

    def send_mqtt(self, payload):
        '''Send mqtt message
        '''
        if self.mqtt_out_topic:
            try:
                publish.single(self.mqtt_out_topic, payload, hostname = self.mqtt_host, port = self.mqtt_port)
                logging.debug(f"MQTT  publish {self.mqtt_out_topic} => {payload}")
            except Exception as e:
                logging.error(e)
            else:
                return True

    def set_datetime(self, date=None):
        '''Set the date (or now) to the phone
        '''
        if date is None:
            date= datetime.datetime.now()
        self.state_machine.SetDateTime(date)
    
    @staticmethod
    def json_serial(obj):
        if isinstance(obj, (datetime.datetime, datetime.date)):
            return obj.isoformat()
        raise TypeError ("Type %s not serializable" % type(obj))


if __name__ == "__main__":
    from FUTIL.my_logging import *
    my_logging(console_level = DEBUG, logfile_level = INFO, details = True)
    sms_sender = SmsSender(gammu_config = "gammu.ini", pin_code = "1234",  mqtt_out_topic = "FSMS\INCOMING", mqtt_host = '192.168.10.155')
    while True:
        try:
            time.sleep(1)
        except KeyboardInterrupt:
            sms_sender.stop()
            sys.exit()