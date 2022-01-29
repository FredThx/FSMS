import modem
import time
import logging
import parse

class Sim800l(modem.Modem):
    '''Un modem GSM SIM800L
    '''
    endstop = ['OK', 'ERROR']

    def __init__(self, port='/dev/serial0', pin = "1234"):
        super().__init__(port)
        self.pin = pin
   
    def test(self, param, endstop = None, timeout = None):
        '''request the modem and return a list of parameters
        '''
        result = self.send_cmd(f'AT+{param}=?', endstop, timeout)
        logging.debug(result)
        return result
    
    def read(self, param, endstop = None, timeout = None):
        '''read a value of parameter
        '''
        result = self.send_cmd(f"AT+{param}?", endstop, timeout)
        logging.debug(result)
        return result
    
    def write(self, param, value, endstop = None, timeout = None):
        '''Write value to the modem
        '''
        if type(value)==str:
            value = f'"{value}"'
        result = self.send_cmd(f"AT+{param}={value}", endstop, timeout)
        logging.debug(result)
        return result

    def execute(self, param, endstop = None, timeout = None):
        '''Execute command
        '''
        result = self.send_cmd(f"AT+{param}", endstop, timeout)
        logging.debug(result)
        return result
    
    def write_pin(self):
        '''Unlock the sim with pin code
        '''
        timeout = time.time() + self.default_timeout*5
        while self.read("CPIN")[1]=="+CPIN: SIM PIN" and time.time() < timeout:
            time.sleep(0.1)
            self.write("CPIN", self.pin, endstop="SMS Ready", timeout = 5)
            time.sleep(0.1)
        
    def send_sms(self, dest, text):
        '''Send a sms
        '''
        self.write_pin()
        self.write("CMGF", 1)
        self.write("CSCS","GSM")
        self._write(f'AT+CMGS="{dest}"')
        self._read('> ')
        self.connect(timeout = 60)
        self._write(f'{text}\x1a')
        rep = self._read()
        #rep = self.write("CMGS", f'"{dest}"\r\n{text}\x1a', timeout = 60)
        return rep
    
    def status(self):
        '''Return a dict with status of the modem
        '''
        result = {}
        result['manufacturer'] = self.execute('CGMI')[1]
        result['model'] = self.execute('CGMM')[1]
        result['PII'] = self.send_cmd("ATI")[1]
        result['csq'] = float(self.execute('CSQ')[1].split(":")[1].replace(',','.'))
        result['cpin'] = self.read("CPIN")[1]
        result['creg'] = self.read("CREG")[1]
        return result

    def cnetscan(self):
        self.write('cnetscan',1)#Show lac and bsic information 
        cnetscan = self.execute('CNETSCAN', timeout=45)
        if len(cnetscan)>2 and cnetscan[-1]=='OK':
            cnetscan =  cnetscan[1:-1]
        return cnetscan

    def wait_for_reg(self):
        '''wait for Network Registration 
        '''
        loop = True
        p_creg = {}
        while loop:
            self.write_pin()
            try:
                creg = self.read('CREG')[1]
            except IndexError:
                pass
            else:
                p_creg = parse.parse("+CREG: {n},{stat},{lac},{ci}", creg)
                if not p_creg:
                    p_creg = parse.parse("+CREG: {n},{stat}", creg)
                logging.debug(f"CREG : {p_creg}")
                if p_creg and p_creg['stat'] in ('1','3','5'):
                    loop = False
            time.sleep(1)
        logging.info(f"CREG : {p_creg}")
        if p_creg['stat']== '1':
            logging.info("CREG : Registered, home network")
        elif p_creg['stat']== '3':
            logging.info("CREG : Registation denied")
        if p_creg['stat']== '5':
            logging.info("CREG : Registered, roaming ")


if __name__ == '__main__':
    from FUTIL.my_logging import *
    my_logging(console_level = DEBUG, logfile_level = INFO, details = True)
    tel = Sim800l('/dev/serial0')
    tel.write_pin()
    print(tel.status())
    #print("Scan cellular network ....")
    #print(tel.cnetscan())
    tel.wait_for_reg()
    print("Send a sms...")
    print(tel.send_sms("+33608648987", "ça-va Frédéric?"))


    
