#include "LPFilter.h"




// SERIAL COMMUNICATION
#define BAUD_RATE       19200
#define PRINT_RATE      10.0f  // Hz
#define LOOP_RATE       200.0f  //hz
#define CUTOFF_FREQ     5.0f   // Hz (low-pass filter cutoff)

// global variables
unsigned long scheduledprinttime;   // ms
unsigned long scheduledlooptime;   // ms
unsigned long starttime;            // ms
LPFilter      lpfilter;
volatile long period_value = 0; //period measuring setup
volatile long prev_time = 0; //start with timer at 0
volatile long new_time = 0;
int RPM;

void setup() {
 
 // Initialize low-pass filter
 lpfilter = LPFilter(1.0/LOOP_RATE, 1.0/CUTOFF_FREQ);

 // Initialize serial port
 Serial.begin(BAUD_RATE);

 // Set next record time to now
 starttime          = millis();
 scheduledprinttime = starttime;

 // when pin D2 goes high, call the rising function
 attachInterrupt(0, rising, RISING);
}

void loop() {
if (millis() > scheduledlooptime) {
   scheduledlooptime+= 1000.0/LOOP_RATE;

   // Filter the measurement
   float filtered_period_value = lpfilter.step(period_value);

 if (millis() > scheduledprinttime) {
   scheduledprinttime += 1000.0/PRINT_RATE;

 
   // Write data to serial port

   //float filteredRPM = 60000000/(7*filtered_period_value);
   
    Serial.println(filtered_period_value,1);
 }
}
}

void rising() {
new_time = micros();
period_value = new_time - prev_time;
prev_time = new_time;
}
