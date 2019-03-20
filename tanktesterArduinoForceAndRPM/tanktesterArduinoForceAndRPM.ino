/******************************************************************************
 * Thruster Load Test
 *
 * Reads analog data from the thruster test rig load cell (TE Connectivity FC22)
 * and converts and prints the data to a serial port
 ******************************************************************************/

#include "LPFilter.h"
#include <Servo.h>

// SERIAL COMMUNICATION
#define BAUD_RATE       19200
#define PRINT_RATE      10.0f  // Hz
#define LOOP_RATE       200.0f  // hz
#define CUTOFF_FREQ     5.0f   // Hz (low-pass filter cutoff)

// TEST RIG PARAMETERS
#define LOAD_CELL_PIN   A0
#define ESC_PIN         9

// global variables
unsigned long scheduledprinttime;   // ms
unsigned long scheduledlooptime;   // ms
unsigned long starttime;            // ms
float         cookedforce;
float         rawforce;
float         tarevalue;            // pounds  :|
LPFilter      lpfilter;
LPFilter      lpfilterRPM;
int           throttle;
int           rampthrottle;
volatile long period_value = 0; //period measuring setup
volatile long prev_time = 0; //start with timer at 0
volatile long new_time = 0;
int           RPM;
int           output;
Servo         esc;

void setup() {
  // Tare the load cell on startup
  float forceaverage = 0;
  for (int i = 0; i < 5; i++) {
    forceaverage += measureForce(LOAD_CELL_PIN);
    delay(0.1);
  }
  tarevalue = forceaverage/5.0f;

  // Initialize low-pass filter
  lpfilter = LPFilter(1.0/LOOP_RATE, 1.0/CUTOFF_FREQ);
  lpfilterRPM = LPFilter(1.0/LOOP_RATE, 1.0/CUTOFF_FREQ);

  // Initialize serial port
  Serial.begin(BAUD_RATE);

  // Set next record time to now
  starttime          = millis();
  scheduledprinttime = starttime;

  // Power the RPM sensor from D13
  pinMode(13,OUTPUT);
  digitalWrite(13,HIGH);

  // Set up PWM
  esc.attach(ESC_PIN);
  esc.writeMicroseconds(1000);

  // when pin D2 goes high, call the rising function
  attachInterrupt(0, rising, RISING);
}

void loop() {
  // listen for new RPM commands
  if (Serial.available()) {
    int input = Serial.parseInt();
    if ( input > 800 && input < 2200 ) {
      output = input;
    }
  }
  esc.writeMicroseconds(output);
  
  if (millis() > scheduledlooptime) {
    scheduledlooptime += 1000.0/LOOP_RATE;

    if ( period_value > 100000 ) {
      period_value = 0; // Clear high numbers on the first point
    }
      
    // Take a measurement
    float rawforce = (measureForce(LOAD_CELL_PIN) - tarevalue);
    float filtered_period_value = period_value; //lpfilterRPM.step(period_value);
   
    // Filter the measurement
    float cookedforce = lpfilter.step(rawforce);
 
    if (millis() > scheduledprinttime) {
      scheduledprinttime += 1000.0/PRINT_RATE;

      float filteredRPM = 60000000/(7*filtered_period_value);

      if ( filtered_period_value > 0 && filtered_period_value < 1500 ) {
        // This is unrealistic because RPM would be too high
      } else {
        // Write data to serial port
        Serial.print(cookedforce,2);
        Serial.print(",");
  //      Serial.print(filteredRPM,1);
  //      Serial.print(",");
        Serial.println(filtered_period_value,1);
      }
    }

    if ( micros() - new_time > 250000 ) {
      period_value = 0;
    }
  }
}


/* This function measures the force on the FC22 compression load cell. The load
 * cell is already amplified with an output range of 0.5 to 4.5 V and a
 * measurement range of 0-25 lb.
 *
 * The range of the sensor is 4.0 V and the offset is 0.5 V, so that the
 * relationship between voltage and force is:
 *
 * F = 25.0/4.0*(V-0.5) = 6.25*(V-0.5)
 *
 * The voltage can be calculated from:
 *
 * V = ADC/1023*Vcc = ADC/1023*Vcc
 *
 * So the resulting relationship is:
 *
 * F = 6.25*(ADC*Vcc/1023-0.5)
 *
 * In this measurement scenario, the sensor is preloaded with a tare weight that
 * allows both positive and negative loads to be measured. This function only
 * provides the measured force without accounting for the tare weight. That must
 * be recorded separately and subtracted from this measurement.
 */
float measureForce(int pin) {
  const static float Kf     = 12.5;
  const static float Kadc   = 5.0/1023.0;
  const static float offset = 0.5;

  return Kf * (Kadc * analogRead(pin) - offset);
}

void rising() {
  new_time = micros();
  period_value = new_time - prev_time;
  prev_time = new_time;
}
