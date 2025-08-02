#include <driver/i2s.h>
#include "audio_signal.hpp"
#include <Arduino.h> // pour sqrt et log10

// Configuration I2S
const i2s_config_t i2s_config = {
  .mode = i2s_mode_t(I2S_MODE_MASTER | I2S_MODE_RX),
  .sample_rate = 44100,
  .bits_per_sample = I2S_BITS_PER_SAMPLE_32BIT,
  .channel_format = I2S_CHANNEL_FMT_ALL_LEFT,
  .communication_format = I2S_COMM_FORMAT_STAND_I2S,
  .intr_alloc_flags = 0,
  .dma_buf_count = 8,
  .dma_buf_len = 64,
  .use_apll = false,
  .tx_desc_auto_clear = false,
  .fixed_mclk = 0
};

const i2s_pin_config_t pin_config = {
  .bck_io_num = I2S_SCK,
  .ws_io_num = I2S_WS,
  .data_out_num = I2S_PIN_NO_CHANGE,
  .data_in_num = I2S_SD
};

int initI2SMicrophone() {
  i2s_driver_install(I2S_NUM_0, &i2s_config, 0, NULL);
  i2s_set_pin(I2S_NUM_0, &pin_config);
  i2s_zero_dma_buffer(I2S_NUM_0);
  // Serial.println("INMP441 is ready !");
  Serial.printf("I2S PINS — SCK: %d, WS: %d, SD: %d\n", I2S_SCK, I2S_WS, I2S_SD);
  return 0;
}

double readVolume_dBFS() {
  const int buffer_len = 64;
  int32_t buffer[buffer_len];
  size_t bytes_read;

  i2s_read(I2S_NUM_0, (void*)buffer, sizeof(buffer), &bytes_read, portMAX_DELAY);

  if (bytes_read == 0) {
    Serial.println("I2S read returned 0 bytes!");
  }

  int samples_read = bytes_read / sizeof(int32_t);
  double sum = 0;

  for (int i = 0; i < samples_read; i++) {
    // Décale à droite de 8 bits pour récupérer les 24 bits utiles
    int32_t sample = buffer[i] >> 8;

    // Maintenant l'échelle est [-2^23, 2^23 - 1] = [-8388608, 8388607]
    float normalized = sample / 8388608.0f;
    sum += normalized * normalized;
  }

  double rms = sqrt(sum / samples_read);
  double dB = 20.0 * log10(rms + 1e-9); // +1e-9 pour éviter log(0)

  return dB;
}