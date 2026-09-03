#!/usr/bin/env python3
"""Embedded firmware architecture scanner and dashboard generator."""
import datetime
import html
import json
import os
import re
import sys
from pathlib import Path

SKIP = {".git", "node_modules", "build", "dist", "target", "out", "__pycache__", ".venv", "venv", ".pio", ".vscode"}
SRC_EXTENSIONS = {".c", ".h", ".cc", ".cpp", ".cxx", ".hpp", ".rs", ".S", ".s", ".ino"}
CONFIG_EXTENSIONS = {".ld", ".dts", ".dtsi", ".overlay", ".ioc", ".map", ".cfg"}
SCRIPT_EXTENSIONS = {".sh", ".bash", ".bat", ".cmd", ".ps1", ".py"}
CONFIG_NAMES = {
    "platformio.ini", "CMakeLists.txt", "Makefile", "Kconfig", "prj.conf",
    "sdkconfig", "sdkconfig.defaults", "Cargo.toml", "west.yml",
    ".cproject", ".project", "boards.txt", "Justfile", "Taskfile.yml",
    "Dockerfile", "openocd.cfg"
}
STANDARD_TYPES = {
    "void", "bool", "char", "short", "int", "long", "float", "double",
    "size_t", "ptrdiff_t", "intptr_t", "uintptr_t", "int8_t", "uint8_t",
    "int16_t", "uint16_t", "int32_t", "uint32_t", "int64_t", "uint64_t",
    "usize", "isize", "String", "str", "Option", "Result", "Vec", "Box",
    "Rc", "Arc", "TaskHandle_t", "QueueHandle_t", "SemaphoreHandle_t",
    "BaseType_t", "TickType_t", "HAL_StatusTypeDef", "GPIO_TypeDef",
    "UART_HandleTypeDef", "SPI_HandleTypeDef", "k_tid_t", "esp_err_t"
}

def text(path):
    try:
        return path.read_text(encoding="utf-8", errors="replace")
    except OSError:
        return ""

def rel(path, root):
    return str(path.relative_to(root)).replace(os.sep, "/")

def files(root):
    for current, dirs, names in os.walk(root):
        dirs[:] = [d for d in dirs if d not in SKIP and not d.startswith(".")]
        for name in names:
            path = Path(current) / name
            name_lower = name.lower()
            if (path.suffix in SRC_EXTENSIONS or
                path.suffix in CONFIG_EXTENSIONS or
                path.suffix in SCRIPT_EXTENSIONS or
                name in CONFIG_NAMES or
                name_lower.startswith("readme") or
                name_lower.startswith("makefile") or
                path.suffix == ".uvprojx"):
                yield path

def safe_id(value):
    val = re.sub(r"[^A-Za-z0-9_]", "_", str(value))
    return val if val and val[0].isalpha() else "sym_" + val

def unique(items):
    result, seen = [], set()
    for item in items:
        key = json.dumps(item, sort_keys=True)
        if key not in seen:
            result.append(item)
            seen.add(key)
    return result

def by_id(items):
    return list({item["id"]: item for item in items}.values())

def source_file(path, root, role="source", contains=None, line=None):
    result = {"path": rel(path, root), "role": role}
    if contains:
        result["contains"] = sorted(set(contains))
    if line:
        result["line"] = line
    return result

# --- 1. Project Type Detection ---
def detect_project_type(records, root):
    names = {path.name for path, _ in records}
    joined = "\n".join(content for _, content in records)
    markers = []
    
    is_cube_ide = ".cproject" in names or (".project" in names and any(p.name.startswith("STM32") and p.suffix == ".ld" for p, _ in records))
    if is_cube_ide: markers.append("STM32CubeIDE")
    
    is_cube_mx = any(p.suffix == ".ioc" for p, _ in records)
    if is_cube_mx: markers.append("STM32CubeMX")
    
    is_arduino = any(p.suffix == ".ino" for p, _ in records) or "Arduino.h" in joined or "boards.txt" in names
    if is_arduino: markers.append("Arduino")
    
    is_pio = "platformio.ini" in names
    if is_pio: markers.append("PlatformIO")
    
    is_zephyr = "west.yml" in names or "prj.conf" in names or "zephyr" in joined.lower()
    if is_zephyr: markers.append("Zephyr")
    
    is_espidf = "sdkconfig" in names or "sdkconfig.defaults" in names or "idf.py" in joined or "idf_component.yml" in names
    if is_espidf: markers.append("ESP-IDF")
    
    is_cmake = "CMakeLists.txt" in names
    if is_cmake: markers.append("CMake")
    
    is_make = any(p.name.lower().startswith("makefile") for p, _ in records)
    if is_make: markers.append("Make")
    
    is_rust = "Cargo.toml" in names
    if is_rust: markers.append("Rust")
    
    is_keil = any(p.suffix in {".uvprojx", ".uvoptx"} for p, _ in records)
    if is_keil: markers.append("Keil/MDK")
    
    is_freertos = "FreeRTOS.h" in joined or "xTaskCreate" in joined or "FreeRTOSConfig.h" in names
    if is_freertos: markers.append("FreeRTOS")
    
    is_dts = any(p.suffix in {".dts", ".dtsi", ".overlay"} for p, _ in records)
    if is_dts: markers.append("Device Tree")
    
    if "arm-none-eabi" in joined or "riscv" in joined.lower():
        markers.append("Embedded toolchain")
        
    if is_cube_ide: primary = "STM32CubeIDE"
    elif is_cube_mx and not is_pio: primary = "STM32CubeMX"
    elif is_espidf: primary = "ESP-IDF"
    elif is_zephyr: primary = "Zephyr"
    elif is_pio: primary = "PlatformIO"
    elif is_arduino: primary = "Arduino"
    elif is_rust: primary = "Rust Embedded"
    elif is_cmake: primary = "CMake"
    elif is_make: primary = "Make"
    elif is_keil: primary = "Keil/MDK"
    else: primary = "Bare-metal C/C++" if markers else "Unknown"

    system_type = "rtos" if (is_freertos or is_zephyr or is_espidf) else "embedded-linux" if is_dts else "bare-metal"
    topology = "single-mcu"

    return {
        "primaryType": primary,
        "projectType": system_type,
        "systemType": system_type,
        "topology": topology,
        "markers": markers,
        "isEmbedded": bool(markers or any(p.suffix in SRC_EXTENSIONS for p, _ in records))
    }

# --- 2. Multi-README Discovery ---
def scan_readmes(records, root):
    readmes = []
    root_readme_data = {"path": "README.md", "title": root.name, "content": "", "exists": False, "source": "project-readme"}
    
    readme_paths = []
    for path, content in records:
        name_lower = path.name.lower()
        if name_lower.startswith("readme"):
            readme_paths.append((path, content))
            
    readme_paths.sort(key=lambda x: (x[0].parent != root, str(x[0])))
    
    for path, content in readme_paths:
        r_path = rel(path, root)
        is_root = (path.parent == root)
        
        title_match = re.search(r"^#\s+(.+)$", content, re.MULTILINE)
        title = title_match.group(1).strip() if title_match else (root.name if is_root else path.parent.name)
        
        paragraphs = [re.sub(r"[`*_#]", "", part).strip() for part in content.split("\n\n") if part.strip() and not part.lstrip().startswith("#")]
        summary = paragraphs[0][:300] if paragraphs else f"Documentation in {r_path}"
        
        entry = {
            "path": r_path,
            "title": title,
            "summary": summary,
            "directory": "." if is_root else rel(path.parent, root),
            "isRoot": is_root,
            "lines": len(content.splitlines()),
            "lastModified": datetime.date.fromtimestamp(path.stat().st_mtime).isoformat() if path.exists() else None,
            "source": "scanner"
        }
        readmes.append(entry)
        
        if is_root and not root_readme_data["exists"]:
            root_readme_data = {
                "path": r_path,
                "title": title,
                "content": content,
                "exists": True,
                "lastModified": entry["lastModified"],
                "source": "project-readme"
            }

    return root_readme_data, readmes

# --- 3. Hardware Detection ---
def scan_hardware(records, root, project_info):
    joined = "\n".join(content for _, content in records)
    target = {}
    board = {}
    clock_config = {}
    peripherals = []
    pin_mappings = []
    source_files = []
    
    for path, content in records:
        if path.suffix == ".ioc":
            source_files.append(rel(path, root))
            mcu_m = re.search(r"Mcu\.Name=([^\r\n]+)", content)
            if mcu_m: target["mcu"] = mcu_m.group(1).strip()
            family_m = re.search(r"Mcu\.Family=([^\r\n]+)", content)
            if family_m: target["family"] = family_m.group(1).strip()
            board_m = re.search(r"BoardName=([^\r\n]+)", content)
            if board_m: board["name"] = board_m.group(1).strip()
            
            sysclk_m = re.search(r"RCC\.SYSCLKFreq_VALUE=([0-9]+)", content)
            if sysclk_m:
                hz = int(sysclk_m.group(1))
                clock_config["sysclk"] = f"{hz // 1000000}MHz"
                target["frequencyMHz"] = hz // 1000000
                
            for ip_m in re.finditer(r"Mcu\.IP\d+=([^\r\n]+)", content):
                ip_name = ip_m.group(1).strip()
                p_type = ("uart" if "USART" in ip_name or "UART" in ip_name else
                          "spi" if "SPI" in ip_name else
                          "i2c" if "I2C" in ip_name else
                          "can" if "CAN" in ip_name else
                          "adc" if "ADC" in ip_name else
                          "timer" if "TIM" in ip_name else
                          "dma" if "DMA" in ip_name else
                          "usb" if "USB" in ip_name else "peripheral")
                peripherals.append({
                    "id": safe_id(ip_name.lower()),
                    "name": ip_name,
                    "type": p_type,
                    "source": rel(path, root)
                })
                
            for pin_m in re.finditer(r"(P[A-Z]\d+)\.Signal=([^\r\n]+)", content):
                pin_mappings.append({
                    "pin": pin_m.group(1),
                    "signal": pin_m.group(2).strip(),
                    "source": rel(path, root)
                })

    for path, content in records:
        if path.name == "platformio.ini":
            source_files.append(rel(path, root))
            board_m = re.search(r"board\s*=\s*([^\r\n]+)", content)
            if board_m:
                b_name = board_m.group(1).strip()
                board.setdefault("name", b_name)
                if not target.get("mcu"):
                    if "f411re" in b_name: target["mcu"] = "STM32F411RE"; target["family"] = "STM32F4"
                    elif "f401" in b_name: target["mcu"] = "STM32F401"; target["family"] = "STM32F4"
                    elif "f103" in b_name or "bluepill" in b_name: target["mcu"] = "STM32F103C8"; target["family"] = "STM32F1"
                    elif "esp32" in b_name: target["mcu"] = "ESP32"; target["family"] = "ESP32"
                    elif "pico" in b_name or "rp2040" in b_name: target["mcu"] = "RP2040"; target["family"] = "RP2040"
            mcu_m = re.search(r"board_build\.mcu\s*=\s*([^\r\n]+)", content)
            if mcu_m: target["mcu"] = mcu_m.group(1).strip()
            fcpu_m = re.search(r"board_build\.f_cpu\s*=\s*([0-9]+)L?", content)
            if fcpu_m:
                hz = int(fcpu_m.group(1))
                clock_config["sysclk"] = f"{hz // 1000000}MHz"
                target["frequencyMHz"] = hz // 1000000

    for path, content in records:
        if path.name == "prj.conf":
            source_files.append(rel(path, root))
            b_m = re.search(r'CONFIG_BOARD="?([^"\r\n]+)"?', content)
            if b_m: board.setdefault("name", b_m.group(1).strip())
            soc_m = re.search(r'CONFIG_SOC="?([^"\r\n]+)"?', content)
            if soc_m: target.setdefault("mcu", soc_m.group(1).strip())

    for path, content in records:
        if path.name in {"sdkconfig", "sdkconfig.defaults"}:
            source_files.append(rel(path, root))
            t_m = re.search(r'CONFIG_IDF_TARGET="?([^"\r\n]+)"?', content)
            if t_m:
                target.setdefault("mcu", t_m.group(1).strip().upper())
                target.setdefault("family", "ESP32")

    if not target.get("mcu"):
        mcu_match = re.search(r"\b(STM32[A-Z0-9]+|ESP32[A-Z0-9-]*|nRF\w+|RP2040|SAMD\w+|MSP430\w+|ATmega\w+|GD32\w+)\b", joined, re.I)
        if mcu_match:
            target["mcu"] = mcu_match.group(1)

    mcu_str = target.get("mcu", "").upper()
    if "STM32" in mcu_str or "nucleo" in board.get("name", "").lower():
        target.setdefault("vendor", "STMicroelectronics")
        target.setdefault("architecture", "ARM Cortex-M4" if ("F4" in mcu_str or "G4" in mcu_str) else "ARM Cortex-M3" if "F1" in mcu_str else "ARM Cortex-M0+" if "G0" in mcu_str else "ARM Cortex-M")
    elif "ESP32" in mcu_str:
        target.setdefault("vendor", "Espressif Systems")
        target.setdefault("architecture", "Xtensa LX6/LX7" if "C" not in mcu_str else "RISC-V")
    elif "NRF" in mcu_str:
        target.setdefault("vendor", "Nordic Semiconductor")
        target.setdefault("architecture", "ARM Cortex-M4")
    elif "RP2040" in mcu_str:
        target.setdefault("vendor", "Raspberry Pi")
        target.setdefault("architecture", "ARM Cortex-M0+")
    elif "SAM" in mcu_str or "ATMEGA" in mcu_str:
        target.setdefault("vendor", "Microchip / Atmel")
        target.setdefault("architecture", "ARM Cortex-M0+" if "SAM" in mcu_str else "AVR")
    else:
        arch_m = re.search(r"\b(ARM Cortex-M[0-9A-Za-z]*|Cortex-A\w*|RISC-V|AVR|Xtensa)\b", joined, re.I)
        if arch_m: target.setdefault("architecture", arch_m.group(1))

    if not target.get("frequencyMHz"):
        clk_m = re.search(r"\b(?:SYS_CLOCK_HZ|SystemCoreClock|configCPU_CLOCK_HZ|F_CPU)\s*(?:=|#define\s+\w+)?\s*([0-9]{6,10})", joined)
        if clk_m:
            hz = int(clk_m.group(1))
            clock_config.setdefault("sysclk", f"{hz // 1000000}MHz")
            target["frequencyMHz"] = hz // 1000000

    peripheral_patterns = {
        "uart": (r"\b(UART\w*|USART\w*|Serial\d?)\b", "uart"),
        "spi": (r"\b(SPI\w*)\b", "spi"),
        "i2c": (r"\b(I2C\w*|Wire\d?)\b", "i2c"),
        "can": (r"\b(CAN\w*|FDCAN\w*)\b", "can"),
        "adc": (r"\b(ADC\w*)\b", "adc"),
        "timer": (r"\b(TIM\w*|TIMER\w*)\b", "timer"),
        "dma": (r"\b(DMA\w*)\b", "dma"),
        "gpio": (r"\b(GPIO\w*|pinMode)\b", "gpio"),
        "usb": (r"\b(USB\w*)\b", "usb")
    }
    seen_peripherals = {p["id"] for p in peripherals}
    for p_name, (pat, p_kind) in peripheral_patterns.items():
        for match in re.finditer(pat, joined):
            sym = match.group(1).upper()
            pid = safe_id(sym.lower())
            if pid not in seen_peripherals and len(sym) <= 12:
                seen_peripherals.add(pid)
                peripherals.append({
                    "id": pid,
                    "name": sym,
                    "type": p_kind,
                    "source": "scanner"
                })

    return {
        "target": target,
        "board": board,
        "clockConfig": clock_config,
        "power": {"operatingVoltage": "3.3V" if ("STM32" in mcu_str or "ESP" in mcu_str or "NRF" in mcu_str) else None, "sleepModes": [], "powerBudget": {}},
        "peripherals": peripherals,
        "pinMappings": pin_mappings,
        "sensors": [],
        "actuators": [],
        "communication": [],
        "debugInterfaces": [],
        "sourceFiles": sorted(set(source_files))
    }

# --- 4. Categorized Configuration Parameters ---
def categorize_param(name):
    u = name.upper()
    # Check feature flags first (ENABLE_, DISABLE_, USE_, etc.)
    if any(u.startswith(p) for p in ("ENABLE_", "DISABLE_", "USE_", "HAS_", "WITH_", "WITHOUT_", "SUPPORT_")):
        return "feature"
    if any(k in u for k in ("CLK", "CLOCK", "HSE", "HSI", "PLL", "SYSCLK", "F_CPU")):
        return "clock"
    if any(k in u for k in ("UART", "USART", "SPI", "I2C", "CAN", "ADC", "DAC", "PWM", "TIM", "DMA", "GPIO", "USB", "I2S")):
        return "peripheral"
    if any(k in u for k in ("STACK", "HEAP", "FLASH", "RAM", "SRAM", "EEPROM", "BUFFER_SIZE", "MEM_")):
        return "memory"
    if any(k in u for k in ("BAUD", "BAUDRATE", "WIFI", "LORA", "MQTT", "HTTP", "TIMEOUT")) or re.search(r"\b(BLE|ETH|IP|PORT|CHANNEL)\b", u) or "_BLE" in u or "BLE_" in u or "_ETH" in u:
        return "communication"
    if u.startswith("CONFIG_") or u.startswith("CONFIG") or any(k in u for k in ("TASK", "PRIORITY", "SEMAPHORE", "MUTEX", "QUEUE", "TICK")):
        return "rtos"
    if any(k in u for k in ("SLEEP", "POWER", "WAKEUP", "STANDBY", "VOLTAGE", "LOW_POWER")):
        return "power"
    if any(k in u for k in ("DEBUG", "LOG", "TRACE", "ASSERT", "PRINTF", "VERBOSE")):
        return "debug"
    if u.startswith("-O") or u.startswith("-G") or u.startswith("-W") or "__OPTIMIZE__" in u:
        return "compiler"
    return "application"

def scan_configurations(records, root):
    sources = []
    params = []
    profiles = []
    
    profile_defs = (
        ("platformio.ini", "PlatformIO environment"),
        ("CMakeLists.txt", "CMake build"),
        ("Makefile", "Make build"),
        ("west.yml", "Zephyr west build"),
        ("Cargo.toml", "Cargo build")
    )
    for fname, label in profile_defs:
        if (root / fname).exists():
            profiles.append({"id": safe_id(label.lower()), "name": label, "source": fname})
            sources.append(fname)
            
    seen_params = set()
    for path, content in records:
        r_path = rel(path, root)
        
        if path.name == "platformio.ini":
            for m in re.finditer(r"-D\s*([A-Za-z0-9_]+)(?:=([^\s\r\n]+))?", content):
                name = m.group(1)
                val = m.group(2)
                line = content.count("\n", 0, m.start()) + 1
                pid = safe_id(name).lower()
                if pid not in seen_params:
                    seen_params.add(pid)
                    params.append({
                        "id": pid,
                        "name": name,
                        "value": val,
                        "category": categorize_param(name),
                        "file": r_path,
                        "line": line,
                        "source": "platformio.ini build_flags"
                    })
                    
        if path.suffix in SRC_EXTENSIONS or path.name in {"FreeRTOSConfig.h", "prj.conf", "sdkconfig"}:
            if "config" in path.name.lower() or path.suffix == ".h" or path.name in {"prj.conf", "sdkconfig"}:
                sources.append(r_path)
            for m in re.finditer(r"^[ \t]*#define\s+([A-Za-z_][A-Za-z0-9_]*)(?:\s+([^\r\n/]+))?", content, re.M):
                name = m.group(1)
                val = m.group(2).strip() if m.group(2) else None
                if name.endswith("_H") or name.endswith("_H_") or name.startswith("__") or name in {"NULL", "TRUE", "FALSE"}:
                    continue
                line = content.count("\n", 0, m.start()) + 1
                pid = safe_id(name).lower()
                if pid not in seen_params:
                    seen_params.add(pid)
                    params.append({
                        "id": pid,
                        "name": name,
                        "value": val,
                        "category": categorize_param(name),
                        "file": r_path,
                        "line": line,
                        "source": "source definition"
                    })
            for m in re.finditer(r"^(CONFIG_[A-Za-z0-9_]+)=(.*)$", content, re.M):
                name = m.group(1)
                val = m.group(2).strip()
                line = content.count("\n", 0, m.start()) + 1
                pid = safe_id(name).lower()
                if pid not in seen_params:
                    seen_params.add(pid)
                    params.append({
                        "id": pid,
                        "name": name,
                        "value": val,
                        "category": categorize_param(name),
                        "file": r_path,
                        "line": line,
                        "source": "Kconfig option"
                    })

    by_category = {}
    for p in params:
        by_category.setdefault(p["category"], []).append(p)

    feature_flags = [p for p in params if p["category"] == "feature"]

    return {
        "buildProfiles": profiles,
        "parameters": params,
        "parametersByCategory": by_category,
        "featureFlags": feature_flags,
        "runtimeConfiguration": [],
        "kconfigOptions": [p for p in params if p["name"].startswith("CONFIG_")],
        "deviceTreeOverlays": [rel(p, root) for p, _ in records if p.suffix == ".overlay"],
        "generatedFiles": [],
        "configurationSources": sorted(set(sources))
    }

# --- 5. Makefile Role Analysis & Build System ---
def categorize_make_target(name, recipe=""):
    nl = name.lower()
    rl = recipe.lower()
    if nl in {"flash", "program", "upload", "burn", "dfu"} or any(k in rl for k in ("openocd", "st-flash", "esptool", "nrfjprog", "avrdude")):
        return "flash"
    if nl in {"monitor", "debug", "gdb", "console", "serial"} or any(k in rl for k in ("gdb", "minicom", "screen", "putty")):
        return "debug"
    if nl in {"clean", "distclean", "mrproper"}:
        return "clean"
    if nl in {"test", "check", "verify", "unity"}:
        return "test"
    if nl in {"size", "lint", "cppcheck", "valgrind"}:
        return "analysis"
    if nl in {"format", "style", "clang-format"}:
        return "format"
    if nl in {"doc", "docs", "doxygen"}:
        return "docs"
    if nl in {"all", "build", "compile", "default", "elf", "bin", "hex", "lib"} or any(k in rl for k in ("gcc", "g++", "clang", "ld", "make")):
        return "build"
    return "utility"

def scan_build(records, root, project_info):
    names = {p.name for p, _ in records}
    system_type = project_info.get("primaryType", "custom")
    build_files = [rel(p, root) for p, _ in records if p.name in CONFIG_NAMES or p.suffix == ".ld" or p.name.lower().startswith("makefile")]
    
    makefiles_data = []
    has_other_build = any(k in names for k in ("platformio.ini", "CMakeLists.txt", "west.yml", "Cargo.toml", "sdkconfig"))
    
    for path, content in records:
        if path.name.lower().startswith("makefile"):
            r_path = rel(path, root)
            targets = []
            variables = {}
            lines = content.splitlines()
            current_target = None
            current_recipe = []
            
            for line in lines:
                var_m = re.match(r"^([A-Za-z0-9_]+)\s*[?:+]?=\s*(.*)$", line)
                if var_m:
                    variables[var_m.group(1)] = var_m.group(2).strip()
                target_m = re.match(r"^([A-Za-z0-9_\-\.]+)\s*:(?!=)\s*(.*)$", line)
                if target_m and not line.startswith("\t"):
                    if current_target:
                        rec = "\n".join(current_recipe).strip()
                        targets.append({
                            "name": current_target,
                            "recipe": rec,
                            "category": categorize_make_target(current_target, rec)
                        })
                    current_target = target_m.group(1)
                    current_recipe = []
                elif current_target and (line.startswith("\t") or line.startswith("  ")):
                    current_recipe.append(line.strip())
                    
            if current_target:
                rec = "\n".join(current_recipe).strip()
                targets.append({
                    "name": current_target,
                    "recipe": rec,
                    "category": categorize_make_target(current_target, rec)
                })

            compilation_targets = [t for t in targets if t["category"] == "build"]
            if any("cmake" in t["recipe"].lower() or "platformio" in t["recipe"].lower() for t in targets):
                role = "wrapper"
            elif has_other_build or not compilation_targets:
                role = "utility"
            else:
                role = "primary"

            makefiles_data.append({
                "path": r_path,
                "role": role,
                "targets": targets,
                "variables": variables
            })

    toolchain = {
        "compiler": "arm-none-eabi-gcc" if "ARM" in project_info.get("primaryType", "") or "STM32" in str(records) else None,
        "linker": None,
        "objcopy": None,
        "objdump": None,
        "targetTriple": None,
        "version": None
    }
    
    return {
        "system": {
            "type": system_type,
            "files": sorted(set(build_files)),
            "buildDirectory": "build" if "build" in names else ".pio" if "platformio.ini" in names else "target" if "Cargo.toml" in names else "out",
            "generator": None
        },
        "toolchain": toolchain,
        "makefiles": makefiles_data,
        "profiles": [],
        "targets": [t["name"] for mf in makefiles_data for t in mf["targets"]],
        "artifacts": [],
        "linkerScripts": [x for x in build_files if x.endswith(".ld")],
        "commands": {
            "configure": None,
            "build": "pio run" if "platformio.ini" in names else "make" if makefiles_data and makefiles_data[0]["role"] == "primary" else "west build" if "west.yml" in names else "cargo build" if "Cargo.toml" in names else None,
            "test": None,
            "flash": "make flash" if any(any(t["name"] == "flash" for t in mf["targets"]) for mf in makefiles_data) else None,
            "debug": None
        },
        "flashAndDebug": {},
        "staticAnalysis": [],
        "ci": []
    }

# --- 6. Utility Tools & Scripts Detection ---
def categorize_tool(name, content=""):
    nl = name.lower()
    cl = content.lower()
    if any(k in nl for k in ("flash", "upload", "program", "burn")) or any(k in cl for k in ("openocd", "st-flash", "esptool", "nrfjprog", "avrdude")):
        return "flash"
    if any(k in nl for k in ("debug", "gdb", "monitor", "serial")) or any(k in cl for k in ("gdb", "minicom", "screen")):
        return "debug"
    if any(k in nl for k in ("build", "compile", "make")) or any(k in cl for k in ("gcc", "cmake", "cargo")):
        return "build"
    if any(k in nl for k in ("test", "check", "verify")) or any(k in cl for k in ("pytest", "unity")):
        return "test"
    if any(k in nl for k in ("generate", "codegen", "proto")):
        return "code-generation"
    if any(k in nl for k in ("size", "lint", "cppcheck")):
        return "analysis"
    if any(k in nl for k in ("format", "style", "clang-format")):
        return "format"
    if any(k in nl for k in ("setup", "install", "bootstrap", "env")):
        return "environment"
    return "utility"

def scan_tools(records, root):
    tools = []
    for path, content in records:
        r_path = rel(path, root)
        is_script = path.suffix in SCRIPT_EXTENSIONS and not (r_path.startswith("src/") or r_path.startswith("include/"))
        is_cfg = path.suffix == ".cfg" or path.name in {"openocd.cfg", "Justfile", "Taskfile.yml", "Dockerfile", "docker-compose.yml"}
        
        if is_script or is_cfg:
            script_type = ("shell-script" if path.suffix in {".sh", ".bash"} else
                           "python-script" if path.suffix == ".py" else
                           "batch-script" if path.suffix in {".bat", ".cmd"} else
                           "powershell-script" if path.suffix == ".ps1" else
                           "docker" if "docker" in path.name.lower() else
                           "task-runner" if "file" in path.name.lower() else "config")
            tools.append({
                "id": safe_id(path.stem.lower()),
                "name": path.name,
                "path": r_path,
                "type": script_type,
                "category": categorize_tool(path.name, content),
                "source": "scanner"
            })
    return tools

# --- 7. Memory Layout ---
def scan_memory_layout(records, root):
    regions, sections, scripts, maps = [], [], [], []
    for path, content in records:
        if path.suffix == ".ld":
            scripts.append(rel(path, root))
            for m in re.finditer(r"([A-Za-z0-9_]+)\s*(?:\([^)]*\))?\s*:\s*ORIGIN\s*=\s*([^,]+),\s*LENGTH\s*=\s*([^\r\n;]+)", content, re.I):
                name = m.group(1).upper()
                kind = "flash" if any(k in name for k in ("FLASH", "ROM", "CODE")) else "ram" if any(k in name for k in ("RAM", "SRAM", "DATA")) else "eeprom" if "EEPROM" in name else "other"
                regions.append({
                    "id": safe_id(name.lower()),
                    "name": name,
                    "type": kind,
                    "origin": m.group(2).strip(),
                    "length": m.group(3).strip(),
                    "source": rel(path, root)
                })
            for m in re.finditer(r"\.([A-Za-z0-9_]+)\s*:\s*\{[^}]*\}\s*>\s*([A-Za-z0-9_]+)", content):
                sections.append({
                    "name": "." + m.group(1),
                    "region": m.group(2),
                    "source": rel(path, root)
                })
        if path.suffix == ".map":
            maps.append(rel(path, root))
            
    return {
        "addressWidth": 32,
        "regions": regions,
        "sections": sections,
        "partitions": [],
        "stack": {},
        "heap": {},
        "specialAreas": [],
        "linkerScripts": scripts,
        "mapFiles": maps,
        "usage": {}
    }

# --- 8. User-Defined Data Types ---
def type_is_project(name, path):
    return (bool(re.match(r"^[A-Za-z_]\w*$", name)) and
            name not in STANDARD_TYPES and
            not any(h in name for h in ("HAL_", "_TypeDef", "FreeRTOS", "esp_", "k_", "nrfx_", "nrf_")) and
            path.name not in {"stdint.h", "stddef.h", "stdbool.h"})

def scan_data_types(records, root):
    result = {}
    definitions = []
    patterns = (
        ("struct", r"\btypedef\s+struct(?:\s+\w+)?\s*\{([^}]*)\}\s*(\w+)\s*;"),
        ("union", r"\btypedef\s+union(?:\s+\w+)?\s*\{([^}]*)\}\s*(\w+)\s*;"),
        ("enum", r"\btypedef\s+enum(?:\s+\w+)?\s*\{([^}]*)\}\s*(\w+)\s*;"),
        ("struct", r"\bstruct\s+(\w+)\s*\{([^}]*)\}"),
        ("union", r"\bunion\s+(\w+)\s*\{([^}]*)\}"),
        ("enum", r"\benum\s+(\w+)\s*\{([^}]*)\}"),
        ("typedef", r"\btypedef\s+[A-Za-z_]\w*\s+(\w+)\s*;"),
        ("class", r"\bclass\s+(\w+)\s*[:{]")
    )
    
    for path, content in records:
        if path.suffix not in SRC_EXTENSIONS:
            continue
        for kind, pat in patterns:
            for match in re.finditer(pat, content):
                groups = match.groups()
                if kind in {"struct", "union", "enum"} and len(groups) == 2:
                    if re.match(r"^[A-Za-z_]\w*$", groups[1]):
                        name, body = groups[1], groups[0]
                    else:
                        name, body = groups[0], groups[1]
                else:
                    name, body = groups[0], ""
                    
                if not name or not type_is_project(name, path):
                    continue
                    
                line = content.count("\n", 0, match.start()) + 1
                item = result.setdefault(name, {
                    "id": safe_id(name).lower(),
                    "name": name,
                    "kind": kind,
                    "language": "Rust" if path.suffix == ".rs" else "C/C++",
                    "userDefined": True,
                    "ownership": "project",
                    "role": f"Project-defined {kind} used by firmware components.",
                    "description": "",
                    "files": [],
                    "fields": [],
                    "members": [],
                    "usedByModules": [],
                    "usedByComponents": [],
                    "usage": [],
                    "objectInstances": [],
                    "source": "scanner",
                    "confidence": "medium",
                    "evidence": []
                })
                item["files"].append(source_file(path, root, "definition", [name], line))
                item["evidence"].append({"file": rel(path, root), "line": line, "reason": "user-defined type declaration"})
                definitions.append((name, path, content, line, kind, body))

    for name, path, content, line, kind, body in definitions:
        item = result[name]
        if kind == "enum" and body:
            for member_m in re.finditer(r"([A-Za-z_][A-Za-z0-9_]*)(?:\s*=\s*([^,}\r\n]+))?", body):
                item["members"].append({
                    "name": member_m.group(1),
                    "value": member_m.group(2).strip() if member_m.group(2) else None
                })
        elif kind in {"struct", "union"} and body:
            for field_m in re.finditer(r"(?:^|;)\s*([A-Za-z_][A-Za-z0-9_]*)\s+([A-Za-z_][A-Za-z0-9_]*)\s*(?:\[[^\]]*\])?\s*(?=;|$)", body, re.M):
                f_type, f_name = field_m.groups()
                item["fields"].append({
                    "name": f_name,
                    "type": f_type,
                    "typeReference": result.get(f_type, {}).get("id"),
                    "role": "User-defined field" if f_type in result else "Field"
                })

    for item in result.values():
        item["files"] = unique(item["files"])
        item["evidence"] = unique(item["evidence"])
        item["fields"] = unique(item["fields"])
        item["members"] = unique(item["members"])
        
    return list(result.values())

# --- 9. Functions & Call Graph ---
def scan_functions(records, root, types):
    known_types = {t["name"]: t["id"] for t in types}
    functions = {}
    func_pattern = re.compile(
        r"(?:^[ \t]*)"
        r"(?:(static|inline|extern)\s+)?"
        r"([A-Za-z_][A-Za-z0-9_]*\s*(?:\*+)?)\s+"
        r"([A-Za-z_][A-Za-z0-9_]*)\s*"
        r"\(([^)]*)\)\s*"
        r"\{",
        re.M
    )
    
    for path, content in records:
        if path.suffix not in SRC_EXTENSIONS or path.suffix in {".h", ".hpp"}:
            continue
        r_path = rel(path, root)
        parts = Path(r_path).parts
        mod = parts[1] if len(parts) > 2 and parts[0] in {"src", "app", "lib", "components"} else parts[0] if len(parts) > 1 else "firmware"
        mod_id = safe_id(mod).lower()
        comp_id = safe_id(path.stem).lower()
        
        for m in func_pattern.finditer(content):
            storage, ret_type, name, params_str = m.groups()
            if name in {"if", "while", "for", "switch", "catch"}:
                continue
            line = content.count("\n", 0, m.start()) + 1
            is_static = (storage == "static")
            
            start_pos = m.end() - 1
            brace_count = 1
            idx = start_pos + 1
            while idx < len(content) and brace_count > 0:
                if content[idx] == "{": brace_count += 1
                elif content[idx] == "}": brace_count -= 1
                idx += 1
            body = content[start_pos:idx]
            
            params = [p.strip() for p in params_str.split(",") if p.strip() and p.strip() != "void"]
            ref_types = [tid for tname, tid in known_types.items() if re.search(r"\b" + re.escape(tname) + r"\b", params_str + " " + ret_type)]
            
            fid = safe_id(name).lower()
            functions[name] = {
                "id": fid,
                "name": name,
                "file": r_path,
                "line": line,
                "signature": f"{ret_type.strip()} {name}({params_str.strip()})",
                "returnType": ret_type.strip(),
                "parameters": params,
                "static": is_static,
                "visibility": "private" if is_static else "public",
                "body": body,
                "callers": [],
                "callees": [],
                "referencedTypes": ref_types,
                "module": mod_id,
                "component": comp_id,
                "source": "scanner",
                "confidence": "medium"
            }

    edges = []
    seen_edges = set()
    for caller_name, caller_info in functions.items():
        body = caller_info.pop("body", "")
        for callee_name in functions:
            if callee_name == caller_name:
                continue
            if re.search(r"\b" + re.escape(callee_name) + r"\s*\(", body):
                caller_info["callees"].append(callee_name)
                functions[callee_name]["callers"].append(caller_name)
                edge_key = f"{caller_name}->{callee_name}"
                if edge_key not in seen_edges:
                    seen_edges.add(edge_key)
                    edges.append({
                        "caller": caller_name,
                        "callee": callee_name,
                        "file": caller_info["file"],
                        "line": caller_info["line"]
                    })

    for f in functions.values():
        f["callers"] = sorted(set(f["callers"]))
        f["callees"] = sorted(set(f["callees"]))

    mermaid_lines = ["flowchart LR"]
    for e in edges:
        mermaid_lines.append(f"    {safe_id(e['caller'])}[{e['caller']}] --> {safe_id(e['callee'])}[{e['callee']}]")
    call_graph_mermaid = "\n".join(mermaid_lines) if edges else "flowchart LR\n    none[No function calls detected]"

    return list(functions.values()), {"edges": edges, "mermaid": call_graph_mermaid}

# --- 10. Macros ---
def scan_macros(records, root):
    macros = []
    seen = set()
    for path, content in records:
        if path.suffix not in SRC_EXTENSIONS:
            continue
        r_path = rel(path, root)
        for m in re.finditer(r"^[ \t]*#define\s+([A-Za-z_][A-Za-z0-9_]*)(?:\(([^)]*)\))?(?:[ \t]+([^\r\n/]+))?", content, re.M):
            name = m.group(1)
            params_str = m.group(2)
            val = m.group(3).strip() if m.group(3) else None
            if name.endswith("_H") or name.endswith("_H_") or name.startswith("__") or name in {"NULL", "TRUE", "FALSE"}:
                continue
            mid = safe_id(name).lower()
            if mid not in seen:
                seen.add(mid)
                line = content.count("\n", 0, m.start()) + 1
                params = [p.strip() for p in params_str.split(",")] if params_str else []
                macros.append({
                    "id": mid,
                    "name": name,
                    "value": val,
                    "file": r_path,
                    "line": line,
                    "parameterized": bool(params_str is not None),
                    "parameters": params,
                    "category": categorize_param(name),
                    "source": "scanner"
                })
    return macros

# --- 11. Modules & Components ---
def scan_modules(records, root, types, functions):
    groups = {}
    for path, content in records:
        if path.suffix not in SRC_EXTENSIONS:
            continue
        r_path = rel(path, root)
        parts = Path(r_path).parts
        mod = parts[1] if len(parts) > 2 and parts[0] in {"src", "app", "lib", "components"} else parts[0] if len(parts) > 1 else "firmware"
        mod_id = safe_id(mod).lower()
        
        item = groups.setdefault(mod_id, {
            "id": mod_id,
            "name": mod.replace("_", " ").title(),
            "type": "application",
            "role": f"{mod.replace('_', ' ').title()} firmware subsystem.",
            "description": "",
            "files": [],
            "components": [],
            "dataTypes": [],
            "dependencies": [],
            "configurationRefs": [],
            "tasks": [],
            "interrupts": [],
            "timers": [],
            "queues": [],
            "objects": [],
            "source": "scanner",
            "confidence": "medium",
            "evidence": []
        })
        
        symbols = [f["name"] for f in functions if f["file"] == r_path]
        item["files"].append(source_file(path, root, "implementation", symbols[:30]))
        item["evidence"].append({"file": r_path, "line": 1, "reason": "source layout"})
        
        for t in types:
            if re.search(r"\b" + re.escape(t["name"]) + r"\b", content):
                item["dataTypes"].append({"id": t["id"], "role": "uses"})
                
        for match in re.finditer(r"\b(xTaskCreate(?:Static)?|k_thread_create)\b", content):
            item["tasks"].append({"name": match.group(1), "file": r_path, "line": content.count("\n", 0, match.start()) + 1})

    for item in groups.values():
        item["files"] = unique(item["files"])
        item["dataTypes"] = unique(item["dataTypes"])
        item["evidence"] = unique(item["evidence"])
        
    return list(groups.values())

def scan_components(modules_data, functions, records, root):
    comps = {}
    func_by_comp = {}
    for f in functions:
        func_by_comp.setdefault(f["component"], []).append(f)
        
    for mod in modules_data:
        for f_item in mod["files"]:
            path_str = f_item["path"]
            stem = Path(path_str).stem
            comp_id = safe_id(stem).lower()
            lower = stem.lower()
            
            kind = ("driver" if any(x in lower for x in ("driver", "hal", "gpio", "uart", "spi", "i2c", "can", "adc", "timer")) else
                    "service" if any(x in lower for x in ("manager", "service", "storage", "telemetry", "comm")) else
                    "middleware" if any(x in lower for x in ("protocol", "codec", "buffer")) else "application")
            
            public_headers = []
            header_candidate = path_str.replace(".c", ".h")
            if any(p == header_candidate for p, _ in records):
                public_headers.append(header_candidate)
                
            comp_funcs = func_by_comp.get(comp_id, [])
            provides = [f["name"] for f in comp_funcs if not f.get("static")]
            consumes = sorted(set(callee for f in comp_funcs for callee in f.get("callees", [])))
            
            comps[comp_id] = {
                "id": comp_id,
                "name": stem.replace("_", " ").title(),
                "type": kind,
                "language": "Rust" if path_str.endswith(".rs") else "C/C++",
                "role": f"{stem.replace('_', ' ').title()} {kind} component.",
                "description": "",
                "files": [f_item],
                "publicHeaders": public_headers,
                "provides": provides,
                "consumes": consumes,
                "dependencies": [],
                "dataTypes": mod["dataTypes"],
                "objects": [],
                "interrupts": [],
                "configurationRefs": [],
                "source": "scanner",
                "confidence": "medium",
                "evidence": mod["evidence"][:3],
                "module": mod["id"]
            }
    return list(comps.values())

# --- 12. Objects & Ownership ---
def scan_objects(records, root, types):
    known = {item["name"]: item for item in types}
    output = []
    for path, content in records:
        if path.suffix not in SRC_EXTENSIONS:
            continue
        r_path = rel(path, root)
        for match in re.finditer(r"\b(static\s+)?([A-Z][A-Za-z0-9_]*)\s+([A-Za-z0-9_]+)\s*(?:[=;{])", content):
            is_static = bool(match.group(1))
            type_name = match.group(2)
            name = match.group(3)
            if type_name not in known or name in {"void", "int", "char"}:
                continue
            line = content.count("\n", 0, match.start()) + 1
            output.append({
                "id": safe_id(name).lower(),
                "name": name,
                "typeReference": known[type_name]["id"],
                "kind": "static" if is_static else "global",
                "role": f"Runtime instance of {type_name}.",
                "lifetime": {
                    "scope": "firmware" if is_static else "firmware",
                    "startsAt": "declaration or initialization",
                    "endsAt": "reset",
                    "createdBy": None,
                    "destroyedBy": None,
                    "persistsAcrossReset": False
                },
                "ownership": {
                    "model": "static" if is_static else "global",
                    "owner": {"kind": "source-file", "id": r_path},
                    "transferEvents": []
                },
                "storage": {
                    "location": "global-data",
                    "region": "ram",
                    "section": ".bss",
                    "size": None
                },
                "creation": {"function": None, "file": r_path, "line": line},
                "usage": [],
                "files": [source_file(path, root, "definition", [name], line)],
                "source": "scanner",
                "confidence": "medium",
                "evidence": [{"file": r_path, "line": line, "reason": "project-defined object instance"}]
            })
            
        for match in re.finditer(r"\b(malloc|calloc|realloc|xQueueCreate(?:Static)?|xTaskCreate(?:Static)?)\s*\(", content):
            fn = match.group(1)
            line = content.count("\n", 0, match.start()) + 1
            dynamic = fn in {"malloc", "calloc", "realloc"}
            output.append({
                "id": f"{fn.lower()}_{line}",
                "name": fn,
                "typeReference": None,
                "kind": "heap" if dynamic else "rtos",
                "role": f"Created resource from {fn}.",
                "lifetime": {
                    "scope": "heap-allocation" if dynamic else "task",
                    "startsAt": "creation call",
                    "endsAt": "unknown",
                    "createdBy": None,
                    "destroyedBy": None,
                    "persistsAcrossReset": False
                },
                "ownership": {
                    "model": "unknown",
                    "owner": {"kind": "unknown", "id": "unknown"},
                    "transferEvents": []
                },
                "storage": {
                    "location": "heap" if dynamic else "rtos-managed",
                    "region": "ram",
                    "section": None,
                    "size": None
                },
                "creation": {"function": None, "file": r_path, "line": line},
                "usage": [],
                "files": [source_file(path, root, "creation", [fn], line)],
                "source": "scanner",
                "confidence": "low",
                "evidence": [{"file": r_path, "line": line, "reason": "allocation or RTOS creation call"}]
            })
            
    return by_id(output)

# --- 13. State Machines ---
def scan_state_machines(records, root, types):
    state_machines = []
    for t in types:
        if t["kind"] == "enum" and ("state" in t["name"].lower() or any("state" in m["name"].lower() for m in t.get("members", []))):
            members = [m["name"] for m in t.get("members", [])]
            transitions = []
            seen_trans = set()
            
            for path, content in records:
                # Find switch statements
                for sw_m in re.finditer(r"switch\s*\([^)]*\)\s*\{", content):
                    # Find closing brace of switch block
                    start_pos = sw_m.end() - 1
                    brace_count = 1
                    idx = start_pos + 1
                    while idx < len(content) and brace_count > 0:
                        if content[idx] == "{": brace_count += 1
                        elif content[idx] == "}": brace_count -= 1
                        idx += 1
                    sw_body = content[start_pos:idx]
                    
                    # Split switch body into case blocks using regex
                    case_splits = re.split(r"\bcase\s+([A-Za-z0-9_]+)\s*:", sw_body)
                    # case_splits[0] is preamble before first case
                    # then pairs: (case_label, case_content)
                    for i in range(1, len(case_splits), 2):
                        c_label = case_splits[i].strip()
                        c_body = case_splits[i+1] if i + 1 < len(case_splits) else ""
                        if c_label in members:
                            for next_m in re.finditer(r"(?:state|current_state)\s*=\s*([A-Za-z0-9_]+)", c_body):
                                target_state = next_m.group(1)
                                if target_state in members:
                                    pair = (c_label, target_state)
                                    if pair not in seen_trans:
                                        seen_trans.add(pair)
                                        transitions.append(pair)
                                        
            if transitions:
                mm_lines = ["stateDiagram-v2"]
                mm_lines.append(f"    [*] --> {members[0]}")
                for src, dst in transitions:
                    mm_lines.append(f"    {src} --> {dst}")
                mermaid_str = "\n".join(mm_lines)
            else:
                mm_lines = ["stateDiagram-v2"]
                mm_lines.append(f"    [*] --> {members[0] if members else 'Init'}")
                for i in range(len(members) - 1):
                    mm_lines.append(f"    {members[i]} --> {members[i+1]}")
                mermaid_str = "\n".join(mm_lines)

            state_machines.append({
                "id": safe_id(t["name"].lower()),
                "title": f"{t['name']} Machine",
                "description": f"State machine derived from {t['name']} and switch-case transitions.",
                "states": members,
                "transitions": [{"from": s, "to": d} for s, d in transitions],
                "source": "scanner",
                "mermaid": mermaid_str
            })
            
    if not state_machines:
        state_machines.append({
            "id": "device-lifecycle",
            "title": "Device Lifecycle",
            "description": "Generic device lifecycle state machine.",
            "states": ["Boot", "Running", "Sleep"],
            "transitions": [{"from": "Boot", "to": "Running"}, {"from": "Running", "to": "Sleep"}, {"from": "Sleep", "to": "Running"}],
            "source": "generated",
            "mermaid": "stateDiagram-v2\n    [*] --> Boot\n    Boot --> Running\n    Running --> Sleep\n    Sleep --> Running"
        })
    return state_machines

# --- 14. Sequences & Diagrams ---
def scan_sequence_diagrams(functions):
    main_func = next((f for f in functions if f["name"] == "main"), None)
    if main_func and main_func["callees"]:
        lines = ["sequenceDiagram", "    autonumber", "    actor Hardware", "    Hardware->>main: Reset Handler"]
        for callee in main_func["callees"]:
            lines.append(f"    main->>{callee}: {callee}()")
            sub_callees = next((f["callees"] for f in functions if f["name"] == callee), [])
            for sub in sub_callees[:3]:
                lines.append(f"    {callee}->>{sub}: {sub}()")
        mermaid_str = "\n".join(lines)
    else:
        mermaid_str = "sequenceDiagram\n    Reset->>Startup: initialize\n    Startup->>Application: start"

    return [{
        "id": "startup",
        "title": "Firmware Startup",
        "description": "Boot and initialization sequence derived from main() call hierarchy.",
        "source": "scanner",
        "mermaid": mermaid_str
    }]

def scan_dependencies(modules_data, components_data, functions):
    # Component-to-component dependencies
    func_to_comp = {f["name"]: f["component"] for f in functions}
    comp_deps = {}
    
    for f in functions:
        src_comp = f["component"]
        for callee in f["callees"]:
            dst_comp = func_to_comp.get(callee)
            if dst_comp and dst_comp != src_comp:
                key = (src_comp, dst_comp)
                comp_deps.setdefault(key, []).append(callee)

    edges = []
    for (src, dst), via in comp_deps.items():
        edges.append({
            "from": src,
            "to": dst,
            "via": sorted(set(via))
        })
        
    mermaid_lines = ["flowchart TD"]
    for e in edges:
        labels = ", ".join(e["via"][:2])
        mermaid_lines.append(f"    {safe_id(e['from'])}[{e['from']}] -->|{labels}| {safe_id(e['to'])}[{e['to']}]")
        
    mermaid_str = "\n".join(mermaid_lines) if edges else "flowchart TD\n    none[No cross-component calls]"
    return {"edges": edges, "mermaid": mermaid_str}

def scan_diagrams(types, modules_data, functions):
    classes = "classDiagram\n" + "\n".join(f"    class {safe_id(t['name'])} {{\n        <<{t['kind']}>>\n        +{t['role'][:60]}\n    }}" for t in types[:40])
    
    return {
        "classDiagrams": [{
            "id": "user-defined-types",
            "title": "User-Defined Types",
            "description": "Project-defined types and roles.",
            "source": "generated",
            "mermaid": classes
        }],
        "sequenceDiagrams": scan_sequence_diagrams(functions),
        "interactionDiagrams": [{
            "id": "components",
            "title": "Firmware Components",
            "description": "Detected module boundaries.",
            "source": "generated",
            "mermaid": "flowchart LR\n" + "\n".join(f"    {safe_id(m['id'])}[{m['name']}]" for m in modules_data[:30])
        }],
        "stateMachines": scan_state_machines([], None, types),
        "flowCharts": [{
            "id": "startup",
            "title": "Firmware Startup",
            "description": "Generic startup flow.",
            "source": "generated",
            "mermaid": "flowchart TD\n    Reset --> Init\n    Init --> Main"
        }]
    }

# --- 15. Pipelines & Flow ---
def scan_pipelines(modules_data, types_data):
    if not modules_data:
        return []
    stages = []
    for module in modules_data[:8]:
        type_ref = module.get("dataTypes", [{}])[0].get("id") if module.get("dataTypes") else None
        stages.append({
            "id": safe_id(module["id"]).lower(),
            "name": module["name"],
            "component": module["id"],
            "inputType": None,
            "outputType": type_ref,
            "objectLifetime": "module-defined",
            "ownership": "module-owned"
        })
    edges = [{"from": stages[idx]["id"], "to": stages[idx + 1]["id"], "label": "data flow"} for idx in range(len(stages) - 1)]
    mermaid = "flowchart LR\n" + "\n".join(f"    {safe_id(s['id'])}[{s['name']}]" for s in stages)
    if edges:
        mermaid += "\n" + "\n".join(f"    {e['from']} -->|{e['label']}| {e['to']}" for e in edges)
    return [{
        "id": "firmware-data-flow",
        "name": "Firmware Data Flow",
        "description": "Detected flow between firmware modules.",
        "stages": stages,
        "edges": edges,
        "mermaid": mermaid
    }]

# --- 16. Per-File Index & Symbol Index ---
def build_file_index(records, root, functions, types, macros, objects_data):
    file_map = {}
    for path, content in records:
        if path.suffix not in SRC_EXTENSIONS:
            continue
        r_path = rel(path, root)
        parts = Path(r_path).parts
        mod = parts[1] if len(parts) > 2 and parts[0] in {"src", "app", "lib", "components"} else parts[0] if len(parts) > 1 else "firmware"
        file_map[r_path] = {
            "path": r_path,
            "language": "Rust" if path.suffix == ".rs" else "C/C++",
            "lines": len(content.splitlines()),
            "functions": [],
            "types": [],
            "macros": [],
            "globals": [],
            "module": mod
        }
        
    for f in functions:
        if f["file"] in file_map:
            file_map[f["file"]]["functions"].append(f["name"])
    for t in types:
        for tf in t.get("files", []):
            if tf["path"] in file_map:
                file_map[tf["path"]]["types"].append(t["name"])
    for m in macros:
        if m["file"] in file_map:
            file_map[m["file"]]["macros"].append(m["name"])
    for o in objects_data:
        for of in o.get("files", []):
            if of["path"] in file_map:
                file_map[of["path"]]["globals"].append(o["name"])

    for f_info in file_map.values():
        f_info["functions"] = sorted(set(f_info["functions"]))
        f_info["types"] = sorted(set(f_info["types"]))
        f_info["macros"] = sorted(set(f_info["macros"]))
        f_info["globals"] = sorted(set(f_info["globals"]))

    return sorted(file_map.values(), key=lambda x: x["path"])

def build_symbol_index(functions, types, macros, objects_data):
    symbols = []
    for f in functions:
        symbols.append({
            "name": f["name"],
            "kind": "function",
            "file": f["file"],
            "line": f["line"],
            "detail": f["signature"]
        })
    for t in types:
        first_file = t["files"][0]["path"] if t.get("files") else ""
        first_line = t["files"][0].get("line", 1) if t.get("files") else 1
        symbols.append({
            "name": t["name"],
            "kind": t["kind"],
            "file": first_file,
            "line": first_line,
            "detail": t["role"]
        })
    for m in macros:
        symbols.append({
            "name": m["name"],
            "kind": "macro",
            "file": m["file"],
            "line": m["line"],
            "detail": m.get("value") or ""
        })
    for o in objects_data:
        first_file = o["files"][0]["path"] if o.get("files") else ""
        first_line = o["files"][0].get("line", 1) if o.get("files") else 1
        symbols.append({
            "name": o["name"],
            "kind": "object",
            "file": first_file,
            "line": first_line,
            "detail": f"{o['kind']} instance ({o['role']})"
        })
    symbols.sort(key=lambda s: s["name"].lower())
    return symbols

def link_type_usage(types_data, modules_data, components_data):
    for item in types_data:
        module_ids = [m["id"] for m in modules_data if any(ref.get("id") == item["id"] for ref in m.get("dataTypes", []))]
        component_ids = [c["id"] for c in components_data if any(ref.get("id") == item["id"] for ref in c.get("dataTypes", []))]
        item["usedByModules"] = [{"id": mid, "role": "uses"} for mid in module_ids]
        item["usedByComponents"] = [{"id": cid, "role": "uses"} for cid in component_ids]
        item["usage"] = unique(item.get("usage", []) +
                              [{"role": "consumes", "module": mid, "description": "Referenced by module."} for mid in module_ids] +
                              [{"role": "consumes", "component": cid, "description": "Referenced by component."} for cid in component_ids])

# --- 17. Main Orchestration ---
def init_architecture(target_root=None):
    root = Path(target_root or os.getcwd()).resolve()
    records = [(p, text(p)) for p in files(root)]
    
    project_info = detect_project_type(records, root)
    root_readme, all_readmes = scan_readmes(records, root)
    types = scan_data_types(records, root)
    functions, call_graph = scan_functions(records, root, types)
    macros = scan_macros(records, root)
    modules_data = scan_modules(records, root, types, functions)
    components_data = scan_components(modules_data, functions, records, root)
    link_type_usage(types, modules_data, components_data)
    objects_data = scan_objects(records, root, types)
    state_machines = scan_state_machines(records, root, types)
    
    diagrams_data = scan_diagrams(types, modules_data, functions)
    diagrams_data["stateMachines"] = state_machines
    
    dependencies_data = scan_dependencies(modules_data, components_data, functions)
    file_index = build_file_index(records, root, functions, types, macros, objects_data)
    symbol_index = build_symbol_index(functions, types, macros, objects_data)
    tools_data = scan_tools(records, root)
    
    paragraphs = [re.sub(r"[`*_#]", "", part).strip() for part in root_readme.get("content", "").split("\n\n") if part.strip() and not part.lstrip().startswith("#")]
    summary = paragraphs[0][:1000] if paragraphs else "Embedded firmware architecture"
    brief_data = {
        "purpose": summary[:300],
        "systemType": project_info["projectType"],
        "architectureTopology": project_info["topology"],
        "summary": summary,
        "operatingEnvironment": [],
        "primaryResponsibilities": [],
        "constraints": [],
        "safetyAndReliability": [],
        "powerRequirements": [],
        "timingRequirements": [],
        "documentationStatus": "generated",
        "sourceFiles": [root_readme["path"]] if root_readme["exists"] else []
    }

    data = {
        "meta": {
            "displayName": root.name.replace("-", " ").replace("_", " ").title(),
            "version": "1.0.0",
            "description": "Embedded firmware architecture map.",
            "generatedAt": datetime.date.today().isoformat(),
            **project_info,
            "languages": sorted({"Rust" if p.suffix == ".rs" else "C/C++" for p, _ in records if p.suffix in SRC_EXTENSIONS}),
            "buildSystems": [project_info["primaryType"]]
        },
        "readme": root_readme,
        "readmes": all_readmes,
        "brief": brief_data,
        "hardware": scan_hardware(records, root, project_info),
        "configurations": scan_configurations(records, root),
        "memoryLayout": scan_memory_layout(records, root),
        "modules": modules_data,
        "components": components_data,
        "dataTypes": types,
        "objects": objects_data,
        "diagrams": diagrams_data,
        "dataPipelines": scan_pipelines(modules_data, types),
        "build": scan_build(records, root, project_info),
        "functions": functions,
        "macros": macros,
        "callGraph": call_graph,
        "fileIndex": file_index,
        "symbolIndex": symbol_index,
        "dependencies": dependencies_data,
        "tools": tools_data
    }

    override = root / "docs" / "architecture" / "embedded-overrides.json"
    if override.is_file():
        try:
            extra = json.loads(text(override))
            for key, value in extra.items():
                if isinstance(value, list) and isinstance(data.get(key), list) and all(isinstance(x, dict) and "id" in x for x in value + data[key]):
                    data[key] = by_id(data[key] + value)
                elif isinstance(value, dict) and isinstance(data.get(key), dict):
                    data[key].update(value)
                else:
                    data[key] = value
        except json.JSONDecodeError:
            data.setdefault("warnings", []).append({"type": "invalid-override", "file": str(override)})

    return data

# --- 18. HTML Dashboard Rendering ---
def inline(val):
    val = html.escape(val, quote=True)
    val = re.sub(r"`([^`]+)`", r"<code>\1</code>", val)
    val = re.sub(r"\*\*([^*]+)\*\*", r"<strong>\1</strong>", val)
    val = re.sub(r"\*([^*]+)\*", r"<em>\1</em>", val)
    return re.sub(r"\[([^]]+)\]\((https?://[^)]+)\)", r'<a href="\2" rel="noopener">\1</a>', val)

def markdown_to_html(val):
    if not val: return '<p class="muted">No README content found.</p>'
    output, code, inside = [], [], False
    for line in val.splitlines():
        if line.startswith("```"):
            if inside:
                output.append("<pre><code>" + html.escape("\n".join(code)) + "</code></pre>")
                code = []
            inside = not inside
            continue
        if inside:
            code.append(line)
            continue
        match = re.match(r"^(#{1,6})\s+(.+)$", line)
        if match:
            output.append(f"<h{len(match.group(1))}>{inline(match.group(2))}</h{len(match.group(1))}>")
        elif re.match(r"^[-*+]\s+", line):
            output.append("<li>" + inline(re.sub(r"^[-*+]\s+", "", line)) + "</li>")
        elif line.startswith("> "):
            output.append("<blockquote>" + inline(line[2:]) + "</blockquote>")
        elif line.strip():
            output.append("<p>" + inline(line) + "</p>")
    if inside:
        output.append("<pre><code>" + html.escape("\n".join(code)) + "</code></pre>")
    return "\n".join(output)

def val_str(data):
    return html.escape(json.dumps(data, indent=2) if isinstance(data, (dict, list)) else "" if data is None else str(data))

def file_list(items):
    if not items: return '<p class="muted">No source files detected.</p>'
    return "<ul>" + "".join(f"<li><code>{html.escape(str(item.get('path', item)))}</code> <span>{html.escape(str(item.get('role', 'source')))}</span>{(' line ' + str(item['line'])) if isinstance(item, dict) and item.get('line') else ''}</li>" for item in items) + "</ul>"

def card(title, body):
    return f'<article class="card"><h3>{html.escape(str(title))}</h3>{body}</article>'

def render(data):
    meta = data["meta"]
    readme_data = data["readme"]
    readmes = data.get("readmes", [])
    
    nav = [
        ("brief", "Brief"),
        ("readme", "Project README"),
        ("hardware", "Hardware"),
        ("configurations", "Configurations"),
        ("memory-layout", "Memory Layout"),
        ("modules-components", "Modules & Components"),
        ("dependencies", "Dependencies"),
        ("files", "Files"),
        ("functions", "Functions"),
        ("macros", "Macros"),
        ("call-graph", "Call Graph"),
        ("tools", "Tools & Scripts"),
        ("class-diagrams", "Class Diagrams"),
        ("sequence-diagrams", "Sequence Diagrams"),
        ("interaction-diagrams", "Interaction Diagrams"),
        ("state-machines", "State Machines"),
        ("flow-charts", "Flow Charts"),
        ("data-pipelines", "Data Pipelines"),
        ("build", "Build"),
        ("symbol-index", "Symbol Index")
    ]
    
    nav_html = "".join(f'<button class="nav-btn" onclick="showTab(\'{key}\',this)">{html.escape(label)}</button>' for key, label in nav)
    def section(ident, title, body): return f'<section class="section" id="sec-{ident}"><h2>{html.escape(title)}</h2>{body}</section>'

    brief_body = card("Purpose", f"<p>{html.escape(data['brief'].get('summary', ''))}</p>") + card("Architecture Topology", f"<pre>{val_str({'primaryType': meta.get('primaryType'), 'systemType': data['brief'].get('systemType'), 'topology': data['brief'].get('architectureTopology'), 'markers': meta.get('markers', [])})}</pre>")

    readmes_table = '<div class="card"><h3>Project Documentation Index</h3><table class="data-table"><thead><tr><th>File</th><th>Directory</th><th>Summary</th></tr></thead><tbody>'
    for r in readmes:
        readmes_table += f'<tr><td><code>{html.escape(r["path"])}</code></td><td>{html.escape(r["directory"])}</td><td>{html.escape(r["summary"])}</td></tr>'
    readmes_table += '</tbody></table></div>'
    
    readme_body = readmes_table + f'<div class="toolbar"><code>{html.escape(readme_data.get("path", "README.md"))}</code><button onclick="copyReadme()">Copy Markdown</button></div><article class="readme">{markdown_to_html(readme_data.get("content", ""))}</article><details><summary>View Markdown source</summary><pre id="readme-source">{html.escape(readme_data.get("content", ""))}</pre></details>'

    hw = data["hardware"]
    hw_body = (
        card("Target MCU & Architecture", f"<pre>{val_str(hw.get('target', {}))}</pre>") +
        card("Board", f"<pre>{val_str(hw.get('board', {}))}</pre>") +
        card("Clock Configuration", f"<pre>{val_str(hw.get('clockConfig', {}))}</pre>") +
        card("Peripherals", "<div class=\"grid\">" + "".join(card(p.get("name", p.get("id")), f"<p><b>Type:</b> {html.escape(p.get('type',''))}</p><p class='muted'>{html.escape(p.get('source',''))}</p>") for p in hw.get("peripherals", [])) + "</div>") +
        card("Pin Mappings", f"<pre>{val_str(hw.get('pinMappings', []))}</pre>") +
        card("Hardware Source Files", file_list([{"path": x, "role": "hardware config"} for x in hw.get("sourceFiles", [])]))
    )

    cfg = data["configurations"]
    cfg_cats_html = ""
    for cat, p_list in cfg.get("parametersByCategory", {}).items():
        rows = "".join(f"<tr><td><code>{html.escape(p['name'])}</code></td><td>{html.escape(str(p['value']) if p['value'] is not None else '')}</td><td><code>{html.escape(p['file'])}:{p.get('line','')}</code></td></tr>" for p in p_list)
        cfg_cats_html += f'<div class="card"><h3>Category: {html.escape(cat.title())} ({len(p_list)})</h3><table class="data-table"><thead><tr><th>Parameter</th><th>Value</th><th>Source</th></tr></thead><tbody>{rows}</tbody></table></div>'
        
    configurations_body = (
        card("Build Profiles", f"<pre>{val_str(cfg.get('buildProfiles', []))}</pre>") +
        cfg_cats_html +
        card("Configuration Sources", file_list([{"path": x, "role": "configuration"} for x in cfg.get("configurationSources", [])]))
    )

    mem = data["memoryLayout"]
    mem_body = (
        card("Memory Regions", f"<pre>{val_str(mem.get('regions', []))}</pre>") +
        card("Sections", f"<pre>{val_str(mem.get('sections', []))}</pre>") +
        card("Linker / Map Files", file_list([{"path": x, "role": "linker/map file"} for x in mem.get("linkerScripts", []) + mem.get("mapFiles", [])]))
    )

    module_body = (
        "<h3>Modules</h3><div class=\"grid\">" +
        "".join(card(m["name"], f"<p><b>Role:</b> {html.escape(m.get('role', ''))}</p>{file_list(m.get('files', []))}") for m in data["modules"]) +
        "</div><h3>Components</h3><div class=\"grid\">" +
        "".join(card(c["name"], f"<p><b>Role:</b> {html.escape(c.get('role', ''))}</p><p><b>Provides:</b> <code>{html.escape(', '.join(c.get('provides', [])) or 'none')}</code></p><p><b>Consumes:</b> <code>{html.escape(', '.join(c.get('consumes', [])) or 'none')}</code></p>{file_list(c.get('files', []))}") for c in data["components"]) +
        "</div><h3>User-Defined Data Types</h3><div class=\"grid\">" +
        "".join(card(t["name"], f"<p><b>Kind:</b> {html.escape(t.get('kind',''))}</p><p><b>Role:</b> {html.escape(t.get('role', ''))}</p><p><b>Fields:</b> {html.escape(', '.join(f['name'] for f in t.get('fields', [])) or 'none')}</p>{file_list(t.get('files', []))}") for t in data["dataTypes"]) +
        "</div><h3>Objects & Storage</h3><div class=\"grid\">" +
        "".join(card(o["name"], f"<p><b>Kind:</b> {html.escape(o.get('kind',''))}</p><p><b>Role:</b> {html.escape(o.get('role', ''))}</p><pre>{val_str({'storage': o.get('storage'), 'lifetime': o.get('lifetime'), 'ownership': o.get('ownership')})}</pre>{file_list(o.get('files', []))}") for o in data["objects"]) +
        "</div>"
    )

    dep = data.get("dependencies", {})
    dependencies_body = (
        card("Inter-Component Call Graph", f"<pre class=\"mermaid\">{html.escape(dep.get('mermaid', ''))}</pre>") +
        card("Dependency Edges", f"<pre>{val_str(dep.get('edges', []))}</pre>")
    )

    files_rows = "".join(f"<tr><td><code>{html.escape(f['path'])}</code></td><td>{html.escape(f['language'])}</td><td>{f['lines']}</td><td><code>{html.escape(', '.join(f['functions']))}</code></td><td><code>{html.escape(', '.join(f['types']))}</code></td><td><code>{html.escape(', '.join(f['macros']))}</code></td></tr>" for f in data.get("fileIndex", []))
    files_body = f'<div class="card"><table class="data-table"><thead><tr><th>Path</th><th>Lang</th><th>Lines</th><th>Functions</th><th>Types</th><th>Macros</th></tr></thead><tbody>{files_rows}</tbody></table></div>'

    func_cards = "".join(card(f["name"], f"<p><code>{html.escape(f['signature'])}</code></p><p><b>File:</b> <code>{html.escape(f['file'])}:{f['line']}</code> ({html.escape(f['visibility'])})</p><p><b>Callers:</b> <code>{html.escape(', '.join(f.get('callers', [])) or 'none')}</code></p><p><b>Callees:</b> <code>{html.escape(', '.join(f.get('callees', [])) or 'none')}</code></p>") for f in data.get("functions", []))
    functions_body = f'<div class="grid">{func_cards}</div>' if func_cards else '<p class="muted">No functions detected.</p>'

    macro_rows = "".join(f"<tr><td><code>{html.escape(m['name'])}</code></td><td><code>{html.escape(str(m['value']) if m['value'] is not None else '')}</code></td><td><span class='badge'>{html.escape(m['category'])}</span></td><td><code>{html.escape(m['file'])}:{m['line']}</code></td></tr>" for m in data.get("macros", []))
    macros_body = f'<div class="card"><table class="data-table"><thead><tr><th>Macro</th><th>Value</th><th>Category</th><th>Source</th></tr></thead><tbody>{macro_rows}</tbody></table></div>'

    cg = data.get("callGraph", {})
    call_graph_body = card("Function Call Relationships", f"<pre class=\"mermaid\">{html.escape(cg.get('mermaid', ''))}</pre>") + card("Call Edges", f"<pre>{val_str(cg.get('edges', []))}</pre>")

    tools = data.get("tools", [])
    mfs = data["build"].get("makefiles", [])
    tools_rows = "".join(f"<tr><td><code>{html.escape(t['name'])}</code></td><td><code>{html.escape(t['path'])}</code></td><td>{html.escape(t['type'])}</td><td><span class='badge'>{html.escape(t['category'])}</span></td></tr>" for t in tools)
    tools_table = f'<table class="data-table"><thead><tr><th>Name</th><th>Path</th><th>Type</th><th>Category</th></tr></thead><tbody>{tools_rows}</tbody></table>' if tools else '<p class="muted">No utility scripts detected.</p>'
    
    mf_cards = ""
    for mf in mfs:
        tgt_rows = "".join(f"<tr><td><code>{html.escape(tgt['name'])}</code></td><td><span class='badge'>{html.escape(tgt['category'])}</span></td><td><pre>{html.escape(tgt['recipe'])}</pre></td></tr>" for tgt in mf["targets"])
        mf_cards += card(f"Makefile: {mf['path']} (Role: {mf['role']})", f"<table class=\"data-table\"><thead><tr><th>Target</th><th>Category</th><th>Recipe</th></tr></thead><tbody>{tgt_rows}</tbody></table>")
        
    tools_body = card("Project Helper Tools & Scripts", tools_table) + mf_cards

    sections = [
        section("brief", "Brief", brief_body),
        section("readme", "Project README", readme_body),
        section("hardware", "Hardware", hw_body),
        section("configurations", "Configurations", configurations_body),
        section("memory-layout", "Memory Layout", mem_body),
        section("modules-components", "Modules & Components", module_body),
        section("dependencies", "Dependencies", dependencies_body),
        section("files", "Files", files_body),
        section("functions", "Functions", functions_body),
        section("macros", "Macros", macros_body),
        section("call-graph", "Call Graph", call_graph_body),
        section("tools", "Tools & Scripts", tools_body)
    ]

    diagram_ids = {
        "classDiagrams": ("class-diagrams", "Class Diagrams"),
        "sequenceDiagrams": ("sequence-diagrams", "Sequence Diagrams"),
        "interactionDiagrams": ("interaction-diagrams", "Interaction Diagrams"),
        "stateMachines": ("state-machines", "State Machines"),
        "flowCharts": ("flow-charts", "Flow Charts")
    }
    for key, (ident, title) in diagram_ids.items():
        body = "".join(card(x.get("title", "Diagram"), f"<p>{html.escape(x.get('description', ''))}</p><pre class=\"mermaid\">{html.escape(x.get('mermaid', ''))}</pre>") for x in data["diagrams"].get(key, [])) or '<p class="muted">No diagrams detected.</p>'
        sections.append(section(ident, title, body))

    sections.append(section("data-pipelines", "Data Pipelines", card("Pipelines", f"<pre class=\"mermaid\">{html.escape(data.get('dataPipelines', [{}])[0].get('mermaid', ''))}</pre><pre>{val_str(data.get('dataPipelines', []))}</pre>")))
    sections.append(section("build", "Build", card("Build System & Toolchain", f"<pre>{val_str(data['build'])}</pre>")))

    sym_rows = "".join(f"<tr><td><code>{html.escape(s['name'])}</code></td><td><span class='badge'>{html.escape(s['kind'])}</span></td><td><code>{html.escape(s['file'])}:{s['line']}</code></td><td>{html.escape(str(s['detail']))}</td></tr>" for s in data.get("symbolIndex", []))
    symbol_body = f'<div class="card"><input type="text" id="sym-filter" placeholder="Filter symbols..." onkeyup="filterSymbols()" style="width:100%;padding:8px;margin-bottom:12px;background:var(--panel2);border:1px solid var(--border);color:var(--text);border-radius:6px;"><table class="data-table" id="sym-table"><thead><tr><th>Symbol</th><th>Kind</th><th>Location</th><th>Detail</th></tr></thead><tbody>{sym_rows}</tbody></table></div>'
    sections.append(section("symbol-index", "Symbol Index", symbol_body))

    css = """
:root{--bg:#0d1117;--panel:#161b22;--panel2:#21262d;--border:#30363d;--text:#e6edf3;--muted:#8b949e;--accent:#58a6ff}
*{box-sizing:border-box}
body{margin:0;background:var(--bg);color:var(--text);font:14px system-ui,sans-serif}
header{position:sticky;top:0;z-index:2;background:var(--panel);border-bottom:1px solid var(--border);padding:18px 28px}
header h1{margin:0 0 4px}header p{margin:0;color:var(--muted)}
.layout{display:flex;min-height:calc(100vh - 78px)}
aside{width:260px;flex:none;background:var(--panel);border-right:1px solid var(--border);padding:16px;position:fixed;top:78px;bottom:0;overflow:auto}
main{margin-left:260px;padding:28px;max-width:1500px;width:calc(100% - 260px)}
.nav-btn{display:block;width:100%;text-align:left;background:none;border:1px solid transparent;color:var(--muted);padding:9px 12px;border-radius:7px;margin:2px 0;cursor:pointer;font-size:13px}
.nav-btn:hover,.nav-btn.active{background:var(--panel2);border-color:var(--accent);color:var(--text)}
.section{display:none}.section.active{display:block}
h2{border-bottom:1px solid var(--border);padding-bottom:10px}h3{color:var(--accent);margin-top:0}
.grid{display:grid;grid-template-columns:repeat(auto-fit,minmax(300px,1fr));gap:16px}
.card{background:var(--panel);border:1px solid var(--border);border-radius:10px;padding:18px;margin:0 0 16px;overflow:auto}
pre{background:#090c10;border:1px solid var(--border);padding:14px;border-radius:7px;overflow:auto;white-space:pre-wrap;word-break:break-word}
code{color:#9cdcfe}.muted{color:var(--muted)}
.files span{color:var(--muted);margin-left:8px}
.toolbar{display:flex;gap:12px;align-items:center;margin-bottom:14px}
button{color:var(--text);background:var(--panel2);border:1px solid var(--border);border-radius:6px;padding:7px 10px;cursor:pointer}
.readme{background:var(--panel);border:1px solid var(--border);border-radius:10px;padding:24px;line-height:1.6}
.readme img{max-width:100%}
.data-table{width:100%;border-collapse:collapse;margin-top:8px}
.data-table th,.data-table td{border:1px solid var(--border);padding:8px 12px;text-align:left}
.data-table th{background:var(--panel2);color:var(--accent)}
.badge{background:var(--panel2);border:1px solid var(--border);padding:2px 6px;border-radius:4px;font-size:11px;color:var(--accent)}
@media(max-width:750px){aside{position:static;width:100%;border-right:0;border-bottom:1px solid var(--border);display:flex;flex-wrap:wrap;gap:4px}.layout{display:block}main{margin:0;width:100%;padding:16px}.nav-btn{width:auto}}
"""
    script = """
function showTab(id,b){
  document.querySelectorAll('.section').forEach(x=>x.classList.remove('active'));
  var x=document.getElementById('sec-'+id);
  if(x)x.classList.add('active');
  document.querySelectorAll('.nav-btn').forEach(x=>x.classList.remove('active'));
  if(b)b.classList.add('active');
  if(window.mermaid)mermaid.run();
}
function copyReadme(){
  navigator.clipboard.writeText(document.getElementById('readme-source').textContent);
}
function filterSymbols(){
  var input=document.getElementById('sym-filter');
  var filter=input.value.toUpperCase();
  var table=document.getElementById('sym-table');
  var tr=table.getElementsByTagName('tr');
  for(var i=1;i<tr.length;i++){
    var txt=tr[i].textContent||tr[i].innerText;
    tr[i].style.display=txt.toUpperCase().indexOf(filter)>-1?'':'none';
  }
}
document.querySelector('.section').classList.add('active');
document.querySelector('.nav-btn').classList.add('active');
if(window.mermaid)mermaid.initialize({startOnLoad:false,theme:'dark'});
"""
    return (
        "<!doctype html><html lang=\"en\"><head><meta charset=\"utf-8\"><meta name=\"viewport\" content=\"width=device-width,initial-scale=1\">"
        f"<title>{html.escape(meta.get('displayName', 'Embedded Architecture'))} - Architecture</title>"
        "<script src=\"https://cdn.jsdelivr.net/npm/mermaid@10/dist/mermaid.min.js\"></script>"
        f"<style>{css}</style></head><body><header>"
        f"<h1>{html.escape(meta.get('displayName', 'Embedded Architecture'))}</h1>"
        f"<p>Embedded architecture map | {html.escape(meta.get('primaryType', 'unknown'))} ({html.escape(meta.get('projectType', 'unknown'))}) | Generated {html.escape(meta.get('generatedAt', ''))}</p>"
        f"</header><div class=\"layout\"><aside>{nav_html}</aside><main>" + "\n".join(sections) + f"</main></div><script>{script}</script></body></html>"
    )

def main():
    target = next((Path(arg).resolve() for arg in sys.argv[1:] if not arg.startswith("--") and Path(arg).exists()), Path.cwd().resolve())
    arch = target if target.name == "architecture" else target / "docs" / "architecture"
    arch.mkdir(parents=True, exist_ok=True)
    data = init_architecture(str(target))
    (arch / "architecture.json").write_text(json.dumps(data, indent=2), encoding="utf-8")
    (arch / "architecture.html").write_text(render(data), encoding="utf-8")
    print(f"[arch-wiki-es] Generated embedded architecture files in {arch}")

if __name__ == "__main__":
    main()
