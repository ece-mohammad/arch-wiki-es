# Embedded-Only Arch-Wiki Implementation Plan

## 1. Goal

Transform `arch-wiki` from an API/backend architecture documentation tool into an embedded-systems architecture documentation tool.

The generated `architecture.json` and `architecture.html` must document:

0. Project brief
1. Hardware
2. Configurations
3. Memory layout
4. Modules and components
5. Class diagrams
6. Sequence diagrams
7. Interaction diagrams
8. State machines
9. Flow charts
10. Data pipelines and flow diagrams
11. Firmware build

The documentation must also include:

- The target project's `README.md`.
- User-defined data types only.
- The role and usage of every documented user-defined type.
- The files that contain every module, component, and user-defined type.
- The lifetime and ownership of created objects.

The existing API/backend concepts are out of scope and should be removed, not retained as optional compatibility sections.

## 2. Remove Unrelated API Features

### Files to update

- `templates/build_html.py`
- `templates/architecture.json`
- `templates/architecture.html`
- `SKILL.md`
- `README.md`
- `package.json`
- `bin/install.js`

### Remove from the JSON schema

Delete these sections and concepts:

- `workspaces`
- `infrastructure`
- `dockerDiagram`
- `swaggerSchemas`
- `systemEndpoints`
- `dataFlow` when it describes HTTP request processing
- `permissions`
- `sqlQueries`
- API endpoints and route metadata
- `basePath`, `auth`, and `permission` fields

### Remove from the scanner/generator

Remove API/backend-specific logic including:

- Express route scanning
- FastAPI route scanning
- Spring controller scanning
- Swagger/OpenAPI generation
- SQL query generation
- Docker Compose scanning
- RBAC/permission extraction
- HTTP request pipeline generation
- Backend framework detection

Remove the Swagger UI dependency and related CDN assets from generated HTML.

### Remove from the dashboard

Delete these navigation sections:

- API Modules
- Docker Topology
- Swagger & OpenAPI
- Permissions
- SQL Queries
- Infrastructure
- Core Layer
- Request Pipeline

The dashboard should only contain embedded-system sections.

## 3. Final JSON Structure

Replace the current template with this embedded-only top-level structure:

```json
{
  "meta": {},
  "readme": {},
  "brief": {},
  "hardware": {},
  "configurations": {},
  "memoryLayout": {},
  "modules": [],
  "components": [],
  "dataTypes": [],
  "objects": [],
  "diagrams": {
    "classDiagrams": [],
    "sequenceDiagrams": [],
    "interactionDiagrams": [],
    "stateMachines": [],
    "flowCharts": []
  },
  "dataPipelines": [],
  "build": {}
}
```

Every generated item should support traceability metadata where applicable:

```json
{
  "source": "scanner|override|manual",
  "confidence": "high|medium|low|unknown",
  "evidence": [
    "src/example.c:42"
  ]
}
```

## 4. Project Metadata and Brief

### `meta`

Retain metadata relevant to firmware:

```json
{
  "displayName": "Environmental Sensor Firmware",
  "version": "1.0.0",
  "description": "Firmware for a low-power environmental sensor.",
  "generatedAt": "2026-08-10",
  "projectType": "bare-metal|rtos|embedded-linux|hybrid",
  "languages": ["C", "C++"],
  "frameworks": ["FreeRTOS"],
  "buildSystems": ["CMake"],
  "toolchains": ["arm-none-eabi-gcc"]
}
```

### `brief`

```json
{
  "purpose": "Low-power environmental sensor firmware",
  "systemType": "rtos",
  "summary": "Collects, validates, stores, and transmits sensor measurements.",
  "operatingEnvironment": [],
  "primaryResponsibilities": [],
  "constraints": [],
  "safetyAndReliability": [],
  "powerRequirements": [],
  "timingRequirements": [],
  "documentationStatus": "generated|partially-reviewed|reviewed",
  "sourceFiles": ["README.md"]
}
```

Use README content for high-level context only. Do not infer precise pin mappings, clock values, memory addresses, power budgets, or safety guarantees from prose without source evidence.

## 5. Include the Target Project README

### JSON representation

Add a `readme` object:

```json
{
  "path": "README.md",
  "title": "Environmental Sensor Firmware",
  "content": "# Environmental Sensor Firmware\n\n...",
  "exists": true,
  "lastModified": "2026-08-10",
  "source": "project-readme"
}
```

### Scanner behavior

Add `_scan_readme(root)` that:

1. Prefers root-level `README.md`.
2. Supports case variations and fallback README formats where practical.
3. Reads UTF-8 with safe error handling.
4. Extracts the first H1 as the title.
5. Preserves the original Markdown content.
6. Records a missing-file state rather than inventing content.
7. Uses README references as evidence for high-level descriptions.

### HTML behavior

Add a `Project README` dashboard section containing:

- Rendered Markdown.
- Escaped raw Markdown source view.
- Copy-Markdown button.
- Source path and modification date.
- Missing README placeholder.
- Warnings for decode failures or unresolved local links.

Implement a standard-library Markdown subset for headings, paragraphs, lists, code fences, links, images, blockquotes, horizontal rules, and basic tables. Escape all generated content and never insert raw README HTML directly.

Embed the README in the generated HTML at generation time so the dashboard remains readable if the source README is unavailable later.

## 6. Hardware

Add a `hardware` object:

```json
{
  "target": {
    "board": "STM32 Nucleo-F411RE",
    "mcu": "STM32F411RE",
    "vendor": "STMicroelectronics",
    "architecture": "ARM Cortex-M4",
    "core": "Cortex-M4F",
    "frequencyMHz": 100,
    "endianness": "little",
    "toolchainTarget": "arm-none-eabi"
  },
  "power": {
    "inputVoltage": "3.3V",
    "operatingVoltage": "3.3V",
    "sleepModes": [],
    "powerBudget": {}
  },
  "peripherals": [],
  "pinMappings": [],
  "sensors": [],
  "actuators": [],
  "communication": [],
  "debugInterfaces": [],
  "clockTree": {},
  "sourceFiles": []
}
```

Detect hardware evidence from:

- PlatformIO `platformio.ini`.
- STM32CubeMX `.ioc` files.
- Device-tree files and overlays.
- Board definitions.
- HAL initialization code.
- GPIO/pin/peripheral macros.
- UART, SPI, I2C, CAN, USB, PWM, ADC, DMA, timer, RTC, Ethernet, Wi-Fi, Bluetooth, LoRa, and GPS usage.

The HTML should display MCU/board cards, power details, clock information, peripherals, pin mappings, sensors, actuators, interfaces, and source evidence.

## 7. Configurations

Add a `configurations` object:

```json
{
  "buildProfiles": [],
  "featureFlags": [],
  "runtimeConfiguration": [],
  "kconfigOptions": [],
  "deviceTreeOverlays": [],
  "generatedFiles": [],
  "configurationSources": []
}
```

Scan:

- `platformio.ini`
- `CMakeLists.txt`
- `CMakePresets.json`
- `Makefile`
- `sdkconfig`
- `sdkconfig.defaults`
- `Kconfig`
- `prj.conf`
- `defconfig`
- `config.h` and `*_config.h`
- Device-tree overlays
- CI build definitions

Capture defines, include directories, compiler/linker flags, optimization modes, board variants, feature flags, runtime defaults, and generated configuration files.

The HTML should provide debug/release comparison, feature flag tables, runtime settings, Kconfig/device-tree information, and configuration source links.

## 8. Memory Layout

Add a `memoryLayout` object:

```json
{
  "addressWidth": 32,
  "regions": [],
  "sections": [],
  "partitions": [],
  "stack": {},
  "heap": {},
  "specialAreas": [],
  "linkerScripts": [],
  "mapFiles": [],
  "usage": {}
}
```

Parse:

- GNU linker scripts.
- ARM scatter files.
- IAR linker files.
- Linker map files.
- Firmware size reports.
- Bootloader/application/OTA partition definitions.
- `.text`, `.rodata`, `.data`, `.bss`, `.noinit`, DMA, stack, heap, and retained-memory sections.

The HTML should display an address-range diagram, flash/RAM usage, section-to-region mappings, partitions, stack/heap details, and overflow warnings. Distinguish declared values from measured post-build usage.

## 9. Modules and Components

### Modules

Modules represent logical firmware subsystems:

```json
{
  "id": "sensor_manager",
  "name": "Sensor Manager",
  "type": "application|driver|middleware|hal|protocol|storage|service|board-support",
  "role": "Coordinates sensor initialization, acquisition, validation, and publication.",
  "description": "Sensor data acquisition subsystem.",
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
  "confidence": "high",
  "evidence": []
}
```

### Components

Components represent concrete source-level units:

```json
{
  "id": "i2c_driver",
  "name": "I2C Driver",
  "type": "driver",
  "language": "C",
  "role": "Translates sensor requests into MCU-specific I2C transactions.",
  "description": "I2C hardware abstraction and transfer implementation.",
  "files": [],
  "publicHeaders": [],
  "provides": [],
  "consumes": [],
  "dependencies": [],
  "dataTypes": [],
  "objects": [],
  "interrupts": [],
  "configurationRefs": [],
  "source": "scanner",
  "confidence": "high",
  "evidence": []
}
```

### File references

Replace plain string file lists with structured references:

```json
{
  "path": "src/sensors/sensor_manager.c",
  "role": "implementation",
  "language": "C",
  "contains": ["sensor_manager_init", "sensor_manager_read"],
  "lineRange": {
    "start": 10,
    "end": 180
  }
}
```

Supported file roles include `definition`, `declaration`, `implementation`, `public-interface`, `private-interface`, `configuration`, `generated`, `linker-script`, `test`, `mock`, `fixture`, `registration`, `usage`, and `documentation`.

Detect modules/components from source directories, CMake targets, PlatformIO libraries, ESP-IDF components, Zephyr modules, Rust crates, public headers, driver registration, RTOS tasks, interrupts, timers, queues, and inter-component includes/calls.

## 10. User-Defined Data Types Only

Add a top-level `dataTypes` array. It must contain only types defined by the project.

Include:

- Project C/C++ structs, unions, enums, typedefs, callback types, opaque handles, classes, and interfaces.
- Project Rust structs, enums, traits, unions, and type aliases.
- Project-defined message, event, frame, state, configuration, error, and protocol types.

Exclude:

- Primitive language types.
- `stdint.h` and standard integer types.
- C/C++ standard-library types.
- Rust primitive and standard-library types.
- RTOS types.
- Vendor SDK/HAL types.
- External dependency types.
- System-header-only declarations.

Named project aliases of standard types should still be included:

```c
typedef uint32_t SensorId;
```

```json
{
  "id": "sensor_id",
  "name": "SensorId",
  "kind": "typedef",
  "underlyingType": "uint32_t",
  "userDefined": true,
  "ownership": "project"
}
```

Each type must include a role and usage information:

```json
{
  "id": "sensor_reading",
  "name": "SensorReading",
  "kind": "struct",
  "language": "C",
  "userDefined": true,
  "ownership": "project",
  "role": "Represents one validated sensor measurement.",
  "description": "Measurement value, timestamp, and quality flags.",
  "files": [],
  "fields": [],
  "usedByModules": [],
  "usedByComponents": [],
  "usage": [],
  "objectInstances": [],
  "source": "scanner",
  "confidence": "high",
  "evidence": []
}
```

### Type fields

Standard field types may be shown as labels but must not become top-level entries:

```json
{
  "name": "temperature",
  "type": "int16_t",
  "typeReference": null,
  "role": "Temperature in centidegrees Celsius"
}
```

References to other project-defined types should resolve through `typeReference`:

```json
{
  "name": "metadata",
  "type": "MeasurementMetadata",
  "typeReference": "measurement_metadata",
  "role": "Measurement source and quality metadata"
}
```

### Type usage

```json
{
  "role": "consumes",
  "usageType": "function-parameter",
  "module": "telemetry",
  "component": "telemetry_encoder",
  "symbol": "telemetry_encode",
  "files": [
    {
      "path": "src/telemetry/telemetry_encoder.c",
      "line": 42
    }
  ],
  "description": "Consumes a validated reading to create a telemetry frame."
}
```

Supported usage roles include `defines`, `declares`, `input`, `output`, `produces`, `consumes`, `reads`, `writes`, `stores`, `loads`, `queues`, `dequeues`, `serializes`, `deserializes`, `transmits`, `receives`, `encodes`, `decodes`, `configures`, `represents-state`, `represents-event`, `represents-error`, `callback`, `contains`, and `references`.

Add scanners for type definitions, fields, type ownership classification, type usages, module/component linking, function signatures, queue payloads, message buffers, serialization, storage, callbacks, and state transitions.

## 11. Object Lifetime and Ownership

Add a top-level `objects` array describing concrete created or managed objects based on user-defined types.

```json
{
  "id": "telemetry_frame_queue_item",
  "name": "telemetry_frame",
  "typeReference": "telemetry_frame",
  "kind": "global|static|stack|heap|pool|rtos|persistent|peripheral-handle",
  "role": "Carries one encoded frame between the telemetry and radio tasks.",
  "lifetime": {
    "scope": "until dequeued or discarded",
    "startsAt": "queue allocation",
    "endsAt": "queue release",
    "createdBy": "telemetry_task",
    "destroyedBy": "radio_task",
    "persistsAcrossReset": false
  },
  "ownership": {
    "model": "pool-managed",
    "owner": {
      "kind": "component",
      "id": "telemetry_queue"
    },
    "creator": {
      "kind": "component",
      "id": "telemetry"
    },
    "releaseResponsibility": {
      "kind": "component",
      "id": "telemetry_queue"
    },
    "transferEvents": []
  },
  "storage": {
    "location": "static-queue-buffer",
    "region": "ram",
    "section": ".bss",
    "size": null
  },
  "creation": {
    "function": "telemetry_init",
    "file": "src/telemetry/telemetry_queue.c",
    "line": 18
  },
  "usage": [],
  "files": [],
  "source": "scanner",
  "confidence": "medium",
  "evidence": []
}
```

### Lifetime vocabulary

Support `firmware`, `boot`, `until-reset`, `power-cycle`, `task`, `function`, `block`, `transaction`, `interrupt`, `callback`, `connection`, `session`, `heap-allocation`, `pool-allocation`, `persistent`, and `unknown`.

### Ownership vocabulary

Support `static`, `global`, `stack-owned`, `unique`, `shared`, `borrowed`, `pool-managed`, `queue-owned`, `task-owned`, `interrupt-owned`, `module-owned`, `component-owned`, `system-owned`, `externally-owned`, `transferred`, and `unknown`.

### Detection

Add scanners for:

- Global and file-scope static objects.
- Function-local static and stack objects.
- `malloc`, `calloc`, `realloc`, `free`, `new`, `delete`, and custom allocators.
- Static memory pools.
- C++ constructors/destructors.
- Rust owned, borrowed, `Box`, `Rc`, `Arc`, `static`, and `'static` values.
- RTOS tasks, queues, semaphores, mutexes, event groups, timers, message buffers, and stream buffers.
- Peripheral handles, DMA buffers, callback contexts, and persistent objects.

Record creator, initializer, activation, suspend/resume, release/destruction, reset behavior, storage location, owner, usage, and ownership transfers.

Pointer passing must not automatically be classified as ownership transfer. C/C++ inferences must include confidence and warnings when ownership or cleanup cannot be proven.

### Ownership transfers

```json
{
  "from": {"kind": "component", "id": "sensor_manager"},
  "to": {"kind": "component", "id": "telemetry_encoder"},
  "object": "sensor_reading_instance",
  "ownership": "borrowed",
  "trigger": "telemetry_encode(reading)",
  "file": "src/telemetry/telemetry_encoder.c",
  "line": 41,
  "returnsToOwner": true
}
```

## 12. Diagram Generation

Add diagram collections under `diagrams`:

```json
{
  "classDiagrams": [],
  "sequenceDiagrams": [],
  "interactionDiagrams": [],
  "stateMachines": [],
  "flowCharts": []
}
```

All diagrams should use user-defined types, modules, components, objects, and hardware entities. Standard types may appear as field labels but must not become diagram entities.

### Class diagrams

Use Mermaid `classDiagram` for:

- C structs, unions, enums, callback tables, and opaque handles.
- C++ classes, inheritance, composition, and interfaces.
- Rust structs, traits, implementations, and module relationships.
- Module/component ownership and user-defined type composition.

### Sequence diagrams

Use Mermaid `sequenceDiagram` for:

- Boot and initialization.
- Sensor sampling.
- ISR-to-task handoff.
- Task-to-task messaging.
- Protocol exchange.
- OTA update.
- Fault recovery.
- Object creation, borrowing, transfer, and release.

Annotate messages with user-defined data types where detected.

### Interaction diagrams

Use Mermaid flowcharts for:

- Bootloader/application interaction.
- Driver/peripheral interaction.
- Task/queue interaction.
- Firmware/host interaction.
- Power-management interaction.
- Recovery interaction.

### State machines

Use Mermaid `stateDiagram-v2` for:

- Device lifecycle.
- Connection lifecycle.
- Firmware update lifecycle.
- Sensor states.
- Power states.
- Fault/recovery states.
- Protocol parser states.

Include project-defined state and event types where available.

### Flow charts

Use Mermaid `flowchart TD` for:

- Reset/startup.
- Main loop.
- RTOS task execution.
- Interrupt handling.
- Firmware update.
- Error handling.
- Low-power entry and wake-up.

### Data pipelines

```json
{
  "id": "sensor_telemetry",
  "name": "Sensor Telemetry Pipeline",
  "description": "Acquisition, validation, buffering, encoding, and transmission.",
  "stages": [
    {
      "id": "acquire",
      "component": "sensor_manager",
      "inputType": null,
      "outputType": "sensor_reading_raw",
      "objectLifetime": "one sampling transaction",
      "ownership": "sensor_manager-owned"
    }
  ],
  "edges": [],
  "mermaid": "flowchart LR\n..."
}
```

## 13. Firmware Build

Add a `build` object:

```json
{
  "system": {
    "type": "CMake|Make|PlatformIO|west|idf.py|Cargo|custom",
    "files": [],
    "buildDirectory": "build",
    "generator": "Ninja"
  },
  "toolchain": {
    "compiler": "arm-none-eabi-gcc",
    "linker": "arm-none-eabi-g++",
    "objcopy": "arm-none-eabi-objcopy",
    "objdump": "arm-none-eabi-objdump",
    "targetTriple": "arm-none-eabi",
    "version": null
  },
  "profiles": [],
  "targets": [],
  "artifacts": [],
  "linkerScripts": [],
  "commands": {
    "configure": null,
    "build": null,
    "test": null,
    "flash": null,
    "debug": null
  },
  "flashAndDebug": {},
  "staticAnalysis": [],
  "ci": []
}
```

Detect CMake, Make, PlatformIO, Zephyr `west`, ESP-IDF `idf.py`, Cargo, Ninja, Meson, Bazel, toolchain files, linker scripts, OpenOCD/J-Link/GDB configuration, CI workflows, firmware artifacts, size reports, and flash/debug commands.

The HTML should show toolchain, profiles, targets, flags, artifacts, memory reports, flash/debug commands, static analysis, and CI steps.

## 14. Scanner Refactor

Refactor `templates/build_html.py` around embedded-specific functions:

```text
_detect_embedded_project()
_detect_build_system()
_scan_readme()
_scan_brief()
_scan_hardware()
_scan_configurations()
_scan_memory_layout()
_scan_modules()
_scan_components()
_scan_project_defined_types()
_scan_type_usages()
_scan_objects()
_scan_object_lifetimes()
_scan_object_ownership()
_scan_class_diagrams()
_scan_sequence_diagrams()
_scan_interaction_diagrams()
_scan_state_machines()
_scan_flow_charts()
_scan_data_pipelines()
_scan_build()
_merge_manual_overrides()
_validate_manifest()
_generate_html()
```

Supported project markers should include:

- `platformio.ini`
- `CMakeLists.txt`
- `Makefile`
- `west.yml`
- `prj.conf`
- `sdkconfig`
- `idf.py` project metadata
- `Cargo.toml` with embedded targets
- `.ioc`
- `.dts`/`.dtsi`
- Embedded linker scripts
- `arm-none-eabi-*` or RISC-V embedded toolchains
- FreeRTOS, Zephyr, or other RTOS markers

If no embedded markers are found, report that state instead of falling back to backend scanners.

## 15. Manual Overrides

Add `templates/embedded-overrides.example.json` and support an optional target-project file:

```text
docs/architecture/embedded-overrides.json
```

Allow overrides for:

- Board and MCU.
- Pin mappings.
- Clock tree.
- Power and timing constraints.
- Memory partitions.
- Module/component roles.
- User-defined types and type usage.
- Object lifetime and ownership.
- State machines and data pipelines.
- Build, flash, and debug commands.

Merge in this order:

1. Scanner output.
2. Existing manifest data where applicable.
3. Manual override file.
4. Explicit user/AI edits.

Manual values should retain `source: "override"` and should not silently erase scanner warnings.

## 16. HTML Dashboard

### Navigation

Use this order:

1. Brief
2. Project README
3. Hardware
4. Configurations
5. Memory Layout
6. Modules & Components
7. Class Diagrams
8. Sequence Diagrams
9. Interaction Diagrams
10. State Machines
11. Flow Charts
12. Data Pipelines
13. Build

### Modules & Components subsection

Include tabs or subsections for:

- Modules.
- Components.
- User-defined data types.
- Created objects.
- Lifetime and ownership.

Every card/table should show role, structured file references, source evidence, and confidence.

### HTML implementation

Add renderer helpers in `build_html.py`:

```text
_render_brief()
_render_readme()
_render_hardware()
_render_configurations()
_render_memory_layout()
_render_modules()
_render_components()
_render_data_types()
_render_objects()
_render_lifetime_ownership()
_render_diagrams()
_render_data_pipelines()
_render_build()
```

Update `templates/architecture.html` by regenerating it from the new renderer. Do not maintain a separate hand-written dashboard implementation.

The HTML must be responsive and handle long code blocks, tables, diagrams, file paths, and README content on mobile devices.

## 17. Skill and Package Documentation

### `SKILL.md`

Remove instructions for routes, APIs, Swagger, permissions, SQL, Docker, and backend frameworks.

Add invocation triggers for:

- Board/MCU changes.
- New peripherals, sensors, actuators, or drivers.
- New tasks, interrupts, queues, timers, or callbacks.
- New modules/components.
- New user-defined types.
- Object allocation or ownership changes.
- Linker scripts or memory partitions.
- Build profiles, toolchains, or flash/debug methods.
- State machines, flow charts, or data pipelines.
- README and firmware documentation changes.

The workflow should inspect the README, scan firmware sources/configuration/build files, update the embedded manifest, and regenerate the HTML dashboard.

### `README.md`

Rewrite the package documentation around embedded architecture mapping. Document:

- Supported firmware types.
- Supported build systems.
- Hardware and memory scanning.
- User-defined type filtering.
- Object lifetime/ownership analysis.
- README embedding.
- Manual overrides.
- Diagram generation.
- Dashboard sections.
- Scanner limitations and confidence reporting.

### `package.json`

Replace API-oriented keywords with embedded terms such as:

```json
[
  "ai-skill",
  "embedded-systems",
  "firmware",
  "microcontroller",
  "rtos",
  "bare-metal",
  "platformio",
  "cmake",
  "zephyr",
  "freertos",
  "stm32",
  "esp32",
  "memory-layout",
  "firmware-architecture"
]
```

## 18. Validation Rules

Validate that:

- Only the embedded schema is generated.
- No API/backend/Docker/Swagger/SQL/permission sections remain.
- `architecture.json` is valid JSON.
- Every module has a role and source files.
- Every component has a role and source files.
- Every documented type is project-defined.
- Standard, RTOS, vendor, and external types are excluded from `dataTypes`.
- Every user-defined type has a role, definition/declaration file, and usage list where detectable.
- Every `typeReference` resolves to a project-defined type.
- Every object has a type reference where applicable.
- Every object has lifetime and ownership metadata, or explicit `unknown` values.
- Claimed creators, destructors, releases, and transfers have evidence.
- Dynamic allocations with no release path produce warnings.
- Missing source files are reported.
- Mermaid IDs and labels are sanitized.
- Generated HTML contains every navigation section.
- All dynamic text, source content, and README Markdown are escaped.
- Relative README links and images are handled safely.

## 19. Tests and Fixtures

Add test fixtures for:

```text
tests/
├── fixtures/
│   ├── bare-metal-c/
│   ├── freertos-stm32/
│   ├── platformio-esp32/
│   ├── zephyr/
│   ├── esp-idf/
│   └── rust-embedded/
├── test_detection.py
├── test_readme.py
├── test_hardware.py
├── test_configurations.py
├── test_memory_layout.py
├── test_modules_components.py
├── test_data_types.py
├── test_objects.py
├── test_lifetime_ownership.py
├── test_diagrams.py
├── test_build.py
├── test_manifest.py
└── test_html_generation.py
```

Test at least:

- Embedded project detection.
- Build-system detection.
- README extraction and safe rendering.
- Hardware and peripheral detection.
- Configuration extraction.
- Linker-script and map-file parsing.
- Module/component grouping.
- File-role and line-range detection.
- Struct, enum, union, typedef, class, trait, and callback detection.
- Standard/external/vendor/RTOS type exclusion.
- User-defined type usage and role detection.
- Queue payload and serialization detection.
- Global, static, stack, heap, pool, RTOS, DMA, and persistent object detection.
- Ownership transfer and borrowed-access distinction.
- Missing cleanup warnings.
- Diagram generation and Mermaid sanitization.
- JSON validation.
- Responsive HTML generation.
- Missing or malformed source files.

## 20. Implementation Order

1. Replace `templates/architecture.json` with the embedded-only schema.
2. Remove API/backend/Docker/Swagger/SQL/permission scanner and renderer logic.
3. Add embedded project and build-system detection.
4. Add README scanning and HTML embedding.
5. Implement brief, hardware, configurations, and memory layout scanning.
6. Implement module/component scanning and structured file references.
7. Implement user-defined type extraction and standard-type filtering.
8. Implement type roles, usage records, and type relationships.
9. Implement object detection, lifetime tracking, and ownership analysis.
10. Implement class, sequence, interaction, state, and flow diagrams.
11. Implement data-pipeline extraction and diagrams.
12. Implement firmware build scanning.
13. Add manual overrides and manifest validation.
14. Rewrite the HTML dashboard and regenerate `templates/architecture.html`.
15. Rewrite `SKILL.md`, `README.md`, and package metadata.
16. Add fixtures and automated tests.
17. Run syntax checks, scanner tests, manifest validation, and browser verification.

## 21. Expected Traceability

The finished documentation should support these relationships:

```text
Module
  -> Component
    -> User-defined Type
      -> Definition and Usage Files
        -> Created Object
          -> Lifetime
          -> Storage
          -> Owner
          -> Creator
          -> Transfer
          -> Release/Destruction
```

It should also support reverse navigation:

```text
Source File
  -> Module/Component
  -> User-defined Types
  -> Object Instances
  -> Lifetime and Ownership Responsibilities
```

The result should be an embedded-only, evidence-based architecture map that documents firmware structure, hardware, memory, types, object behavior, data movement, diagrams, and reproducible builds in both machine-readable JSON and interactive HTML.
