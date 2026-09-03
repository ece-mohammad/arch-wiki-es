#!/bin/bash
# Flash utility script
openocd -f interface/stlink.cfg -f target/stm32f4x.cfg -c "program build/firmware.bin 0x08000000 verify reset exit"
