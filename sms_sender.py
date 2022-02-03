import time, datetime
import logging
import gammu
import threading

class SmsSender:
    '''Une file d'attente pour envoyer des sms via gammu
    '''
    def __init__(self, state_machine, pin_code = None, delay = 1, nb_trys_max = 5):
        '''Initialisation
        state_machine : a gammu.StateMachine
        delay : time between two sms
        '''
        self.state_machine = state_machine
        self.delay = delay
        self.pin_code = pin_code
        self.nb_trys_max = nb_trys_max
        self.queue = []
        logging.debug(f"SmsSender created : {self}")
        self.set_datetime()
        self.thread_is_running = True
        self.thread = threading.Thread(target=self.always_run)
        self.thread.start()

    def always_run(self):
        '''backbround function
        '''
        while self.thread_is_running:
            self.run()
            #logging.debug("Queue is empty.")
            time.sleep(0.1)

    def send(self, message, callback = None):
        '''Add a message to the queue and sent messages
        callback is function with one argument
        '''
        self.queue.append((message, callback, 0))

    def set_pin(self, pin = None):
        pin = pin or self.pin_code
        try:
            if pin and self.state_machine.GetSecurityStatus():
                    self.state_machine.EnterSecurityCode("PIN",pin)
        except gammu.ERR_TIMEOUT as e:
            logging.error(f"Error during PIN indentification : {e}")

    def run(self):
        '''Send messages
        '''
        while self.queue:
            logging.debug(f"Queue lenght : {len(self.queue)}.")
            message, callback, trys = self.queue.pop(0)
            logging.debug(f"Try n°{trys} for {message}.")
            try:
                rep = self.state_machine.SendSMS(message)
            except Exception as e:
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

    def get_inbox(self, only_unread = False):
        '''Return all inbox sms
        '''
        #sim_used = self.state_machine.GetSMSStatus().get('SIMUsed')
        sim_size = self.state_machine.GetSMSStatus().get('SIMSize')
        inbox = []
        for location in range(1,sim_size+1):
            try:
                sms = self.state_machine.GetSMS(0,location)[0]
                del sms['UDH']
                #Attention, la lecture du sms rend le sms lu
                if not only_unread or sms.get('State')=='UnRead':
                    inbox.append(sms)
            except gammu.ERR_EMPTY:
                pass
        return inbox


    def set_datetime(self, date=None):
        '''Set the date (or now) to the phone
        '''
        if date is None:
            date= datetime.datetime.now()
        self.state_machine.SetDateTime(date)
