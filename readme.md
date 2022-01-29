# FSMS

A web server with simple API to send SMS via GAMMU compatible GSM modem.

## Hardware

* raspberry pi to host web server
* GSM modem (ex SIM800L) on raspberry pi serial port
* SIM card

## Software

* Gammu ( https://fr.wammu.eu/gammu/ )
* Flask web server ( https://flask.palletsprojects.com/ )
* gevent wsgi server ( http://www.gevent.org/ )
* python

## API

http://my-host:5000/sms?text=sms_text&numbers=tel_numbers

## Author

Fredthx
