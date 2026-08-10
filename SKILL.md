---
name: arch-wiki
description: >
  Scans embedded firmware projects and updates docs/architecture/architecture.json
  and docs/architecture/architecture.html with hardware, configuration, memory,
  modules, user-defined types, object ownership, diagrams, data pipelines, and build metadata.
---

# arch-wiki - Embedded Firmware Architecture Skill

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

### STEP 5 — Verify Dashboard in Browser

Verify `docs/architecture/architecture.html`:

1. **Top Header:** Brand title, subtitle, and badges (Version, Tech Stack, Generated Date) render at the top without navigation buttons.
2. **Left Sidebar:** All section buttons (`Overview`, `Prerequisites`, `API Modules`, `System Architecture`, `Docker Topology`, `Swagger & OpenAPI`, `Permissions`, `SQL Queries`, `Infrastructure`, `Core Layer`, `Request Pipeline`) are listed under `NAVIGATION`.
3. **Prerequisites Tab:** Software runtimes, container engines, database requirements, and step-by-step setup commands.
4. **Swagger & OpenAPI Tab:**
   - **Interactive Swagger UI:** Embedded native `SwaggerUIBundle` explorer with try-it-out functionality and dark theme overrides.
   - **API Catalog & cURL:** Endpoint list with copyable `cURL` request snippets.
   - **OpenAPI 3.0 JSON Spec:** Formatted JSON specification with 1-click copy button.
5. **Interactive Diagrams:** System Architecture and Docker Topology render cleanly via Mermaid.js with interactive pan/zoom toolbars and hand (grab) cursor feedback.
6. **SQL Queries:** Full system query catalog displayed with syntax highlighting and mapped endpoints.

---

## Quick-Use Prompt Templates

### Prompt A — "I added a new module"

```
Run arch-wiki to update the architecture map.

I just added a new module called [MODULE_NAME]:
- Files: src/modules/[name]/
- Base path: /api/v1/[path]
- Permissions needed: [list permissions]
- Endpoints:
  - GET / → [description] → permission: [x]
  - POST / → [description] → permission: [x]

Read docs/architecture/architecture.json, add the new module entry,
update permissions.catalog and details arrays,
then run: python docs/architecture/build_html.py
```

### Prompt B — "I added endpoints to an existing module"

```
Run arch-wiki to update the architecture map.

I added new endpoints to the [MODULE_NAME] module (id: [module-id]):
- [METHOD] [path] → [description] → permission: [x] or null

Read docs/architecture/architecture.json, find module with id "[module-id]",
add the new endpoints, update permissions.catalog,
then run: python docs/architecture/build_html.py
```

### Prompt C — "I updated Docker services or topology"

```
Run arch-wiki to update the architecture map.

I added/updated Docker services in docker-compose.yml:
- Service: [Name], Image: [image:tag], Port: [port], Type: [type]
- Inter-service connections: [from] -> [to] via [protocol]

Read docs/architecture/architecture.json, update infrastructure and dockerDiagram arrays,
then run: python docs/architecture/build_html.py
```

### Prompt D — "I added a new SQL Query or Repository Method"

```
Run arch-wiki to update the architecture map.

I added a new SQL query / repository function:
- File: src/modules/[module]/[file]
- Function: [ClassName.methodName()]
- SQL: "[SELECT ...]"
- Tables: [table1, table2]
- Purpose: [Explanation of what the query does]
- Mapped Endpoints: [METHOD /api/v1/path]

Read docs/architecture/architecture.json, append to sqlQueries array,
then run: python docs/architecture/build_html.py
```

### Prompt E — "I updated permissions or page mappings"

```
Run arch-wiki to update the architecture map.

I updated permission mappings:
- Permission Slug: [slug]
- Action: [READ|WRITE|DELETE]
- Mapped Endpoints: [METHOD /path]
- Admin Dashboard Pages: [Page Name]

Read docs/architecture/architecture.json, update permissions.details,
then run: python docs/architecture/build_html.py
```

### Prompt F — "Full Rescan & Parity Audit"

```
Run arch-wiki to rescan the codebase and sync the architecture map.

1. Read docs/architecture/architecture.json to inspect current manifest
2. Audit actual codebase:
   - Entry point / app bootstrap (route registrations, system endpoints)
   - All module route files (endpoints, permissions, swagger annotations)
   - All repository files (SQL queries, DB operations)
   - Middleware directory
   - docker-compose.yml (infrastructure & container topology)
3. Apply all edits to architecture.json
4. Run: python docs/architecture/build_html.py
5. Verify parity and report additions/changes
```
```bash
python3 /path/to/arch-wiki/templates/build_html.py --sync /path/to/firmware-project
```

The generator writes `docs/architecture/architecture.json` and
`docs/architecture/architecture.html` in the target project. It rescans and
regenerates both files on every invocation.

## Generated Sections

- Brief
- Project README
- Hardware
- Configurations
- Memory Layout
- Modules & Components
- Class Diagrams
- Sequence Diagrams
- Interaction Diagrams
- State Machines
- Flow Charts
- Data Pipelines
- Build

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
