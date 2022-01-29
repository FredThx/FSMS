from mimetypes import MimeTypes
from flask import Flask, request, current_app
from flask_httpauth import HTTPBasicAuth
from flask_cors import CORS

import gammu
from sms_sender import SmsSender

from werkzeug.security import generate_password_hash, check_password_hash

from FUTIL.my_logging import *
my_logging(console_level = DEBUG, logfile_level = INFO, details = True)

app = Flask(__name__)
CORS(app)

auth = HTTPBasicAuth()

users = {
    "fredthx": generate_password_hash("thx_")
}

@auth.verify_password
def verify_password(username, password):
    if username in users:
        return check_password_hash(users.get(username), password)
    return False

@app.before_first_request
def load_sms_sender():
    logging.info("Start gammu state machine ....")
    state_machine = gammu.StateMachine()
    state_machine.ReadConfig(Filename='gammu.ini')
    state_machine.Init()
    logging.info("Gammu state machine is initialised.")
    current_app.sms_sender = SmsSender(state_machine, pin_code = "1234")



@app.route('/')
@auth.login_required
def index():
    return "Salut"


@app.route('/sms')
@auth.login_required
def sms():
    text = request.args.get('text')
    numbers = request.args.get('numbers')
    logging.debug(f"http : /&text = {text} numbers={numbers}")
    if text and numbers:        
        message = {"Text":text, "SMSC" : {"Location" : 1}, "Number" : numbers}
        current_app.sms_sender.send(message)
        return "OK (ou pas!)"
    else:
        return "Need text and number(s)!"


if __name__ == "__main__":
    app.run(host='0.0.0.0', port=50888, debug=True)