import base64
import commands
import cv2
import importlib
import json
import math
import numpy as np
from operator import itemgetter
import os
import Queue
import random
import settings 
import sys
import subprocess
import threading
import time
import traceback

from thirtybirds_2_0.Network.manager import init as thirtybirds_network
from thirtybirds_2_0.Adaptors.Cameras.c920 import init as camera_init
from thirtybirds_2_0.Updates.manager import init as updates_init

BASE_PATH = os.path.dirname(os.path.realpath(__file__))
UPPER_PATH = os.path.split(os.path.dirname(os.path.realpath(__file__)))[0]
DEVICES_PATH = "%s/Hosts/" % (BASE_PATH )
THIRTYBIRDS_PATH = "%s/thirtybirds_2_0" % (UPPER_PATH )

sys.path.append(BASE_PATH)
sys.path.append(UPPER_PATH)

########################
## IMAGES
########################

class Images(object):
    def __init__(self, capture_path):
        self.capture_path = capture_path
        self.camera = camera_init(self.capture_path)
    def capture_image(self, filename):
        self.camera.take_capture(filename)
    def get_capture_filenames(self):
        return [ filename for filename in os.listdir(self.capture_path) if filename.endswith(".png") ]
    def delete_captures(self):
        previous_filenames = self.get_capture_filenames()
        for previous_filename in previous_filenames:
            os.remove("{}{}".format(self.capture_path,  previous_filename))
    def get_capture_filepaths(self):
        filenames = self.get_capture_filenames()
        return list(map((lambda filename:  os.path.join(self.capture_path, filename)), filenames))
    def get_image_as_base64(self, filename):
        pathname = "{}{}".format(self.capture_path, filename)
        with open(pathname, "rb") as image_file:
            return base64.b64encode(image_file.read())

########################
## NETWORK
########################

class Network(object):
    def __init__(self, hostname, network_message_handler, network_status_handler):
        self.hostname = hostname
        self.thirtybirds = thirtybirds_network(
            hostname=hostname,
            role="client",
            discovery_multicastGroup=settings.discovery_multicastGroup,
            discovery_multicastPort=settings.discovery_multicastPort,
            discovery_responsePort=settings.discovery_responsePort,
            pubsub_pubPort=settings.pubsub_pubPort,
            message_callback=network_message_handler,
            status_callback=network_status_handler
        )

########################
## MAIN
########################

class Main(threading.Thread):
    def __init__(self, hostname):
        threading.Thread.__init__(self)
        self.hostname = hostname
        self.capture_path = "/home/pi/wetlands/captures/"
        self.queue = Queue.Queue()
        self.network = Network(hostname, self.network_message_handler, self.network_status_handler)
        #self.utils = Utils(hostname)
        self.images = Images(self.capture_path)

        self.network.thirtybirds.subscribe_to_topic("reboot")
        self.network.thirtybirds.subscribe_to_topic("remote_update")
        self.network.thirtybirds.subscribe_to_topic("remote_update_scripts")
        self.network.thirtybirds.subscribe_to_topic("capture_image")
        self.network.thirtybirds.subscribe_to_topic("client_monitor_request")
        self.network.thirtybirds.subscribe_to_topic("capture_and_upload")
        self.network.thirtybirds.subscribe_to_topic("perform_object_detection")
        self.network.thirtybirds.subscribe_to_topic("process_images_and_report")

    def network_message_handler(self, topic_msg):
        # this method runs in the thread of the caller, not the tread of Main

        topic, msg =  topic_msg # separating just to eval msg.  best to do it early.  it should be done in TB.
        if topic not in  ["client_monitor_request"]:
            print "Main.network_message_handler", topic_msg
        if len(msg) > 0: 
            msg = eval(msg)
        self.add_to_queue(topic, msg)

    def network_status_handler(self, topic_msg):
        # this method runs in the thread of the caller, not the tread of Main
        print "Main.network_status_handler", topic_msg

    def add_to_queue(self, topic, msg):
        self.queue.put((topic, msg))

    def run(self):
        while True:
            try:
                topic, msg = self.queue.get(True)

                if topic == "wetlands-environment-1/image_capture/request":
                    self.images.delete_captures()
                    filename = "{}{}".format(self.hostname, ".png")
                    self.images.capture_image(filename)
                    image_as_string = self.images.get_image_as_base64(filename)
                    print image_as_string

            except Exception as e:
                exc_type, exc_value, exc_traceback = sys.exc_info()
                print e, repr(traceback.format_exception(exc_type, exc_value,exc_traceback))

########################
## INIT
########################

def init(HOSTNAME):
    main = Main(HOSTNAME)
    main.daemon = True
    main.start()
    return main
