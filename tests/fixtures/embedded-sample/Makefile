# Utility helper makefile
PORT ?= /dev/ttyACM0
BAUD ?= 115200

all:
	@echo "Use platformio to build"

flash:
	openocd -f board.cfg -c "program build/firmware.elf verify reset exit"

monitor:
	minicom -D $(PORT) -b $(BAUD)

clean:
	rm -rf .pio build
