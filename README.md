# arch-wiki-es

`arch-wiki-es` is an embedded firmware architecture and symbol documentation skill for AI coding assistants. It is a specialized fork of `arch-wiki` geared specifically towards embedded systems, microcontrollers, and firmware codebases. It bridges high-level firmware architecture mapping with Doxygen-style symbol extraction, call graphs, and hardware/configuration indexing.

It scans an embedded firmware repository and generates:

- `docs/architecture/architecture.json`: Machine-readable architecture metadata, symbol catalogs, and configuration parameters.
- `docs/architecture/architecture.html`: Interactive architecture dashboard with project documentation, searchable symbol index, and embedded Mermaid diagrams.

## Documented Architecture

Turn any backend codebase into an interactive architecture wiki that both developers and AI coding assistants can use.

`arch-wiki` is an AI skill (agent instruction set) that keeps your **living architecture documentation** in perfect sync with your codebase. Every time you add a module, endpoint, permission, SQL query, or Docker service — you invoke the skill, and it:
The generated files contain:

0. Brief
1. Project README
2. Hardware
3. Configurations
4. Memory Layout
5. Modules & Components
6. Class Diagrams
7. Sequence Diagrams
8. Interaction Diagrams
9. State Machines
10. Flow Charts
11. Data Pipelines
12. Build

The output is a **single self-contained HTML file** with:
- 📊 Overview stats dashboard
- 📋 System Prerequisites & Setup Pipeline
- 📦 API Modules catalog with all endpoints & 1-click AI Analysis Prompts
- 🤖 Interactive Senior Developer Analysis Prompts modal for every API endpoint
- 🏗️ System Architecture diagram with pan/zoom & hand cursor (Mermaid)
- 🐋 Docker Topology diagram with pan/zoom & hand cursor (Mermaid)
- 📄 One-click PDF Export (exports all 11 sections into a single formatted PDF document)
- ⚡ Interactive Swagger UI (try-it-out enabled with polished dark mode theme)
- 🔐 Permissions & RBAC mapping
- 🗃️ SQL Queries catalog with syntax highlighting
- 🖥️ Infrastructure services catalog
- 🛡️ Core Layer & Request Pipeline docs
Modules, components, and user-defined types include their role and structured source-file references. The type catalog excludes primitive, standard-library, vendor SDK, and RTOS types. User-defined types include their fields, usage roles, modules, components, evidence, and source locations.

Created objects include allocation kind, storage location, lifetime, owner, creator, ownership transfers, and release/destruction information. Unproven C/C++ ownership is reported as unknown with a warning rather than guessed.

The target project's README is embedded in both JSON and HTML at generation time. Regenerate after changing the README. Mermaid is loaded from a CDN when diagrams are rendered, so network access is needed for diagram rendering in a browser.

## Supported Projects

The scanner recognizes common markers for:
`arch-wiki-es` is dedicated exclusively to bare-metal, RTOS, and embedded Linux firmware, providing structured insight into hardware peripherals, memory maps, clock trees, state machines, call graphs, and build systems.

## Documented Architecture

## Project Structure

```
arch-wiki/
├── SKILL.md              ← AI skill definition
├── README.md             ← This file
└── templates/
    └── build_html.py       ← HTML dashboard generator + architecture.json initialiser (~83 KB)
```

> `architecture.json` is automatically generated on first run by `build_html.py --init`
> via a **zero-dependency codebase scanner**. It automatically scans your `docker-compose.yml`,
> route files (`*.routes.ts`, `routers/*.py`), and `package.json` to populate endpoints,
> services, workspaces, permissions, prerequisites, and SQL queries without manual setup!
> Built-in deduplication automatically filters out build directories (`dist/`, `build/`, `node_modules/`)
> to prevent duplicate route definitions.

**In your target project**, the architecture setup is simple:

```
your-project/
└── docs/
    └── architecture/
        ├── architecture.json   ← Generated on first run (AI keeps updated)
        ├── build_html.py       ← Generator (copied from arch-wiki/templates/)
        └── architecture.html   ← Generated output (never edit manually)
```

---

## Quick Start (Installation & Setup)
It reads source/header files, build files, linker scripts, map files, device-tree files, Kconfig files, and project README content using only Python's standard library.
The generated documentation contains:

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

Analysis is entirely dependency-free and uses only Python's standard library.

## Install

```bash
npx arch-wiki-es
```

For local development:

```bash
node ./bin/install.js
```

The installer registers `SKILL.md` and the generator script with supported AI assistant skill environments (Antigravity, Claude Code, and local workspace `.skills/`).

## Generate Documentation

Once installed, **you never need to run python scripts manually**. Simply open your AI coding assistant and ask:

> 💬 *"Run the `arch-wiki` skill on this project"*

The AI Assistant will autonomously:
1. Copy the codebase scanner engine into `docs/architecture/build_html.py`.
2. Scan Docker services (`docker-compose.yml`), API endpoints (`*.routes.ts`, `routers/*.py`), permissions, prerequisites, and SQL queries.
3. Create/Sync `docs/architecture/architecture.json`.
4. Generate the interactive dashboard at `docs/architecture/architecture.html`.

---

## Setup Guides

### Setup in Antigravity

Copy `SKILL.md` into your Antigravity skills directory:
From a target firmware project after installing the skill:
Run the generator from the target firmware repository:

```bash
python3 docs/architecture/build_html.py --init
```

For subsequent updates after firmware changes:

```bash
python3 docs/architecture/build_html.py --sync
```

To scan a target project from an external checkout:

```bash
python3 /path/to/arch-wiki-es/templates/build_html.py --init /path/to/firmware-project
```

The generated dashboard can be opened directly in any web browser. Mermaid diagrams render client-side using the Mermaid CDN.

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

## Types and Source Traceability

Only project-defined types are documented as `dataTypes`. Primitive types, standard-library types, RTOS types, vendor HAL types, and external dependency types are excluded from top-level catalogs (though they appear as parameter or field types).

Each module, component, and user-defined type includes structured file references where detected:

```json
{
  "path": "src/sensors/sensor_manager.c",
  "role": "implementation",
  "contains": ["sensor_manager_init"],
  "line": 42
}
```

User-defined type entries include:

- The type's firmware role.
- Struct fields and enum members (with values).
- Modules and components that use the type.
- Usage roles such as `produces`, `consumes`, `queues`, `serializes`, or `stores`.
- Definition files and line evidence.

## Object Lifetime and Storage

The `objects` section documents concrete instances and resources created by firmware:

- Global and static variables (in `.data` or `.bss`).
- Stack allocations.
- Dynamic heap allocations (`malloc`, `calloc`, `pvPortMalloc`).
- RTOS resources such as task stacks, message queues, and semaphores.
- Peripheral handles and hardware buffers.

Each object records storage location, memory section, lifetime scope, creator function, and ownership model. Unproven C/C++ ownership is reported as `unknown` with low confidence rather than guessed.

## Manual Overrides

For hardware specifications, safety constraints, or pin functions that cannot be deduced from source code alone, add an optional override file at:

```text
docs/architecture/embedded-overrides.json
```

Use it to provide board/MCU details, pin mappings, power and timing requirements, memory partitions, module/component roles, user-defined type relationships, object ownership, diagrams, and flash/debug commands. The example format is in `templates/embedded-overrides.example.json`.

### 🤖 Interactive Senior Developer Endpoint Analysis Prompts

Clicking on **any API endpoint** in the **API Modules** view (or using its **📋 Prompt** button) opens an interactive modal with a tailor-made **Senior Developer Analysis Prompt**.

The prompt is dynamically formatted for the selected endpoint (e.g. `POST /api/v1/orders`), instructing an AI coding assistant to:
1. Act as a senior developer joining the project.
2. Analyze the endpoint using `architecture.json`, `arch-wiki` documentation, and project source code.
3. Discover the actual implementation flow and generate accurate **Mermaid sequence** and **flowchart** diagrams.
4. Adhere to strict boundaries (only include components and interactions that actually exist in code, do not infer missing components, do not modify code).

Includes a 1-click **📋 Copy to Clipboard** button directly on every endpoint card and inside the modal for instant integration with AI assistants.

---
Override values are merged after scanner output. Lists containing objects with an `id` replace matching generated entries; object values extend generated sections. Invalid override JSON is reported in the generated manifest warnings.
Use it to supply board details, pin mappings, power budgets, memory partitions, or custom state machines. Overrides are merged into the generated data at scan time. An example format is available in `templates/embedded-overrides.example.json`.

## Project Structure

| Section | Purpose |
|---|---|
| `meta` | Project name, version, generated date, tech stack |
| `prerequisites` | Required runtime engines, infrastructure tools, databases, and setup steps |
| `workspaces` | Monorepo apps/packages (backend, frontend, packages) |
| `infrastructure` | Docker services (database, cache, queue, proxy, etc.) |
| `dockerDiagram` | Container topology nodes & edges for Mermaid diagram |
| `systemArchitectureDiagram` | Software component diagram nodes & edges |
| `swaggerSchemas` | OpenAPI spec metadata, servers, security scheme, schemas |
| `modules` | API modules with endpoints, permissions, file lists |
| `systemEndpoints` | Health/telemetry endpoints outside module structure |
| `coreLayer` | Middleware, core services, guards |
| `dataFlow` | Request pipeline steps (for the Request Pipeline view) |
| `permissions` | RBAC catalog (slugs list + detailed endpoint/page mappings) |
| `sqlQueries` | SQL query catalog with function, tables, purpose, endpoints |

---

## Framework Compatibility

The skill is designed to work with **any backend framework**. The AI adapts the source file scanning paths based on your stack:

| Framework | Route Files | Repository/Query Files |
|---|---|---|
| **Express / NestJS** | `src/modules/<name>/<name>.routes.ts` | `src/modules/<name>/<name>.repository.ts` |
| **FastAPI** | `app/routers/<name>.py` | `app/crud/<name>.py` |
| **Django** | `<app>/urls.py` + `views.py` | `<app>/models.py` |
| **Rails** | `config/routes.rb` + `app/controllers/` | `app/models/` |
| **Laravel** | `routes/api.php` + `app/Http/Controllers/` | `app/Models/` |
| **Spring Boot** | `src/.../controller/` | `src/.../repository/` |
| **Go (Gin/Echo)** | `internal/handler/` | `internal/repository/` |

---

## Dashboard Screenshots

The generated `architecture.html` includes 11 navigation sections:

| Section | Description |
|---|---|
| 📌 **Overview** | Stats cards + workspace list + system endpoints |
| 📋 **Prerequisites** | Developer tools, database runtimes, & step-by-step setup commands |
| 📦 **API Modules** | Searchable module cards with all endpoints & 1-click Senior Developer AI analysis prompt modals |
| 🏗️ **System Architecture** | Mermaid component diagram with pan/zoom toolbar & hand cursor |
| 🐋 **Docker Topology** | Mermaid container dependency graph with pan/zoom toolbar & hand cursor |
| ⚡ **Swagger & OpenAPI** | Live Swagger UI (Dark Theme), API catalog with cURL snippets, & OpenAPI JSON spec |
| 🔐 **Permissions & Scopes** | RBAC catalog, system scope fallbacks (authenticated/public), & scope-to-endpoint mapping |
| 🗃️ **SQL Queries** | Query catalog with SQL syntax highlighting |
| 🖥️ **Infrastructure** | Docker service cards with feature tags |
| 🛡️ **Core Layer** | Middleware and core service documentation |
| 🔄 **Request Pipeline** | Step-by-step request flow visualization |
| 📄 **PDF Export** | 1-click PDF generator that forces pre-rendering of diagrams, Swagger views, and scope mappings |

```text
arch-wiki-es/
├── SKILL.md
├── README.md
├── bin/install.js
├── templates/
│   ├── architecture.json
│   ├── architecture.html
│   ├── build_html.py
│   └── embedded-overrides.example.json
└── plans/
    └── embedded-arch-wiki.md
```

## Limitations

## Benchmark

The benchmark compares the same software understanding tasks using two approaches:

1. Direct AI exploration of the repository.
2. AI using `arch-wiki` and `architecture.json`.

The goal is not to measure token consumption only. The main goal is to evaluate whether `arch-wiki` can reduce repository exploration while producing a more accurate and useful architecture understanding.

### 1. Benchmark Prompts

| # | Task | Prompt |
|---|---|---|
| 1 | General Architecture | `Understand this project and explain: 1. Main architecture 2. Main modules 3. How an Order request flows through the system 4. Database interaction 5. External services. Do not modify anything.` |
| 2 | General Architecture with arch-wiki | Same prompt, with: `Use arch-wiki and architecture.json. Do not modify anything.` |
| 3 | Authentication Understanding | `You are joining this project as a new senior developer. You need to understand how authentication works. Explain: 1. Login flow 2. JWT generation 3. Refresh token flow 4. Database interaction 5. Redis interaction 6. Relevant files.` |
| 4 | Authentication with arch-wiki | Same prompt, with: `Use arch-wiki and architecture.json.` |
| 5 | Change Impact Analysis | `You need to add a new authentication feature. Find where this functionality should be implemented and explain which files would need to change and why. Do not modify anything.` |
| 6 | Change Impact Analysis with arch-wiki | Same prompt, with: `Use arch-wiki and architecture.json. Do not modify anything.` |

### 2. Results

| # | Approach | Exploration | Time | Result |
|---|---|---:|---:|---|
| 1 | Direct repository exploration | 17 files / 14 folders | ~2 min | Detailed architecture analysis with strong source-level details, but some conclusions were inaccurate or inferred. |
| 2 | `arch-wiki` + `architecture.json` | 1 file / 3 folders | ~1 min | Much faster and significantly less exploration. Produced a comprehensive architecture overview, but some details were inferred incorrectly. |
| 3 | Direct repository exploration | 7 files / 10 folders | ~1 min | Strong authentication analysis with detailed login, JWT, refresh token, DB and Redis flows. |
| 4 | `arch-wiki` + `architecture.json` | 7 files / 7 folders | ~1 min | Similar quality to direct exploration while using the architecture documentation to guide the investigation. |
| 5 | Direct repository exploration | 11 files / 20 folders | ~1 min | Good change impact analysis, but explored a relatively large part of the repository for an authentication-related task. |
| 6 | `arch-wiki` + `architecture.json` | 1 file / 6 folders | ~1 min | Much more focused exploration and produced a useful change-impact map based on the existing architecture. |

### 3. Opinion

| # | Task | Opinion |
|---|---|---|
| 1 vs 2 | General Architecture | **Major improvement.** `arch-wiki` reduced exploration from 17 files / 14 folders to 1 file / 3 folders while still producing a comprehensive architecture overview. The main weakness is that the AI may trust documented information too much and infer details that are not actually present in the source code. |
| 3 vs 4 | Authentication | **Very similar quality.** The direct approach explored 7 files / 10 folders, while the `arch-wiki` approach explored 7 files / 7 folders. This shows that the generated architecture information can guide the AI without sacrificing much accuracy. |
| 5 vs 6 | Change Impact | **Strong improvement.** The direct approach explored 11 files / 20 folders, while the `arch-wiki` approach explored only 1 file / 6 folders. The architecture manifest helped the AI identify the relevant architectural boundaries and affected files much faster. |

### 4. Initial Benchmark Conclusion

The most interesting result is not simply that `arch-wiki` makes the AI faster.

The important observation is:

> **The AI can use a pre-generated architecture representation as a map of the system instead of rediscovering the architecture from scratch for every question.**

In the tested scenarios, `arch-wiki` significantly reduced repository exploration, especially for high-level architecture and change-impact questions.

The benchmark also exposed an important limitation:

> **Architecture documentation must be accurate. If `architecture.json` contains incorrect or inferred information, the AI can propagate those mistakes instead of discovering the truth directly from the source code.**

Therefore, the next step is to measure **accuracy**, not just exploration reduction.


## Requirements
The scanner is intentionally dependency-free and evidence-based. It does not replace a compiler, linker, static analyzer, or hardware review. Complex macro-generated types, custom allocators, ownership conventions, electrical constraints, and generated diagrams may require manual overrides.

Current analysis is intentionally conservative:
The scanner is intentionally lightweight, dependency-free, and evidence-based:

- Hardware parameters are extracted from recognizable configuration markers, register initializations, and build settings.
- Static C/C++ analysis cannot infer pointer ownership through complex macro layers or function pointer tables without explicit evidence or overrides.
- The built-in Markdown renderer handles standard README constructs without requiring external libraries.
- The generator runs on standard Python 3 with zero third-party package dependencies.

## License

MIT.
