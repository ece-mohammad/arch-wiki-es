# arch-wiki-es

`arch-wiki-es` is an embedded firmware architecture and symbol documentation skill for AI coding assistants. It is a specialized fork of `arch-wiki` geared specifically towards embedded systems, microcontrollers, and firmware codebases. It bridges high-level firmware architecture mapping with Doxygen-style symbol extraction, call graphs, hardware/configuration indexing, and 1-click AI senior developer analysis prompts.

It scans an embedded firmware repository and generates:

- `docs/architecture/architecture.json`: Machine-readable architecture metadata, symbol catalogs, and configuration parameters.
- `docs/architecture/architecture.html`: Interactive architecture dashboard with project documentation, searchable symbol index, embedded Mermaid diagrams, and 1-click AI analysis prompts.

`arch-wiki-es` is dedicated exclusively to bare-metal, RTOS, and embedded Linux firmware, providing structured insight into hardware peripherals, memory maps, clock trees, state machines, call graphs, and build systems.

## Key Features

- **Doxygen + Architecture Hybrid**: Combines high-level system topology with per-symbol function signatures, callers, callees, macros, and types.
- **Incremental Synchronization (`--sync`)**: Quickly rescan after modifying drivers, functions, or configurations to keep living documentation in sync.
- **Interactive Senior Embedded Developer Prompts**: Click on any function, driver component, or state machine in the dashboard to generate a custom prompt for your AI assistant (Antigravity, Claude, ChatGPT, Cursor) with full call hierarchy, register context, and safety constraints.
- **.gitignore Aware**: Automatically parses root and nested `.gitignore` files to prune build directories, generated files, and ignored headers during scanning.
- **Hardware-Aware Scanning**: Extracts MCU targets, frequencies, pin mappings, and peripheral registers from STM32CubeIDE, STM32CubeMX, PlatformIO, Zephyr, ESP-IDF, Arduino, and Make/CMake files.
- **Source-Derived State Machines & Sequences**: Generates interactive Mermaid diagrams directly from state enums, `switch`/`case` transitions, and `main()` boot call trees.
- **Categorized Configuration Parameters**: Automatically classifies `#define` constants and flags into `clock`, `peripheral`, `memory`, `communication`, `rtos`, `power`, `debug`, and `feature` categories.
- **Zero Third-Party Dependencies**: Runs on standard Python 3 standard library.

## Documented Architecture

The generated documentation contains 20 core architectural sections:

0. **Brief & Topology Overview**: System purpose, primary framework, RTOS/bare-metal classification, and MCU topology.
1. **Project README & Multi-README Index**: Embedded root README alongside an indexed catalog of all submodule and driver READMEs found in the project.
2. **Hardware & Peripherals Configuration**: Detected MCU, family, board, clock tree configuration, active peripherals (UART, SPI, I2C, CAN, ADC, Timers, DMA, GPIO, USB), and pin mappings.
3. **Categorized Configuration Parameters**: Preprocessor defines and compile flags grouped by functional category (`clock`, `peripheral`, `memory`, `communication`, `rtos`, `power`, `debug`, `feature`, `compiler`, `application`) with source file and line attribution.
4. **Memory Layout & Linker Map**: Memory regions (FLASH, RAM, EEPROM), origins, lengths, section mappings (`.text`, `.rodata`, `.data`, `.bss`, `.noinit`), stack/heap sizes, and linker scripts.
5. **Modules & Components**: Logical subsystems, concrete source units, public API declarations, and `provides`/`consumes` interfaces.
6. **Dependencies & Inter-Component Integration**: Cross-component call graphs and interface bindings.
7. **Files & Per-File Catalog**: Source file catalog listing functions, types, macros, globals, and line counts per file.
8. **Functions & Signatures**: Function signatures, return types, parameters, visibility (`public`/`private`), callers, and callees.
9. **Macros & Preprocessor Definitions**: Constants and parameterized macros with values, category, and source location.
10. **Call Graph**: Function call hierarchy visualized via interactive Mermaid diagrams.
11. **Tools & Scripts**: Project utility scripts (`.sh`, `.bat`, `.py`), OpenOCD/debug configs, task runners, and Makefile target role analysis (`primary`, `utility`, `wrapper`).
12. **Class Diagrams**: User-defined structs, unions, enums, and class relationships.
13. **Sequence Diagrams**: Firmware startup and hardware initialization call hierarchy derived from `main()`.
14. **Interaction Diagrams**: Subsystem boundaries and component communication channels.
15. **State Machines**: Source-derived finite state machines extracted from state enums and `switch`/`case` transition logic.
16. **Flow Charts**: Firmware execution loops, interrupt service routines, and reset flows.
17. **Data Pipelines**: Data flow between firmware modules with queue and buffer payload typing.
18. **Firmware Build & Toolchain**: Detected build system, toolchain target triple, build profiles, and flash/debug commands.
19. **Searchable Symbol Index**: Filterable index of all project functions, types, macros, and global objects.

## Supported Projects & Frameworks

The scanner automatically identifies project environments and tailors hardware and configuration extraction accordingly:

- **STM32CubeIDE & STM32CubeMX**: Parses `.ioc`, `.cproject`, `.project`, linker scripts, and HAL initialization code.
- **PlatformIO**: Parses `platformio.ini` environments, boards, frameworks, build flags, and library dependencies.
- **ESP-IDF**: Parses `sdkconfig`, `sdkconfig.defaults`, target chip definitions, and component manifests.
- **Zephyr RTOS**: Parses `west.yml`, `prj.conf`, Kconfig options, and device-tree overlays (`.dts`, `.overlay`).
- **FreeRTOS & RTOS Projects**: Parses `FreeRTOSConfig.h`, task creation calls, queues, and semaphores.
- **Arduino**: Parses `.ino` sketches, `boards.txt`, core libraries, and peripheral setup routines.
- **Bare-metal C/C++ (Make & CMake)**: Parses `Makefile` rules, `CMakeLists.txt`, toolchain flags, and GNU linker scripts (`.ld`).
- **Keil / MDK**: Parses `.uvprojx` project definitions and target device settings.
- **Rust Embedded**: Parses `Cargo.toml`, `.cargo/config.toml`, target architectures, and memory layouts.

## Installation & Uninstallation

The installer registers `SKILL.md` and the generator script with supported AI assistant skill environments:
- **Antigravity AI Agent** (`~/.gemini/antigravity/skills/arch-wiki-es` and `~/.gemini/config/skills/arch-wiki-es`)
- **Claude Code** (`~/.claude/skills/arch-wiki-es`)
- **Cursor AI** (`~/.cursor/skills/arch-wiki-es`)
- **Local Workspace** (`.skills/arch-wiki-es` and `.agents/skills/arch-wiki-es`)

### Method 1: NPX (Global Installer)

**Install:**

```bash
npx arch-wiki-es
```

**Uninstall:**

```bash
npx arch-wiki-es --uninstall
```

### Method 2: From Local Repository Clone

**Install:**

```bash
node bin/install.js
```
*(or `npm run install-skill`)*

**Uninstall:**

```bash
node bin/uninstall.js
```
*(or `npm run uninstall-skill`, or `node bin/install.js --uninstall`)*

### Method 3: Manual Removal (Per Assistant)

If you prefer to remove the skill manually from specific AI assistants:

- **Antigravity AI Agent**:
  - Linux/macOS:
    ```bash
    rm -rf ~/.gemini/antigravity/skills/arch-wiki-es ~/.gemini/config/skills/arch-wiki-es
    ```
  - Windows (PowerShell):
    ```powershell
    Remove-Item -Recurse -Force "$HOME\.gemini\antigravity\skills\arch-wiki-es", "$HOME\.gemini\config\skills\arch-wiki-es" -ErrorAction SilentlyContinue
    ```

- **Claude Code**:
  - Linux/macOS:
    ```bash
    rm -rf ~/.claude/skills/arch-wiki-es
    ```
  - Windows (PowerShell):
    ```powershell
    Remove-Item -Recurse -Force "$HOME\.claude\skills\arch-wiki-es" -ErrorAction SilentlyContinue
    ```

- **Cursor AI**:
  - Linux/macOS:
    ```bash
    rm -rf ~/.cursor/skills/arch-wiki-es
    ```
  - Windows (PowerShell):
    ```powershell
    Remove-Item -Recurse -Force "$HOME\.cursor\skills\arch-wiki-es" -ErrorAction SilentlyContinue
    ```

- **Project Workspace**:
  - Linux/macOS:
    ```bash
    rm -rf .skills/arch-wiki-es .agents/skills/arch-wiki-es
    ```
  - Windows (PowerShell):
    ```powershell
    Remove-Item -Recurse -Force ".skills\arch-wiki-es", ".agents\skills\arch-wiki-es" -ErrorAction SilentlyContinue
    ```

## Syncing After Codebase Changes

### First-Time Initialization

Run from your firmware repository:

```bash
python3 docs/architecture/build_html.py --init
```

### Incremental Synchronization

Whenever you add a driver, modify function signatures, update state machine transitions, or adjust linker scripts:

```bash
python3 docs/architecture/build_html.py --sync
```

To run against an external repository:

```bash
python3 /path/to/arch-wiki-es/templates/build_html.py --sync /path/to/firmware-project
```

The generator will scan the repository and update both `architecture.json` and `architecture.html`.

## Interactive AI Senior Developer Prompts

Inside `docs/architecture/architecture.html`:

- Every function in the **Functions** tab features an **AI Prompt** button.
- Every component in **Modules & Components** features an **AI Prompt** button.
- Every state machine in **State Machines** features an **AI Prompt** button.

Clicking the button opens an interactive modal preloaded with a structured prompt tailored for AI coding assistants:

```text
You are joining this project as a senior embedded firmware engineer.

Analyze this firmware function:
HAL_StatusTypeDef sensor_read(SensorReading* reading)
File: src/sensor.c:42 (public)
Module: sensors | Component: sensor
Callers: main, telemetry_task
Callees: i2c_read, sensor_calibrate

Use:
1. docs/architecture/architecture.json
2. arch-wiki-es documentation
3. the project source code and hardware configuration

Discover the actual implementation flow, hardware register interactions, and call hierarchy.

Analyze:
- Control flow, callers, callees, and hardware peripheral/register accesses
- Concurrency, ISR safety, reentrancy, and timing constraints
- Stack usage, buffer bounds, and error recovery

Generate:
1. Mermaid sequence diagram (execution and call flow)
2. Mermaid flowchart (logic branching and error recovery)
```

Click **Copy Prompt** (or direct copy on the card) to copy the prompt to your clipboard and paste it directly into your AI chat window.

## Manifest Sections

`architecture.json` contains these top-level sections:

| Section | Contents |
|---|---|
| `meta` | Primary project type, system type, topology, languages, detected markers, and generation date |
| `readme` | Embedded project root README content and source metadata |
| `readmes` | Multi-README index across all project directories with summary, path, and lines |
| `brief` | System purpose, architecture topology, constraints, and documentation status |
| `hardware` | MCU, board, clock configuration, peripherals, pin mappings, and power metadata |
| `configurations` | Build profiles, categorized parameters (`clock`, `peripheral`, `rtos`, `memory`, etc.), and feature flags |
| `memoryLayout` | Linker regions, sections, partitions, stack, heap, and map files |
| `modules` | Logical firmware subsystems, roles, files, tasks, and type usage |
| `components` | Concrete drivers, services, HALs, public APIs, provides, and consumes |
| `dataTypes` | Project-defined structs, enums (with members), unions, typedefs, and classes |
| `objects` | Created objects, storage, lifetime, ownership, and cleanup metadata |
| `diagrams` | Class, boot sequence, component interaction, source-derived state machines, and flow charts |
| `dataPipelines` | Detected data movement between firmware modules |
| `build` | Build system, toolchain, Makefile role analysis (primary/utility), targets, and commands |
| `functions` | Function definitions, signatures, return types, parameters, callers, and callees |
| `macros` | Preprocessor defines with values, category, parameters, file, and line |
| `callGraph` | Caller → callee call graph edges and Mermaid diagram |
| `fileIndex` | Per-file catalog of functions, types, macros, globals, and line counts |
| `symbolIndex` | Flat searchable/filterable index of all project symbols |
| `dependencies` | Inter-component/module call graph and dependencies |
| `tools` | Helper scripts, openocd configs, and task runner utilities categorized by task |

## Manual Overrides

For hardware specifications, safety constraints, or pin functions that cannot be deduced from source code alone, add an optional override file at:

```text
docs/architecture/embedded-overrides.json
```

Use it to supply board details, pin mappings, power budgets, memory partitions, or custom state machines. Overrides are merged into the generated data at scan time. An example format is available in `templates/embedded-overrides.example.json`.

## Project Structure

```text
arch-wiki-es/
├── SKILL.md
├── README.md
├── bin/
│   ├── install.js
│   └── uninstall.js
├── templates/
│   ├── architecture.json
│   ├── architecture.html
│   ├── build_html.py
│   └── embedded-overrides.example.json
└── plans/
    └── embedded-arch-wiki.md
```

## Limitations

The scanner is intentionally lightweight, dependency-free, and evidence-based:

- Respects `.gitignore` rules across root and subdirectories to avoid scanning build artifacts and generated files.
- Hardware parameters are extracted from recognizable configuration markers, register initializations, and build settings.
- Static C/C++ analysis cannot infer pointer ownership through complex macro layers or function pointer tables without explicit evidence or overrides.
- The built-in Markdown renderer handles standard README constructs without requiring external libraries.
- The generator runs on standard Python 3 with zero third-party package dependencies.

## License

MIT.
