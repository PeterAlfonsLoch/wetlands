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
    "wetlands-environment-3": "wetlands landscape",
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


class PhotoTimer(threading.Thread):
    def __init__(self, message_target, hostname, delay_between_photos=20, initial_delay=0):
        threading.Thread.__init__(self)
        self.delay_between_photos = delay_between_photos # seconds
        self.initial_delay = initial_delay # seconds
        self.hostname = hostname
        self.message_target = message_target
    def run(self):
        time.sleep(self.initial_delay)
        while True:
            self.message_target.add_to_queue("local/timer/response", self.hostname)
            time.sleep(self.delay_between_photos)


class SamOS(object):
    ''' Class that manages our wetlands (sets up and updates genetic algo'''

    def __init__(self, message_target):
        ''' initializes all the wetlands. '''

        self.message_target = message_target
        self.wetlands = {}

        print 'initializing SAMOS'

        for hostname in CLIENT_FITNESS_LABELS:
            storage = hostname + '.pkl'
            print 'loading wetlands', hostname, 'from', storage
            if os.path.exists(storage):
                with open(storage, 'r') as infile:
                    wetland = pickle.load(infile)
            else:
                # creates a new wetlands if we are starting from scratch
                # sets the mutation_rate and pop_max
                wetland = genetics.Population(CLIENT_FITNESS_LABELS[hostname], mutation_rate=0.02, pop_max=50)
                with open(storage, 'w') as outfile:
                    pickle.dump(wetland, outfile)

            self.wetlands[hostname] = wetland
            env_state = wetland.get_current_state()
            self.message_target.add_to_queue("local/env_state/response", (hostname, env_state))
            self.message_target.add_to_queue("local/speech/response", (hostname, wetland.generations + 1, wetland.current_dna + 1))

    def update_wetland(self, hostname, filename):
        ''' Updates the a wetland with a new image '''
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
        self.message_target.add_to_queue("local/speech/response", (hostname, wetland.generations + 1, wetland.current_dna + 1))


# Main handles network send/recv and can see all other classes directly
class Main(threading.Thread):
    def __init__(self, hostname):
        threading.Thread.__init__(self)
        self.network = Network(hostname, self.network_message_handler, self.network_status_handler)
        self.queue = Queue.Queue()
        self.network.thirtybirds.subscribe_to_topic("controller/")
        self.samos = SamOS(self)

        self.timer1 = PhotoTimer(self, "wetlands-environment-1", initial_delay=1, delay_between_photos=10)
        self.timer2 = PhotoTimer(self, "wetlands-environment-2", initial_delay=3, delay_between_photos=11)
        self.timer3 = PhotoTimer(self, "wetlands-environment-3", initial_delay=7, delay_between_photos=12)
        self.timer1.start()
        self.timer2.start()
        self.timer3.start()

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
                if topic == "local/timer/response":
                    # tell the PIs to capture an image
                    self.network.thirtybirds.send("{}/image_capture/request".format(data),"")

                # listening for the PIs to recieve an image
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
                    print 'sending to', hostname
                    print env_state
                    self.network.thirtybirds.send("{}/env_state/set".format(hostname), env_state)

                    # iteration = "iteration {}".format(random.randint(1, 295147905179352825856))
                if topic == "local/speech/response":
                    hostname, generation, iteration = data
                    self.network.thirtybirds.send("{}/speech/say".format(hostname), (generation, iteration))

            except Exception as e:
                exc_type, exc_value, exc_traceback = sys.exc_info()
                print e, repr(traceback.format_exception(exc_type, exc_value,exc_traceback))

#main = None # reference here for

def init(hostname):
    main = Main(hostname)
    main.daemon = True
    main.start()
    return main





