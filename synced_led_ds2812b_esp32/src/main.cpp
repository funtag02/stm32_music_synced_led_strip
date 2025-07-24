#include <Arduino.h>
#include "main.h"

void setup() {
  Serial.begin(9600);
  Serial.println("Setting up the LED Strip System...");
  if (initLedStrip() == 0) {
    Serial.println("initialized led strip !");
  } else {
    Serial.println("ERROR !!");
  }
}

void loop() {
  Serial.println(updateColorsOnLedStrip() == 0 
                    ? "Led Strip colors are successfully updated !" 
                    : "ERROR !");
}