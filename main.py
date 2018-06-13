######################
### LOAD LIBS AND GLOBALS ###
######################

import importlib
import os
import math
import settings
import sys
import time

BASE_PATH = os.path.dirname(os.path.realpath(__file__))
UPPER_PATH = os.path.split(os.path.dirname(os.path.realpath(__file__)))[0]
#THIRTYBIRDS_PATH = "%s/thirtybirds_2_0" % (UPPER_PATH )

sys.path.append(BASE_PATH)
sys.path.append(UPPER_PATH)

from thirtybirds_2_0.Network.info import init as network_info_init


network_info = network_info_init()
args = sys.argv 

try:
    hostname = args[args.index("-hostname")+1] # pull hostname from command line argument, if there is one
except Exception as E:
    hostname = network_info.getHostName()

#print "hostname = {}".format(hostname)

####################
### PAUSE UNTIL ONLINE  ###
####################

PAUSE_UNTIL_ONLINE_MAX_SECONDS = 30

def pause_until_online(max_seconds):
    for x in range(max_seconds):
        if network_info.getOnlineStatus():
            print "connected to Internet"
            break
        else:
            print "waiting for connection to Internet..."
            time.sleep(1)

pause_until_online(PAUSE_UNTIL_ONLINE_MAX_SECONDS)

#########################
### LOAD DEVICE-SPECIFIC CODE ###
#########################

if hostname in settings.client_names:
    role = "client"

elif hostname in settings.server_names:
    role = "controller"

elif hostname in settings.dashboard_names:
    role = "dashboard"

host = importlib.import_module("Roles.%s.main" % (role))
client = host.init(hostname)
