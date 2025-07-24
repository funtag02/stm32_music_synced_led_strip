#include "led_strip.hpp"
#include <Adafruit_NeoPixel.h>

#define NUM_LEDS 240
#define PIN_LED_STRIP 13

#define BASE_BPM 174
#define UPDATE_PRECISION 8.0 // freezes appear above 8.0

// int inf_led; // first led of the snake
// int sup_led; // last led of the snake
int ledValues[NUM_LEDS][3]; // n leds x (r, g, b)
int tempo = BASE_BPM;
unsigned long lastUpdateTime = 0;

int tmpIterationColorPos = 0;

Adafruit_NeoPixel strip = Adafruit_NeoPixel(NUM_LEDS, PIN_LED_STRIP, NEO_GRB + NEO_KHZ800);

// only one strip for now
int initLedStrip() {
    Serial.println("setting up led stip...");
    strip.begin();
    strip.setBrightness(40); // = 40 / 255
    strip.show();

    // fill array with turned off leds
    for (int i = 0; i < NUM_LEDS; i++) {
        ledValues[i][0] = 0; // R
        ledValues[i][1] = 0; // G
        ledValues[i][2] = 0; // B
    }

    return 0;
}

int shiftLedColors(){
    Serial.println("updating array : shifting leds to the right by 1...");
    // shift all leds to the right (by 1)
    for (int i = NUM_LEDS; i >= 1; i--) {
        ledValues[i][0] = ledValues[i - 1][0];
        ledValues[i][1] = ledValues[i - 1][1];
        ledValues[i][2] = ledValues[i - 1][2];
    }

    return 0;
}

int tmpUpdateFirstLed(){
  Serial.println("updating array : the first led's color...");
  // TEMPORARY LOGIC : add new value to the first led
  if (tmpIterationColorPos == 3){
    tmpIterationColorPos = 0;
  }
  switch (tmpIterationColorPos){
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
  tmpIterationColorPos++;

  return 0;
}

int updateStripLeds() {
    Serial.println("Updating colors on led strip...");
    // update the strip, with new array
    for (int i = 0; i < NUM_LEDS; i++) {
      strip.setPixelColor(i, ledValues[i][0], ledValues[i][1], ledValues[i][2]);
    }

    return 0;
}

int updateColorsOnLedStrip() {
    Serial.println("updating colors on led strip...");
    float updateEachInSeconds = ( 60.0 / tempo ) / UPDATE_PRECISION; // 1/24s for 174 BPM (1/3s but 8 times more detailed)
    unsigned long updateEachInMillis = (unsigned long)(updateEachInSeconds * 1000);
    unsigned long currentTime = millis();
  
    if (currentTime - lastUpdateTime >= updateEachInMillis) {
      lastUpdateTime = currentTime;
    
      if (shiftLedColors() == 0){
        Serial.println("leds shifted to the right !");
      } else {
        Serial.println("ERROR !!");
        return 1;
      }

      if (tmpUpdateFirstLed() == 0){
        Serial.println("TEMPORARY CODE CHUNK - updated first led value");
      } else {
        Serial.println("ERROR !!");
        return 1;
      }

      Serial.println("Array has been successfully updated !");

      if (updateStripLeds() == 0){
        Serial.println("Led strip has been successfully updated !");
      } else {
        Serial.println("ERROR !!");
        return 1;
      }

      strip.show(); // display colors on strip
    }

    return 0;
}