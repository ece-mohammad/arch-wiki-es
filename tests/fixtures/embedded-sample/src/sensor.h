#ifndef SENSOR_H
#define SENSOR_H

#include <stdint.h>

#define SENSOR_MAX_CHANNELS 8
#define SENSOR_TIMEOUT_MS 100

typedef enum {
    SENSOR_STATE_IDLE = 0,
    SENSOR_STATE_SAMPLING,
    SENSOR_STATE_READY,
    SENSOR_STATE_ERROR
} SensorState;

typedef struct {
    uint16_t value;
    uint32_t timestamp;
} SensorReading;

void sensor_init(void);
SensorReading sensor_read(void);
SensorState sensor_get_state(void);
void sensor_process(void);

#endif // SENSOR_H
