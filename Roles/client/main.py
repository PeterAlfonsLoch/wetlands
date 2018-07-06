import base64
import commands
import cv2
import importlib
import json
import math
#import numpy as np
#from operator import itemgetter
import os
import Queue
import random
import settings 
import serial
import sys
#import subprocess
import threading
import time
import traceback
import subprocess

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
## SPEECH
########################
class Speech(threading.Thread):
    def __init__(self):
        threading.Thread.__init__(self)
        self.queue = Queue.Queue()

    def number_to_audio_files(self, number):
        out = []
        number = str(number)
        for digit in number:
            out.append(BASE_PATH + '/audio/' + digit + '.wav')
        return out

    def add_to_queue(self, topic, msg):
        self.queue.put((topic, msg))

    def run(self):
        while True:
            topic, msg = self.queue.get(True)
            if topic == "local/speech/say":
                generation, iteration = msg
                generation_files = self.number_to_audio_files(generation)
                iteration_files = self.number_to_audio_files(iteration)

                print generation, iteration
                print generation_files
                print iteration_files

                all_audio = [BASE_PATH + 'audio/generation.wav']
                all_audio += generation_files
                all_audio = [BASE_PATH + 'audio/iteration.wav']
                all_audio += iteration_files

                for audio_file in all_audio:
                    subprocess.call(['omxplayer', audio_file])


########################
## DMX
########################

class DMX(threading.Thread):
    def __init__(self):
        threading.Thread.__init__(self)
        self.queue = Queue.Queue()
        self.ser = serial.Serial()
        self.ser.port = '/dev/ttyUSB0'
        if self.ser.isOpen():
            self.ser.close()
        print ('Opening Enttec USB DMX Pro on', self.ser.port, 'at', self.ser.baudrate, 'baud')
        self.ser.open()

        # if you add or modify DMX channels, adjust below!
        self.device_states = [0]*40
        self.name_to_address_map = {
            # "mister_1": 0,
            # "mister_2": 1,
            # "pump": 2,
            # "grow_light": 3,
            # "dj_light_2_d": 7,
            # "dj_light_2_r": 8,
            # "dj_light_2_g": 9,
            # "dj_light_2_b": 10,
            # "dj_light_1_d": 14,
            # "dj_light_1_r": 15,
            # "dj_light_1_g": 16,
            # "dj_light_1_b": 17,
            # "raindrops_1": 31,
            # "raindrops_2": 32,
            # "raindrops_3": 33,
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
            "dj_light_3_r": 27,
            "dj_light_3_g": 28,
            "dj_light_3_b": 29,
            "raindrops_1": 32,
            "raindrops_2": 33,
            "raindrops_3": 34,
        }
    def convert_to_DMX_addresses(self, data):
        values_for_dmx = {}
        for device_name,dmx_val in data.items():
            values_for_dmx[str(self.name_to_address_map[device_name])] = dmx_val
        return values_for_dmx

    def sendmsg(self, label, message=[]):
        # How many data points to send
        l = len(message)
        lm = l >> 8
        ll = l - (lm << 8)
        if l <= 600:
            if self.ser.isOpen():
                # Create the array to write to the serial port
                arr = [0x7E, label, ll, lm] + message + [0xE7]
                # Convert to byte array and write it
                self.ser.write(bytearray(arr))
        else:
            # Too long!
            sys.stderr.write('TX_ERROR: Malformed message! The message to be send is too long!\n')

    def add_to_queue(self, topic, msg):
        self.queue.put((topic, msg))

    def run(self):
        toggle = False
        while True:
            topic, msg = self.queue.get(True)
            if topic == "local/env_state/set":
                dmx_address_to_value_map = self.convert_to_DMX_addresses(msg)
                print dmx_address_to_value_map
                for address, value in dmx_address_to_value_map.items():
                    self.device_states[int(address)] = int(value)
                self.sendmsg(6, self.device_states)


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
        self.dmx = DMX()
        self.dmx.start()

        self.speech = Speech()
        self.speech.start()

        #self.network.thirtybirds.subscribe_to_topic("reboot")
        #self.network.thirtybirds.subscribe_to_topic("remote_update")
        #self.network.thirtybirds.subscribe_to_topic("remote_update_scripts")
        self.network.thirtybirds.subscribe_to_topic(self.hostname)
        self.network.thirtybirds.subscribe_to_topic("wetlands-environment-all/")

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

                if topic == "{}/image_capture/request".format(self.hostname):
                    self.images.delete_captures()
                    filename = "{}{}".format(self.hostname, ".png")
                    self.images.capture_image(filename)
                    image_as_string = self.images.get_image_as_base64(filename)
                    self.network.thirtybirds.send("controller/image_capture/response", (self.hostname,image_as_string))

                if topic == "{}/env_state/set".format(self.hostname):
                    self.dmx.add_to_queue("local/env_state/set", msg)

                if topic == "{}/speech/say".format(self.hostname):
                    self.speech.add_to_queue("local/speech/say", msg)

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
