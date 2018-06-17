import serial
import time
import sys

# Create a new instance of the serial
ser = serial.Serial()

# Set the COM Port the DMX Pro is listening on
ser.port = '/dev/ttyUSB0'

# Baud rate doesn't matter on FTDI chips
# ser.baudrate = 57600

# Make sure the port isn't open, and if it is, close it
if ser.isOpen():
    ser.close()

# Let everyone know!
print ('Opening Enttec USB DMX Pro on', ser.port, 'at', ser.baudrate, 'baud')

# Open the serial connection
ser.open()

# Formulate the frame to send to the ENTTEC DMXUSB Pro
def sendmsg(label, message=[]):
    # How many data points to send
    l = len(message)
    lm = l >> 8
    ll = l - (lm << 8)
    if l <= 600:
        if ser.isOpen():
            # Create the array to write to the serial port
            arr = [0x7E, label, ll, lm] + message + [0xE7]
            # Convert to byte array and write it
            ser.write(bytearray(arr))
    else:
        # Too long!
        sys.stderr.write('TX_ERROR: Malformed message! The message to be send is too long!\n')

# Sending the DMX frame (entire thing)
def sendDMX(channels):
    # Sends an array of up to 512 channels
    data = [0] + channels
    # Fill up the channels up to the minimum of 25
    while len(data) < 25:
        # Make all the extra channels 0
        data += [0]
    # Send all the data with label 6
    sendmsg(6, data)

# The real useful code. This just tests the code above

patterns = [
    [0,0,0,0,0,0,0,0,0,0,0,0],
    [255,0,0,0,0,0,0,0,0,0,0,0],
    [255,255,0,0,0,0,0,0,0,0,0,0],
    [255,255,255,0,0,0,0,0,0,0,0,0],
    [255,255,255,255,0,0,0,0,0,0,0,0],
    [255,255,255,255,12,0,0,0,0,0,0,0],
    [255,255,255,255,12,40,0,0,0,0,0,0],
    [255,255,255,255,12,60,0,0,0,0,0,0],
    [255,255,255,255,12,80,0,0,0,0,0,0],
    [255,255,255,255,12,100,0,0,0,0,0,0],
    [255,255,255,255,12,120,0,0,0,0,0,0],
    [255,255,255,255,12,140,0,0,0,0,0,0],
    [255,255,255,255,12,160,0,0,0,0,0,0],
    [255,255,255,255,12,160,0,0,0,0,0,0],
    [255,255,255,255,12,180,0,0,0,0,0,0],
    [255,255,255,255,12,200,0,0,0,0,0,0],
    [255,255,255,255,12,220,0,0,0,0,0,0],
]


# Endless demo loop
while True:
    for pattern in patterns:
        print pattern
        sendDMX(pattern)
        time.sleep(2)
  