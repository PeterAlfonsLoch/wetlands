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



class SamOS(object):
    ''' Class that manages our wetlands (sets up and updates genetic algo'''

    def __init__(self, message_target):
        ''' initializes all the wetlands. '''

        self.message_target = message_target

        # self.message_target.add_to_queue("local/env_state/response", (hostname, env_state))



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

    def set_state(self, hostname, env_state):
        self.message_target.add_to_queue("local/env_state/response", (hostname, env_state))

    def set_items(self, hostname, **kwargs):
        self.message_target.add_to_queue("local/env_state/response", (hostname, kwargs))

    def take_photo(self, hostname):
        self.message_target.add_to_queue("local/image_capture/response", hostname)

    def set_light(self, hostname, light_number, dimmer=0, r=0, g=0, b=0):
        light_name = 'dj_light_{}_'.format(light_number)
        state = {}
        state[light_name+'_r'] = r
        state[light_name+'_g'] = g
        state[light_name+'_b'] = b
        state[light_name+'_d'] = dimmer
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
        self.take_photo('wetlands-environment-1')
        time.sleep(self.delay)

class Dripper(Sketch):
    def draw(self):
        print 'capture'
        self.take_photo('wetlands-environment-2')
        time.sleep(15)

'''END TEGA STUFF'''

def init(hostname):
    main = Main(hostname)
    main.daemon = True
    main.start()

    '''TEGA STUFF HERE'''
    photos = PhotoTaker(main)
    photos.start()

    '''END TEGA STUFF'''

    return main





