#include <Arduino.h>
#include "main.h"

void setup() {
  strip.begin();
  strip.setBrightness(40); // = 40 / 255
  strip.show();

  Serial.begin(9600);
  Serial.println("Setting up the LED Strip System...");

  // fill array with turned off leds
  for (int i = 0; i < NUM_LEDS; i++) {
    ledValues[i][0] = 0; // R
    ledValues[i][1] = 0; // G
    ledValues[i][2] = 0; // B
  }
}

void loop() {
  float updateEachInSeconds = ( 60.0 / tempo ) / UPDATE_PRECISION; // 1/12s for 174 BPM (1/3s but 8 times more detailed)
  unsigned long updateEachInMillis = (unsigned long)(updateEachInSeconds * 1000);
  unsigned long currentTime = millis();

  if (currentTime - lastUpdateTime >= updateEachInMillis) {
    lastUpdateTime = currentTime;

    Serial.println("printing colors on led strip...");

    // shift all leds to the right (by 1)
    for(int i = NUM_LEDS; i >= 1; i--) {
      ledValues[i][0] = ledValues[i - 1][0];
      ledValues[i][1] = ledValues[i - 1][1];
      ledValues[i][2] = ledValues[i - 1][2];
    }

    // TEMPORARY LOGIC : add new value to the first led
    if (tmpIterationColor == 3){
      tmpIterationColor = 0;
    }
    switch (tmpIterationColor){
      case 0:
        ledValues[0][0] = 255;
        ledValues[0][1] = 0;
        ledValues[0][2] = 0;
        break;

      case 1:
        ledValues[0][0] = 0;
        ledValues[0][1] = 255;
        ledValues[0][2] = 0;
        break;
      
      case 2:
        ledValues[0][0] = 0;
        ledValues[0][1] = 0;
        ledValues[0][2] = 255;
        break;
    }
    tmpIterationColor++;

    // update the strip, with new array
    for (int i = 0; i < NUM_LEDS; i++) {
      strip.setPixelColor(i, ledValues[i][0], ledValues[i][1], ledValues[i][2]);
    }
    strip.show(); // display colors on strip
  }
}