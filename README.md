# arch-wiki

`arch-wiki` is an embedded firmware architecture documentation skill for AI coding assistants. It scans a firmware repository and generates:

- `docs/architecture/architecture.json`: machine-readable architecture metadata.
- `docs/architecture/architecture.html`: interactive architecture dashboard with the project README and generated diagrams embedded in the output.

The tool is embedded-only. It documents firmware and hardware rather than REST APIs, SQL, Swagger, Docker, or backend services.

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

- Bare-metal C/C++
- FreeRTOS
- Zephyr
- Embedded Linux/device tree
- PlatformIO
- CMake
- Make
- ESP-IDF
- STM32CubeMX
- Rust embedded projects

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

## Install

```bash
npx arch-wiki
```

For local development:

```bash
node ./bin/install.js
```

The installer registers `SKILL.md` and the scanner with supported AI assistant skill locations.

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

```bash
python3 docs/architecture/build_html.py --init
```

For subsequent changes:

```bash
python3 docs/architecture/build_html.py --sync
```

The script creates `docs/architecture/` when needed. The first run creates or replaces the generated JSON and HTML files. Subsequent runs rescan the project and regenerate both files.

To scan a different project from a local checkout:

```bash
python3 /path/to/arch-wiki/templates/build_html.py --init /path/to/firmware-project
```

The target project must be passed as an existing path. If no target path is supplied, the current working directory is scanned.

The generated dashboard can be opened directly in a browser. Mermaid diagrams require access to the Mermaid CDN referenced by the HTML.

## Manifest Sections

`architecture.json` contains these top-level sections:

| Section | Contents |
|---|---|
| `meta` | Project type, languages, detected markers, and generation date |
| `readme` | Embedded project README content and source metadata |
| `brief` | System purpose, constraints, and documentation status |
| `hardware` | MCU, board, peripherals, interfaces, pins, and power metadata |
| `configurations` | Build profiles, feature flags, Kconfig, and device-tree settings |
| `memoryLayout` | Linker regions, sections, partitions, stack, heap, and map files |
| `modules` | Logical firmware subsystems, roles, files, tasks, and type usage |
| `components` | Concrete source-level drivers, services, HALs, and application units |
| `dataTypes` | Project-defined structs, enums, unions, typedefs, classes, and traits |
| `objects` | Created objects, storage, lifetime, ownership, and cleanup metadata |
| `diagrams` | Class, sequence, interaction, state, and flow diagrams |
| `dataPipelines` | Detected data movement between firmware modules |
| `build` | Build system, toolchain, targets, artifacts, and flash/debug metadata |

## Types and Source Traceability

Only project-defined types are documented as `dataTypes`. Primitive types, standard-library types, RTOS types, vendor HAL types, and external dependency types are excluded. They can still appear as field or signature labels.

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
- Fields and references to other project-defined types.
- Modules and components that use the type.
- Usage roles such as `produces`, `consumes`, `queues`, `serializes`, or `stores`.
- Definition and usage files.
- Evidence and confidence metadata.

## Object Lifetime and Ownership

The `objects` section documents concrete instances and resources created by firmware, including:

- Global and static objects.
- Stack objects.
- Heap allocations.
- RTOS resources such as tasks and queues.
- Pool-managed objects.
- Peripheral handles and buffers where detectable.

Each object may include:

- User-defined type reference.
- Runtime role.
- Storage location and memory section.
- Lifetime scope and start/end events.
- Creator and destruction/release path.
- Owner and ownership model.
- Ownership transfers and usage files.

C and C++ ownership cannot always be proven statically. The scanner reports `unknown` ownership and low confidence instead of claiming a transfer or cleanup path without evidence.

## Manual Overrides

Static analysis cannot reliably determine every board detail, safety constraint, or ownership policy. Add an optional file at:

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
arch-wiki/
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

- Hardware values are extracted only from recognizable source/configuration markers.
- Detailed pin maps, clock trees, power budgets, and runtime configuration require explicit source evidence or overrides.
- C/C++ ownership is uncertain when custom allocators, callbacks, or pointer conventions obscure responsibility.
- Generated diagrams are starting points and should be reviewed against the firmware.
- The built-in Markdown renderer covers common README constructs, not the complete Markdown specification.
- The generator uses only the Python standard library; no third-party Python package is required.

## License

MIT.
