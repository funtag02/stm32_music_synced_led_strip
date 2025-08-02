#ifndef AUDIO_SIGNAL_HPP
#define AUDIO_SIGNAL_HPP

#define I2S_WS 18      // Word Select (LRCL)
#define I2S_SCK 19     // Serial Clock (SCK)
#define I2S_SD 5      // Serial Data (SD)

int initI2SMicrophone();
double readVolume_dBFS();

#endif