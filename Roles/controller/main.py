import base64
import json
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

class Timer(threading.Thread):
    def __init__(self, message_target):
        threading.Thread.__init__(self)
        self.delay_between_photos = 5.0 # seconds
        self.message_target = message_target
    def run(self):
        while True:
            self.message_target.add_to_queue("local/timer/response","")
            time.sleep(self.delay_between_photos)


class SamOS(object):
    def __init__(self, message_target):
        self.message_target = message_target
    def generate_env_state_from_capture(self, filename):
        self.read_image_file_as_numpy_array()
        self.pre_process_image_data()
        self.classifly_image()
        env_state = self.generate_env_state()
        print env_state
        self.message_target.add_to_queue("local/env_state/response",env_state)

    def read_image_file_as_numpy_array(self):
        return

    def pre_process_image_data(self):
        return

    def classifly_image(self):
        return

    def generate_env_state(self):
        return {
            "mister_1":random.randint(0,1),
            "mister_2":random.randint(0,1),
            "grow_light":random.randint(0,1),
            "raindrops_1":random.randint(0,255),
            "raindrops_2":random.randint(0,255),
            "pump":random.randint(0,1),
            "dj_light_1_r":random.randint(0,255),
            "dj_light_1_g":random.randint(0,255),
            "dj_light_1_b":random.randint(0,255),
            "dj_light_2_r":random.randint(0,255),
            "dj_light_2_g":random.randint(0,255),
            "dj_light_2_b":random.randint(0,255),
        }


# Main handles network send/recv and can see all other classes directly
class Main(threading.Thread):
    def __init__(self, hostname):
        threading.Thread.__init__(self)
        self.network = Network(hostname, self.network_message_handler, self.network_status_handler)
        self.queue = Queue.Queue()
        self.network.thirtybirds.subscribe_to_topic("controller/")
        self.timer = Timer(self)
        self.timer.start()
        self.samos = SamOS(self)

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

                if topic == "local/timer/response":
                    self.network.thirtybirds.send("wetlands-environment-1/image_capture/request","")

                if topic == "controller/image_capture/response":
                    hostname, image_as_string = data
                    timestamp = datetime.datetime.now().isoformat()
                    filename = "{}_{}.png".format(hostname, timestamp)
                    pathname = "Captures/{}".format(filename)
                    with open(pathname, "wb") as fh:
                        fh.write(image_as_string.decode('base64'))
                    self.samos.generate_env_state_from_capture(filename)

                if topic == "local/env_state/response":
                    self.network.thirtybirds.send("wetlands-environment-1/env_state/set",data)

            except Exception as e:
                exc_type, exc_value, exc_traceback = sys.exc_info()
                print e, repr(traceback.format_exception(exc_type, exc_value,exc_traceback))

#main = None # reference here for

def init(hostname):
    main = Main(hostname)
    main.daemon = True
    main.start()
    return main





