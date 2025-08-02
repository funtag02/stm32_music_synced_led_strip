#include <Arduino.h>
#include "main.h"
#include "led_strip.hpp"
#include "audio_signal.hpp"

void setup() {
  Serial.begin(115200); // base : 9600
  delay(1000);
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
                    : "STRIP ERROR !");

  double dB = readVolume_dBFS();

  if (dB) {
    Serial.printf("Sound level measured : %.2f dBFS\n", dB);
  } else {
    Serial.println("MICROPHONE ERROR !!");
  }
}