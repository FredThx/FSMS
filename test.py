import gammu
from sms_sender import SmsSender


state_machine = gammu.StateMachine()
state_machine.ReadConfig(Filename='gammu.ini')
state_machine.Init()
sms_sender = SmsSender(state_machine, pin_code = "1234")