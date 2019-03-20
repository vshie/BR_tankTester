/******************************************************************************
 * Thruster Load Test
 *
 * Reads analog data from the thruster test rig load cell (TE Connectivity FC22)
 * and converts and prints the data to a serial port
 ******************************************************************************/

#include "LPFilter.h"




// SERIAL COMMUNICATION
#define BAUD_RATE       19200
#define PRINT_RATE      10.0f  // Hz
#define LOOP_RATE       200.0f  //hz
#define CUTOFF_FREQ     5.0f   // Hz (low-pass filter cutoff)

// TEST RIG PARAMETERS
#define LOAD_CELL_PIN   A0
//#define MECH_ADVANTAGE  (26.56f/29.938f)    // Lever arm ratio (T500X14) - vertical/horizontal
//#define MECH_ADVANTAGE  (26.50f/29.938f)    // Lever arm ratio (T500X13) - vertical/horizontal
//#define MECH_ADVANTAGE  (26.378f/29.938f)    // Lever arm ratio (T500) - vertical/horizontal
//#define MECH_ADVANTAGE  (25.625f/29.938f)    // Lever arm ratio (T200) - vertical/horizontal
//#define MECH_ADVANTAGE  (24.25f/29.938f)    // Lever arm ratio (M200) - vertical/horizontal
//#define MECH_ADVANTAGE  (18.875f/29.938f)    // Lever arm ratio (TWHOI) - vertical/horizontal

// global variables
unsigned long scheduledprinttime;   // ms
unsigned long scheduledlooptime;   // ms
unsigned long starttime;            // ms
float         cookedforce;
float         rawforce;
float         tarevalue;            // pounds  :|
LPFilter      lpfilter;
int           throttle;
int           rampthrottle;

void setup() {
  // Tare the load cell on startup
  float forceaverage = 0;
  for (int i = 0; i < 5; i++) {
    forceaverage += measureForce(LOAD_CELL_PIN);
    delay(1.0/PRINT_RATE);
  }
  tarevalue = forceaverage/5.0f;

  // Initialize low-pass filter
  lpfilter = LPFilter(1.0/LOOP_RATE, 1.0/CUTOFF_FREQ);

  // Initialize serial port
  Serial.begin(BAUD_RATE);

  // Set next record time to now
  starttime          = millis();
  scheduledprinttime = starttime;
}

void loop() {
 if (millis() > scheduledlooptime) {
    scheduledlooptime+= 1000.0/LOOP_RATE;
      // Take a measurement
   float rawforce = (measureForce(LOAD_CELL_PIN) - tarevalue);//MECH_ADVANTAGE;

    // Filter the measurement
    float cookedforce = lpfilter.step(rawforce);
 
  if (millis() > scheduledprinttime) {
    scheduledprinttime += 1000.0/PRINT_RATE;

  
    // Write data to serial port

     Serial.println(cookedforce,1);
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
