#!/usr/bin/python2

import datetime
import os
import sys
import time

from argparse import ArgumentParser

import dropbox
from dropbox.files import WriteMode
from dropbox.exceptions import ApiError, AuthError

import pigpio
import serial

def readArduino(ser):
    line = ser.readline()
    return line.split(',')

def setPWM(ser,pwm):
    ser.write("%4.0f\n"%pwm)

# DEFAULT VALUES
# Dropbox token
TOKEN = ''

WELCOME_TEXT = """
Welcome to Tankinator test platform !
This script automates tank testing by running the thruster for a set duration while recording data,
with a long duration pause between each throttle level for tank to settle.
Push ctrl+c to exit at any time.
"""
parser = ArgumentParser(description=WELCOME_TEXT)
parser.add_argument(
        "--power-supply-serial",
        dest="power_supply_serial",
        required=False,
        type=str,
        default="/dev/ttyUSB0",
        help="Serial to communicate with power supply."
)
parser.add_argument(
        "--arduino-serial",
        dest="arduino_serial",
        required=False,
        type=str,
        default="/dev/ttyACM0",
        help="Serial to communicate with force/rpm sensor."
)

args = parser.parse_args()

# min and max throttle
STOP_THROTTLE = 1000
MIN_THROTTLE = 1000
MAX_THROTTLE = 2000
# in TWHOI = 25.25, T200 = 25.625, T500X14 = 26.56, T500x15 = 26.586
MECH_VERTICAL = 26.586
# in advtg = vert/horiz
MECH_HORIZ = 29.938
# in T200 = 14, T100 = 12
POLE_COUNT = 14
settle_time = 20 #seconds between throttle steps. Change to input if frequently varied across tests
rest_time = 1.5 # seconds to run before starting logging

# clear screen
os.system('clear')

print(WELCOME_TEXT)

# initialize raspberry gpio
#pi = pigpio.pi() # initialize servo style ESC control
#pi.set_servo_pulsewidth(18, MIN_THROTTLE) # set initial PWM

# Power supply output
# scale rs232 to usb
power_supply_serial = serial.Serial(
        port=args.power_supply_serial,\
        baudrate=19200,\
        parity=serial.PARITY_NONE,\
        stopbits=serial.STOPBITS_ONE,\
        bytesize=serial.EIGHTBITS,\
        timeout=3)

if power_supply_serial.is_open:
    print "Opened power supply serial port successfully."
else:
    print "Error opening power supply serial port."

# Force sensor
arduino_serial = serial.Serial(
        port=args.arduino_serial,\
        baudrate=19200,\
        parity=serial.PARITY_NONE,\
        stopbits=serial.STOPBITS_ONE,\
        bytesize=serial.EIGHTBITS,\
        timeout=3)

if arduino_serial.is_open:
    print "Opened Arduino serial port successfully."
else:
    print "Error opening Arduino serial port."

print ""

setPWM(arduino_serial,STOP_THROTTLE)

test_name = raw_input('Enter name of this test: ')
if type(test_name) != str:
    print("Error: Test name should be a string!")
    sys.exit(-1)

timenow = '{date:%Y.%m.%d %H.%M.%S}'.format(date=datetime.datetime.now())
fname = test_name + ' ' + timenow #create filename from user name and time at start of test
print('File will be created: %s' % fname)

duration = int(raw_input('Duration of each throttle step (seconds) (Adam says 3sec, with 20 second pause between): '))
if type(duration) != float and type(duration) != int:
    print("Error: Duration is not a number!")
    sys.exit(-1)

num_steps = int(raw_input('# of steps from 0 to full throttle (one direction - if wrong, swap 2 motor wires): '))
if type(num_steps) != int:
    print("Error: Number of steps is not a int!")
    sys.exit(-1)

loop_period = 0.1 # 1/ this = hz
throttle_bump = (MAX_THROTTLE-MIN_THROTTLE)/(num_steps-1) # % increase of throttle level
calc_duration = duration*num_steps + num_steps*settle_time
print("Test time will be: %d seconds" % calc_duration)
print("The total number of measurements will be %d." % (duration*num_steps/loop_period))
print("Go make something.")

f = open("/home/pi/tankinator/BR_tankTester/data/%s.csv" % fname, "a+") # write header for CSV once
f.write("Time, PWM, RPM, Current, Voltage, Power, Force, Efficiency")
f.write('\n')
f.close()
f = open("/home/pi/tankinator/BR_tankTester/data/%s.csv" % (fname+"-average"), "a+") # write header for CSV once
f.write("Time, PWM, RPM, Current, Voltage, Power, Force, Efficiency")
f.write('\n')
f.close()
LOCALFILE = '%s' % fname #file to backup
BACKUPPATH = '/%s' % fname
first_loop = True;

for throttle in range(MIN_THROTTLE,MAX_THROTTLE+1,throttle_bump): # exit when throttle exceeds 100% microseconds
    setPWM(arduino_serial,STOP_THROTTLE)
    
    if first_loop:
        first_loop = False
    else:
        print('Letting tank settle for %d seconds' % settle_time)    
        time.sleep(settle_time)
    
    setPWM(arduino_serial,throttle)

    time.sleep(rest_time)# let things settle out before starting log

    start_time = time.time()

    rpmSum = 0
    currentSum = 0
    voltageSum = 0
    powerSum = 0
    forceSum = 0
    efficiencySum = 0
    count = 0

    while time.time() - start_time < duration:
        rpm = 0
        current = 0
        voltage = 0
        power = 0
        force = 0
        efficiency = 0

        power_supply_serial.write('MEASURE:voltage:DC?') #from documentation.
        power_supply_serial.write(b'\rL1\r') #sends enter after request to get return
        voltage = float(power_supply_serial.readline()) #cast to float
        power_supply_serial.write('MEASURE:current:DC?')
        power_supply_serial.write(b'\rL1\r')
        current = float(power_supply_serial.readline())
        power = voltage * current #calculate the useful metric

        arduino_serial.flushInput()# clear input before taking reading for rough sync to seperate Arduino :(
        data = readArduino(arduino_serial)
        if len(data) is 2:
            force = data[0]
            force = float(force)/(MECH_VERTICAL/MECH_HORIZ) # Lever arm mechanical advantage correction
            if power > 0:
                efficiency = 453.59*force/power #Efficiency calculation in grams/watt
            period = float(data[1]) # Arduino configured to output at 10hz of this script
            if period > 0:
                rpm = 60000000/(period*(POLE_COUNT/2))#Get rpm from filtered period value, incorporate pole count

        print "%4.0f us\t\t" % throttle,
        print "%4.1f rpm\t" % rpm,
        print "%3.2f A\t\t" % current,
        print "%3.2f V\t\t" % voltage,
        print "%5.1f W\t\t" % power,
        print "%3.2f lb\t\t" % force,
        print "%3.2f g/W" % efficiency

        rpmSum += rpm
        currentSum += current
        voltageSum += voltage
        powerSum += power
        forceSum += force
        efficiencySum += efficiency
        count += 1

        #todo: add average output line

        try: #to log data
            f = open("/home/pi/tankinator/BR_tankTester/data/%s.csv" % fname, "a+") #open new file in append mode
            f.write(datetime.datetime.now().strftime("%H:%M:%S.%f")) # write data in csv format
            f.write(',')
            f.write("%4.0f"%throttle)
            f.write(',')
            f.write("%4.2f"%rpm)
            f.write(',')
            f.write("%3.2f"%current)
            f.write(',')
            f.write("%3.2f"%voltage)
            f.write(',')
            f.write("%5.2f"%power)
            f.write(',')
            f.write("%3.2f"%force)
            f.write(',')
            f.write("%3.2f"%efficiency)
            f.write('\n')
            f.close()
        except:
            print("data not saved pal")

    rpmAvg = rpmSum/count
    currentAvg = currentSum/count
    voltageAvg = voltageSum/count
    powerAvg = powerSum/count
    forceAvg = forceSum/count
    efficiencyAvg = efficiencySum/count

    print "%4.0f us\t\t" % throttle,
    print "%4.1f rpm\t" % rpmAvg,
    print "%3.2f A\t\t" % currentAvg,
    print "%3.2f V\t\t" % voltageAvg,
    print "%5.1f W\t\t" % powerAvg,
    print "%3.2f lb\t\t" % forceAvg,
    print "%3.2f g/W\t" % efficiencyAvg,
    print "(Average)"

    try: #to log data
        f = open("/home/pi/tankinator/BR_tankTester/data/%s.csv" % (fname+"-average"), "a+") #open new file in append mode
        f.write(datetime.datetime.now().strftime("%H:%M:%S.%f")) # write data in csv format
        f.write(',')
        f.write("%4.0f"%throttle)
        f.write(',')
        f.write("%4.2f"%rpmAvg)
        f.write(',')
        f.write("%3.2f"%currentAvg)
        f.write(',')
        f.write("%3.2f"%voltageAvg)
        f.write(',')
        f.write("%5.2f"%powerAvg)
        f.write(',')
        f.write("%3.2f"%forceAvg)
        f.write(',')
        f.write("%3.2f"%efficiencyAvg)
        f.write('\n')
        f.close()
    except:
        print("data not saved pal")

setPWM(arduino_serial,STOP_THROTTLE)
time.sleep(2)
print("test complete dude")

# Add OAuth2 access token here.
# You can generate one for yourself in the App Console.
# See <https://blogs.dropbox.com/developers/2014/05/generate-an-access-token-for-your-own-account/>
def backup():# Uploads contents of logfile to Dropbox
    with open(LOCALFILE, 'rb') as f:
        # We use WriteMode=overwrite to make sure that the settings in the file
        # are changed on upload
        print("Uploading " + LOCALFILE + " to Dropbox as " + BACKUPPATH + "...")
        try:
            dbx.files_upload(f.read(), BACKUPPATH, mode=WriteMode('overwrite'))
        except ApiError as err:
            # This checks for the specific error where a user doesn't have
            # enough Dropbox space quota to upload this file
            if (err.error.is_path() and
                    err.error.get_path().reason.is_insufficient_space()):
                sys.exit("ERROR: Cannot back up; insufficient space.")
            elif err.user_message_text:
                print(err.user_message_text)
                sys.exit()
            else:
                print(err)
                sys.exit()

if __name__ == '__main__':
    # Check for an access token
    if (len(TOKEN) == 0):
        sys.exit("ERROR: Looks like you didn't add your access token. "
            "Open up backup-and-restore-example.py in a text editor and "
            "paste in your token in line 14.")# Create an instance of a Dropbox class, which can make requests to the API.
    print("Creating a Dropbox object...")
    dbx = dropbox.Dropbox(TOKEN)
    try:# Check that the access token is valid
        dbx.users_get_current_account()
    except AuthError as err:
        sys.exit("ERROR: Invalid access token; try re-generating an "
            "access token from the app console on the web.")
    backup()    # Create a backup of the current log file
    print("Data saved to Adam's dropbox by TANKINATOR!!!!!!")
