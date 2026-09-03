#include <stdint.h>
#include "sensor.h"

#define SYS_CLOCK_HZ 84000000

static void system_clock_config(void) {
}

static void bsp_init(void) {
    system_clock_config();
}

int main(void) {
    bsp_init();
    sensor_init();
    while (1) {
        sensor_process();
        SensorReading r = sensor_read();
        (void)r;
    }
    return 0;
}
