import base64
import json
import pickle
import os
import Queue
#import RPi.GPIO as GPIO
import random
import settings
import time
import datetime
import threading
import traceback
import socket
import sys

WL1 = "wetlands-environment-1"
WL2 = "wetlands-environment-2"
WL3 = "wetlands-environment-3"

BASE_PATH = os.path.dirname(os.path.realpath(__file__))
UPPER_PATH = os.path.split(os.path.dirname(os.path.realpath(__file__)))[0]
THIRTYBIRDS_PATH = "%s/thirtybirds_2_0" % (UPPER_PATH )

from thirtybirds_2_0.Network.manager import init as network_init

class Network(object):
    def __init__(self, hostname, network_message_handler, network_status_handler):
        self.hostname = hostname
        self.thirtybirds = network_init(
            hostname=self.hostname,
            role="server",
            discovery_multicastGroup=settings.discovery_multicastGroup,
            discovery_multicastPort=settings.discovery_multicastPort,
            discovery_responsePort=settings.discovery_responsePort,
            pubsub_pubPort=settings.pubsub_pubPort,
            message_callback=network_message_handler,
            status_callback=network_status_handler
        )


# Main handles network send/recv and can see all other classes directly
class Main(threading.Thread):
    def __init__(self, hostname):
        threading.Thread.__init__(self)
        self.network = Network(hostname, self.network_message_handler, self.network_status_handler)
        self.queue = Queue.Queue()
        self.network.thirtybirds.subscribe_to_topic("controller/")


        # timer = Timer(self)
        # timer.start()

    def network_message_handler(self, topic_data):
        # this method runs in the thread of the caller, not the tread of Main
        topic, data =  topic_data # separating just to eval msg.  best to do it early.  it should be done in TB.
        #print topic, data
        if len(data) > 0:
            try:
                data = eval(data)
            except Exception:
                pass
        self.add_to_queue(topic, data)

    def network_status_handler(self, status_ip_hostname):
        # this method runs in the thread of the caller, not the tread of Main
        print "Main.network_status_handler", status_ip_hostname
        if status_ip_hostname["status"] == "device_discovered":
            self.add_to_queue("register_with_server", status_ip_hostname["hostname"])

    def add_to_queue(self, topic, data):
        self.queue.put((topic, data))

    def run(self):
        while True:
            try:
                topic, data = self.queue.get(True)

                # listen for the timer function (every 5 seconds)
                if topic == "local/image_capture/response":
                    # tell the PIs to capture an image
                    self.network.thirtybirds.send("{}/image_capture/request".format(data), "")

                # listening for the PIs to recieve an image
                if topic == "controller/image_capture/response":
                    hostname, image_as_string = data
                    print 'got photo', hostname
                    timestamp = int(time.time())
                    filename = "{}_{}.png".format(hostname, timestamp)
                    pathname = "Captures/{}".format(filename)
                    with open(pathname, "wb") as fh:
                        fh.write(image_as_string.decode("base64"))

                if topic == "local/env_state/response":
                    hostname, env_state = data
                    self.network.thirtybirds.send("{}/env_state/set".format(hostname), env_state)

            except Exception as e:
                exc_type, exc_value, exc_traceback = sys.exc_info()
                print e, repr(traceback.format_exception(exc_type, exc_value,exc_traceback))

#main = None # reference here for


class Sketch(threading.Thread):
    def __init__(self, message_target):
        threading.Thread.__init__(self)
        self.message_target = message_target
        self.setup()
        self.daemon = True
        self.start()

    def set_state(self, hostname, env_state):
        self.message_target.add_to_queue("local/env_state/response", (hostname, env_state))

    def set_values(self, hostname, **kwargs):
        self.message_target.add_to_queue("local/env_state/response", (hostname, kwargs))

    def take_photo(self, hostname):
        self.message_target.add_to_queue("local/image_capture/response", hostname)

    def set_light(self, hostname, light_number, dimmer=0, r=0, g=0, b=0):
        light_name = 'dj_light_{}_'.format(light_number)
        state = {}
        state[light_name + 'r'] = r
        state[light_name + 'g'] = g
        state[light_name + 'b'] = b
        state[light_name + 'd'] = dimmer
        self.set_state(hostname, state)

    def setup(self):
        pass

    def draw(self):
        pass

    def run(self):
        while True:
            self.draw()


'''TEGA STUFF HERE'''

class PhotoTaker(Sketch):
    def setup(self):
        self.delay = 5

    def draw(self):
        print 'capture'
        self.take_photo('wetlands-environment-3')
        time.sleep(self.delay)

class StateExample(Sketch):
    def draw(self):
        self.set_state('wetlands-environment-3', {
            "mister_1": 0,
            "mister_2": 0,
            "pump": 0,
            "grow_light": 0,
            "dj_light_3_d": 255,
            "dj_light_3_r": 28,
            "dj_light_3_g": 29,
            "dj_light_3_b": 30,
            "dj_light_2_d": 255,
            "dj_light_2_r": 9,
            "dj_light_2_g": 10,
            "dj_light_2_b": 11,
            "dj_light_1_d": 255,
            "dj_light_1_r": 16,
            "dj_light_1_g": 17,
            "dj_light_1_b": 18,
            "raindrops_1": 255,
            "raindrops_2": 255,
            "raindrops_3": 255,
        })
        time.sleep(1)
        self.set_state('wetlands-environment-3', {
            "mister_1": 0,
            "mister_2": 0,
            "pump": 0,
            "grow_light": 0,
            "dj_light_3_d": 27,
            "dj_light_3_r": 28,
            "dj_light_3_g": 29,
            "dj_light_3_b": 30,
            "dj_light_2_d": 0,
            "dj_light_2_r": 9,
            "dj_light_2_g": 10,
            "dj_light_2_b": 11,
            "dj_light_1_d": 0,
            "dj_light_1_r": 16,
            "dj_light_1_g": 17,
            "dj_light_1_b": 18,
            "raindrops_1": 0,
            "raindrops_2": 0,
            "raindrops_3": 0,
        })
        time.sleep(6)

class LightsTest(Sketch):
    def draw(self):
        print 'lights'

        r1 = random.randint(0, 255)
        g1 = random.randint(0, 255)
        b1 = random.randint(0, 255)

        self.set_light('wetlands-environment-3', light_number=1, r=r1, b=b1, g=g1, dimmer=255)

        time.sleep(1)


class LightsTest2(Sketch):
    def setup(self):
        self.r = 0
        self.b = 0
        self.g = 0

    def draw(self):
        self.g += 10
        if self.g > 255:
            self.g = 0

        self.r += 3
        if self.r > 255:
            self.r = 0

        self.b += 7
        if self.b > 255:
            self.b = 0


        self.set_light('wetlands-environment-1', light_number=1, r=self.r, b=self.b, g=self.g, dimmer=255)
        self.set_light('wetlands-environment-1', light_number=2, r=self.r, b=self.b, g=self.g, dimmer=255)
        self.set_light('wetlands-environment-1', light_number=3, r=self.r, b=self.b, g=self.g, dimmer=255)

        self.set_values('wetlands-environment-1',raindrops_1=0)
        self.set_values('wetlands-environment-1',raindrops_2=0)
        self.set_values('wetlands-environment-1',raindrops_3=0)

        time.sleep(0.1)

class Dripper(Sketch):
    def draw(self):
        self.set_values('wetlands-environment-1', raindrops_1=255)
        self.set_values('wetlands-environment-1', raindrops_2=255)
        self.set_values('wetlands-environment-1', raindrops_3=255)
        time.sleep(0.5)
        self.set_values('wetlands-environment-1', raindrops_1=0)
        self.set_values('wetlands-environment-1', raindrops_2=0)
        self.set_values('wetlands-environment-1', raindrops_3=0)
            time.sleep(random.randint(3, 6))

class MisterExample(Sketch):
    def draw(self):
        self.set_values('wetlands-environment-2', mister_1=255)
        time.sleep(10)
        self.set_values('wetlands-environment-2', mister_1=0)
        time.sleep(random.randint(2, 10))

class RedBlink(Sketch):
    def draw(self):
        self.set_light('wetlands-environment-3',  1, 255,255,0,0)
        time.sleep(0.5)
        self.set_light('wetlands-environment-3', 1, 0,0,0,0)
        time.sleep(0.5)


class Three(Sketch):
    def draw(self):
        self.set_values('wetlands-environment-1',raindrops_1=255)
        self.set_values('wetlands-environment-1',raindrops_2=255)
        self.set_values('wetlands-environment-1',raindrops_3=255)
        time.sleep(0.2)
        self.set_values('wetlands-environment-1',raindrops_1=0)
        self.set_values('wetlands-environment-1',raindrops_2=0)
        self.set_values('wetlands-environment-1',raindrops_3=0)
        time.sleep(0.2)
        self.set_light('wetlands-environment-1', 1, 255,random.randint(0,255),random.randint(0,255),random.randint(0,255))
        self.set_light('wetlands-environment-1', 2, 255,random.randint(0,255),random.randint(0,255),random.randint(0,255))
        time.sleep(2)
        self.set_light('wetlands-environment-1', 1, 0,0,0,0)
        self.set_light('wetlands-environment-1', 2, 0,0,0,0)
        time.sleep(0.2) 

class TestAll(Sketch):
    def draw(self):
        names = [WL1, WL2, WL3]
        for n in names:
            self.set_values(n, mister_1=255)
            self.set_values(n, mister_2=255)
            self.set_light(n, 1, 255,random.randint(0,255),random.randint(0,255),random.randint(0,255))
            self.set_light(n, 2, 255,random.randint(0,255),random.randint(0,255),random.randint(0,255))
            self.set_light(n, 3, 255,random.randint(0,255),random.randint(0,255),random.randint(0,255))
            time.sleep(3)
            self.set_values(n, mister_1=0)
            self.set_values(n, mister_2=0)
            time.sleep(1)
            self.set_light(n, 1, 255,random.randint(0,255),random.randint(0,255),random.randint(0,255))
            self.set_light(n, 2, 255,random.randint(0,255),random.randint(0,255),random.randint(0,255))
            self.set_light(n, 3, 255,random.randint(0,255),random.randint(0,255),random.randint(0,255))
            self.set_values(n,raindrops_1=255)
            self.set_values(n,raindrops_2=255)
            self.set_values(n,raindrops_3=255)
            time.sleep(0.1)
            self.set_values(n,raindrops_1=0)
            self.set_values(n,raindrops_2=0)
            self.set_values(n,raindrops_3=0)
            time.sleep(0.2)
            self.set_values(n,raindrops_1=255)
            self.set_values(n,raindrops_2=255)
            self.set_values(n,raindrops_3=255)
            time.sleep(0.1)
            self.set_values(n,raindrops_1=0)
            self.set_values(n,raindrops_2=0)
            self.set_values(n,raindrops_3=0)
            time.sleep(0.2)
            self.set_values(n,raindrops_1=255)
            self.set_values(n,raindrops_2=255)
            self.set_values(n,raindrops_3=255)
            time.sleep(0.1)
            self.set_values(n,raindrops_1=0)
            self.set_values(n,raindrops_2=0)
            self.set_values(n,raindrops_3=0)
            time.sleep(0.2)
       # self.set_values('wetlands-environment-2',raindrops_1=255)
        #self.set_values('wetlands-environment-2',raindrops_2=255)
        #self.set_values('wetlands-environment-2',raindrops_3=255)
        #time.sleep(0.2)
        #self.set_values('wetlands-environment-2',raindrops_1=0)
        #self.set_values('wetlands-environment-2',raindrops_2=0)
        #self.set_values('wetlands-environment-2',raindrops_3=0)
        #time.sleep(0.2)
        #self.set_light('wetlands-environment-2', 1, 255,random.randint(0,255),random.randint(0,255),random.randint(0,255))
        #self.set_light('wetlands-environment-2', 2, 255,random.randint(0,255),random.randint(0,255),random.randint(0,255))
        #time.sleep(3)
        #self.set_light('wetlands-environment-2', 1, 0,0,0,0)
        #self.set_light('wetlands-environment-2', 2, 0,0,0,0)
        #time.sleep(1) 



'''END TEGA STUFF'''

def init(hostname):
    main = Main(hostname)
    main.daemon = True
    main.start()

    '''TEGA STUFF HERE'''
    #photos = PhotoTaker(main)
    #ripper = Dripper(main)
    #lights = LightsTest(main)
    #lights2 = LightsTest2(main)
    #mister = MisterExample(main)
    #redblink = redBlink(main)
    test = TestAll(main)
    '''END TEGA STUFF'''

    return main





