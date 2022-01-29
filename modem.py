from curses import baudrate
import serial
import logging


class Modem:
    '''Un modem 
    '''
    baudrate = 115000
    default_timeout = 1
    endstop = ['OK', 'ERROR']

    def __init__(self, port='/dev/serial0'):
        self.port = port
        self.serial = None

    def connect(self, timeout = None):
        if timeout is None:
            timeout = self.default_timeout
        try:
            self.serial = serial.Serial(self.port, self.baudrate, timeout = timeout)
        except serial.serialutil.SerialException as e:
            logging.warning(e)
            self.serial = None

    def _write(self, cmd):
        '''Write AT commande to the modem
        '''
        self.serial.write(cmd.encode()+b'\r')

    def _read(self, endstop = None):
        '''read the serial port until enstop or timeout
        return a list a lines
        '''
        result = []
        line = b''
        rep = True
        if endstop is None:
            endstop = self.endstop
        if type(endstop)!=list:
            endstop=list(endstop)
        while rep and (result == [] or result[-1] not in endstop):
            rep = self.serial.read()
            if rep != b'\r':
                if rep != b'\n':
                    line += rep
                else:
                    if line:
                        result.append(line.decode('utf-8'))
                    line = b''
        return result

    def send_cmd(self, cmd, endstop = None, timeout = None):
        '''Witte cmd and return result
        '''
        self.connect(timeout)
        self._write(cmd)
        return self._read(endstop)


if __name__ == '__main__':
    m = Modem('/dev/serial0')
    print(m.send_cmd('AT'))
    