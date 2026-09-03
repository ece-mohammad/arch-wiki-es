#include <stdint.h>
#include "sensor.h"

#define SENSOR_CALIBRATION_OFFSET 12

static SensorReading current_reading;
static SensorState current_state = SENSOR_STATE_IDLE;

static void sensor_hw_reset(void) {
}

void sensor_init(void) {
    sensor_hw_reset();
    current_state = SENSOR_STATE_IDLE;
}

SensorReading sensor_read(void) {
    return current_reading;
}

SensorState sensor_get_state(void) {
    return current_state;
}

void sensor_process(void) {
    switch (current_state) {
        case SENSOR_STATE_IDLE:
            current_state = SENSOR_STATE_SAMPLING;
            break;
        case SENSOR_STATE_SAMPLING:
            current_reading.value = 42 + SENSOR_CALIBRATION_OFFSET;
            current_reading.timestamp = 1000;
            current_state = SENSOR_STATE_READY;
            break;
        case SENSOR_STATE_READY:
            current_state = SENSOR_STATE_IDLE;
            break;
        case SENSOR_STATE_ERROR:
        default:
            sensor_init();
            break;
    }
}
