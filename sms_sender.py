import time
import logging

class SmsSender:
    '''Une file d'attente pour envoyer des sms via gammu
    '''
    def __init__(self, state_machine, pin_code = None, delay = 1):
        '''Initialisation
        state_machine : a gammu.StateMachine
        delay : time between two sms
        '''
        self.state_machine = state_machine
        self.delay = delay
        self.pin_code = pin_code
        self.queue = []
        self.is_running = False
        logging.debug(f"SmsSender created : {self}")

    def send(self, message, callback = None):
        '''Add a message to the queue and sent messages
        callback is function with one argument
        '''
        self.queue.append((message, callback))
        if not self.is_running:
            self.run()

    def run(self):
        '''Send messages
        '''
        self.is_running = True
        while self.queue:
            message, callback = self.queue.pop(0)
            if self.pin_code and self.state_machine.GetSecurityStatus():
                self.state_machine.EnterSecurityCode("PIN",self.pin_code)
            try:
                rep = self.state_machine.SendSMS(message)
            except Exception as e:
                rep = e
                logging.error(f"SMS not send : {message} => {rep}")
            else:
                logging.debug(f"SMS send : {message} => {rep}")
            if callback:
                callback(rep)
            time.sleep(self.delay)
        self.is_running = False