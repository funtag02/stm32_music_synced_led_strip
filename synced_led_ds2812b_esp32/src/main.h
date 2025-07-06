#ifndef MAIN_H
#define MAIN_H

#include <Adafruit_NeoPixel.h>

#define NUM_LEDS 240
#define PIN_LED_STRIP 13

Adafruit_NeoPixel strip = Adafruit_NeoPixel(NUM_LEDS, PIN_LED_STRIP, NEO_GRB + NEO_KHZ800);

void setUniLedColor(int r, int g, int b);

#endif