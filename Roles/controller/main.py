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
import label_image
import genetics

BASE_PATH = os.path.dirname(os.path.realpath(__file__))
UPPER_PATH = os.path.split(os.path.dirname(os.path.realpath(__file__)))[0]
THIRTYBIRDS_PATH = "%s/thirtybirds_2_0" % (UPPER_PATH )

CLIENT_FITNESS_LABELS = {
    "wetlands-environment-1": "landscape painting",
    "wetlands-environment-2": "wetlands landscape",
    "wetlands-environment-3": "crowd",
}

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
        self.wetlands = {}

        for hostname in CLIENT_FITNESS_LABELS:
            storage = hostname + '.pkl'
            if os.path.exists(storage):
                with open(storage, 'r') as infile:
                    wetland = pickle.load(infile)
            else:
                wetland = genetics.Population(CLIENT_FITNESS_LABELS[hostname])

            self.wetlands[hostname] = wetland
            env_state = wetland.get_current_state()
            self.message_target.add_to_queue("local/env_state/response", (hostname, env_state))

    def update_wetland(self, hostname, filename):
        wetland = self.wetlands[hostname]

        if wetland.finished is True:
            return True

        if wetland.current_dna < len(wetland.population) - 1:
            wetland.calculate_current_fitness(filename)
            wetland.current_dna += 1
        else:
            wetland.natural_selection()
            wetland.generate()
            wetland.evaluate()
            wetland.current_dna = 0

        storage = hostname + '.pkl'
        with open(storage, 'w') as outfile:
            pickle.dump(wetland, outfile)

        next_env_state = wetland.get_current_state()
        print next_env_state
        self.message_target.add_to_queue("local/env_state/response", (hostname, next_env_state))


# Main handles network send/recv and can see all other classes directly
class Main(threading.Thread):
    def __init__(self, hostname):
        threading.Thread.__init__(self)
        self.network = Network(hostname, self.network_message_handler, self.network_status_handler)
        self.queue = Queue.Queue()
        self.network.thirtybirds.subscribe_to_topic("controller/")
        self.samos = SamOS(self)
        self.timer = Timer(self)
        self.timer.start()

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
                    self.network.thirtybirds.send("wetlands-environment-2/image_capture/request","")
                    self.network.thirtybirds.send("wetlands-environment-3/image_capture/request","")

                if topic == "controller/image_capture/response":
                    hostname, image_as_string = data
                    timestamp = int(time.time())
                    filename = "{}_{}.png".format(hostname, timestamp)
                    pathname = "Captures/{}".format(filename)
                    with open(pathname, "wb") as fh:
                        fh.write(image_as_string.decode("base64"))
                    self.samos.update_wetland(hostname, pathname)

                if topic == "local/env_state/response":
                    hostname, env_state = data
                    self.network.thirtybirds.send("{}/env_state/set".format(hostname), env_state)

                    # iteration = "iteration {}".format(random.randint(1, 295147905179352825856))
                    # self.network.thirtybirds.send("{}/speak".format(hostname), iteration)

            except Exception as e:
                exc_type, exc_value, exc_traceback = sys.exc_info()
                print e, repr(traceback.format_exception(exc_type, exc_value,exc_traceback))

#main = None # reference here for

def init(hostname):
    main = Main(hostname)
    main.daemon = True
    main.start()
    return main





