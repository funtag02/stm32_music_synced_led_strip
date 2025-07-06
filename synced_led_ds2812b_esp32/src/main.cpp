#include <Arduino.h>
#include "main.h"

void setup() {
  strip.begin();
  strip.show();
  strip.setBrightness(40); // = 40 / 255
  strip.show();

  Serial.begin(9600);
}

int inf_led; // first led of the snake
int sup_led; // last led of the snake

void loop() {
  Serial.println("printing colors on led strip...");
  // strip.setPixelColor(0, 40, 40, 130);
  // strip.show();

  int ledValues[NUM_LEDS][3]; // n leds x (r, g, b) 

  // offset the snake by 1 at each iteration
  if (inf_led > (NUM_LEDS - 4) ) {
    inf_led = 0;
    sup_led = 4;
  } else {
    inf_led++;
    sup_led = inf_led + 4;
  }

  // update leds array (snake)
  for (int i = inf_led; i < sup_led; i++){
    ledValues[i][0] = 255;
    ledValues[i][1] = 0;
    ledValues[i][2] = 0;
  }

  // update all other leds (everything but the snake)
  for (int i = 0; i < NUM_LEDS; i++){
    if (i < inf_led || i > sup_led){
      ledValues[i][0] = 5;
      ledValues[i][1] = 5;
      ledValues[i][2] = 5;
    }
  }

  /*
  for (int i = 0; i < NUM_LEDS; i++) {
    ledValues[i][0] = random(0, 256); // R
    ledValues[i][1] = random(0, 256); // G
    ledValues[i][2] = random(0, 256); // B
  }
  */

  // update the strip, with new array, then display colors
  for (int i = 0; i < NUM_LEDS; i++) {
    strip.setPixelColor(i, ledValues[i][0], ledValues[i][1], ledValues[i][2]);
  }
  strip.show();
}

void setUniLedColor(int r, int g, int b) {
  for (int i = 0; i < NUM_LEDS; i++) {
      strip.setPixelColor(i, r, g, b);
  }
  strip.show();
}
