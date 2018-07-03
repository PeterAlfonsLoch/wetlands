import threading
import serial
import time
import sys
import random

class Sketch(threading.Thread):
    def __init__(self):
        threading.Thread.__init__(self)

        self.framerate = 10.0
        self.delay = 1.0 / self.framerate

        self.ser = serial.Serial()
        self.ser.port = '/dev/ttyUSB0'
        if self.ser.isOpen():
            self.ser.close()
        self.ser.open()

        self.frames = 0
        self._millis = 0.0
        self._start = time.time()
        self.setup()

    def convert_to_DMX_addresses(self, data):
        values_for_dmx = {}
        for device_name, dmx_val in data.items():
            if device_name in self.dmx_channels:
                values_for_dmx[str(self.dmx_channels[device_name])] = dmx_val
        return values_for_dmx

    def set_state(self, state):
        dmx_address_to_value_map = self.convert_to_DMX_addresses(state)
        print dmx_address_to_value_map
        for address, value in dmx_address_to_value_map.items():
            self.device_states[int(address)] = int(value)
        self.sendmsg(6, self.device_states)

    def sendmsg(self, label, message=[]):
        l = len(message)
        lm = l >> 8
        ll = l - (lm << 8)
        if l <= 600:
            if self.ser.isOpen():
                arr = [0x7E, label, ll, lm] + message + [0xE7]
                self.ser.write(bytearray(arr))
        else:
            sys.stderr.write('TX_ERROR: Malformed message! The message to be send is too long!\n')

    def sendDMX(self, channels):
        data = [0] + channels
        while len(data) < 25:
            data += [0]
        self.sendmsg(6, data)

    def light(self, lightname, r, g, b):
        state = {}
        state[lightname+'_r'] = r
        state[lightname+'_g'] = g
        state[lightname+'_b'] = b
        state[lightname+'_d'] = 255

        self.set_state(state)

    def millis(self):
        return self._millis

    def run(self):
        while True:
            self._millis = time.time() - self._start
            self.frames += 1
            time.sleep(self.delay)
            self.draw()

    def setup(self):
        self.device_states = [0]*40
        self.dmx_channels = {
            "mister_1": 1,
            "mister_2": 2,
            "pump": 3,
            "grow_light": 4,
            "dj_light_2_d": 8,
            "dj_light_2_r": 9,
            "dj_light_2_g": 10,
            "dj_light_2_b": 11,
            "dj_light_1_d": 15,
            "dj_light_1_r": 16,
            "dj_light_1_g": 17,
            "dj_light_1_b": 18,
            "raindrops_1": 32,
            "raindrops_2": 33,
            "raindrops_3": 34,
        }

        self.last_change = 0

    def draw(self):
        if self.millis() - self.last_change > 1000:
            r = random.randint(0, 255)
            g = random.randint(0, 255)
            b = random.randint(0, 255)
            self.light('dj_light_1', r, g, b)
            self.last_change = self.millis()

        # if self.millis() - self.last_drop > 1000:
        #     self.set_state({"raindrops_3": 255})
        #     self.last_drop = self.millis()
        # self.set_state({'dj_light_1_g': self.color[0]


sketch = Sketch()
sketch.start()
