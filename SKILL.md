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
skill is intentionally embedded-only; do not add API, Swagger, SQL, Docker, or
backend documentation sections.

## Invoke After

- Adding or changing a board, MCU, peripheral, sensor, actuator, or driver.
- Adding or changing a task, interrupt, timer, queue, callback, or state machine.
- Adding a project-defined struct, enum, class, trait, message, event, or protocol type.
- Changing object allocation, storage, lifetime, ownership, or cleanup behavior.
- Changing a linker script, memory partition, build profile, toolchain, or flash method.
- Changing a data pipeline, README, device-tree overlay, Kconfig, or firmware configuration.

## Workflow

1. Read the target project's `README.md`.
2. Inspect the existing `docs/architecture/architecture.json` if present.
3. Identify the board, MCU, build system, toolchain, and RTOS.
4. Scan hardware configuration, source, headers, linker scripts, map files, and build files.
5. Scan modules, components, source file roles, and project-defined types.
6. Exclude primitive, standard-library, vendor SDK, and RTOS types from `dataTypes`.
7. Record each user-defined type's role, usage, and containing files.
8. Record created objects, storage, lifetime, owner, transfers, and release paths.
9. Update diagrams, data pipelines, and build metadata.
10. Apply `docs/architecture/embedded-overrides.json` when source analysis cannot determine intent.
11. Run:

```bash
python3 docs/architecture/build_html.py --sync
```

12. Verify the generated HTML contains the README and all embedded sections.

For a target project outside the current working directory, pass its existing path:

```bash
python3 /path/to/arch-wiki-es/templates/build_html.py --sync /path/to/firmware-project
```

The generator writes `docs/architecture/architecture.json` and
`docs/architecture/architecture.html` in the target project. It rescans and
regenerates both files on every invocation.

## Generated Sections

- Brief & Topology Overview
- Project README & Multi-README Index
- Hardware & Peripherals Configuration
- Categorized Configuration Parameters
- Memory Layout & Linker Map
- Modules & Components (with Public APIs)
- Dependencies & Inter-Component Integration
- Files & Per-File Catalog
- Functions & Signatures
- Macros & Preprocessor Definitions
- Call Graph (Caller → Callee)
- Tools & Scripts (Makefile Analysis & Utility Scripts)
- Class Diagrams
- Sequence Diagrams (Boot/Init Sequence)
- Interaction Diagrams
- State Machines (Source-Derived)
- Flow Charts
- Data Pipelines
- Build System & Toolchain
- Searchable Flat Symbol Index

## Evidence Rules

Do not invent electrical, timing, power, memory, or ownership facts. Every inferred
value should include a source file and confidence. C/C++ ownership should be
`unknown` when creation, transfer, or cleanup cannot be established from evidence.

`dataTypes` contains user-defined project types only. Standard types may appear as
field or signature labels but must not become independent documentation entries.

## Type and File Rules

- Include project-defined structs, unions, enums, typedefs, classes, traits, callback types, message types, and protocol types.
- Exclude primitive, standard-library, vendor SDK, HAL, RTOS, and external dependency types.
- Include a role for each module, component, type, and created object.
- Use structured file references with path, file role, symbols, and line evidence when available.
- Record both definition files and meaningful usage files; do not list a header merely because it was included.
- Link fields to other project-defined types with `typeReference`.
- Record type usage roles such as `produces`, `consumes`, `queues`, `stores`, `serializes`, `deserializes`, `transmits`, and `receives`.

## Object Lifetime and Ownership Rules

For created objects and resources, inspect:

- Global, static, stack, heap, pool, RTOS, persistent, DMA, and peripheral-handle storage.
- Creation and initialization functions.
- Activation, suspension, reset, release, and destruction paths.
- Module, component, task, or system ownership.
- Borrowed access, shared access, queue transfer, DMA handoff, and ownership transfer.

Do not treat every pointer argument as an ownership transfer. If creation,
release, or responsibility cannot be proven, use `unknown` and include a warning
with the relevant source evidence.

## Override Rules

Use `docs/architecture/embedded-overrides.json` for facts that static scanning
cannot safely infer, including board details, pin mappings, power constraints,
memory partitions, module roles, type relationships, object ownership, state
machines, data pipelines, and flash/debug commands. Preserve `source` and
`confidence` metadata when applying overrides.

## Verification Checklist

- `architecture.json` contains only the embedded schema.
- The generated README content matches the target project's README.
- All requested navigation sections are present in the HTML.
- No standard or vendor types appear as top-level `dataTypes` entries.
- Modules, components, and types have roles and source files where detectable.
- Created objects show lifetime, storage, ownership, and confidence.
- Unresolved cleanup or ownership is visible as a warning.
- Mermaid diagrams render or show their source fallback.
- The dashboard works on desktop and narrow screens.
