#!/usr/bin/python
import os 
os.system('clear') # clear screen
import serial #Libraries
import time
import datetime
import pigpio
import sys
pi = pigpio.pi() #initialize servo style ESC control
pi.set_servo_pulsewidth(18,1500) #initialize
time.sleep(5)
MAX_THROTTLE = 2000 #max must always be more than minimum. Swap motor wires to change direction!
MIN_THROTTLE = 1500
ser = serial.Serial(#scale rs232 to usb
	    port='/dev/ttyUSB0',\
	    baudrate=19200,\
	    parity=serial.PARITY_NONE,\
	    stopbits=serial.STOPBITS_ONE,\
	    bytesize=serial.EIGHTBITS,\
	    timeout=3)
ser2 = serial.Serial(#Arduino used as ADC
	    port='/dev/ttyACM0',\
	    baudrate=19200,\
	    parity=serial.PARITY_NONE,\
	    stopbits=serial.STOPBITS_ONE,\
	    bytesize=serial.EIGHTBITS,\
	    timeout=3)
print "Welcome to Tankinator test platform!! Automated in 4/2018 by TonyW"
print "This script automates tank testing by running the thruster for a set durationm while recording data, with a long duration pause between each throttle level for tank to settle"
print "Push ctrl+c to exit at any time. Launch script with /tankinator/./tanktester.py"
ser2.flushInput()# clear input before taking reading for rough sync to seperate Arduino :(
scale_level = (ser2.readline()) # Arduino configured to output at 10hz of this script
print "The current reading of the force sensor is %s"%scale_level
test_name = raw_input('Enter name of this test: ')
timenow='{date:%Y-%m-%d %H:%M:%S}.csv'.format( date=datetime.datetime.now() )
fname = test_name + ' ' + timenow #create filename from user name and time at start of test
d_steps = input('Duration of each throttle step (seconds) (Adam says 5sec, with 30 second pause between)')
num_steps = input('# of steps from 0 to full throttle (one direction - if wrong, swap 2 motor wires)')
settle_time = 40 #seconds between throttle steps. Change to input if frequently varied across tests
loop_period = 0.1 # 1/ this = hz
throttle_bump = (MAX_THROTTLE-MIN_THROTTLE)/num_steps # % increase of throttle level
calc_duration = (float(d_steps)*float(num_steps))+((num_steps-1)*settle_time) 
print 'test time will be '
print (calc_duration)
print 'seconds. %s measurements will be logged. Go make something.'%((float(d_steps)*float(num_steps)) * (1/loop_period))
time.sleep(1)
f=open("/home/pi/tankinator/%s"%fname, "a+") # write header for CSV once
f.write("Time, Force, Power, Voltage, Current, PWM")
f.write('\n')
f.close()
prevthrottle=MIN_THROTTLE
throttle = MIN_THROTTLE #center point throttle
runmotor=1 #flag used to control data logging & output
# note start time
start_time = time.time()   
while (throttle <=MAX_THROTTLE) and (prevthrottle != MAX_THROTTLE): # exit when throttle exceeds 100% microseconds
	if ((time.time() - start_time)>d_steps): # if the runtime is over
		pi.set_servo_pulsewidth(18,MIN_THROTTLE) # turn off output
		print 'Letting tank settle for %s seconds'%settle_time
		time.sleep(settle_time) # do nothing, let tank settle
		runmotor = 1 #raise flag to allow throttle change
		start_time = time.time() # begin next throttle step 
	if runmotor==1 and ((time.time()-start_time)<d_steps): #if change is ok and during next run period
		prevthrottle = throttle #used to limit ramp up
		while throttle < (prevthrottle + throttle_bump):
			throttle = throttle + (throttle_bump/10) #ramping to not make it shake
			pi.set_servo_pulsewidth(18,throttle) #set new throttle point
			time.sleep(0.06)
		time.sleep(1.5)# let things settle out before starting log	
		runmotor = 0 #keep it from increasing again within same period
	try:  #to talk to power supply
		ser.write('MEASURE:VOLTAGE:DC?') #from documentation. 
		ser.write(b'\rL1\r') #sends enter after request to get return
		VOLTAGE = float(ser.readline()) #cast to float
		ser.write('MEASURE:CURRENT:DC?')
		ser.write(b'\rL1\r')
		CURRENT = float(ser.readline())
		POWER = VOLTAGE * CURRENT #calculate the useful metric
	except:
		print "power supply comm error dude"
	try: #to read the external ADC. Need to update prompts to include lever arm, remove this from Arduino sketch
		input = float(ser2.readline()) # Arduino configured to output at 10hz of this script
		ser2.flushInput()# clear input before taking reading for rough sync to seperate Arduino :(
		FORCE = input #add scaling here to include lever arm input, remove from Arduino output
		print {"PWM":throttle,"CURRENT":CURRENT,"VOLTAGE":VOLTAGE,"POWER":POWER,"FORCE":FORCE,"TIME":datetime.datetime.now().strftime("%H:%M:%S.%f")} #attempt at json readable format
	except:
			print "sorry man, force sensor comm error"
	try: #to log data
		f=open("/home/pi/tankinator/%s"%fname, "a+") #open new file in append mode
		f.write(datetime.datetime.now().strftime("%H:%M:%S.%f")) # write data in csv format
		f.write(',')
		f.write("%s"%FORCE)
		f.write(',')
		f.write("%s"%POWER)
		f.write(',')
		f.write("%s"%VOLTAGE)
		f.write(',')
		f.write("%s"%CURRENT)
		f.write(',')
		f.write("%s"%throttle)
		f.write('\n')
		f.close()
		#print "log file line logged"
	except:
		print "data not saved pal"				
	time.sleep(loop_period) #unmanaged 10hz as initially tested. may run faster? Too many #s to analyze
pi.set_servo_pulsewidth(18,MIN_THROTTLE) #turn onff motor post test
os.execv(__file__, sys.argv) # relaunches this script for next test