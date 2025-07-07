#ifndef MAIN_H
#define MAIN_H

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

int tmpIterationColor = 0;

Adafruit_NeoPixel strip = Adafruit_NeoPixel(NUM_LEDS, PIN_LED_STRIP, NEO_GRB + NEO_KHZ800);

#endif