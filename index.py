from mimetypes import MimeTypes
from flask import Flask, request, current_app, render_template, jsonify
from flask_httpauth import HTTPBasicAuth
from flask_cors import CORS

#import gammu
from sms_sender import SmsSender

from werkzeug.security import generate_password_hash, check_password_hash

from FUTIL.my_logging import *
my_logging(console_level = DEBUG, logfile_level = INFO, details = True)

app = Flask(__name__)
CORS(app)

auth = HTTPBasicAuth()
from users import users
users={user:generate_password_hash(password) for user, password in users.items()}

@auth.verify_password
def verify_password(username, password):
    if username in users:
        return check_password_hash(users.get(username), password)
    return False

#@app.before_first_request
#def load_sms_sender():
with app.app_context():
    '''Initialisation de SmsSender
    '''
    if not hasattr(current_app,"sms_sender"):
        current_app.sms_sender = True
        current_app.sms_sender = SmsSender(gammu_config = "gammu.ini", pin_code = "1234",  mqtt_out_topic = "FSMS\INCOMING", mqtt_host = '192.168.10.155')


@app.route('/')
@auth.login_required
def index():
    '''page d'acceuil
    '''
    logging.info(f"request '/' from {request.remote_addr} : args = {request.args}")
    status = current_app.sms_sender.get_status()
    return render_template('acceuil.html', status = status)


@app.route('/status')
@auth.login_required
def status():
    logging.info(f"request '/status' from {request.remote_addr} : args = {request.args}")
    status = current_app.sms_sender.get_status()
    return jsonify(status)

@app.route('/inbox')
@auth.login_required
def inbox():
    logging.info(f"request '/inbox' from {request.remote_addr} : args = {request.args}")
    inbox = current_app.sms_sender.get_inbox()
    print(inbox)
    return jsonify(inbox)


@app.route('/sms')
@auth.login_required
def sms():
    '''API envoie de SMS
    '''
    logging.info(f"request '/sms' from {request.remote_addr} : args = {request.args}")
    text = request.args.get('text')
    numbers = request.args.get('numbers')
    logging.debug(f"http : /&text = {text} numbers={numbers}")
    if text and numbers:        
        message = {"Text":text, "SMSC" : {"Location" : 1}, "Number" : numbers}
        current_app.sms_sender.send(message)
        return "OK"
    else:
        return "Need text and number(s)!"


if __name__ == "__main__":
    app.run(host='0.0.0.0', port=5000, debug=True,use_reloader=False)