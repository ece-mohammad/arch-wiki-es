---
name: arch-wiki-es
description: >
  Scans embedded firmware projects and updates docs/architecture/architecture.json
  and docs/architecture/architecture.html with hardware, configuration, memory,
  modules, user-defined types, object ownership, diagrams, data pipelines, and build metadata.
---

# arch-wiki-es - Embedded Firmware Architecture Skill

Use this skill for C, C++, Rust, bare-metal, RTOS, embedded Linux, PlatformIO,
CMake, Make, Zephyr, ESP-IDF, STM32CubeMX, and similar firmware projects. This
skill is intentionally embedded-only; do not add web API, Swagger, SQL, Docker, or
backend documentation sections.

## When to Invoke (Sync Triggers)

Invoke this skill whenever changes occur in the codebase:

- **Hardware & Peripherals**: Adding or changing MCU, board, clock tree, GPIO, UART, SPI, I2C, CAN, ADC, timers, DMA, sensors, or actuators.
- **Components & APIs**: Adding or modifying driver functions, public header prototypes, RTOS tasks, message queues, callbacks, or state machines.
- **Data Types & Enums**: Adding project-defined structs, enums (and member values), typedefs, classes, or packet definitions.
- **Memory & Build**: Modifying linker scripts (`.ld`), memory regions, section allocations, preprocessor `#define` flags, or Makefile targets.
- **Documentation & Submodules**: Updating the root README or adding documentation to driver/component subdirectories.

## Execution Commands

### 1. First-Time Setup (or Full Init)

```bash
python3 docs/architecture/build_html.py --init
```

*Scans the repository, extracts hardware parameters, categorized configuration flags, functions, call graphs, state machines, and builds `docs/architecture/architecture.json` and `docs/architecture/architecture.html`.*

### 2. Incremental Sync (After Codebase Changes)

```bash
python3 docs/architecture/build_html.py --sync
```

*Rescans modified sources, updates symbol catalogs, recalculates cross-component dependencies and call graphs, and refreshes the interactive dashboard.*

For a project outside the current working directory:

```bash
python3 /path/to/arch-wiki-es/templates/build_html.py --sync /path/to/firmware-project
```

## AI Assistant Sync Workflow Prompts

Use these prompt patterns when asking an AI assistant to sync or audit architecture documentation:

### Prompt A — "I added or modified a driver / peripheral component"

```
I added a new driver/component to the firmware.
Run arch-wiki-es to sync the architecture map:
1. Run `python3 docs/architecture/build_html.py --sync`
2. Verify that the new component appears under Modules & Components with its public APIs.
3. Check that peripheral bindings and inter-component dependencies are updated.
```

### Prompt B — "I modified functions, macros, or state machine transitions"

```
I updated firmware functions and state machine logic.
Run arch-wiki-es to rescan:
1. Run `python3 docs/architecture/build_html.py --sync`
2. Ensure the state diagram in State Machines tab reflects the new transitions.
3. Verify the updated function signatures and call graph edges.
```

### Prompt C — "I updated memory layout, clock setup, or build flags"

```
I changed the target MCU / clock configuration / linker script.
Run arch-wiki-es to sync:
1. Run `python3 docs/architecture/build_html.py --sync`
2. Verify updated memory regions (FLASH, RAM) and frequency in Hardware and Memory Layout tabs.
3. Check that newly added #define parameters are categorized correctly.
```

### Prompt D — "Full Rescan & Parity Audit"

```
Run arch-wiki-es to perform a full parity audit against the firmware codebase:
1. Run `python3 docs/architecture/build_html.py --sync`
2. Audit actual codebase against docs/architecture/architecture.json:
   - Verify all public APIs in header files are documented in Functions tab.
   - Verify all user-defined structs and enums are captured in User-Defined Data Types.
   - Verify unproven C/C++ ownership is marked unknown with warnings.
   - Verify all build targets in Makefiles/platformio.ini are listed.
```

## 🤖 Interactive Senior Embedded Developer Prompts

The generated `architecture.html` includes an interactive modal system:

- Every **Function card** has a **📋 AI Prompt** button.
- Every **Component card** has a **📋 AI Prompt** button.
- Every **State Machine card** has a **📋 AI Prompt** button.

Clicking any of these generates a tailor-made prompt formatted for an AI coding assistant (Antigravity, Claude, ChatGPT, Cursor) instructing it to:
1. Trace execution flow, callers, callees, and register access.
2. Analyze concurrency, ISR safety, interrupt priorities, and reentrancy.
3. Check stack consumption, buffer bounds, and error recovery.
4. Output Mermaid sequence diagrams and logic flowcharts.

## Generated Architecture Sections

0. **Brief & Topology Overview**: MCU topology, bare-metal vs RTOS classification.
1. **Project README & Multi-README Index**: Embedded root README and catalog of all driver READMEs.
2. **Hardware & Peripherals Configuration**: Detected MCU, clock frequencies, peripherals, pinout.
3. **Categorized Configuration Parameters**: Defines grouped by functional category (`clock`, `peripheral`, `rtos`, etc.).
4. **Memory Layout & Linker Map**: Flash/RAM origins, lengths, sections (`.text`, `.data`, `.bss`).
5. **Modules & Components**: Logical firmware subsystems, drivers, public APIs (`provides`/`consumes`).
6. **Dependencies & Inter-Component Integration**: Cross-component call graphs.
7. **Files & Per-File Catalog**: Source files catalog with symbol counts and line totals.
8. **Functions & Signatures**: Full signatures, return types, parameters, visibility, callers/callees.
9. **Macros & Preprocessor Definitions**: Defines with values, parameter lists, and categories.
10. **Call Graph**: Function call hierarchy visualized via Mermaid flowchart.
11. **Tools & Scripts**: Makefile target role analysis (`primary`, `utility`, `wrapper`) and helper scripts.
12. **Class Diagrams**: Structs, enums, unions, and relationships.
13. **Sequence Diagrams**: Startup and hardware initialization call hierarchy derived from `main()`.
14. **Interaction Diagrams**: Subsystem boundaries and communication channels.
15. **State Machines**: Source-derived state machines extracted from enums and `switch`/`case` transitions.
16. **Flow Charts**: Firmware execution loops, reset flows, and interrupt handlers.
17. **Data Pipelines**: Detected data flow between firmware modules.
18. **Firmware Build & Toolchain**: Build system, toolchain target triple, and flash/debug commands.
19. **Searchable Symbol Index**: Filterable index of all project functions, types, macros, and globals.

## Evidence Rules

Do not invent electrical, timing, power, memory, or ownership facts. Every inferred
value should include a source file and confidence. C/C++ ownership should be
`unknown` when creation, transfer, or cleanup cannot be established from evidence.

`dataTypes` contains user-defined project types only. Standard types may appear as
field or signature labels but must not become independent documentation entries.

## Manual Overrides

Use `docs/architecture/embedded-overrides.json` for facts that static scanning
cannot safely infer, including board details, pin mappings, power constraints,
memory partitions, module roles, type relationships, object ownership, state
machines, data pipelines, and flash/debug commands. Overrides are merged during `--sync`.

## Verification Checklist

- `architecture.json` contains only the embedded schema (21 top-level keys).
- The generated README content matches the target project's README.
- All requested navigation sections are present in the HTML.
- No standard or vendor types appear as top-level `dataTypes` entries.
- Modules, components, and types have roles and source files where detectable.
- Created objects show lifetime, storage, ownership, and confidence.
- Unresolved cleanup or ownership is visible as a warning.
- Mermaid diagrams render or show their source fallback.
- The dashboard works on desktop and narrow screens.
