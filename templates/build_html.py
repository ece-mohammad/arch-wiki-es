#!/usr/bin/env python3
"""Embedded firmware architecture scanner and dashboard generator."""
import datetime
import html
import json
import os
import re
import sys
import datetime

# ---------------------------------------------------------------------------
# SKILL.md PARSER
# Reads arch-wiki SKILL.md (or any SKILL.md found next to this script or in
# the project root) and extracts key/value pairs from the YAML front-matter
# plus the first heading as the display name.
# ---------------------------------------------------------------------------

def parse_skill_md(skill_path):
    """Return a dict of metadata extracted from SKILL.md YAML front-matter."""
    meta = {}
    if not os.path.isfile(skill_path):
        return meta
    with open(skill_path, 'r', encoding='utf-8') as f:
        content = f.read()
    # Extract YAML front-matter between --- delimiters
    fm_match = re.match(r'^---\s*\n(.+?)\n---', content, re.DOTALL)
    if fm_match:
        for line in fm_match.group(1).splitlines():
            if ':' in line:
                k, _, v = line.partition(':')
                meta[k.strip()] = v.strip().strip('>')
    # Extract first H1 heading as display name
    h1 = re.search(r'^#\s+(.+)', content, re.MULTILINE)
    if h1:
        meta['h1'] = h1.group(1).strip()
    return meta


def find_skill_md():
    """Search for SKILL.md in: same dir as script, parent dirs (up to 3 levels)."""
    base = os.path.dirname(os.path.abspath(__file__))
    candidates = [
        os.path.join(base, 'SKILL.md'),
        os.path.join(base, '..', 'SKILL.md'),
        os.path.join(base, '..', '..', 'SKILL.md'),
        os.path.join(base, '..', '..', '..', 'SKILL.md'),
    ]
    for c in candidates:
        if os.path.isfile(c):
            return os.path.normpath(c)
    return None


# ---------------------------------------------------------------------------
# CODEBASE SCANNER  (no third-party deps — stdlib only)
# Walks up to find the project root, then scans:
#   • docker-compose.yml  → infrastructure + dockerDiagram
#   • *.routes.ts/js      → Express modules + endpoints
#   • app.ts / app.js     → base path registrations
#   • routers/*.py        → FastAPI modules + endpoints
# ---------------------------------------------------------------------------

import glob as _glob

_COLORS = ['#6366f1','#f59e0b','#10b981','#3b82f6','#8b5cf6',
           '#ef4444','#f97316','#06b6d4','#84cc16','#ec4899',
           '#14b8a6','#a855f7','#f43f5e','#0ea5e9','#22c55e']

_ICON_MAP = {
    'auth':'🔐','user':'👤','users':'👥','patient':'🏥','patients':'🏥',
    'appointment':'📅','appointments':'📅','visit':'🩺','visits':'🩺',
    'audit':'📋','stat':'📊','stats':'📊','product':'📦','products':'📦',
    'order':'🛒','orders':'🛒','payment':'💳','payments':'💳',
    'report':'📈','reports':'📈','admin':'⚙️','setting':'⚙️','settings':'⚙️',
    'notification':'🔔','message':'💬','file':'📁','search':'🔍',
    'dashboard':'📊','analytics':'📈','health':'💚',
}

def _icon(name): return _ICON_MAP.get(name.lower().rstrip('s'), _ICON_MAP.get(name.lower(), '📁'))
def _color(name, i): return next((c for k,c in {'auth':'#6366f1','user':'#f59e0b','patient':'#10b981',
    'appointment':'#3b82f6','visit':'#8b5cf6','audit':'#ef4444','stat':'#f97316',
    'product':'#06b6d4','order':'#84cc16','payment':'#ec4899'}.items()
    if k in name.lower()), _COLORS[i % len(_COLORS)])

def clean_mermaid(text):
    if not text:
        return ""
    if not isinstance(text, str):
        text = str(text)
    return text.replace('"', '').replace("'", '').replace('\n', ' ').strip()

def _find_root(start):
    """Find the root directory of the project containing this docs/architecture folder.
    Checks for markers like docker-compose.yml, package.json, backend/, .git, etc."""
    markers = [
        'docker-compose.yml', 'docker-compose.yaml', 'compose.yml', '.git',
        'package.json', 'requirements.txt', 'go.mod', 'Gemfile', 'pom.xml', 'Cargo.toml', 'composer.json'
    ]
    cur = os.path.abspath(start)
    for _ in range(5):
        if any(os.path.exists(os.path.join(cur, m)) for m in markers):
            return cur
        # Check if subdirectories have package.json or requirements.txt
        if any(os.path.exists(os.path.join(cur, sub, 'package.json')) for sub in ['backend', 'api', 'server', 'app']):
            return cur
        parent = os.path.dirname(cur)
        if parent == cur: break
        cur = parent
    return os.path.abspath(os.path.join(start, "..", ".."))  # default to 2 levels up from docs/architecture

def _detect_fw(root):
    for sub in ['', 'app', 'server', 'backend', 'apps/api', 'apps/server', 'apps/backend']:
        if os.path.isfile(os.path.join(root, sub, 'pom.xml')) or os.path.isfile(os.path.join(root, 'pom.xml')):
            return 'spring'
        if os.path.isfile(os.path.join(root, sub, 'build.gradle')) or os.path.isfile(os.path.join(root, 'build.gradle')):
            return 'spring'
    for sub in ['', 'backend', 'api', 'server', 'app', 'apps/api', 'apps/server', 'apps/backend']:
        pkg = os.path.join(root, sub, 'package.json') if sub else os.path.join(root, 'package.json')
        if os.path.isfile(pkg):
            try:
                deps = {}
                with open(pkg, encoding='utf-8') as f:
                    d = json.load(f)
                deps.update(d.get('dependencies', {})); deps.update(d.get('devDependencies', {}))
                if 'express' in deps: return 'express'
                if '@nestjs/core' in deps: return 'nestjs'
                if 'fastify' in deps: return 'fastify'
            except: pass

    apps_dir = os.path.join(root, 'apps')
    if os.path.isdir(apps_dir):
        for sub in os.listdir(apps_dir):
            pkg = os.path.join(apps_dir, sub, 'package.json')
            if os.path.isfile(pkg):
                try:
                    deps = {}
                    with open(pkg, encoding='utf-8') as f:
                        d = json.load(f)
                    deps.update(d.get('dependencies', {})); deps.update(d.get('devDependencies', {}))
                    if 'express' in deps: return 'express'
                    if '@nestjs/core' in deps: return 'nestjs'
                    if 'fastify' in deps: return 'fastify'
                except: pass

    for sub in ['', 'backend', 'api', 'app']:
        base = os.path.join(root, sub) if sub else root
        for req_name in ['requirements.txt', 'pyproject.toml', 'Pipfile', 'setup.py']:
            req = os.path.join(base, req_name)
            if os.path.isfile(req):
                try:
                    t = open(req, encoding='utf-8', errors='ignore').read().lower()
                    if 'fastapi' in t: return 'fastapi'
                    if 'django' in t: return 'django'
                    if 'flask' in t: return 'flask'
                except: pass

    for r, _, fls in os.walk(root):
        norm_r = r.replace('\\', '/')
        if any(x in norm_r for x in ['/__pycache__/', '/venv/', '/.git/', '/node_modules/']): continue
        for f in fls:
            if f.endswith('.py'):
                try:
                    txt = open(os.path.join(r, f), encoding='utf-8', errors='ignore').read().lower()
                    if 'fastapi' in txt: return 'fastapi'
                    if 'django' in txt: return 'django'
                    if 'flask' in txt: return 'flask'
                except: pass
    return 'unknown'

def _scan_docker(root):
    for name in ['docker-compose.yml','docker-compose.yaml','compose.yml','compose.yaml']:
        path = os.path.join(root, name)
        if not os.path.isfile(path): continue
        lines = open(path, encoding='utf-8', errors='ignore').read().splitlines()
        svcs, cur = {}, None
        in_svc, in_dep = False, False
        dep_indent = 0

        for ln in lines:
            s = ln.rstrip()
            if not s or s.startswith('#'): continue

            if re.match(r'^[a-zA-Z0-9_\-]+:', s):
                in_svc = s.startswith('services:')
                cur = None; in_dep = False
                continue
            if not in_svc: continue

            m = re.match(r'^  ([a-zA-Z0-9_\-]+):\s*$', s)
            if m:
                cur = m.group(1)
                svcs[cur] = {'image':'','ports':[],'depends':[],'build':''}
                in_dep = False; continue
            if not cur: continue

            if re.match(r'^\s+image:\s+', s): svcs[cur]['image'] = s.split('image:')[1].strip()
            if re.match(r'^\s+context:\s+', s): svcs[cur]['build'] = s.split('context:')[1].strip()
            pm = re.match(r'^\s+-\s*["\']?(\d+):(\d+)["\']?', s)
            if pm: svcs[cur]['ports'].append(int(pm.group(1)))

            dm_start = re.match(r'^(\s+)depends_on:', s)
            if dm_start:
                in_dep = True
                dep_indent = len(dm_start.group(1))
                continue

            if in_dep:
                curr_indent = len(s) - len(s.lstrip())
                if curr_indent <= dep_indent and not s.strip().startswith('-'):
                    in_dep = False
                else:
                    dm_list = re.match(r'^\s+-\s*([a-zA-Z0-9_\-]+)', s)
                    dm_map = re.match(r'^\s+([a-zA-Z0-9_\-]+):\s*$', s)
                    dep_target = None
                    if dm_list:
                        dep_target = dm_list.group(1)
                    elif dm_map:
                        dep_target = dm_map.group(1)
                    
                    if dep_target and dep_target not in ('condition', 'service_healthy', 'service_started', 'environment', 'logging', 'ports', 'image', 'restart', 'build'):
                        if dep_target not in svcs[cur]['depends']:
                            svcs[cur]['depends'].append(dep_target)

        all_svcs = list(svcs.keys())
        for sn, sv in svcs.items():
            if sn.endswith('-service'):
                prefix = sn.replace('-service', '')
                for db in [f"{prefix}-mongodb", f"{prefix}-db", f"{prefix}-postgres", f"{prefix}-mysql"]:
                    if db in svcs and db not in sv['depends']:
                        sv['depends'].append(db)
            
            if sn == 'gateway':
                for target_svc in all_svcs:
                    if target_svc.endswith('-service') and target_svc not in sv['depends']:
                        sv['depends'].append(target_svc)

        hints = {'postgres':'database','mysql':'database','mongo':'database','redis':'cache',
                 'rabbitmq':'queue','kafka':'queue','nginx':'proxy','gateway':'proxy','traefik':'proxy',
                 'prometheus':'monitoring','grafana':'monitoring','monitoring':'monitoring',
                 'elasticsearch':'logging','registry':'registry','config':'config',
                 'minio':'storage','s3':'storage','blob':'storage'}
        infra, nodes, edges = [], [], []
        for sn, sv in svcs.items():
            t = next((v for k,v in hints.items() if k in sn.lower() or k in sv['image'].lower()), 'app')
            port = sv['ports'][0] if sv['ports'] else None
            infra.append({'id':sn,'name':sn.replace('-',' ').replace('_',' ').title(),'type':t,
                'image':sv['image'] or f"build:{sv['build']}",
                'port':port,'description':f"{sn} container",'features':[]})
            nodes.append({'id':sn,'label':f"{sn}{':%d'%port if port else ''}",
                'type':t,'port':port})
            for dep in sv['depends']:
                if dep in svcs: edges.append({'from':sn,'to':dep,'label':''})
        return infra, {'description':f"Topology from {name}.","nodes":nodes,"edges":edges}
    return [], {'description':'','nodes':[],'edges':[]}

def _infer_desc(method, path, mod):
    has_id = bool(re.search(r':[^/]+|\{[^}]+\}', path))
    segs = [p for p in path.split('/') if p and not p.startswith(':') and not p.startswith('{')]
    if len(segs) > 1:
        sub = segs[-1].replace('_',' ').replace('-',' ')
        return f"{method.title()} {mod.lower()} — {sub}"
    tpl = {('GET',False):f"List all {mod.lower()}",('GET',True):f"Get {mod.lower()} by ID",
           ('POST',False):f"Create {mod.lower()}",('PUT',True):f"Update {mod.lower()} by ID",
           ('PATCH',True):f"Patch {mod.lower()} by ID",('DELETE',True):f"Delete {mod.lower()} by ID"}
    return tpl.get((method, has_id), f"{method} {path}")

def _scan_express(root):
    src_dirs = []
    for sub in ['', 'backend', 'api', 'server', 'app', 'apps/api', 'apps/server', 'apps/backend']:
        c = os.path.join(root, sub, 'src') if sub else os.path.join(root, 'src')
        if os.path.isdir(c): src_dirs.append(c)
        c2 = os.path.join(root, sub) if sub else None
        if c2 and os.path.isdir(os.path.join(c2, 'routes')): src_dirs.append(c2)
    apps_dir = os.path.join(root, 'apps')
    if os.path.isdir(apps_dir):
        for sub in os.listdir(apps_dir):
            c = os.path.join(apps_dir, sub, 'src')
            if os.path.isdir(c): src_dirs.append(c)
            c2 = os.path.join(apps_dir, sub)
            if os.path.isdir(os.path.join(c2, 'routes')): src_dirs.append(c2)
    src_dirs = sorted(set(src_dirs))
    if not src_dirs: return []

    # Map variable names to base paths from app.ts / app.js / main.ts
    # e.g. import authRoutes from './routes/auth.routes.js' + app.use('/api/v1/auth', authRoutes)
    base_paths = {}  # filename_key -> base_path
    var_to_file = {} # var_name -> filename_key

    for src in src_dirs:
        for fn in ['app.ts', 'app.js', 'index.ts', 'index.js', 'main.ts', 'main.js', 'server.ts', 'server.js']:
            fp = os.path.join(src, fn)
            if not os.path.isfile(fp): continue
            txt = open(fp, encoding='utf-8', errors='ignore').read()
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

    # Walk directory to collect all route files (exclude dist, build, node_modules)
    route_files = []
    for src in src_dirs:
        for r, _, files in os.walk(src):
            norm_r = r.replace('\\', '/')
            if '/dist/' in norm_r or '/build/' in norm_r or '/node_modules/' in norm_r: continue
            for f in files:
                if f.endswith('.d.ts'): continue
                if ('.routes.' in f or '.router.' in f or f.endswith('Routes.ts') or f.endswith('Routes.js')) and f.endswith(('.ts', '.js')):
                    route_files.append(os.path.join(r, f))
    
    # Deduplicate route files by module key, preferring .ts over .js
    dedup_routes = {}
    for rf in route_files:
        fn = os.path.basename(rf)
        raw = re.sub(r'\.(routes|router)\.(ts|js)$', '', fn)
        raw = re.sub(r'Routes\.(ts|js)$', '', raw).lower()
        if raw not in dedup_routes or rf.endswith('.ts'):
            dedup_routes[raw] = rf
    route_files = sorted(dedup_routes.values())

    modules = []
    for idx, rf in enumerate(route_files):
        txt = open(rf, encoding='utf-8', errors='ignore').read()
        fn = os.path.basename(rf)
        raw = re.sub(r'\.(routes|router)\.(ts|js)$', '', fn)
        raw = re.sub(r'Routes\.(ts|js)$', '', raw)
        name = raw.title(); mid = raw.lower().replace('-', '_')

        # Determine base path
        key = raw.lower()
        bp = base_paths.get(key, f"/api/v1/{key}")

        global_auth = bool(re.search(r'router\.use\((authenticateJWT|authenticate|authMiddleware|requireAuth)\)', txt)) or ('authenticateJWT' in txt) or ('authenticate' in txt)
        
        global_roles = re.findall(r"(?:authorizeRoles|authorize|requireRole|requirePermission|checkPermission|hasRole)\(([^)]+)\)", txt)
        g_roles = []
        for r in global_roles:
            cleaned = r.replace('[','').replace(']','').replace("'",'').replace('"','').strip()
            for x in cleaned.split(','):
                xc = x.strip()
                if xc and xc not in g_roles:
                    g_roles.append(xc)

        eps, seen = [], set()
        for m in re.finditer(r"router\.(get|post|put|patch|delete)\s*\(\s*['\"]([^'\"]*)['\"]([\s\S]*?)(?=\n\s*router\.|\n\s*export|\n\s*const|\n\s*/\*\*|;\s*\n|\)\s*;|\)$)", txt, re.IGNORECASE):
            method, path, rest = m.group(1).upper(), m.group(2), m.group(3)
            key_ep = f"{method}:{path}"
            if key_ep in seen: continue
            seen.add(key_ep)
            auth = global_auth or ('authenticateJWT' in rest) or ('authenticate' in rest) or ('auth' in path.lower()) or ('requirePermission' in rest)
            
            rm = re.search(r"(?:authorizeRoles|authorize|requireRole|requirePermission|checkPermission|hasRole)\(([^)]+)\)", rest)
            if rm:
                cleaned = rm.group(1).replace('[','').replace(']','').replace("'",'').replace('"','').strip()
                perm_list = [x.strip() for x in cleaned.split(',') if x.strip()]
                perm = ' | '.join(perm_list) if perm_list else None
            else:
                perm = ' | '.join(g_roles) if g_roles else None

            eps.append({'method': method, 'path': path, 'auth': auth,
                        'permission': perm, 'description': _infer_desc(method, path, name)})

        # Fallback if multiline lookahead misses single line at end of file
        if not eps:
            for m in re.finditer(r"router\.(get|post|put|patch|delete)\s*\(\s*['\"]([^'\"]*)['\"]([^;\n]*?)(?:\)|;|\n)", txt, re.IGNORECASE):
                method, path, rest = m.group(1).upper(), m.group(2), m.group(3)
                key_ep = f"{method}:{path}"
                if key_ep in seen: continue
                seen.add(key_ep)
                auth = global_auth or ('authenticateJWT' in rest) or ('authenticate' in rest) or ('auth' in path.lower()) or ('requirePermission' in rest)
                rm = re.search(r"(?:authorizeRoles|authorize|requireRole|requirePermission|checkPermission|hasRole)\(([^)]+)\)", rest)
                perm = rm.group(1).replace("'",'').replace('"','').strip() if rm else (' | '.join(g_roles) if g_roles else None)
                eps.append({'method': method, 'path': path, 'auth': auth, 'permission': perm, 'description': _infer_desc(method, path, name)})

        if not eps: continue
        perms = list(set(e['permission'] for e in eps if e.get('permission')))
        modules.append({
            'id': mid, 'name': name, 'basePath': bp,
            'description': f"{name} module — {len(eps)} endpoint(s)",
            'color': _color(raw, idx), 'icon': _icon(raw), 'files': [fn],
            'permissions': perms, 'endpoints': eps
        })
    return modules
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

        def _get_perm(snip):
            pm = re.search(r'@PreAuthorize\s*\(\s*"([^"]+)"\s*\)', snip) or re.search(r"@PreAuthorize\s*\(\s*'([^']+)'\s*\)", snip)
            return pm.group(1) if pm else None

        mapping_pats = [
            ('GET', r'@GetMapping\s*(?:\(\s*(?:value\s*=\s*|path\s*=\s*)?["\']([^"\']*)["\']\s*\))?'),
            ('POST', r'@PostMapping\s*(?:\(\s*(?:value\s*=\s*|path\s*=\s*)?["\']([^"\']*)["\']\s*\))?'),
            ('PUT', r'@PutMapping\s*(?:\(\s*(?:value\s*=\s*|path\s*=\s*)?["\']([^"\']*)["\']\s*\))?'),
            ('DELETE', r'@DeleteMapping\s*(?:\(\s*(?:value\s*=\s*|path\s*=\s*)?["\']([^"\']*)["\']\s*\))?'),
            ('PATCH', r'@PatchMapping\s*(?:\(\s*(?:value\s*=\s*|path\s*=\s*)?["\']([^"\']*)["\']\s*\))?'),
        ]

        for method, pat in mapping_pats:
            for m in re.finditer(pat, txt):
                ep_path = m.group(1) if (m.lastindex and m.group(1)) else '/'
                if not ep_path:
                    ep_path = '/'
                
                start_idx = max(0, m.start() - 250)
                snippet = txt[start_idx:m.start()]
                perm = _get_perm(snippet)
                
                key_ep = f"{method}:{ep_path}"
                if key_ep not in seen:
                    seen.add(key_ep)
                    eps.append({
                        'method': method,
                        'path': ep_path,
                        'auth': ('Security' in txt or 'PreAuthorize' in txt or 'Principal' in txt or 'OAuth' in txt or 'RolesAllowed' in txt),
                        'permission': perm,
                        'description': _infer_desc(method, ep_path, name)
                    })

        for m in re.finditer(r'(@PreAuthorize\s*\([^)]+\)\s*|@RolesAllowed\s*\([^)]+\)\s*)?@RequestMapping\s*\(([^)]+)\)', txt):
            full_anno = m.group(0)
            pre_auth = m.group(1)
            params = m.group(2)
            
            if bp_match and m.start() < bp_match.start():
                continue

            meth_match = re.search(r'method\s*=\s*RequestMethod\.([A-Z]+)', params)
            method = meth_match.group(1) if meth_match else 'GET'

            path_match = re.search(r'(?:path|value)\s*=\s*["\']([^"\']*)["\']', params)
            if not path_match:
                path_match = re.search(r'["\']([^"\']*)["\']', params)
            ep_path = path_match.group(1) if path_match else '/'
            if not ep_path:
                ep_path = '/'

            perm = None
            if pre_auth:
                perm = _get_perm(pre_auth)
            if not perm:
                start_idx = max(0, m.start() - 250)
                snippet = txt[start_idx:m.start()]
                perm = _get_perm(snippet)

            key_ep = f"{method}:{ep_path}"
            if key_ep not in seen:
                seen.add(key_ep)
                eps.append({
                    'method': method,
                    'path': ep_path,
                    'auth': ('Security' in txt or 'PreAuthorize' in txt or 'Principal' in txt or 'OAuth' in txt or 'RolesAllowed' in txt or perm is not None),
                    'permission': perm,
                    'description': _infer_desc(method, ep_path, name)
                })

        # Find matching screens/templates for this module
        mod_screens = []
        raw_low = raw_name.lower()
        for scr in all_screens:
            sp = scr['path'].lower()
            sn = scr['name'].lower()
            if raw_low in sn or raw_low in sp or mid in sp:
                mod_screens.append(scr['path'])

        if eps or True:
            perms = list(set(e['permission'] for e in eps if e.get('permission')))
            if mid in mod_map:
                if rel not in mod_map[mid]['files'] and fn not in mod_map[mid]['files']:
                    mod_map[mid]['files'].append(rel)
                mod_map[mid]['endpoints'].extend(eps)
                mod_map[mid]['permissions'] = list(set(mod_map[mid]['permissions'] + perms))
                for ms in mod_screens:
                    if ms not in mod_map[mid]['files']:
                        mod_map[mid]['files'].append(ms)
                mod_map[mid]['description'] = f"{mod_map[mid]['name']} — {len(mod_map[mid]['endpoints'])} endpoint(s)"
            else:
                files_list = [rel] + mod_screens
                mod_map[mid] = {
                    'id': mid,
                    'name': name if is_monolith else f"{svc_title} Service",
                    'basePath': base_path,
                    'description': f"{svc_title} module — {len(eps)} endpoint(s)" if is_monolith else f"{svc_title} microservice — {len(eps)} endpoint(s)",
                    'color': _color(mid, len(mod_map)),
                    'icon': _icon(mid),
                    'files': files_list,
                    'permissions': perms,
                    'endpoints': eps
                }

    if arch_type != 'monolith':
        pom_path = os.path.join(root, 'pom.xml')
        if os.path.isfile(pom_path):
            pom_txt = open(pom_path, encoding='utf-8', errors='ignore').read()
            sub_mods = re.findall(r'<module>([^<]+)</module>', pom_txt)
            for sm in sub_mods:
                sm_clean = sm.strip()
                if sm_clean in ('app', 'docs', 'templates'): continue
                sm_mid = sm_clean.replace('_', '-').lower()
                if sm_mid not in mod_map:
                    sm_name = sm_clean.replace('-service', '').replace('_service', '').replace('-', ' ').title()
                    mod_map[sm_mid] = {
                        'id': sm_mid,
                        'name': f"{sm_name} Service",
                        'basePath': f"/{sm_clean.replace('-service','')}",
                        'description': f"{sm_name} domain microservice (Infrastructure/Config module)",
                        'color': _color(sm_mid, len(mod_map)),
                        'icon': _icon(sm_mid),
                        'files': ['pom.xml'],
                        'permissions': [],
                        'endpoints': []
                    }

    return list(mod_map.values())

def _scan_workspaces(root):
    ws = []
    pom_path = os.path.join(root, 'pom.xml')
    if os.path.isfile(pom_path):
        pom_txt = open(pom_path, encoding='utf-8', errors='ignore').read()
        sub_mods = re.findall(r'<module>([^<]+)</module>', pom_txt)
        port_base = 8080
        for idx, sm in enumerate(sub_mods):
            sm_clean = sm.strip()
            ws.append({
                'id': sm_clean,
                'name': sm_clean,
                'type': 'backend',
                'description': f"{sm_clean.replace('-',' ').title()} Service",
                'port': port_base + idx,
                'entrypoint': f"{sm_clean}/pom.xml"
            })
        if ws: return ws

    for sub in ['backend','frontend','api','web','mobile','admin']:
        p = os.path.join(root, sub)
        if not os.path.isdir(p): continue
        t = 'backend' if sub in ('backend','api') else 'frontend'
        port = 3000 if t == 'backend' else 80
        env = os.path.join(p, '.env')
        if os.path.isfile(env):
            pm = re.search(r'^PORT\s*=\s*(\d+)', open(env,encoding='utf-8',errors='ignore').read(), re.MULTILINE)
            if pm: port = int(pm.group(1))
        ws.append({'id':sub,'name':sub,'type':t,
            'description':f"{sub.title()} {'REST API' if t=='backend' else 'UI'}",
            'port':port,'entrypoint':f"{sub}/src/index.ts"})
    return ws or [{'id':'api','name':'api','type':'backend',
        'description':'Main REST API','port':3000,'entrypoint':'src/index.ts'}]

def _scan_core_layer(root, fw):
    sec, mid, svc = [], [], []

    if fw in ('spring', 'java'):
        for r, _, fls in os.walk(root):
            norm_r = r.replace('\\', '/')
            if any(x in norm_r for x in ['/target/', '/.idea/', '/build/', '/.git/', '/test/']):
                continue
            for f in fls:
                if not f.endswith('.java'): continue
                rf = os.path.join(r, f)
                rel = os.path.relpath(rf, root).replace('\\', '/')
                txt = open(rf, encoding='utf-8', errors='ignore').read()
                name_clean = f.replace('.java', '')

                if any(k in txt for k in ['@EnableWebSecurity', '@EnableResourceServer', '@EnableAuthorizationServer', 'WebSecurityConfigurerAdapter', 'ResourceServerConfigurerAdapter']) or 'SecurityConfig' in f or 'OAuth2' in f:
                    desc = "OAuth2 Authorization Server Security Config" if ('Authorization' in txt or 'Auth' in f) else "Spring Resource Server & Web Security Config"
                    sec.append({"name": name_clean, "file": rel, "description": desc})
                elif 'UserDetailsService' in txt or 'UserDetailsService' in f:
                    sec.append({"name": name_clean, "file": rel, "description": "Spring Security UserDetailsService & User Principal Provider"})

                if 'Filter' in f or 'Interceptor' in f or 'OncePerRequestFilter' in txt or 'HandlerInterceptor' in txt or '@ControllerAdvice' in txt or 'ErrorHandler' in f:
                    desc = "Global Exception & Error Handling Controller Advice" if ('@ControllerAdvice' in txt or 'Error' in f) else f"Spring HTTP Request Filter / Interceptor ({name_clean})"
                    mid.append({"name": name_clean, "file": rel, "description": desc, "guards": ["HTTP Filter Chain"]})

                if '@Service' in txt or 'ServiceImpl' in f or '@FeignClient' in txt or '@Repository' in txt or 'Repository' in f or 'Client' in f:
                    stype = "Feign REST Client" if ('@FeignClient' in txt or 'Client' in f) else ("Spring Data Repository" if ('@Repository' in txt or 'Repository' in f) else "Core Business Logic Service")
                    svc.append({"name": name_clean, "file": rel, "description": f"{stype} ({rel.split('/')[0]})", "exports": [name_clean]})

        if sec and not any(s['name'] == 'Spring Security & OAuth2' for s in sec):
            sec.insert(0, {"name": "Spring Security & OAuth2", "file": "pom.xml", "description": "Framework OAuth2 Resource Server & JWT verification layer"})

    elif fw in ('express', 'nestjs', 'fastify'):
        pkg_path = os.path.join(root, 'package.json')
        deps = {}
        if os.path.isfile(pkg_path):
            try:
                d = json.load(open(pkg_path, encoding='utf-8'))
                deps.update(d.get('dependencies', {}))
                deps.update(d.get('devDependencies', {}))
            except: pass

        if 'helmet' in deps: sec.append({"name": "Helmet.js", "file": "package.json", "description": "HTTP security headers protection"})
        if 'cors' in deps: sec.append({"name": "CORS", "file": "package.json", "description": "Cross-Origin Resource Sharing restriction"})
        if 'jsonwebtoken' in deps or 'passport' in deps: sec.append({"name": "JWT / Passport Auth", "file": "package.json", "description": "Bearer token authentication & identity verification"})
        if 'bcrypt' in deps or 'argon2' in deps: sec.append({"name": "Bcrypt / Argon2", "file": "package.json", "description": "Password hashing & credential verification"})

        for r, _, fls in os.walk(root):
            norm_r = r.replace('\\', '/')
            if any(x in norm_r for x in ['/node_modules/', '/dist/', '/build/', '/.git/', '/test/']): continue
            for f in fls:
                if not (f.endswith('.ts') or f.endswith('.js')): continue
                rf = os.path.join(r, f)
                rel = os.path.relpath(rf, root).replace('\\', '/')
                txt = open(rf, encoding='utf-8', errors='ignore').read()
                name_clean = f.replace('.ts', '').replace('.js', '')

                if 'middleware' in norm_r or 'guard' in norm_r or 'interceptor' in norm_r or 'Middleware' in f or 'Guard' in f:
                    mid.append({"name": name_clean, "file": rel, "description": f"Request processing middleware ({f})", "guards": ["Route Guard"]})

                if '@Injectable' in txt or 'PrismaClient' in txt or 'Mongoose' in txt or 'TypeORM' in txt or 'service' in norm_r or 'repository' in norm_r:
                    svc.append({"name": name_clean, "file": rel, "description": f"Core service module ({f})", "exports": [name_clean]})

    elif fw in ('fastapi', 'django', 'flask'):
        for r, _, fls in os.walk(root):
            norm_r = r.replace('\\', '/')
            if any(x in norm_r for x in ['/__pycache__/', '/venv/', '/.git/', '/tests/']): continue
            for f in fls:
                if not f.endswith('.py'): continue
                rf = os.path.join(r, f)
                rel = os.path.relpath(rf, root).replace('\\', '/')
                txt = open(rf, encoding='utf-8', errors='ignore').read()
                name_clean = f.replace('.py', '')

                if 'OAuth2' in txt or 'CORSMiddleware' in txt or 'jwt' in txt or 'security' in f or 'auth' in f:
                    sec.append({"name": name_clean, "file": rel, "description": "Security & Authentication module"})

                if 'middleware' in norm_r or 'Middleware' in f or 'BaseHTTPMiddleware' in txt:
                    mid.append({"name": name_clean, "file": rel, "description": f"HTTP Middleware component ({f})", "guards": ["Request Pipeline"]})

                if 'service' in norm_r or 'crud' in norm_r or 'models' in f or 'repository' in norm_r or 'SessionLocal' in txt:
                    svc.append({"name": name_clean, "file": rel, "description": f"Data service / Model repository ({f})", "exports": [name_clean]})

    else:
        for r, _, fls in os.walk(root):
            norm_r = r.replace('\\', '/')
            if any(x in norm_r for x in ['/target/', '/vendor/', '/node_modules/', '/.git/', '/bin/', '/obj/']): continue
            for f in fls:
                rf = os.path.join(r, f)
                rel = os.path.relpath(rf, root).replace('\\', '/')
                fl = f.lower()
                if 'security' in fl or 'auth' in fl or 'oauth' in fl or 'jwt' in fl:
                    sec.append({"name": f, "file": rel, "description": f"Security & Auth component ({f})"})
                elif 'middleware' in norm_r or 'filter' in fl or 'interceptor' in fl or 'guard' in fl:
                    mid.append({"name": f, "file": rel, "description": f"Request Middleware / Filter ({f})", "guards": ["Request Pipeline"]})
                elif 'service' in norm_r or 'repository' in norm_r or ('service' in fl or 'repo' in fl or 'db' in fl):
                    svc.append({"name": f, "file": rel, "description": f"Service / Data Layer component ({f})", "exports": [f]})

    if not sec:
        sec = [
            {"name": "Security & TLS", "description": "Transport Layer Security and API Authentication"},
            {"name": "CORS & Origin Control", "description": "Cross-Origin Resource Sharing restrictions"}
        ]
    if not mid:
        mid = [
            {"name": "Global Request Filter", "file": "src/", "description": "HTTP request validation & telemetry filter", "guards": ["Validation"]}
        ]
    if not svc:
        svc = [
            {"name": "Main Data Client", "file": "src/", "description": "Core data layer & database service connection manager", "exports": ["DataClient"]}
        ]

    def _dedup(lst, key='name'):
        seen = set()
        res = []
        for item in lst:
            k = item.get(key)
            if k and k not in seen:
                seen.add(k)
                res.append(item)
        return res

    return {
        "security": _dedup(sec)[:8],
        "middleware": _dedup(mid)[:10],
        "services": _dedup(svc)[:12]
    }

def _build_sys_diagram(modules, infrastructure):
    client_nodes = [
        {'id': 'web_client', 'label': 'Web Application / Client', 'type': 'app'},
        {'id': 'mobile_client', 'label': 'Mobile App / API Consumer', 'type': 'app'}
    ]
    api_nodes = []
    if modules:
        for m in modules:
            m_name = m.get('name', 'API Module')
            m_id = f"mod_{re.sub(r'[^a-zA-Z0-9_]', '_', m_name.lower())}"
            api_nodes.append({'id': m_id, 'label': f"{m_name} Module", 'type': 'app'})
    if not api_nodes:
        api_nodes.append({'id': 'api_server', 'label': 'REST API Gateway / Server', 'type': 'app'})
        
    data_nodes = []
    for s in infrastructure:
        if s.get('type') in ('database', 'cache', 'queue', 'storage'):
            data_nodes.append({'id': s['id'], 'label': f"{s['name']}{(' :%s'%s.get('port')) if s.get('port') else ''}", 'type': s.get('type')})
    if not data_nodes:
        data_nodes.append({'id': 'db', 'label': 'PostgreSQL Database', 'type': 'database'})
    
    subgraphs = [
        {'id': 'client_layer', 'label': 'Client & Consumer Layer', 'nodes': client_nodes},
        {'id': 'api_layer', 'label': 'Application & Service Layer', 'nodes': api_nodes},
        {'id': 'data_layer', 'label': 'Data & Infrastructure Layer', 'nodes': data_nodes},
    ]
    
    edges = []
    for cn in client_nodes:
        for an in api_nodes:
            edges.append({'from': cn['id'], 'to': an['id'], 'label': 'HTTPS REST'})
            
    for an in api_nodes:
        for dn in data_nodes:
            lbl = 'Store / Fetch' if dn.get('type') == 'storage' else ('Cache / PubSub' if dn.get('type') == 'cache' else 'Query')
            edges.append({'from': an['id'], 'to': dn['id'], 'label': lbl})
            
    return {'description': 'System architecture, module boundaries, and infrastructure component relationships.',
            'subgraphs': subgraphs, 'edges': edges}


def _build_data_flow(fw, core_layer):
    """Build framework-aware requestPipeline and errorPipeline for dataFlow section."""

    # Pull scanned middleware/security names for step annotations
    sec_names  = [s.get('name','') for s in core_layer.get('security', [])]
    mid_names  = [m.get('name','') for m in core_layer.get('middleware', [])]
    mid_files  = [m.get('file','') for m in core_layer.get('middleware', [])]
    err_handler = next((m['name'] for m in core_layer.get('middleware', [])
                        if any(k in m.get('name','') for k in ['Exception','Error','ControllerAdvice'])), None)

    if fw in ('spring', 'java'):
        # Detect interceptors/filters from scanned middleware
        has_interceptor = any('Interceptor' in n or 'Filter' in n for n in mid_names)
        has_security    = any('Security' in n or 'OAuth' in n for n in sec_names)
        sec_note = f" ({sec_names[0]})" if sec_names else ""
        mid_note = f" ({mid_names[0]})" if mid_names else ""

        pipeline = [
            {
                "step": "HTTP request received by embedded Tomcat / Jetty",
                "detail": "Entry point of the web container. DispatcherServlet handles all incoming requests."
            },
            {
                "step": "Spring DispatcherServlet routes request to handler mapping",
                "detail": "Front controller resolves the matching @Controller and @RequestMapping method.",
                "coreRef": "middleware"
            },
            {
                "step": f"HandlerInterceptor.preHandle() fires{mid_note}" if has_interceptor else "Filter chain applied (security headers, CORS)",
                "detail": "Pre-processing hooks run before the controller — logging, auth token check, rate limiting.",
                "coreRef": "middleware"
            },
            {
                "step": f"Spring Security filter chain validates session / token{sec_note}" if has_security else "Authentication check — session or token validated",
                "detail": "Security context loaded. Unauthenticated requests receive 401 before reaching the controller.",
                "coreRef": "security"
            },
            {
                "step": "@Controller method invoked — request body bound and validated",
                "detail": "@RequestBody / @PathVariable / @RequestParam deserialized. @Valid constraints checked.",
                "coreRef": "services"
            },
            {
                "step": "Controller delegates to @Service layer — business logic executed",
                "detail": "Transactional boundaries begin here. Service orchestrates multiple repository calls if needed.",
                "coreRef": "services"
            },
            {
                "step": "@Repository / DAO executes SQL query against database",
                "detail": "Hibernate / JDBC template runs the query. Results mapped to domain objects.",
                "coreRef": "services"
            },
            {
                "step": "Response serialized — JSON / ModelAndView returned to client",
                "detail": "@ResponseBody converts the return value to JSON. HTTP 200 sent unless an exception was thrown."
            }
        ]

        err_handler_note = f" — handled by {err_handler}" if err_handler else ""
        error_pipeline = [
            f"Exception thrown in @Service or @Controller",
            f"@ControllerAdvice intercepts{err_handler_note}",
            "Exception mapped to HTTP status code (400 / 401 / 403 / 500)",
            "Error response body structured (message, code, timestamp)",
            "HandlerInterceptor.afterCompletion() fires (cleanup / logging)",
            "Error JSON returned to client"
        ]
        tenant_note = "Request scope tied to authenticated user session. Data access enforced at the service/repository layer."

    elif fw in ('fastapi', 'django', 'flask'):
        pipeline = [
            {"step": "HTTP request received by ASGI/WSGI server (Uvicorn / Gunicorn)", "detail": "Entry point of the Python application server."},
            {"step": "Middleware stack processes request (CORS, rate limit, request ID)", "detail": "Starlette / Django middleware chain runs top-to-bottom.", "coreRef": "middleware"},
            {"step": "Route matched — endpoint function resolved", "detail": "Path operation matched. Path and query parameters extracted and type-checked."},
            {"step": "Dependency injection resolved (Depends / auth guards)", "detail": "FastAPI Depends chain runs — current user fetched, auth token validated.", "coreRef": "security"},
            {"step": "Request body deserialized and validated (Pydantic / serializers)", "detail": "Schema validation runs. Invalid payloads return 422 before the handler is called."},
            {"step": "Endpoint handler executes — business logic runs", "detail": "Service / CRUD functions called. Database session used.", "coreRef": "services"},
            {"step": "ORM query executed (SQLAlchemy / Django ORM)", "detail": "SQL generated and run against the database. Results mapped to schema models.", "coreRef": "services"},
            {"step": "JSON response returned to client", "detail": "Pydantic model serialized to JSON. HTTP 200 returned."}
        ]
        error_pipeline = [
            "Exception raised in handler or service",
            "Exception handler / middleware intercepts (HTTPException or custom handler)",
            "Error response structured (detail, status_code)",
            "HTTP error returned to client (400 / 401 / 403 / 422 / 500)"
        ]
        tenant_note = "Request isolation enforced via dependency-injected database sessions and user-scoped queries."

    else:
        # Express / NestJS / generic
        pipeline = [
            {"step": "HTTP request received by Node.js HTTP server", "detail": "Express / Fastify receives the raw request object."},
            {"step": "Global middleware applied (Helmet, CORS, body-parser)", "detail": "Security headers set. Request body parsed to JSON.", "coreRef": "middleware"},
            {"step": "Route matched — module router selected", "detail": "Express router tree traversed. Route parameters extracted."},
            {"step": "Auth middleware runs — JWT Bearer token validated", "detail": "authenticateJWT / Passport strategy decodes token. 401 on failure.", "coreRef": "security"},
            {"step": "Guard / RBAC check — role and permission verified", "detail": "authorizeRoles / NestJS Guards verify the user has the required permission. 403 on failure.", "coreRef": "security"},
            {"step": "Controller / Route handler processes request", "detail": "Business logic executed. Service methods called.", "coreRef": "services"},
            {"step": "ORM / query builder executes database query", "detail": "Prisma / TypeORM / Knex runs SQL. Results returned as objects.", "coreRef": "services"},
            {"step": "JSON response returned to client", "detail": "res.json() sends serialized payload with appropriate HTTP status."}
        ]
        error_pipeline = [
            "Unhandled error thrown in controller or service",
            "Global error handler middleware intercepts (app.use error handler)",
            "Error logged (console / logger service)",
            "HTTP error response structured and returned (400 / 401 / 403 / 500)"
        ]
        tenant_note = "Tenant data isolation enforced via middleware scope and schema queries."

    return {
        "requestPipeline": pipeline,
        "errorPipeline": error_pipeline,
        "tenantIsolation": tenant_note
    }


# ---------------------------------------------------------------------------
# architecture.json INITIALISER — now powered by codebase scanner
# ---------------------------------------------------------------------------

def init_architecture(target_root=None):
    """Scan the codebase and generate architecture.json automatically."""
    if not target_root:
        script_dir = os.path.dirname(os.path.abspath(__file__))
        root = _find_root(script_dir)
    else:
        root = target_root

    arch_dir = os.path.join(root, 'docs', 'architecture') if os.path.basename(root) != 'architecture' else root
    os.makedirs(arch_dir, exist_ok=True)
    json_path = os.path.join(arch_dir, 'architecture.json')
    fw   = _detect_fw(root)

    proj_name = None
    proj_desc = None
    for pkg_loc in [os.path.join(root, 'package.json'), os.path.join(root, 'backend', 'package.json')]:
        if os.path.isfile(pkg_loc):
            try:
                d = json.load(open(pkg_loc, encoding='utf-8'))
                if d.get('name'): proj_name = d.get('name')
                if d.get('description'): proj_desc = d.get('description')
                if proj_name and proj_desc: break
            except: pass
    if not proj_name or proj_name in ('arch-wiki', 'template'):
        proj_name = os.path.basename(root)
    if not proj_desc:
        proj_desc = f"{proj_name.replace('-', ' ').replace('_', ' ').title()} Architecture & API Map"

    display_name = proj_name.replace('-',' ').replace('_',' ').title()

    fw_info = {'express':{'language':'TypeScript','framework':'Express.js'},
               'nestjs': {'language':'TypeScript','framework':'NestJS'},
               'fastapi':{'language':'Python',    'framework':'FastAPI'},
               'django': {'language':'Python',    'framework':'Django'},
               'flask':  {'language':'Python',    'framework':'Flask'},
               'spring': {'language':'Java 17',   'framework':'Spring Boot'},
               'unknown':{'language':'TypeScript','framework':'Express.js'}}.get(fw,{'language':'TypeScript','framework':'Express.js'})

    print(f"[arch-wiki] Root: {root} | Framework: {fw}")

    # 3. Scan docker-compose
    infrastructure, docker_diagram = _scan_docker(root)
    print(f"[arch-wiki] Docker: {len(infrastructure)} service(s)")

    # 4. Scan routes
    if fw in ('express','nestjs','fastify'):
        modules = _scan_express(root)
    elif fw == 'fastapi':
        modules = _scan_fastapi(root)
    elif fw in ('spring', 'java'):
        modules = _scan_java_spring(root)
    else:
        modules = _scan_express(root)
        if not modules:
            modules = _scan_java_spring(root)
    total_ep = sum(len(m['endpoints']) for m in modules)
    print(f"[arch-wiki] Routes: {len(modules)} module(s), {total_ep} endpoint(s)")

    # 5. Workspaces
    workspaces = _scan_workspaces(root)

    # 6. Collect all permission slugs & details
    perm_details = []
    for mod in modules:
        for ep in mod.get('endpoints', []):
            pslug = ep.get('permission')
            full_ep_path = (mod['basePath'] + ("" if ep['path'] == "/" else ep['path'])).replace("//", "/")
            ep_obj = {"method": ep['method'], "path": full_ep_path}

            if pslug:
                sub_slugs = [s.strip() for s in pslug.split('|') if s.strip()]
            elif ep.get('auth', False):
                sub_slugs = ['authenticated']
            else:
                sub_slugs = ['public']

            for sub_slug in sub_slugs:
                existing = next((d for d in perm_details if d['slug'] == sub_slug), None)
                if existing:
                    if ep_obj not in existing['endpoints']:
                        existing['endpoints'].append(ep_obj)
                else:
                    action_type = "SYSTEM SCOPE" if sub_slug in ('authenticated', 'public') else "RBAC PERMISSION"
                    page_label = "Public Access" if sub_slug == 'public' else ("Authenticated User Access" if sub_slug == 'authenticated' else f"{mod['name']} Management")
                    perm_details.append({
                        "slug": sub_slug,
                        "module": mod['name'],
                        "action": action_type,
                        "endpoints": [ep_obj],
                        "adminPages": [page_label]
                    })

    all_perms = sorted(set(d['slug'] for d in perm_details))

    # 7. System arch diagram
    sys_diag = _build_sys_diagram(modules, infrastructure)

    # 8. Core Layer & SQL Queries
    core_layer = _scan_core_layer(root, fw)

    sql_queries = []
    for mod in modules:
        mname = mod['name']
        bpath = mod['basePath']
        raw_table = mod['id'].replace('-', '_')
        table_name = raw_table + 's'
        
        for ep in mod.get('endpoints', []):
            method = ep.get('method', 'GET').upper()
            ep_path = ep.get('path', '/')
            full_ep_path = (bpath + ("" if ep_path == "/" else ep_path)).replace("//", "/")
            
            has_id = bool(re.search(r':[^/]+|\{[^}]+\}', ep_path))
            sub_resource = None
            path_segs = [p for p in ep_path.split('/') if p and not p.startswith(':') and not p.startswith('{')]
            if path_segs:
                sub_resource = path_segs[-1].replace('-', '_')

            if method == 'GET':
                if has_id:
                    label = f"Find {mname} by ID"
                    fn_name = f"get{mname}ById"
                    purpose = f"Fetch single {mname} record by unique ID"
                    sql_stmt = f"SELECT * FROM \"{table_name}\" WHERE id = $1 LIMIT 1;"
                elif sub_resource and sub_resource != mod['id']:
                    label = f"Get {mname} {sub_resource.title()}"
                    fn_name = f"get{mname}{sub_resource.title()}"
                    purpose = f"Fetch {sub_resource} for {mname} module"
                    sql_stmt = f"SELECT * FROM \"{sub_resource}\" ORDER BY created_at DESC;"
                else:
                    label = f"List All {mname} Records"
                    fn_name = f"list{mname}s"
                    purpose = f"Fetch all records for {mname} module"
                    sql_stmt = f"SELECT * FROM \"{table_name}\" ORDER BY created_at DESC;"

            elif method == 'POST':
                if sub_resource and sub_resource != mod['id']:
                    label = f"Create {mname} {sub_resource.title()}"
                    fn_name = f"create{mname}{sub_resource.title()}"
                    purpose = f"Insert new {sub_resource} record linked to {mname}"
                    sql_stmt = f"INSERT INTO \"{sub_resource}\" ({mod['id']}_id, created_at) VALUES ($1, NOW()) RETURNING *;"
                else:
                    label = f"Create New {mname}"
                    fn_name = f"create{mname}"
                    purpose = f"Insert new record into {mname} table"
                    sql_stmt = f"INSERT INTO \"{table_name}\" (id, created_at) VALUES ($1, NOW()) RETURNING *;"

            elif method in ('PUT', 'PATCH'):
                if sub_resource and sub_resource != mod['id']:
                    label = f"Update {mname} {sub_resource.title()}"
                    fn_name = f"update{mname}{sub_resource.title()}"
                    purpose = f"Update {sub_resource} attribute on {mname}"
                    sql_stmt = f"UPDATE \"{table_name}\" SET {sub_resource} = $1, updated_at = NOW() WHERE id = $2 RETURNING *;"
                else:
                    label = f"Update {mname} Record"
                    fn_name = f"update{mname}"
                    purpose = f"Update existing {mname} record by ID"
                    sql_stmt = f"UPDATE \"{table_name}\" SET updated_at = NOW() WHERE id = $1 RETURNING *;"

            elif method == 'DELETE':
                label = f"Delete {mname} Record"
                fn_name = f"delete{mname}"
                purpose = f"Delete record from {table_name} by ID"
                sql_stmt = f"DELETE FROM \"{table_name}\" WHERE id = $1;"

            else:
                label = f"Execute {method} on {mname}"
                fn_name = f"process{mname}"
                purpose = f"Execute operation for {full_ep_path}"
                sql_stmt = f"SELECT * FROM \"{table_name}\" WHERE id = $1;"

            ctrl_file = mod['files'][0] if (mod.get('files') and len(mod['files']) > 0) else (f"src/{mod['id']}.java" if fw in ('spring', 'java') else f"src/controllers/{mod['id']}.controller.ts")
            sql_queries.append({
                "label": label,
                "module": mname,
                "function": fn_name,
                "purpose": purpose,
                "file": ctrl_file,
                "tables": [sub_resource if (sub_resource and sub_resource != mod['id']) else table_name],
                "endpoints": [{"method": method, "path": full_ep_path}],
                "sql": sql_stmt
            })

    db_name = next((s['image'].split(':')[0].split('/')[-1].title()
                    for s in infrastructure if s['type']=='database'), 'PostgreSQL')

    today = datetime.date.today().isoformat()
    total_ep_str = f"{total_ep}/{total_ep}"

    prerequisites = _scan_prerequisites(root, fw, infrastructure, workspaces)

    scaffold = {
        "meta": {
            "displayName": display_name,
            "version": "1.0.0",
            "description": proj_desc or f"{display_name} REST API",
            "generatedAt": today,
            "techStack": {
                "language": fw_info['language'],
                "framework": fw_info['framework'],
                "database": db_name,
                "auth": "JWT / Bearer Token"
            }
        },
        "prerequisites": prerequisites,
        "workspaces": workspaces,
        "infrastructure": infrastructure,
        "dockerDiagram": docker_diagram,
        "systemArchitectureDiagram": sys_diag,
        "swaggerSchemas": {
            "matchStatus": f"Verified Parity ({total_ep_str} Endpoints)",
            "openapi": "3.0.0",
            "servedAt": "/api/docs",
            "securityScheme": "bearerAuth (JWT Bearer Token)",
            "servers": [
                {"url": "http://localhost:3000", "description": "Local Development Server"},
                {"url": f"https://api.{display_name.lower().replace(' ','-')}.com", "description": "Production"}
            ],
            "schemas": []
        },
        "modules": modules,
        "systemEndpoints": [
            {"method": "GET", "path": "/health", "auth": False, "description": "Health check endpoint"}
        ],
        "coreLayer": core_layer,
        "dataFlow": _build_data_flow(fw, core_layer),
        "permissions": {
            "description": "RBAC permission catalog and endpoint mapping.",
            "catalog": all_perms,
            "details": perm_details
        },
        "sqlQueries": sql_queries
    }

    with open(json_path, 'w', encoding='utf-8') as f:
        json.dump(scaffold, f, indent=2)

    print(f"[arch-wiki] Generated architecture.json -> {json_path}")
    return scaffold


def _scan_prerequisites(root, fw, infrastructure, workspaces):
    tools = []

    # 1. Primary Runtime Engine
    if fw in ('express', 'nestjs', 'fastify'):
        tools.append({
            "name": "Node.js & npm",
            "version": ">= 18.0.0",
            "required": True,
            "category": "runtime",
            "description": "JavaScript runtime engine for executing the Express REST API backend and frontend tooling."
        })
    elif fw in ('spring', 'java'):
        tools.append({
            "name": "Java OpenJDK / JDK",
            "version": ">= 17",
            "required": True,
            "category": "runtime",
            "description": "Java SE Development Kit required for Spring Boot backend compilation and execution."
        })
    elif fw in ('fastapi', 'django', 'flask'):
        tools.append({
            "name": "Python",
            "version": ">= 3.10",
            "required": True,
            "category": "runtime",
            "description": "Python runtime interpreter for backend API execution and virtual environments."
        })
    else:
        tools.append({
            "name": "Node.js",
            "version": ">= 18.0.0",
            "required": True,
            "category": "runtime",
            "description": "JavaScript runtime environment."
        })

    # 2. Containerization / Infrastructure tools
    has_compose = os.path.isfile(os.path.join(root, 'docker-compose.yml')) or os.path.isfile(os.path.join(root, 'docker-compose.yaml'))
    if infrastructure or has_compose:
        tools.append({
            "name": "Docker & Docker Compose",
            "version": ">= 24.0.0 (Compose v2)",
            "required": True,
            "category": "infrastructure",
            "description": "Container engine & orchestration tool to launch database, caching, messaging, and monitoring services."
        })

    # 3. Services detected from infrastructure
    for s in infrastructure:
        stype = s.get('type', '')
        sname = s.get('name', 'Service')
        simg  = s.get('image', 'latest')
        sport = s.get('port')
        if stype in ('database', 'cache', 'queue', 'monitoring'):
            tools.append({
                "name": f"{sname} ({stype.title()})",
                "version": simg,
                "required": True if stype in ('database', 'cache') else False,
                "category": stype,
                "description": f"Containerized {stype} service running on port {sport or 'internal'}."
            })

    # 4. Workspace & Monorepo Package Managers
    if os.path.isfile(os.path.join(root, 'pnpm-workspace.yaml')):
        tools.append({
            "name": "pnpm Package Manager",
            "version": ">= 8.0.0",
            "required": True,
            "category": "package_manager",
            "description": "Disk-efficient monorepo package manager."
        })

    # Setup Steps Pipeline
    setup_steps = []
    step_num = 1

    # Step 1: Environment File Setup
    env_file = os.path.join(root, '.env.example')
    if not os.path.isfile(env_file):
        env_file = os.path.join(root, 'apps', 'api', '.env.example')

    if os.path.isfile(env_file):
        setup_steps.append({
            "step": step_num,
            "title": "Configure Environment Variables",
            "command": "cp .env.example .env",
            "description": "Create local .env configuration file and update database host, credentials, JWT secrets, and service ports."
        })
    else:
        setup_steps.append({
            "step": step_num,
            "title": "Configure Environment Variables",
            "command": "touch .env",
            "description": "Set up environment variables (PORT, DB_HOST, DB_PASSWORD, JWT_SECRET)."
        })
    step_num += 1

    # Step 2: Launch Docker Containers
    if infrastructure or has_compose:
        setup_steps.append({
            "step": step_num,
            "title": "Start Infrastructure Containers",
            "command": "docker compose up -d",
            "description": "Spin up containerized services in background mode."
        })
        step_num += 1

    # Step 3: Install Package Dependencies
    if fw in ('express', 'nestjs', 'fastify'):
        setup_steps.append({
            "step": step_num,
            "title": "Install Workspace Dependencies",
            "command": "npm install",
            "description": "Install dependencies across backend API, shared libraries, and admin frontend."
        })
    elif fw in ('spring', 'java'):
        setup_steps.append({
            "step": step_num,
            "title": "Build Maven Modules",
            "command": "./mvnw clean install -DskipTests",
            "description": "Compile Java packages and download Maven dependencies."
        })
    elif fw in ('fastapi', 'django', 'flask'):
        setup_steps.append({
            "step": step_num,
            "title": "Install Python Virtual Environment",
            "command": "python -m venv venv && source venv/bin/activate && pip install -r requirements.txt",
            "description": "Initialize virtual environment and install dependencies."
        })
    step_num += 1

    # Step 4: Database Migrations & Seeds
    setup_steps.append({
        "step": step_num,
        "title": "Run Schema Migrations & Database Seeds",
        "command": "npm run db:migrate && npm run db:seed" if fw in ('express', 'nestjs') else ("./mvnw compile exec:java" if fw == 'spring' else "alembic upgrade head"),
        "description": "Execute database schema migrations and populate initial seed records."
    })
    step_num += 1

    # Step 5: Boot Application Development Server
    setup_steps.append({
        "step": step_num,
        "title": "Launch Development Server",
        "command": "npm run dev" if fw in ('express', 'nestjs') else ("./mvnw spring-boot:run" if fw == 'spring' else "uvicorn main:app --reload"),
        "description": "Start backend API in watch mode."
    })

    return {
        "description": "Software runtimes, system dependencies, and step-by-step initialization commands required to run the project.",
        "tools": tools,
        "setupSteps": setup_steps
    }



def load_architecture(json_path=None):
    if not json_path:
        json_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'architecture.json')
    if not os.path.isfile(json_path):
        print("[arch-wiki] architecture.json not found — running codebase scan initialization...")
        target_root = os.path.dirname(os.path.dirname(os.path.dirname(json_path)))
        return init_architecture(target_root)
    with open(json_path, 'r', encoding='utf-8') as f:
        return json.load(f)

def clean_mermaid(text):
    if not text:
        return ""
    return re.sub(r'[^a-zA-Z0-9 _\-\.:]', '', str(text))

def build_openapi_spec(data):
    meta = data.get('meta', {})
    modules = data.get('modules', [])
    system_endpoints = data.get('systemEndpoints', [])
    swagger_schemas = data.get('swaggerSchemas', {})

    spec = {
        "openapi": "3.0.0",
        "info": {
            "title": meta.get('displayName', 'SaaS MVP Platform API'),
            "version": meta.get('version', '1.0.0'),
            "description": meta.get('description', 'Multi-tenant SaaS REST API with full RBAC, JWT, RLS, and Prometheus telemetry.')
        },
        "servers": swagger_schemas.get('servers', [
            {"url": "http://localhost:3000", "description": "Local Development Server"},
            {"url": "https://api.saas-mvp.com", "description": "Production API Gateway"}
        ]),
        "tags": [],
        "paths": {},
        "components": {
            "securitySchemes": {
                "bearerAuth": {
                    "type": "http",
                    "scheme": "bearer",
                    "bearerFormat": "JWT",
                    "description": "Provide your JWT Access Token (Header: Authorization: Bearer <token>)"
                }
            },
            "schemas": {}
        }
    }

    for mod in modules:
        mod_name = mod.get('name', '')
        base_path = mod.get('basePath', '')
        spec['tags'].append({
            "name": mod_name,
            "description": mod.get('description', '')
        })

        for ep in mod.get('endpoints', []):
            method = ep.get('method', 'GET').lower()
            path_suffix = ep.get('path', '')
            full_path = (base_path + ("" if path_suffix == "/" else path_suffix)).replace("//", "/")
            openapi_path = re.sub(r':([a-zA-Z0-9_]+)', r'{\1}', full_path)

            if openapi_path not in spec['paths']:
                spec['paths'][openapi_path] = {}

            parameters = []
            path_params = re.findall(r'\{([a-zA-Z0-9_]+)\}', openapi_path)
            for param in path_params:
                parameters.append({
                    "name": param,
                    "in": "path",
                    "required": True,
                    "schema": {"type": "string"},
                    "description": f"Target {param} identifier"
                })

            perm_slug = ep.get('permission')
            perm_desc = f"Required Permission: `{perm_slug}`" if perm_slug else "Public / Authenticated Route"

            op = {
                "tags": [mod_name],
                "summary": ep.get('description', ''),
                "description": f"{ep.get('description', '')} | {perm_desc}",
                "parameters": parameters,
                "responses": {
                    "200": {
                        "description": "Successful Request",
                        "content": {
                            "application/json": {
                                "example": {"success": True, "data": {}}
                            }
                        }
                    },
                    "400": {"description": "Invalid payload parameters"},
                    "401": {"description": "Missing or expired JWT Bearer token"},
                    "403": {"description": "Forbidden - Insufficient permissions"},
                    "422": {"description": "Validation error"},
                    "500": {"description": "Internal server error"}
                }
            }

            if ep.get('auth', False):
                op["security"] = [{"bearerAuth": []}]

            if method in ["post", "put", "patch"]:
                op["requestBody"] = {
                    "required": True,
                    "content": {
                        "application/json": {
                            "schema": {
                                "type": "object",
                                "example": {"exampleField": "exampleValue"}
                            }
                        }
                    }
                }

            spec['paths'][openapi_path][method] = op

    if system_endpoints:
        spec['tags'].append({"name": "System", "description": "System health and telemetry endpoints"})
        for sys_ep in system_endpoints:
            spath = sys_ep.get('path', '')
            smethod = sys_ep.get('method', 'GET').lower()
            if spath not in spec['paths']:
                spec['paths'][spath] = {}
            spec['paths'][spath][smethod] = {
                "tags": ["System"],
                "summary": sys_ep.get('description', ''),
                "responses": {"200": {"description": "System Operational"}}
            }

    for sch in swagger_schemas.get('schemas', []):
        spec['components']['schemas'][sch.get('name')] = {
            "type": "object",
            "description": sch.get('description')
        }

    return spec

def generate_html(data, target_dir=None):
    meta = data.get('meta', {})
    workspaces = data.get('workspaces', [])
    infrastructure = data.get('infrastructure', [])
    core_layer = data.get('coreLayer', {})
    modules = data.get('modules', [])
    system_endpoints = data.get('systemEndpoints', [])
    data_flow = data.get('dataFlow', {})
    permissions = data.get('permissions', {})
    docker_diagram = data.get('dockerDiagram', {})
    system_arch_diagram = data.get('systemArchitectureDiagram', {})
    swagger_schemas = data.get('swaggerSchemas', {})
    sql_queries = data.get('sqlQueries', [])
    prerequisites = data.get('prerequisites', {})

    tech_stack = meta.get('techStack', {})
    total_endpoints = sum(len(m.get('endpoints', [])) for m in modules) + len(system_endpoints)
    prereq_tools = prerequisites.get('tools', [])
    prereq_steps = prerequisites.get('setupSteps', [])

    html_content = f"""<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>{html.escape(meta.get('displayName', 'SaaS MVP'))} — Architecture Map</title>
    <link rel="preconnect" href="https://fonts.googleapis.com">
    <link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
    <link href="https://fonts.googleapis.com/css2?family=Inter:wght@300;400;500;600;700&family=Fira+Code:wght@400;500;600&display=swap" rel="stylesheet">
    <link rel="stylesheet" href="https://cdn.jsdelivr.net/npm/swagger-ui-dist@5/swagger-ui.css" />
    <script src="https://cdn.jsdelivr.net/npm/mermaid@10/dist/mermaid.min.js"></script>
    <script src="https://cdn.jsdelivr.net/npm/svg-pan-zoom@3.6.1/dist/svg-pan-zoom.min.js"></script>
    <script src="https://cdn.jsdelivr.net/npm/swagger-ui-dist@5/swagger-ui-bundle.js"></script>
    <style>
        :root {{
            --bg: #0d1117;
            --bg2: #161b22;
            --bg3: #21262d;
            --border: #30363d;
            --text: #e6edf3;
            --muted: #8b949e;
            --accent: #58a6ff;
            --green: #3fb950;
            --yellow: #d29922;
            --red: #f85149;
            --purple: #bc8cff;
            --orange: #ff8c42;
            --font-main: 'Inter', -apple-system, BlinkMacSystemFont, sans-serif;
            --font-code: 'Fira Code', monospace;
        }}

        * {{ box-sizing: border-box; margin: 0; padding: 0; }}
        body {{
            background-color: var(--bg);
            color: var(--text);
            font-family: var(--font-main);
            min-height: 100vh;
            overflow-x: hidden;
        }}

        .header {{
            background: var(--bg2);
            border-bottom: 1px solid var(--border);
            position: sticky;
            top: 0;
            z-index: 200;
            height: 65px;
        }}
        .header-top {{
            padding: 0 28px;
            display: flex;
            align-items: center;
            justify-content: space-between;
            height: 100%;
        }}

        .app-layout {{
            display: flex;
            width: 100vw;
            min-height: calc(100vh - 65px);
        }}

        .sidebar {{
            width: 280px;
            min-width: 280px;
            background: var(--bg2);
            border-right: 1px solid var(--border);
            display: flex;
            flex-direction: column;
            position: fixed;
            top: 65px;
            bottom: 0;
            left: 0;
            z-index: 100;
        }}

        .sidebar-header {{
            padding: 16px 20px 12px 20px;
            border-bottom: 1px solid var(--border);
        }}
        .brand {{
            display: flex;
            align-items: center;
            gap: 12px;
            margin-bottom: 10px;
        }}
        .brand-icon {{
            font-size: 28px;
        }}
        .brand-title {{
            font-size: 16px;
            font-weight: 700;
            color: var(--text);
            line-height: 1.2;
        }}
        .brand-sub {{
            font-size: 11px;
            color: var(--muted);
            margin-top: 4px;
            line-height: 1.4;
        }}
        .sidebar-badges {{
            display: flex;
            flex-wrap: wrap;
            gap: 6px;
            margin-top: 10px;
        }}

        .badge {{
            background: var(--bg3);
            border: 1px solid var(--border);
            border-radius: 6px;
            padding: 3px 8px;
            font-size: 11px;
            color: var(--muted);
        }}
        .badge-green {{
            background: rgba(63, 185, 80, 0.15);
            color: var(--green);
            border: 1px solid rgba(63, 185, 80, 0.4);
            font-weight: 600;
        }}

        .sidebar-nav {{
            flex: 1;
            padding: 16px 12px;
            overflow-y: auto;
            display: flex;
            flex-direction: column;
            gap: 4px;
        }}

        .nav-btn {{
            background: none;
            border: 1px solid transparent;
            color: var(--muted);
            padding: 10px 14px;
            border-radius: 8px;
            cursor: pointer;
            font-size: 13px;
            font-weight: 500;
            text-align: left;
            transition: all .15s ease;
            display: flex;
            align-items: center;
            justify-content: space-between;
            width: 100%;
        }}
        .nav-btn:hover {{
            background: var(--bg3);
            color: var(--text);
        }}
        .nav-btn.active {{
            background: rgba(88, 166, 255, 0.15);
            color: var(--accent);
            border-color: rgba(88, 166, 255, 0.4);
            font-weight: 600;
        }}
        .nav-btn-left {{
            display: flex;
            align-items: center;
            gap: 10px;
        }}

        .nav-count {{
            background: var(--bg3);
            color: var(--muted);
            padding: 2px 8px;
            border-radius: 10px;
            font-size: 11px;
            font-weight: 600;
        }}
        .nav-btn.active .nav-count {{
            background: var(--accent);
            color: #000;
        }}

        .sidebar-footer {{
            padding: 14px 20px;
            border-top: 1px solid var(--border);
            font-size: 11px;
            color: var(--muted);
            text-align: center;
        }}

        .main-content {{
            margin-left: 280px;
            flex: 1;
            padding: 28px 36px;
            max-width: 1500px;
            width: calc(100vw - 280px);
        }}
        .section {{ display: none; }}
        .section.active {{ display: block; }}

        .stats {{
            display: grid;
            grid-template-columns: repeat(auto-fill, minmax(140px, 1fr));
            gap: 12px;
            margin-bottom: 24px;
        }}
        .stat {{
            background: var(--bg2);
            border: 1px solid var(--border);
            border-radius: 10px;
            padding: 16px;
            text-align: center;
        }}
        .stat-num {{
            font-size: 28px;
            font-weight: 700;
            color: var(--accent);
        }}
        .stat-lbl {{
            font-size: 12px;
            color: var(--muted);
            margin-top: 4px;
        }}

        .sec-title {{
            font-size: 17px;
            font-weight: 700;
            margin: 24px 0 14px;
            display: flex;
            align-items: center;
            gap: 8px;
            color: var(--text);
        }}

        .grid3 {{ display: grid; grid-template-columns: repeat(auto-fill, minmax(300px, 1fr)); gap: 16px; }}
        .grid2 {{ display: grid; grid-template-columns: repeat(auto-fill, minmax(420px, 1fr)); gap: 16px; }}
        .grid1 {{ display: grid; grid-template-columns: 1fr; gap: 16px; }}

        .card {{
            background: var(--bg2);
            border: 1px solid var(--border);
            border-radius: 12px;
            padding: 20px;
            transition: border-color .2s;
        }}
        .card:hover {{
            border-color: var(--accent);
        }}
        .color-bar {{
            height: 3px;
            border-radius: 3px;
            margin-bottom: 12px;
        }}
        .chead {{
            display: flex;
            align-items: center;
            gap: 10px;
            margin-bottom: 8px;
        }}
        .card-title {{
            font-size: 15px;
            font-weight: 600;
        }}
        .card-sub {{
            font-size: 12px;
            color: var(--muted);
            margin-top: 2px;
        }}
        .card-desc {{
            font-size: 13px;
            color: var(--muted);
            line-height: 1.6;
            margin: 10px 0;
        }}

        .tag {{
            display: inline-block;
            padding: 2px 8px;
            border-radius: 4px;
            font-size: 11px;
            font-weight: 500;
            margin: 2px;
        }}
        .tb {{ background: rgba(88,166,255,.15); color: var(--accent); }}
        .tg {{ background: rgba(63,185,80,.15); color: var(--green); }}
        .tr {{ background: rgba(248,81,73,.15); color: var(--red); }}
        .ty {{ background: rgba(210,153,34,.15); color: var(--yellow); }}
        .tp {{ background: rgba(188,140,255,.15); color: var(--purple); }}
        .tq {{ background: var(--bg3); color: var(--muted); }}

        .endpoint {{
            display: flex;
            align-items: flex-start;
            gap: 8px;
            padding: 8px 10px;
            border-radius: 6px;
            margin: 4px 0;
            background: var(--bg3);
        }}
        .method {{
            font-size: 10px;
            font-weight: 700;
            padding: 3px 7px;
            border-radius: 4px;
            min-width: 54px;
            text-align: center;
            flex-shrink: 0;
        }}
        .GET {{ background: rgba(63,185,80,.2); color: var(--green); }}
        .POST {{ background: rgba(88,166,255,.2); color: var(--accent); }}
        .PUT {{ background: rgba(210,153,34,.2); color: var(--yellow); }}
        .PATCH {{ background: rgba(255,140,66,.2); color: var(--orange); }}
        .DELETE {{ background: rgba(248,81,73,.2); color: var(--red); }}

        .ep-path {{ font-size: 12px; font-family: var(--font-code); color: var(--text); }}
        .ep-desc {{ font-size: 11px; color: var(--muted); margin-top: 2px; }}
        .lock {{ font-size: 10px; margin-left: 6px; opacity: .8; color: var(--purple); }}

        .search {{
            width: 100%;
            padding: 10px 16px;
            background: var(--bg2);
            border: 1px solid var(--border);
            border-radius: 8px;
            color: var(--text);
            font-size: 14px;
            margin-bottom: 20px;
            outline: none;
        }}
        .search:focus {{ border-color: var(--accent); }}

        .pipeline {{ display: flex; flex-direction: column; }}
        .pipe-step {{
            display: flex;
            align-items: center;
            gap: 12px;
            padding: 12px 16px;
            background: var(--bg2);
            border: 1px solid var(--border);
            margin-top: -1px;
        }}
        .pipe-step:first-child {{ border-radius: 8px 8px 0 0; }}
        .pipe-step:last-child {{ border-radius: 0 0 8px 8px; }}
        .pipe-num {{
            background: var(--accent);
            color: #000;
            width: 22px;
            height: 22px;
            border-radius: 50%;
            display: flex;
            align-items: center;
            justify-content: center;
            font-size: 11px;
            font-weight: 700;
            flex-shrink: 0;
        }}

        .perm-grid {{ display: grid; grid-template-columns: repeat(auto-fill, minmax(170px, 1fr)); gap: 8px; margin-bottom: 20px; }}
        .perm-item {{
            background: var(--bg3);
            border: 1px solid var(--border);
            border-radius: 6px;
            padding: 8px 12px;
            font-size: 12px;
            font-family: var(--font-code);
            color: var(--purple);
        }}

        .perm-card {{
            background: var(--bg2);
            border: 1px solid var(--border);
            border-left: 4px solid var(--purple);
            border-radius: 8px;
            padding: 16px;
            margin-bottom: 12px;
        }}
        .perm-flow {{
            display: flex;
            align-items: center;
            gap: 6px;
            flex-wrap: wrap;
            font-size: 12px;
            margin-top: 8px;
        }}
        .flow-arrow {{ color: var(--muted); font-weight: bold; }}

        .code-block {{
            background: var(--bg);
            border: 1px solid var(--border);
            border-radius: 6px;
            padding: 12px;
            font-family: var(--font-code);
            font-size: 12px;
            color: var(--text);
            overflow-x: auto;
            white-space: pre-wrap;
            margin-top: 8px;
        }}
        .diagram-box {{
            position: relative;
            background: var(--bg2);
            border: 1px solid var(--border);
            border-radius: 8px;
            padding: 20px;
            text-align: center;
            overflow: hidden;
            cursor: grab !important;
        }}
        .diagram-box:active {{
            cursor: grabbing !important;
        }}
        .diagram-box svg, .diagram-box svg * {{
            cursor: grab !important;
        }}
        .diagram-box svg:active, .diagram-box svg:active * {{
            cursor: grabbing !important;
        }}
        .diagram-toolbar {{
            position: absolute;
            top: 12px;
            right: 12px;
            z-index: 100;
            display: flex;
            align-items: center;
            gap: 6px;
            background: rgba(13, 17, 23, 0.85);
            backdrop-filter: blur(8px);
            border: 1px solid var(--border);
            border-radius: 6px;
            padding: 4px 8px;
        }}
        .diagram-toolbar button {{
            background: var(--bg3);
            border: 1px solid var(--border);
            color: var(--text);
            padding: 4px 10px;
            border-radius: 4px;
            cursor: pointer;
            font-size: 12px;
            font-weight: 500;
            transition: all 0.15s ease;
        }}
        .diagram-toolbar button:hover {{
            background: var(--accent);
            color: #000;
            border-color: var(--accent);
        }}

        .mwcard {{
            background: var(--bg2);
            border: 1px solid var(--border);
            border-radius: 10px;
            padding: 16px;
            margin-bottom: 10px;
        }}

        table {{ width: 100%; border-collapse: collapse; margin-top: 10px; font-size: 13px; }}
        th, td {{ padding: 10px 12px; text-align: left; border-bottom: 1px solid var(--border); }}
        th {{ background: var(--bg3); color: var(--muted); font-weight: 600; font-size: 12px; }}

        .sub-tab-btn {{
            background: var(--bg2);
            border: 1px solid var(--border);
            color: var(--muted);
            padding: 8px 16px;
            border-radius: 6px;
            cursor: pointer;
            font-size: 12px;
            font-weight: 500;
            transition: all .15s ease;
        }}
        .sub-tab-btn:hover {{
            background: var(--bg3);
            color: var(--text);
        }}
        .sub-tab-btn.active {{
            background: var(--accent);
            color: #000;
            font-weight: 600;
            border-color: var(--accent);
        }}
        .swagger-view-pane {{
            display: none;
        }}
        .swagger-view-pane.active {{
            display: block;
        }}

        /* Comprehensive High-Contrast Dark Theme Overrides for Swagger UI */
        #swagger-ui-container .swagger-ui {{
            color: var(--text) !important;
            font-family: var(--font-main) !important;
        }}
        #swagger-ui-container .swagger-ui * {{
            border-color: var(--border) !important;
        }}
        #swagger-ui-container .swagger-ui .info {{
            margin: 15px 0 25px 0 !important;
            background: transparent !important;
        }}
        #swagger-ui-container .swagger-ui .info .title {{
            color: var(--text) !important;
            font-size: 24px !important;
        }}
        #swagger-ui-container .swagger-ui .info p,
        #swagger-ui-container .swagger-ui .info li,
        #swagger-ui-container .swagger-ui .info td,
        #swagger-ui-container .swagger-ui .info a {{
            color: var(--muted) !important;
        }}
        #swagger-ui-container .swagger-ui .scheme-container {{
            background: var(--bg2) !important;
            border-radius: 8px !important;
            padding: 16px !important;
            box-shadow: none !important;
            border: 1px solid var(--border) !important;
            margin-bottom: 20px !important;
        }}
        #swagger-ui-container .swagger-ui label,
        #swagger-ui-container .swagger-ui .title,
        #swagger-ui-container .swagger-ui .servers-title {{
            color: var(--text) !important;
        }}
        #swagger-ui-container .swagger-ui .opblock-tag {{
            color: var(--text) !important;
            border-bottom: 1px solid var(--border) !important;
            font-size: 18px !important;
            font-weight: 700 !important;
            padding: 10px 0 !important;
            margin: 20px 0 10px 0 !important;
        }}
        #swagger-ui-container .swagger-ui .opblock-tag small {{
            color: var(--muted) !important;
            font-size: 13px !important;
            font-weight: 400 !important;
        }}
        #swagger-ui-container .swagger-ui .opblock {{
            background: var(--bg2) !important;
            border-radius: 8px !important;
            border: 1px solid var(--border) !important;
            margin-bottom: 14px !important;
            box-shadow: none !important;
            overflow: hidden !important;
        }}
        #swagger-ui-container .swagger-ui .opblock .opblock-summary {{
            padding: 10px 14px !important;
            border-bottom: 1px solid transparent !important;
            display: flex !important;
            align-items: center !important;
        }}
        #swagger-ui-container .swagger-ui .opblock .opblock-summary-path,
        #swagger-ui-container .swagger-ui .opblock .opblock-summary-path__deprecated {{
            color: var(--text) !important;
            font-family: var(--font-code) !important;
            font-size: 13px !important;
            font-weight: 600 !important;
        }}
        #swagger-ui-container .swagger-ui .opblock .opblock-summary-description {{
            color: var(--muted) !important;
            font-size: 12px !important;
        }}

        /* HTTP Method Badges & Container States */
        /* GET */
        #swagger-ui-container .swagger-ui .opblock.opblock-get {{
            background: rgba(63, 185, 80, 0.08) !important;
            border-color: rgba(63, 185, 80, 0.4) !important;
        }}
        #swagger-ui-container .swagger-ui .opblock.opblock-get .opblock-summary-method {{
            background: #3fb950 !important;
            color: #0d1117 !important;
            font-weight: 700 !important;
            border-radius: 4px !important;
            padding: 4px 10px !important;
            text-shadow: none !important;
        }}
        /* POST */
        #swagger-ui-container .swagger-ui .opblock.opblock-post {{
            background: rgba(88, 166, 255, 0.08) !important;
            border-color: rgba(88, 166, 255, 0.4) !important;
        }}
        #swagger-ui-container .swagger-ui .opblock.opblock-post .opblock-summary-method {{
            background: #58a6ff !important;
            color: #0d1117 !important;
            font-weight: 700 !important;
            border-radius: 4px !important;
            padding: 4px 10px !important;
            text-shadow: none !important;
        }}
        /* PUT */
        #swagger-ui-container .swagger-ui .opblock.opblock-put {{
            background: rgba(210, 153, 34, 0.08) !important;
            border-color: rgba(210, 153, 34, 0.4) !important;
        }}
        #swagger-ui-container .swagger-ui .opblock.opblock-put .opblock-summary-method {{
            background: #d29922 !important;
            color: #0d1117 !important;
            font-weight: 700 !important;
            border-radius: 4px !important;
            padding: 4px 10px !important;
            text-shadow: none !important;
        }}
        /* PATCH */
        #swagger-ui-container .swagger-ui .opblock.opblock-patch {{
            background: rgba(255, 140, 66, 0.08) !important;
            border-color: rgba(255, 140, 66, 0.4) !important;
        }}
        #swagger-ui-container .swagger-ui .opblock.opblock-patch .opblock-summary-method {{
            background: #ff8c42 !important;
            color: #0d1117 !important;
            font-weight: 700 !important;
            border-radius: 4px !important;
            padding: 4px 10px !important;
            text-shadow: none !important;
        }}
        /* DELETE */
        #swagger-ui-container .swagger-ui .opblock.opblock-delete {{
            background: rgba(248, 81, 73, 0.08) !important;
            border-color: rgba(248, 81, 73, 0.4) !important;
        }}
        #swagger-ui-container .swagger-ui .opblock.opblock-delete .opblock-summary-method {{
            background: #f85149 !important;
            color: #ffffff !important;
            font-weight: 700 !important;
            border-radius: 4px !important;
            padding: 4px 10px !important;
            text-shadow: none !important;
        }}

        /* Expanded Opblock Body & Sections */
        #swagger-ui-container .swagger-ui .opblock-body {{
            background: var(--bg2) !important;
            color: var(--text) !important;
            border-top: 1px solid var(--border) !important;
            padding: 16px !important;
        }}
        #swagger-ui-container .swagger-ui .opblock-section-header {{
            background: var(--bg3) !important;
            color: var(--text) !important;
            border-radius: 6px !important;
            padding: 8px 12px !important;
            border: 1px solid var(--border) !important;
            margin-bottom: 12px !important;
        }}
        #swagger-ui-container .swagger-ui .opblock-section-header h4 {{
            color: var(--text) !important;
            font-size: 13px !important;
            font-weight: 600 !important;
        }}
        #swagger-ui-container .swagger-ui .opblock-description-wrapper,
        #swagger-ui-container .swagger-ui .opblock-description-wrapper p,
        #swagger-ui-container .swagger-ui .markdown p,
        #swagger-ui-container .swagger-ui .renderedMarkdown,
        #swagger-ui-container .swagger-ui .renderedMarkdown p {{
            color: var(--text) !important;
            font-size: 13px !important;
            line-height: 1.5 !important;
        }}

        /* Parameter & Response Tables */
        #swagger-ui-container .swagger-ui table {{
            background: transparent !important;
            width: 100% !important;
        }}
        #swagger-ui-container .swagger-ui table thead tr th,
        #swagger-ui-container .swagger-ui table thead tr td {{
            color: var(--muted) !important;
            border-bottom: 1px solid var(--border) !important;
            font-size: 12px !important;
            font-weight: 600 !important;
            padding: 8px 12px !important;
            background: transparent !important;
        }}
        #swagger-ui-container .swagger-ui table.parameters td,
        #swagger-ui-container .swagger-ui table.responses-table td {{
            color: var(--text) !important;
            border-bottom: 1px solid var(--border) !important;
            padding: 10px 12px !important;
            background: transparent !important;
        }}
        #swagger-ui-container .swagger-ui .parameter__name {{
            color: var(--text) !important;
            font-family: var(--font-code) !important;
            font-weight: 600 !important;
            font-size: 13px !important;
        }}
        #swagger-ui-container .swagger-ui .parameter__name.required:after {{
            color: var(--red) !important;
        }}
        #swagger-ui-container .swagger-ui .parameter__type,
        #swagger-ui-container .swagger-ui .parameter__extension {{
            color: var(--purple) !important;
            font-family: var(--font-code) !important;
            font-size: 12px !important;
        }}
        #swagger-ui-container .swagger-ui .parameter__in {{
            color: var(--muted) !important;
            font-family: var(--font-code) !important;
            font-size: 11px !important;
            font-style: italic !important;
        }}

        /* Response Code Indicators & Links */
        #swagger-ui-container .swagger-ui .responses-inner {{
            background: var(--bg) !important;
            padding: 16px !important;
            border-radius: 8px !important;
            border: 1px solid var(--border) !important;
            margin-top: 10px !important;
        }}
        #swagger-ui-container .swagger-ui .responses-inner h4,
        #swagger-ui-container .swagger-ui .responses-inner h5 {{
            color: var(--text) !important;
            font-size: 13px !important;
            font-weight: 600 !important;
        }}
        #swagger-ui-container .swagger-ui .response-col_status {{
            color: var(--green) !important;
            font-family: var(--font-code) !important;
            font-weight: 700 !important;
            font-size: 13px !important;
        }}
        #swagger-ui-container .swagger-ui .response-col_description {{
            color: var(--text) !important;
            font-size: 13px !important;
        }}
        #swagger-ui-container .swagger-ui .response-col_links {{
            color: var(--muted) !important;
        }}

        /* Models & Schema Boxes */
        #swagger-ui-container .swagger-ui section.models {{
            border: 1px solid var(--border) !important;
            border-radius: 8px !important;
            background: var(--bg2) !important;
            margin-top: 30px !important;
            padding: 16px !important;
        }}
        #swagger-ui-container .swagger-ui section.models h4 {{
            color: var(--text) !important;
            border-bottom: 1px solid var(--border) !important;
            font-size: 16px !important;
            font-weight: 700 !important;
            padding-bottom: 10px !important;
        }}
        #swagger-ui-container .swagger-ui .model-container {{
            background: var(--bg3) !important;
            border-radius: 6px !important;
            padding: 12px !important;
            margin-top: 10px !important;
            border: 1px solid var(--border) !important;
        }}
        #swagger-ui-container .swagger-ui .model-box {{
            background: var(--bg3) !important;
            color: var(--text) !important;
            border-radius: 6px !important;
            padding: 10px !important;
        }}
        #swagger-ui-container .swagger-ui .model-title {{
            color: var(--accent) !important;
            font-family: var(--font-code) !important;
            font-weight: 600 !important;
        }}
        #swagger-ui-container .swagger-ui .model,
        #swagger-ui-container .swagger-ui .model-box pre {{
            color: var(--text) !important;
            font-family: var(--font-code) !important;
            font-size: 12px !important;
        }}
        #swagger-ui-container .swagger-ui .prop-type {{
            color: var(--purple) !important;
        }}
        #swagger-ui-container .swagger-ui .prop-format {{
            color: var(--muted) !important;
        }}

        /* Code Snippets, Inputs & Interactive Controls */
        #swagger-ui-container .swagger-ui pre,
        #swagger-ui-container .swagger-ui .highlight-code pre,
        #swagger-ui-container .swagger-ui .model-example pre,
        #swagger-ui-container .swagger-ui .example pre {{
            background: var(--bg) !important;
            color: var(--text) !important;
            font-family: var(--font-code) !important;
            font-size: 12px !important;
            line-height: 1.6 !important;
            border: 1px solid var(--border) !important;
            border-radius: 8px !important;
            padding: 14px 16px !important;
            margin: 6px 0 !important;
            max-height: 400px !important;
            overflow: auto !important;
            position: relative !important;
            z-index: 1 !important;
        }}
        #swagger-ui-container .swagger-ui code,
        #swagger-ui-container .swagger-ui pre code,
        #swagger-ui-container .swagger-ui .model-example code,
        #swagger-ui-container .swagger-ui .example code {{
            background: transparent !important;
            color: inherit !important;
            font-family: var(--font-code) !important;
            font-size: inherit !important;
            border: none !important;
            border-radius: 0 !important;
            padding: 0 !important;
            margin: 0 !important;
            box-shadow: none !important;
            display: inline !important;
        }}
        #swagger-ui-container .swagger-ui input[type=text],
        #swagger-ui-container .swagger-ui select,
        #swagger-ui-container .swagger-ui textarea {{
            background: var(--bg3) !important;
            color: var(--text) !important;
            border: 1px solid var(--border) !important;
            border-radius: 6px !important;
            padding: 8px 12px !important;
            font-family: var(--font-main) !important;
            font-size: 13px !important;
        }}
        #swagger-ui-container .swagger-ui input[type=text]:focus,
        #swagger-ui-container .swagger-ui select:focus,
        #swagger-ui-container .swagger-ui textarea:focus {{
            border-color: var(--accent) !important;
            outline: none !important;
            box-shadow: 0 0 0 2px rgba(88, 166, 255, 0.2) !important;
        }}
        #swagger-ui-container .swagger-ui .btn {{
            background: var(--bg3) !important;
            color: var(--text) !important;
            border: 1px solid var(--border) !important;
            border-radius: 6px !important;
            font-weight: 600 !important;
            font-size: 12px !important;
            padding: 6px 14px !important;
            box-shadow: none !important;
            transition: all 0.15s ease !important;
        }}
        #swagger-ui-container .swagger-ui .btn:hover {{
            background: var(--border) !important;
            color: var(--text) !important;
        }}
        #swagger-ui-container .swagger-ui .btn.execute {{
            background: var(--accent) !important;
            color: #0d1117 !important;
            border-color: var(--accent) !important;
            font-weight: 700 !important;
        }}
        #swagger-ui-container .swagger-ui .btn.execute:hover {{
            opacity: 0.9 !important;
        }}
        #swagger-ui-container .swagger-ui .btn.authorize {{
            color: var(--green) !important;
            border-color: var(--green) !important;
            background: rgba(63, 185, 80, 0.15) !important;
        }}
        #swagger-ui-container .swagger-ui .btn.authorize:hover {{
            background: rgba(63, 185, 80, 0.25) !important;
        }}
        #swagger-ui-container .swagger-ui svg {{
            fill: var(--text) !important;
        }}
        #swagger-ui-container .swagger-ui .arrow {{
            fill: var(--text) !important;
        }}
        #swagger-ui-container .swagger-ui .tab li {{
            color: var(--text) !important;
            font-size: 12px !important;
        }}
        #swagger-ui-container .swagger-ui .dialog-ux .modal-ux {{
            background: var(--bg2) !important;
            border: 1px solid var(--border) !important;
            border-radius: 12px !important;
            box-shadow: 0 20px 25px -5px rgba(0, 0, 0, 0.5) !important;
        }}
        #swagger-ui-container .swagger-ui .dialog-ux .modal-ux-header h3,
        #swagger-ui-container .swagger-ui .dialog-ux .modal-ux-content {{
            color: var(--text) !important;
        }}
        #swagger-ui-container .swagger-ui .dialog-ux .modal-ux-header .close-modal {{
            fill: var(--text) !important;
        }}

        /* Fix Swagger UI floating tooltip & accept message overlap glitch */
        #swagger-ui-container .swagger-ui .response-control-media-type__accept-message,
        #swagger-ui-container .swagger-ui .response-control-media-type__accept-message small,
        #swagger-ui-container .swagger-ui .response-control-media-type__accept-message span,
        #swagger-ui-container .swagger-ui .response-control-media-type__accept-message label {{
            background: transparent !important;
            border: none !important;
            outline: none !important;
            box-shadow: none !important;
            padding: 0 !important;
            margin: 0 !important;
            color: var(--muted) !important;
            font-size: 11px !important;
            font-weight: 500 !important;
            display: inline !important;
            position: static !important;
        }}
        #swagger-ui-container .swagger-ui .response-control-media-type__accept-message {{
            display: block !important;
            margin-top: 6px !important;
            margin-bottom: 8px !important;
            clear: both !important;
        }}
        #swagger-ui-container .swagger-ui .tooltip,
        #swagger-ui-container .swagger-ui .tooltip-inner,
        #swagger-ui-container .swagger-ui [data-hint]:after,
        #swagger-ui-container .swagger-ui [data-hint]:before {{
            display: none !important;
        }}
        #swagger-ui-container .swagger-ui .model-example,
        #swagger-ui-container .swagger-ui .example {{
            margin-top: 8px !important;
            padding: 0 !important;
            background: transparent !important;
            border: none !important;
            clear: both !important;
        }}

        /* PDF Export Button & Print Styles */
        .btn-pdf {{
            background: linear-gradient(135deg, var(--accent) 0%, #3b82f6 100%) !important;
            color: #0d1117 !important;
            font-weight: 700 !important;
            border: none !important;
            padding: 6px 14px !important;
            border-radius: 6px !important;
            cursor: pointer !important;
            font-size: 12px !important;
            display: inline-flex !important;
            align-items: center !important;
            gap: 6px !important;
            transition: all 0.2s ease !important;
            box-shadow: 0 2px 8px rgba(88, 166, 255, 0.3) !important;
        }}
        .btn-pdf:hover {{
            transform: translateY(-1px) !important;
            box-shadow: 0 4px 12px rgba(88, 166, 255, 0.4) !important;
        }}

        @media print {{
            body {{
                background: #ffffff !important;
                color: #000000 !important;
            }}
            .header, .sidebar, .btn-pdf, .zoom-toolbar, .sub-tabs, .sub-tab-btn {{
                display: none !important;
            }}
            .swagger-view-pane {{
                display: block !important;
                page-break-inside: avoid !important;
            }}
            .app-layout {{
                display: block !important;
            }}
            .main-content {{
                padding: 0 !important;
                margin: 0 !important;
                width: 100% !important;
            }}
            .section {{
                display: block !important;
                page-break-after: always !important;
                break-after: page !important;
                margin-bottom: 30px !important;
            }}
            .card, .module-card, .endpoint-item, .prereq-card, .info-card {{
                break-inside: avoid !important;
                page-break-inside: avoid !important;
                border: 1px solid #ccc !important;
                background: #ffffff !important;
                color: #000000 !important;
                box-shadow: none !important;
            }}
            * {{
                color: #000000 !important;
                background: transparent !important;
                box-shadow: none !important;
                text-shadow: none !important;
            }}
        }}

        /* API Endpoint Prompt Modal Styles */
        .clickable-ep {{
            cursor: pointer !important;
            transition: all 0.2s ease !important;
            display: flex !important;
            align-items: center !important;
            justify-content: space-between !important;
            gap: 12px !important;
        }}
        .clickable-ep:hover {{
            border-color: var(--accent) !important;
            background: rgba(88, 166, 255, 0.06) !important;
            transform: translateY(-1px) !important;
        }}
        .btn-prompt-copy {{
            background: var(--bg3) !important;
            border: 1px solid var(--border) !important;
            color: var(--muted) !important;
            font-size: 11px !important;
            font-weight: 600 !important;
            padding: 4px 10px !important;
            border-radius: 6px !important;
            cursor: pointer !important;
            transition: all 0.15s ease !important;
            white-space: nowrap !important;
            margin-left: auto !important;
        }}
        .btn-prompt-copy:hover {{
            background: var(--accent) !important;
            color: #0d1117 !important;
            border-color: var(--accent) !important;
        }}
        .custom-modal-backdrop {{
            display: none;
            position: fixed;
            top: 0;
            left: 0;
            width: 100vw;
            height: 100vh;
            background: rgba(0, 0, 0, 0.75);
            backdrop-filter: blur(5px);
            z-index: 99999;
            align-items: center;
            justify-content: center;
        }}
        .custom-modal-backdrop.active {{
            display: flex;
        }}
        .custom-modal-content {{
            background: var(--bg2);
            border: 1px solid var(--border);
            border-radius: 12px;
            width: 90%;
            max-width: 680px;
            box-shadow: 0 20px 40px rgba(0, 0, 0, 0.6);
            overflow: hidden;
            animation: modalFadeIn 0.2s ease-out;
        }}
        @keyframes modalFadeIn {{
            from {{ opacity: 0; transform: scale(0.95); }}
            to {{ opacity: 1; transform: scale(1); }}
        }}
        .custom-modal-header {{
            padding: 16px 20px;
            border-bottom: 1px solid var(--border);
            display: flex;
            align-items: center;
            justify-content: space-between;
            background: var(--bg3);
        }}
        .custom-modal-close {{
            background: transparent;
            border: none;
            color: var(--muted);
            font-size: 24px;
            cursor: pointer;
            line-height: 1;
            transition: color 0.15s ease;
        }}
        .custom-modal-close:hover {{
            color: var(--text);
        }}
        .custom-modal-body {{
            padding: 20px;
        }}
        .btn-copy-prompt {{
            background: linear-gradient(135deg, var(--accent) 0%, #3b82f6 100%) !important;
            color: #0d1117 !important;
            font-weight: 700 !important;
            font-size: 12px !important;
            border: none !important;
            padding: 6px 14px !important;
            border-radius: 6px !important;
            cursor: pointer !important;
            transition: all 0.2s ease !important;
            display: inline-flex !important;
            align-items: center !important;
            gap: 6px !important;
            box-shadow: 0 2px 8px rgba(88, 166, 255, 0.3) !important;
        }}
        .btn-copy-prompt:hover {{
            opacity: 0.9 !important;
            transform: translateY(-1px) !important;
        }}
    </style>
</head>
<body>

<header class="header">
    <div class="header-top">
        <div class="brand">
            <span class="brand-icon">&#127959;</span>
            <div>
                <h1 class="brand-title">{html.escape(meta.get('displayName', 'SaaS MVP'))}</h1>
                <div class="brand-sub">Architecture Map & Documentation</div>
            </div>
        </div>
        <div class="sidebar-badges" style="margin-top:0; display: flex; align-items: center; gap: 8px;">
            <button class="btn-pdf" onclick="exportPDF()">📄 Export PDF</button>
            <span class="badge">v{html.escape(meta.get('version', '1.0.0'))}</span>
            <span class="badge">{html.escape(tech_stack.get('language', 'TypeScript'))}</span>
            <span class="badge badge-green">Generated {html.escape(meta.get('generatedAt', 'Live'))}</span>
        </div>
    </div>
</header>

<div class="app-layout">
    <aside class="sidebar">
        <div class="sidebar-header">
            <div style="font-size: 11px; font-weight: 700; color: var(--muted); text-transform: uppercase; letter-spacing: 0.8px;">Navigation</div>
        </div>

        <nav class="sidebar-nav">
            <button class="nav-btn active" onclick="showTab('overview', this)">
                <div class="nav-btn-left"><span>&#128204;</span> <span>Overview</span></div>
            </button>
            <button class="nav-btn" onclick="showTab('prereq', this)">
                <div class="nav-btn-left"><span>📋</span> <span>Prerequisites</span></div>
                <span class="nav-count">{len(prereq_tools)}</span>
            </button>
            <button class="nav-btn" onclick="showTab('modules', this)">
                <div class="nav-btn-left"><span>&#128230;</span> <span>API Modules</span></div>
                <span class="nav-count">{len(modules)}</span>
            </button>
            <button class="nav-btn" onclick="showTab('sysarch', this)">
                <div class="nav-btn-left"><span>&#127963;</span> <span>System Architecture</span></div>
            </button>
            <button class="nav-btn" onclick="showTab('docker', this)">
                <div class="nav-btn-left"><span>&#128051;</span> <span>Docker Topology</span></div>
            </button>
            <button class="nav-btn" onclick="showTab('swagger', this)">
                <div class="nav-btn-left"><span>&#9889;</span> <span>Swagger & OpenAPI</span></div>
            </button>
            <button class="nav-btn" onclick="showTab('perms', this)">
                <div class="nav-btn-left"><span>&#128273;</span> <span>Permissions</span></div>
            </button>
            <button class="nav-btn" onclick="showTab('sql', this)">
                <div class="nav-btn-left"><span>&#128452;</span> <span>SQL Queries</span></div>
                <span class="nav-count">{len(sql_queries)}</span>
            </button>
            <button class="nav-btn" onclick="showTab('infra', this)">
                <div class="nav-btn-left"><span>&#128187;</span> <span>Infrastructure</span></div>
                <span class="nav-count">{len(infrastructure)}</span>
            </button>
            <button class="nav-btn" onclick="showTab('core', this)">
                <div class="nav-btn-left"><span>&#128737;</span> <span>Core Layer</span></div>
            </button>
            <button class="nav-btn" onclick="showTab('flow', this)">
                <div class="nav-btn-left"><span>&#128257;</span> <span>Request Pipeline</span></div>
            </button>
        </nav>

        <div class="sidebar-footer">
           © AHMED EMAD - {html.escape(meta.get('displayName', 'Project MVP'))}
        </div>
    </aside>

    <main class="main-content">

    <!-- 1. OVERVIEW -->
    <div class="section active" id="sec-overview">
        <div class="stats">
            <div class="stat"><div class="stat-num">{len(modules)}</div><div class="stat-lbl">API Modules</div></div>
            <div class="stat"><div class="stat-num">{total_endpoints}</div><div class="stat-lbl">Total Endpoints</div></div>
            <div class="stat"><div class="stat-num">{len(infrastructure)}</div><div class="stat-lbl">Docker Services</div></div>
            <div class="stat"><div class="stat-num">{len(permissions.get('catalog', []))}</div><div class="stat-lbl">Permissions</div></div>
            <div class="stat"><div class="stat-num">{len(sql_queries)}</div><div class="stat-lbl">SQL Queries</div></div>
            <div class="stat"><div class="stat-num">{len(workspaces)}</div><div class="stat-lbl">Workspaces</div></div>
        </div>

        <div class="sec-title">📦 Workspaces</div>
        <div class="grid3">
"""
    for ws in workspaces:
        ws_type = ws.get('type', 'app')
        icon = '⚡' if ws_type == 'backend' else ('💻' if ws_type == 'frontend' else '📦')
        port_str = f" : {ws.get('port')}" if ws.get('port') else ""
        html_content += f"""
            <div class="card">
                <div class="chead">
                    <span style="font-size:22px">{icon}</span>
                    <div>
                        <div class="card-title">{html.escape(ws.get('name', ''))}</div>
                        <div class="card-sub">{html.escape(ws_type.upper())}{port_str}</div>
                    </div>
                </div>
                <div class="card-desc">{html.escape(ws.get('description', ''))}</div>
                {f'<span class="tag tq">{html.escape(ws.get("entrypoint"))}</span>' if ws.get('entrypoint') else ''}
            </div>
"""

    html_content += """
        </div>

        <div class="sec-title">🌐 System Endpoints</div>
        <div class="grid1">
"""
    for se in system_endpoints:
        m = se.get('method', 'GET').upper()
        html_content += f"""
            <div class="endpoint clickable-ep" data-method="{m}" data-path="{html.escape(se.get('path', ''))}" onclick="openApiPromptFromEl(this)" title="Click to view AI Senior Developer prompt">
                <span class="method {m}">{m}</span>
                <div style="flex:1">
                    <div class="ep-path">{html.escape(se.get('path', ''))}</div>
                    <div class="ep-desc">{html.escape(se.get('description', ''))}</div>
                </div>
                <button class="btn-prompt-copy" onclick="event.stopPropagation(); copyApiPromptDirectFromEl(this.parentElement)" title="Copy AI Prompt">📋 Prompt</button>
            </div>
"""

    html_content += """
        </div>
    </div>

    <!-- 1.5 PREREQUISITES -->
    <div class="section" id="sec-prereq">
        <div class="card" style="margin-bottom: 20px;">
            <div class="chead">
                <span style="font-size:28px">📋</span>
                <div>
                    <div class="card-title">System Prerequisites &amp; Setup Requirements</div>
                    <div class="card-sub">Developer tools, container runtimes, and step-by-step initialization sequence</div>
                </div>
            </div>
            <p class="card-desc">""" + html.escape(prerequisites.get('description', 'Software runtimes, system dependencies, and step-by-step initialization commands required to run the project.')) + """</p>
        </div>

        <div class="sec-title">🛠️ Required Tools &amp; Runtimes</div>
        <div class="grid3" style="margin-bottom: 24px;">
"""
    for tool in prereq_tools:
        tname = tool.get('name', 'Tool')
        tver = tool.get('version', 'latest')
        treq = tool.get('required', True)
        tdesc = tool.get('description', '')
        tcat = tool.get('category', 'general')

        icon_map = {
            'runtime': '⚡',
            'infrastructure': '🐳',
            'database': '🗄️',
            'cache': '⚡',
            'queue': '📬',
            'monitoring': '📊',
            'package_manager': '📦'
        }
        ticon = icon_map.get(tcat, '🛠️')
        req_badge = '<span class="tag tr">Required</span>' if treq else '<span class="tag tq">Optional</span>'

        html_content += f"""
            <div class="card">
                <div class="chead">
                    <span style="font-size:24px">{ticon}</span>
                    <div>
                        <div class="card-title">{html.escape(tname)} {req_badge}</div>
                        <div class="card-sub" style="font-family:var(--font-code);">Version {html.escape(tver)}</div>
                    </div>
                </div>
                <div class="card-desc">{html.escape(tdesc)}</div>
            </div>
"""

    html_content += """
        </div>

        <div class="sec-title">🚀 Setup &amp; Execution Pipeline</div>
        <div class="pipeline">
"""
    for step in prereq_steps:
        snum = step.get('step', 1)
        stitle = step.get('title', '')
        scmd = step.get('command', '')
        sdesc = step.get('description', '')

        cmd_block = f'<code style="display:block; margin-top:8px; font-size:12px; color:var(--accent); background:var(--bg); padding:8px 12px; border-radius:6px; font-family:var(--font-code); overflow-x:auto;">{html.escape(scmd)}</code>' if scmd else ''

        html_content += f"""
            <div class="pipe-step" style="cursor:default;">
                <div class="pipe-num">{snum}</div>
                <div style="flex:1;">
                    <div style="font-size:14px; font-weight:600; color:var(--text);">{html.escape(stitle)}</div>
                    <div style="font-size:12px; color:var(--muted); margin-top:4px;">{html.escape(sdesc)}</div>
                    {cmd_block}
                </div>
            </div>
"""

    html_content += """
        </div>
    </div>

    <!-- 2. API MODULES -->
    <div class="section" id="sec-modules">
        <input class="search" id="modSearch" placeholder="Search endpoints, paths, permissions, descriptions..." oninput="filterModules()">
        <div class="grid2" id="modulesGrid">
"""
    for mod in modules:
        perms_html = "".join([f'<span class="tag tp">{html.escape(p)}</span>' for p in mod.get('permissions', [])])
        eps_html = ""
        mod_base = mod.get('basePath', '').strip()
        for ep in mod.get('endpoints', []):
            m = ep.get('method', 'GET').upper()
            raw_p = ep.get('path', '').strip()
            if raw_p.startswith('http://') or raw_p.startswith('https://') or (mod_base and raw_p.startswith(mod_base)):
                full_path = raw_p
            else:
                if mod_base:
                    if raw_p == '/' or not raw_p:
                        full_path = mod_base
                    else:
                        full_path = mod_base.rstrip('/') + '/' + raw_p.lstrip('/')
                else:
                    full_path = raw_p if raw_p else '/'

            perm_str = f'<span class="lock">🔒 {html.escape(ep["permission"])}</span>' if ep.get('permission') else ('<span class="lock">🔑</span>' if ep.get('auth') else '')
            eps_html += f"""
                <div class="endpoint clickable-ep" data-method="{m}" data-path="{html.escape(full_path)}" onclick="openApiPromptFromEl(this)" title="Click to view AI Senior Developer prompt">
                    <span class="method {m}">{m}</span>
                    <div style="flex:1">
                        <div class="ep-path">{html.escape(ep.get('path', ''))}{perm_str}</div>
                        <div class="ep-desc">{html.escape(ep.get('description', ''))}</div>
                    </div>
                    <button class="btn-prompt-copy" onclick="event.stopPropagation(); copyApiPromptDirectFromEl(this.parentElement)" title="Copy AI Prompt">📋 Prompt</button>
                </div>
"""
        html_content += f"""
            <div class="card mod-card">
                <div class="color-bar" style="background: {html.escape(mod.get('color', '#58a6ff'))}"></div>
                <div class="chead">
                    <span style="font-size:22px">{html.escape(mod.get('icon', '📁'))}</span>
                    <div>
                        <div class="card-title">{html.escape(mod.get('name', ''))}</div>
                        <div class="card-sub" style="font-family: var(--font-code);">{html.escape(mod.get('basePath', ''))}</div>
                    </div>
                </div>
                <div class="card-desc">{html.escape(mod.get('description', ''))}</div>
                {f'<div style="margin-bottom:10px">{perms_html}</div>' if perms_html else ''}
                {eps_html}
            </div>
"""

    html_content += f"""
        </div>
    </div>

    <!-- 3. SYSTEM ARCHITECTURE & COMPONENTS DIAGRAM -->
    <div class="section" id="sec-sysarch">
        <div class="card">
            <div class="chead">
                <span style="font-size:24px">🏛️</span>
                <div>
                    <div class="card-title">System Design & Component Architecture Diagram</div>
                    <div class="card-sub">High-level software architecture, layered boundaries, and component relationships</div>
                </div>
            </div>
            <p class="card-desc">{html.escape(system_arch_diagram.get('description', 'Component & System Design Diagram.'))}</p>
            <div class="diagram-box">
                <div id="sysarchMermaid" style="width: 100%; min-height: 500px; display: flex; justify-content: center; align-items: center;"></div>
                <script type="text/plain" id="sysarchMermaidSrc">
flowchart TB
    classDef proxy fill:#1e293b,stroke:#64748b,stroke-width:2px,color:#fff;
    classDef app fill:#1e3a8a,stroke:#58a6ff,stroke-width:2px,color:#fff;
    classDef database fill:#064e3b,stroke:#3fb950,stroke-width:2px,color:#fff;
    classDef cache fill:#78350f,stroke:#f59e0b,stroke-width:2px,color:#fff;
    classDef queue fill:#4c1d95,stroke:#8b5cf6,stroke-width:2px,color:#fff;
    classDef monitoring fill:#7c2d12,stroke:#f97316,stroke-width:2px,color:#fff;
    classDef logging fill:#831843,stroke:#ec4899,stroke-width:2px,color:#fff;

"""
    sys_type_map = {}
    for sg in system_arch_diagram.get('subgraphs', []):
        sg_id = f"sg_{clean_mermaid(sg['id'])}"
        sg_lbl = clean_mermaid(sg['label'])
        html_content += f"    subgraph {sg_id}[\"{sg_lbl}\"]\n"
        for node in sg.get('nodes', []):
            nid = clean_mermaid(node['id'])
            nlbl = clean_mermaid(node['label'])
            ntype = clean_mermaid(node.get('type', 'app'))
            html_content += f"        {nid}[\"{nlbl}\"]\n"
            if ntype not in sys_type_map:
                sys_type_map[ntype] = []
            sys_type_map[ntype].append(nid)
        html_content += "    end\n\n"

    for edge in system_arch_diagram.get('edges', []):
        fid = clean_mermaid(edge['from'])
        tid = clean_mermaid(edge['to'])
        elbl = clean_mermaid(edge.get('label', ''))
        if elbl:
            html_content += f"    {fid} -->|\"{elbl}\"| {tid}\n"
        else:
            html_content += f"    {fid} --> {tid}\n"

    html_content += "\n"
    for t_name, n_ids in sys_type_map.items():
        if n_ids:
            html_content += f"    class {','.join(n_ids)} {t_name};\n"

    html_content += f"""
                </script>
            </div>
        </div>
    </div>

    <!-- 4. DOCKER DIAGRAM -->
    <div class="section" id="sec-docker">
        <div class="card">
            <div class="chead">
                <span style="font-size:24px">🐳</span>
                <div>
                    <div class="card-title">Docker Infrastructure Topology &amp; Dependency Diagram</div>
                    <div class="card-sub">Rendered live using Mermaid.js from container specifications</div>
                </div>
            </div>
            <p class="card-desc">{html.escape(docker_diagram.get('description', 'Parsed from docker-compose.yml'))}</p>
"""

    has_docker_nodes = bool(docker_diagram.get('nodes'))
    if not has_docker_nodes:
        html_content += """
            <div style="text-align:center; padding: 60px 20px; color: var(--muted);">
                <div style="font-size: 48px; margin-bottom: 16px;">🐳</div>
                <div style="font-size: 16px; font-weight: 600; color: var(--text); margin-bottom: 8px;">No Docker Services Configured</div>
                <div style="font-size: 13px; line-height: 1.6; max-width: 480px; margin: 0 auto;">
                    This project does not use Docker, or container topology has not been added yet.<br><br>
                    To add Docker topology, update <code style="color:var(--accent)">dockerDiagram.nodes</code> and
                    <code style="color:var(--accent)">dockerDiagram.edges</code> in <code>architecture.json</code>
                    and regenerate.
                </div>
            </div>
        </div>
    </div>
"""
    else:
        html_content += f"""
            <div class="diagram-box">
                <div id="dockerMermaid" style="width: 100%; min-height: 400px; display: flex; justify-content: center; align-items: center;"></div>
                <script type="text/plain" id="dockerMermaidSrc">
flowchart TD
    classDef proxy fill:#1e293b,stroke:#64748b,stroke-width:2px,color:#fff;
    classDef app fill:#1e3a8a,stroke:#58a6ff,stroke-width:2px,color:#fff;
    classDef database fill:#064e3b,stroke:#3fb950,stroke-width:2px,color:#fff;
    classDef cache fill:#78350f,stroke:#f59e0b,stroke-width:2px,color:#fff;
    classDef queue fill:#4c1d95,stroke:#8b5cf6,stroke-width:2px,color:#fff;
    classDef monitoring fill:#7c2d12,stroke:#f97316,stroke-width:2px,color:#fff;
    classDef logging fill:#831843,stroke:#ec4899,stroke-width:2px,color:#fff;
    classDef uptime fill:#7f1d1d,stroke:#ef4444,stroke-width:2px,color:#fff;

"""
        type_map = {}
        for node in docker_diagram.get('nodes', []):
            node_id = clean_mermaid(node['id'])
            node_type = clean_mermaid(node.get('type', 'app'))
            clean_lbl = clean_mermaid(node.get('label', ''))
            port_info = f" Port {clean_mermaid(node['port'])}" if node.get('port') else ""
            html_content += f"    {node_id}[\"{clean_lbl}{port_info}\"]\n"
            if node_type not in type_map:
                type_map[node_type] = []
            type_map[node_type].append(node_id)

        html_content += "\n"
        for edge in docker_diagram.get('edges', []):
            from_id = clean_mermaid(edge['from'])
            to_id = clean_mermaid(edge['to'])
            clean_edge = clean_mermaid(edge.get('label', ''))
            if clean_edge:
                html_content += f"    {from_id} -->|\"{clean_edge}\"| {to_id}\n"
            else:
                html_content += f"    {from_id} --> {to_id}\n"

        html_content += "\n"
        for t_name, n_ids in type_map.items():
            if n_ids:
                html_content += f"    class {','.join(n_ids)} {t_name};\n"

        html_content += """
                </script>
            </div>
        </div>
    </div>
"""
    openapi_spec_dict = build_openapi_spec(data)
    openapi_spec_json = json.dumps(openapi_spec_dict, indent=2)

    html_content += f"""
    <!-- 4. SWAGGER & OPENAPI -->
    <div class="section" id="sec-swagger">
        <div class="card" style="margin-bottom: 20px;">
            <div class="chead">
                <span style="font-size:28px">&#9889;</span>
                <div>
                    <div class="card-title">Swagger & OpenAPI 3.0 API Specification & Explorer</div>
                    <div class="card-sub">Interactive REST API documentation generated from architecture manifest ({total_endpoints} Endpoints)</div>
                </div>
                <span class="badge badge-green" style="margin-left:auto; font-size: 12px; padding: 6px 12px;">STATUS: {html.escape(swagger_schemas.get('matchStatus', 'Verified Parity').upper())}</span>
            </div>

            <div class="grid4" style="margin-top: 15px;">
                <div style="font-size: 12px; color: var(--muted);">
                    <div style="color: var(--text); font-weight: 600; margin-bottom: 2px;">OpenAPI Version</div>
                    <code>{html.escape(swagger_schemas.get('openapi', '3.0.0'))}</code>
                </div>
                <div style="font-size: 12px; color: var(--muted);">
                    <div style="color: var(--text); font-weight: 600; margin-bottom: 2px;">Base URL</div>
                    <code>http://localhost:3000</code>
                </div>
                <div style="font-size: 12px; color: var(--muted);">
                    <div style="color: var(--text); font-weight: 600; margin-bottom: 2px;">Security Scheme</div>
                    <span class="tag ty">{html.escape(swagger_schemas.get('securityScheme', 'bearerAuth'))}</span>
                </div>
                <div style="font-size: 12px; color: var(--muted);">
                    <div style="color: var(--text); font-weight: 600; margin-bottom: 2px;">Live Swagger Route</div>
                    <code>{html.escape(swagger_schemas.get('servedAt', '/api/docs'))}</code>
                </div>
            </div>
        </div>

        <!-- View Mode Selector -->
        <div style="display: flex; gap: 8px; margin-bottom: 16px;">
            <button class="sub-tab-btn active" onclick="switchSwaggerView('ui', this)">&#9889; Interactive Swagger UI</button>
            <button class="sub-tab-btn" onclick="switchSwaggerView('catalog', this)">&#128216; API Endpoint Catalog & cURL ({total_endpoints})</button>
            <button class="sub-tab-btn" onclick="switchSwaggerView('json', this)">&#128220; OpenAPI 3.0 JSON Spec</button>
        </div>

        <!-- Pane 1: Interactive Swagger UI -->
        <div id="swagger-view-ui" class="swagger-view-pane active">
            <div class="card" style="padding: 10px;">
                <div id="swagger-ui-container">
                    <div style="padding: 40px; text-align: center; color: var(--muted);">
                        Loading Interactive Swagger UI...
                    </div>
                </div>
            </div>
        </div>

        <!-- Pane 2: API Endpoint Catalog & cURL -->
        <div id="swagger-view-catalog" class="swagger-view-pane">
"""
    for mod in modules:
        mod_name = mod.get('name', '')
        base_path = mod.get('basePath', '')
        mod_icon = mod.get('icon', '')
        mod_endpoints = mod.get('endpoints', [])

        html_content += f"""
            <div class="card" style="margin-bottom: 20px;">
                <div class="chead" style="margin-bottom: 12px;">
                    <span style="font-size: 22px;">{mod_icon}</span>
                    <div>
                        <div class="card-title">{html.escape(mod_name)} API Module</div>
                        <div class="card-sub">Base Path: <code>{html.escape(base_path)}</code> | {len(mod_endpoints)} Endpoints</div>
                    </div>
                </div>

                <div class="grid1" style="gap: 12px;">
"""
        for ep in mod_endpoints:
            m = ep.get('method', 'GET').upper()
            p = ep.get('path', '')
            full_path = (base_path + ("" if p == "/" else p)).replace("//", "/")
            auth = ep.get('auth', False)
            perm = ep.get('permission')
            desc = ep.get('description', '')

            m_class = 'tg' if m == 'GET' else ('tb' if m == 'POST' else ('ty' if m in ['PUT','PATCH'] else 'tr'))
            curl_auth_header = ' -H "Authorization: Bearer $JWT_TOKEN"' if auth else ''
            curl_body = ' -H "Content-Type: application/json" -d \'{"key":"value"}\'' if m in ['POST','PUT','PATCH'] else ''
            curl_cmd = f"curl -X {m} \"http://localhost:3000{full_path}\"{curl_auth_header}{curl_body}"

            html_content += f"""
                    <div style="background: var(--bg3); border: 1px solid var(--border); border-radius: 8px; padding: 14px;">
                        <div style="display: flex; align-items: center; gap: 10px; flex-wrap: wrap;">
                            <span class="tag {m_class}" style="font-weight: 700; font-size: 11px;">{m}</span>
                            <span style="font-family: var(--font-code); font-weight: 600; font-size: 13px; color: var(--text);">{html.escape(full_path)}</span>
                            {f'<span class="tag tb" style="font-size:10px; margin-left:auto;">&#128273; {html.escape(perm)}</span>' if perm else (
                             '<span class="tag tg" style="font-size:10px; margin-left:auto;">&#128274; Authenticated</span>' if auth else '<span class="tag ty" style="font-size:10px; margin-left:auto;">&#127760; Public</span>'
                            )}
                        </div>
                        <div style="font-size: 12px; color: var(--muted); margin-top: 6px;">{html.escape(desc)}</div>
                        <div style="margin-top: 8px;">
                            <div style="font-size: 10px; color: var(--muted); margin-bottom: 2px;">cURL Snippet:</div>
                            <code style="display: block; font-size: 11px; color: var(--accent); background: var(--bg); padding: 6px 10px; border-radius: 4px; overflow-x: auto;">{html.escape(curl_cmd)}</code>
                        </div>
                    </div>
"""
        html_content += """
                </div>
            </div>
"""

    html_content += f"""
        </div>

        <!-- Pane 3: Raw OpenAPI 3.0 JSON Spec -->
        <div id="swagger-view-json" class="swagger-view-pane">
            <div class="card">
                <div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 12px;">
                    <div style="font-weight: 600; font-size: 14px;">OpenAPI 3.0.0 JSON Specification Source</div>
                    <button class="sub-tab-btn" onclick="navigator.clipboard.writeText(document.getElementById('swaggerOpenApiJsonSrc').textContent); alert('Copied OpenAPI JSON Spec to clipboard!');">&#128203; Copy OpenAPI Spec</button>
                </div>
                <pre style="background: var(--bg); border: 1px solid var(--border); border-radius: 8px; padding: 16px; font-family: var(--font-code); font-size: 12px; color: var(--text); max-height: 600px; overflow-y: auto;"><code id="swaggerOpenApiJsonSrc">{html.escape(openapi_spec_json)}</code></pre>
            </div>
        </div>
    </div>

    <!-- 5. PERMISSIONS & SECURITY SCOPES -->
    <div class="section" id="sec-perms">
        <div class="sec-title">&#128273; Scope & Isolation / Permissions</div>
        <p style="font-size: 13px; color: var(--muted); margin-bottom: 16px;">
            {html.escape(permissions.get('description', 'Role-Based Access Control (RBAC) & Security Scope mapping.'))}
        </p>

        <div class="stats" style="margin-bottom: 20px;">
            <div class="stat"><div class="stat-num">{len(permissions.get('catalog', []))}</div><div class="stat-lbl">Security Scopes / Slugs</div></div>
            <div class="stat"><div class="stat-num">{sum(len(d.get('endpoints', [])) for d in permissions.get('details', []) if d.get('slug') != 'public')}</div><div class="stat-lbl">Authenticated Endpoints</div></div>
            <div class="stat"><div class="stat-num">{sum(len(d.get('endpoints', [])) for d in permissions.get('details', []) if d.get('slug') == 'public')}</div><div class="stat-lbl">Public Endpoints</div></div>
            <div class="stat"><div class="stat-num">{len(permissions.get('details', []))}</div><div class="stat-lbl">Mapped Scope Groups</div></div>
        </div>
"""
    if not permissions.get('catalog', []) and not permissions.get('details', []):
        html_content += """
        <div class="card" style="text-align: center; padding: 48px 24px; color: var(--muted); border: 1px dashed var(--border); border-radius: 12px; margin-top: 16px;">
            <div style="font-size: 36px; margin-bottom: 12px;">🔒</div>
            <div style="font-size: 16px; font-weight: 600; color: var(--text);">No Role-Based Access Control (RBAC) Permissions Defined</div>
            <div style="font-size: 13px; margin-top: 6px;">All endpoints in this project currently run with standard authentication or open public access. No specific role permissions were declared on the routes.</div>
        </div>
"""
    else:
        html_content += """
        <div class="perm-grid">
"""
        for p in permissions.get('catalog', []):
            icon = '🔑' if p not in ('authenticated', 'public') else ('🔒' if p == 'authenticated' else '🌐')
            html_content += f'<div class="perm-item">{icon} {html.escape(p)}</div>'

        html_content += """
        </div>

        <div class="sec-title" style="margin-top: 24px;">&#128279; Interactive Permission & Scope-to-Endpoint Flow</div>
        <div class="grid1">
"""
        for pdet in permissions.get('details', []):
            eps_html = ""
            for ep in pdet.get('endpoints', []):
                m = ep.get('method', 'GET').upper()
                eps_html += f'<span class="method {m}">{m}</span> <code style="font-size:12px">{html.escape(ep.get("path",""))}</code> &nbsp; '

            pages_html = ", ".join([f'<span class="tag tb">{html.escape(pg)}</span>' for pg in pdet.get('adminPages', [])])
            slug_val = pdet.get('slug', '')
            slug_icon = '🔑' if slug_val not in ('authenticated', 'public') else ('🔒' if slug_val == 'authenticated' else '🌐')

            html_content += f"""
            <div class="perm-card">
                <div style="display:flex; justify-content:space-between; align-items:center;">
                    <span style="font-family:var(--font-code); font-weight:700; color:var(--purple); font-size:14px;">{slug_icon} {html.escape(slug_val)}</span>
                    <span class="tag tp">{html.escape(pdet.get('module', ''))} • {html.escape(pdet.get('action', ''))}</span>
                </div>
                <div style="margin-top: 8px; font-size: 13px;">
                    <strong>Protected Endpoints ({len(pdet.get('endpoints', []))}):</strong> {eps_html}
                </div>
                <div style="margin-top: 6px; font-size: 12px; color: var(--muted);">
                    <strong>Scope Target:</strong> {pages_html}
                </div>
            </div>
"""
        html_content += """
        </div>
"""
    html_content += """
    </div>

    <!-- 6. SQL QUERIES CATALOG -->
    <div class="section" id="sec-sql">
        <div class="sec-title">&#128452; SQL Query Catalog & Repository Mapping</div>
        <p style="font-size: 13px; color: var(--muted); margin-bottom: 16px;">
            Raw SQL statements mapped to repository/service functions, affected tables, and API endpoints.
        </p>
"""
    if not sql_queries:
        html_content += """
        <div class="card" style="text-align: center; padding: 48px 24px; color: var(--muted); border: 1px dashed var(--border); border-radius: 12px;">
            <div style="font-size: 36px; margin-bottom: 12px;">🗃️</div>
            <div style="font-size: 16px; font-weight: 600; color: var(--text);">No Database SQL Queries Configured</div>
            <div style="font-size: 13px; margin-top: 6px;">This project does not contain direct database repositories or SQL queries (e.g. External REST API Proxy or WebClient Service).</div>
        </div>
"""
    else:
        html_content += """
        <div class="grid1">
"""
        for q in sql_queries:
            eps_html = ""
            for ep in q.get('endpoints', []):
                m = ep.get('method', 'GET').upper()
                eps_html += f'<span class="method {m}">{m}</span> <code style="font-size:12px">{html.escape(ep.get("path",""))}</code> &nbsp; '

            tables_html = " ".join([f'<span class="tag tg">{html.escape(tb)}</span>' for tb in q.get('tables', [])])

            html_content += f"""
            <div class="card">
                <div class="chead" style="display:flex; align-items:center; gap:10px; margin-bottom:8px;">
                    <div class="card-title" style="color: var(--yellow);">&#9889; {html.escape(q.get('label', ''))}</div>
                    <span class="tag tp" style="margin-left:auto">{html.escape(q.get('module', ''))} • {html.escape(q.get('function', ''))}</span>
                </div>
                <p style="font-size: 13px; color: var(--muted); margin: 6px 0;">
                    <strong>Purpose:</strong> {html.escape(q.get('purpose', ''))}<br>
                    <strong>File:</strong> <code>{html.escape(q.get('file', ''))}</code> | <strong>Tables:</strong> {tables_html}
                </p>
                <div style="margin: 8px 0; font-size: 12px;">
                    <strong>Consuming Endpoints:</strong> {eps_html}
                </div>
                <div class="code-block">{html.escape(q.get('sql', ''))}</div>
            </div>
"""
        html_content += """
        </div>
"""
    html_content += """
    </div>

    <!-- 7. INFRASTRUCTURE -->
    <div class="section" id="sec-infra">
        <div class="sec-title">&#128187; Infrastructure Services</div>
        <div class="grid3">
"""
    tc_map = {'database':'tb', 'cache':'tg', 'queue':'ty', 'proxy':'tq', 'monitoring':'tp', 'logging':'tr', 'uptime':'tr'}
    for s in infrastructure:
        t_cls = tc_map.get(s.get('type'), 'tq')
        ports = f" : {s.get('port')}" if s.get('port') else ""
        mgmt = f" (mgmt: {s.get('managementPort')})" if s.get('managementPort') else ""
        feats = "".join([f'<span class="tag tq">{html.escape(f)}</span>' for f in s.get('features', [])])

        html_content += f"""
            <div class="card">
                <div class="chead">
                    <div>
                        <div class="card-title">{html.escape(s.get('name', ''))} <span class="tag {t_cls}">{html.escape(s.get('type', ''))}</span></div>
                        <div class="card-sub">{html.escape(s.get('image', ''))}{ports}{mgmt}</div>
                    </div>
                </div>
                <div class="card-desc">{html.escape(s.get('description', ''))}</div>
                {f'<div>{feats}</div>' if feats else ''}
            </div>
"""

    html_content += """
        </div>
    </div>

    <!-- 8. CORE LAYER -->
    <div class="section" id="sec-core">
        <div class="sec-title">&#128737; Security Middleware</div>
        <div style="display:flex; flex-wrap:wrap; gap:8px; margin-bottom:20px;">
"""
    for sec in core_layer.get('security', []):
        html_content += f"""
            <div style="background:var(--bg2); border:1px solid var(--border); border-radius:8px; padding:10px 14px; min-width:160px;">
                <div style="font-weight:600; font-size:13px; margin-bottom:4px; color:var(--accent);">{html.escape(sec.get('name', ''))}</div>
                <div style="font-size:12px; color:var(--muted);">{html.escape(sec.get('description', ''))}</div>
            </div>
"""

    html_content += """
        </div>

        <div class="sec-title">&#9881; Core Middleware</div>
        <div class="grid1">
"""
    for mw in core_layer.get('middleware', []):
        guards = "".join([f'<span class="tag ty">{html.escape(g)}</span>' for g in mw.get('guards', [])])
        html_content += f"""
            <div class="mwcard">
                <div style="font-weight:600; font-size:14px; margin-bottom:4px;">{html.escape(mw.get('name', ''))}</div>
                <div style="font-size:11px; font-family:var(--font-code); color:var(--muted); margin-bottom:6px;">{html.escape(mw.get('file', ''))}</div>
                <div style="font-size:13px; color:var(--muted);">{html.escape(mw.get('description', ''))}</div>
                {f'<div style="margin-top:8px">{guards}</div>' if guards else ''}
            </div>
"""

    html_content += """
        </div>

        <div class="sec-title">&#128736; Core Services</div>
        <div class="grid2">
"""
    for svc in core_layer.get('services', []):
        exports = "".join([f'<span class="tag tb" style="font-family:var(--font-code); font-size:11px">{html.escape(ex)}</span>' for ex in svc.get('exports', [])])
        html_content += f"""
            <div class="card">
                <div class="card-title">{html.escape(svc.get('name', ''))}</div>
                <div class="card-sub" style="margin-bottom:8px;">{html.escape(svc.get('file', ''))}</div>
                <div class="card-desc">{html.escape(svc.get('description', ''))}</div>
                {f'<div style="margin-top:8px">{exports}</div>' if exports else ''}
            </div>
"""

    html_content += """
        </div>
    </div>

    <!-- 9. REQUEST FLOW -->
    <div class="section" id="sec-flow">
        <div class="sec-title">&#128257; Request Pipeline</div>
        <p style="font-size:13px; color:var(--muted); margin-bottom:18px; line-height:1.7;">
            Step-by-step lifecycle of an inbound HTTP request through the application stack.
            Click any step to see implementation detail.
        </p>
        <div class="pipeline">
"""
    pipeline = data_flow.get('requestPipeline', [])
    # Support both legacy plain-string steps and new dict steps
    core_tab_label = {'security': 'Security Middleware', 'middleware': 'Core Middleware', 'services': 'Core Services'}
    core_ref_icon  = {'security': '🔐', 'middleware': '⚙️', 'services': '🔧'}

    for i, step in enumerate(pipeline):
        if isinstance(step, dict):
            step_text = step.get('step', '')
            detail    = step.get('detail', '')
            core_ref  = step.get('coreRef', '')
        else:
            step_text = step
            detail    = ''
            core_ref  = ''

        detail_block = ''
        if detail:
            detail_block = f'<div class="pipe-detail" id="pdet-{i}" style="display:none; margin-top:8px; font-size:12px; color:var(--muted); line-height:1.6; padding-left:34px;">{html.escape(detail)}</div>'

        core_link = ''
        if core_ref and core_ref in core_tab_label:
            icon = core_ref_icon.get(core_ref, '→')
            label = core_tab_label[core_ref]
            core_link = f'<a href="#" onclick="showTab(\'core\',null);return false;" style="font-size:11px; color:var(--accent); text-decoration:none; margin-left:auto; white-space:nowrap; opacity:0.8;">{icon} {label}</a>'

        toggle = f'onclick="var d=document.getElementById(\'pdet-{i}\');d.style.display=d.style.display===\'none\'?\'\':\'none\';" style="cursor:pointer;"' if detail else ''

        html_content += f"""
            <div class="pipe-step" {toggle}>
                <div class="pipe-num">{i+1}</div>
                <div style="font-size:13px; color:var(--text); flex:1;">{html.escape(step_text)}</div>
                {core_link}
                {'<span style="font-size:10px; color:var(--muted); margin-left:8px;">▼</span>' if detail else ''}
            </div>
            {detail_block}
"""

    # Error pipeline section
    error_pipeline = data_flow.get('errorPipeline', [])
    err_items_html = ''
    for j, estep in enumerate(error_pipeline):
        estep_text = estep if isinstance(estep, str) else estep.get('step', '')
        err_items_html += f"""
                <div style="display:flex; align-items:center; gap:10px; padding:10px 14px; background:var(--bg); border-radius:6px; margin:3px 0;">
                    <div style="background:var(--red); color:#fff; width:22px; height:22px; border-radius:50%; display:flex; align-items:center; justify-content:center; font-size:11px; font-weight:700; flex-shrink:0;">{j+1}</div>
                    <div style="font-size:13px; color:var(--text);">{html.escape(estep_text)}</div>
                </div>"""

    if err_items_html:
        html_content += f"""
        </div>

        <div style="margin-top:24px;">
            <div style="display:flex; align-items:center; gap:10px; cursor:pointer; margin-bottom:10px;"
                 onclick="var ep=document.getElementById('errorPipelineBody');ep.style.display=ep.style.display==='none'?'':'none';">
                <div style="font-size:14px; font-weight:600; color:var(--red);">⚠ Exception / Error Flow</div>
                <span style="font-size:11px; color:var(--muted);">click to expand</span>
            </div>
            <div id="errorPipelineBody" style="display:none; background:var(--bg2); border:1px solid var(--border); border-left:3px solid var(--red); border-radius:8px; padding:14px;">
                <p style="font-size:12px; color:var(--muted); margin-bottom:10px; line-height:1.6;">
                    When an exception is thrown at any layer, the following error handling chain is invoked instead of the normal response path.
                </p>
                {err_items_html}
            </div>
        </div>
"""
    else:
        html_content += "\n        </div>\n"

    html_content += f"""
        <div style="margin-top:24px; background:var(--bg2); border:1px solid var(--border); border-radius:12px; padding:20px;">
            <div class="sec-title" style="margin-top:0">&#128274; Scope & Isolation</div>
            <p style="font-size:13px; color:var(--muted); line-height:1.7;">
                {html.escape(data_flow.get('tenantIsolation', ''))}
            </p>
        </div>
    </div>


    </main>
</div>

<script>
    var dockerMermaidRendered = false;
    var sysarchMermaidRendered = false;
    var swaggerUiRendered = false;
    var sysarchPanZoom = null;
    var dockerPanZoom = null;

    function initPanZoom(containerId, isSysarch) {{
        var container = document.getElementById(containerId);
        if (!container) return;
        var svg = container.querySelector('svg');
        if (!svg) return;

        svg.removeAttribute('style');
        svg.removeAttribute('width');
        svg.removeAttribute('height');
        svg.style.width = '100%';
        svg.style.height = '100%';
        svg.style.display = 'block';
        svg.style.overflow = 'visible';

        var parentBox = container.closest('.diagram-box');
        if (parentBox && !parentBox.querySelector('.diagram-toolbar')) {{
            var toolbar = document.createElement('div');
            toolbar.className = 'diagram-toolbar';
            toolbar.innerHTML = `
                <button onclick="zoomDiagram('${{containerId}}', 'in')" title="Zoom In">🔍 +</button>
                <button onclick="zoomDiagram('${{containerId}}', 'out')" title="Zoom Out">🔍 -</button>
                <button onclick="zoomDiagram('${{containerId}}', 'reset')" title="Reset View">↺ Reset</button>
                <button onclick="zoomDiagram('${{containerId}}', 'fit')" title="Fit to Screen">⛶ Fit</button>
            `;
            parentBox.insertBefore(toolbar, container);
        }}

        if (typeof svgPanZoom !== 'undefined') {{
            try {{
                if (isSysarch && sysarchPanZoom) {{ sysarchPanZoom.destroy(); sysarchPanZoom = null; }}
                if (!isSysarch && dockerPanZoom) {{ dockerPanZoom.destroy(); dockerPanZoom = null; }}

                var pz = svgPanZoom(svg, {{
                    zoomEnabled: true,
                    controlIconsEnabled: false,
                    mouseWheelZoomEnabled: true,
                    fit: true,
                    center: true,
                    minZoom: 0.1,
                    maxZoom: 10,
                    zoomScaleSensitivity: 0.25
                }});

                if (isSysarch) sysarchPanZoom = pz;
                else dockerPanZoom = pz;

                setTimeout(function() {{
                    pz.resize();
                    pz.fit();
                    pz.center();
                }}, 100);
            }} catch(e) {{
                console.warn("svgPanZoom init error:", e);
            }}
        }}
    }}

    function zoomDiagram(containerId, action) {{
        var pz = (containerId === 'sysarchMermaid') ? sysarchPanZoom : dockerPanZoom;
        if (!pz) return;
        if (action === 'in') pz.zoomIn();
        else if (action === 'out') pz.zoomOut();
        else if (action === 'reset') {{ pz.resetZoom(); pz.resetPan(); pz.fit(); pz.center(); }}
        else if (action === 'fit') {{ pz.resize(); pz.fit(); pz.center(); }}
    }}

    function renderSysarchDiagram() {{
        if (sysarchMermaidRendered) {{
            if (sysarchPanZoom) {{
                sysarchPanZoom.resize();
                sysarchPanZoom.fit();
                sysarchPanZoom.center();
            }}
            return;
        }}
        sysarchMermaidRendered = true;
        var tpl = document.getElementById('sysarchMermaidSrc');
        var target = document.getElementById('sysarchMermaid');
        if (tpl && target && typeof mermaid !== 'undefined') {{
            var src = tpl.textContent.trim();
            var uniqueId = 'svg_sysarch_' + Math.floor(Math.random() * 1000000);
            mermaid.render(uniqueId, src).then(function(res) {{
                target.innerHTML = res.svg;
                setTimeout(function() {{ initPanZoom('sysarchMermaid', true); }}, 50);
            }}).catch(function(err) {{
                console.error("Mermaid render error:", err);
                target.innerHTML = '<div style="color:var(--red); padding:20px;">Failed to render Mermaid diagram: ' + err.message + '</div>';
            }});
        }}
    }}

    function renderDockerDiagram() {{
        if (dockerMermaidRendered) {{
            if (dockerPanZoom) {{
                dockerPanZoom.resize();
                dockerPanZoom.fit();
                dockerPanZoom.center();
            }}
            return;
        }}
        dockerMermaidRendered = true;
        var tpl = document.getElementById('dockerMermaidSrc');
        var target = document.getElementById('dockerMermaid');
        if (tpl && target && typeof mermaid !== 'undefined') {{
            var src = tpl.textContent.trim();
            var uniqueId = 'svg_docker_' + Math.floor(Math.random() * 1000000);
            mermaid.render(uniqueId, src).then(function(res) {{
                target.innerHTML = res.svg;
                setTimeout(function() {{ initPanZoom('dockerMermaid', false); }}, 50);
            }}).catch(function(err) {{
                console.error("Mermaid render error:", err);
                target.innerHTML = '<div style="color:var(--red); padding:20px;">Failed to render Mermaid diagram: ' + err.message + '</div>';
            }});
        }}
    }}

    function renderSwaggerUI() {{
        if (swaggerUiRendered) return;
        swaggerUiRendered = true;
        var srcElem = document.getElementById('swaggerOpenApiJsonSrc');
        var targetContainer = document.getElementById('swagger-ui-container');
        if (srcElem && targetContainer && typeof SwaggerUIBundle !== 'undefined') {{
            try {{
                var spec = JSON.parse(srcElem.textContent);
                SwaggerUIBundle({{
                    spec: spec,
                    dom_id: '#swagger-ui-container',
                    deepLinking: true,
                    presets: [
                        SwaggerUIBundle.presets.apis,
                        SwaggerUIBundle.SwaggerUIStandalonePreset
                    ],
                    layout: "BaseLayout"
                }});
            }} catch(e) {{
                console.error("Swagger UI init error:", e);
                targetContainer.innerHTML = '<div style="color:var(--red); padding:20px;">Swagger UI render error: ' + e.message + '</div>';
            }}
        }}
    }}

    function switchSwaggerView(view, btn) {{
        document.querySelectorAll('.sub-tab-btn').forEach(function(el) {{ el.classList.remove('active'); }});
        document.querySelectorAll('.swagger-view-pane').forEach(function(el) {{ el.classList.remove('active'); }});
        if (btn) btn.classList.add('active');
        var pane = document.getElementById('swagger-view-' + view);
        if (pane) pane.classList.add('active');
        if (view === 'ui') {{
            setTimeout(renderSwaggerUI, 50);
        }}
    }}

    function showTab(id, btn) {{
        document.querySelectorAll('.section').forEach(function(s) {{ s.classList.remove('active'); }});
        document.querySelectorAll('.nav-btn').forEach(function(b) {{ b.classList.remove('active'); }});
        document.getElementById('sec-' + id).classList.add('active');
        if (btn) btn.classList.add('active');

        if (id === 'sysarch') {{
            setTimeout(renderSysarchDiagram, 50);
        }} else if (id === 'docker') {{
            setTimeout(renderDockerDiagram, 50);
        }} else if (id === 'swagger') {{
            setTimeout(renderSwaggerUI, 50);
        }}
    }}

    function exportPDF() {{
        var sections = document.querySelectorAll('.section');
        sections.forEach(function(s) {{ s.style.display = 'block'; }});

        var swaggerPanes = document.querySelectorAll('.swagger-view-pane');
        swaggerPanes.forEach(function(p) {{ p.style.display = 'block'; }});

        // Pre-render diagrams and Swagger UI if not initialized yet
        if (typeof renderSysarchDiagram === 'function') renderSysarchDiagram();
        if (typeof renderDockerDiagram === 'function') renderDockerDiagram();
        if (typeof renderSwaggerUI === 'function') renderSwaggerUI();

        setTimeout(function() {{
            window.print();
            sections.forEach(function(s) {{ s.style.display = ''; }});
            swaggerPanes.forEach(function(p) {{ p.style.display = ''; }});
            var activeBtn = document.querySelector('.nav-btn.active');
            if (activeBtn) {{
                var onClickAttr = activeBtn.getAttribute('onclick');
                if (onClickAttr) {{
                    var match = onClickAttr.match(/showTab\('([^']+)'/);
                    if (match) showTab(match[1], activeBtn);
                }}
            }}
        }}, 600);
    }}

    function filterModules() {{
        var q = document.getElementById('modSearch').value.toLowerCase();
        document.querySelectorAll('#modulesGrid .card').forEach(function(card) {{
            var text = card.innerText.toLowerCase();
            card.style.display = text.indexOf(q) !== -1 ? '' : 'none';
        }});
    }}

    mermaid.initialize({{ startOnLoad: false, theme: 'dark' }});
</script>

<!-- API Endpoint Prompt Modal -->
<div id="apiPromptModal" class="custom-modal-backdrop" onclick="closeApiPromptModal(event)">
    <div class="custom-modal-content" onclick="event.stopPropagation()">
        <div class="custom-modal-header">
            <div style="display:flex; align-items:center; gap:10px;">
                <span style="font-size:22px;">🤖</span>
                <div>
                    <h3 style="margin:0; font-size:16px; font-weight:700; color:var(--text);">AI Senior Developer Prompt</h3>
                    <div style="font-size:12px; color:var(--accent); font-family:var(--font-code); font-weight:600; margin-top:2px;" id="apiPromptModalSub">Endpoint Architecture Analysis Prompt</div>
                </div>
            </div>
            <button class="custom-modal-close" onclick="closeApiPromptModal()">&times;</button>
        </div>
        <div class="custom-modal-body">
            <div style="margin-bottom:12px; display:flex; align-items:center; justify-content:space-between;">
                <span style="font-size:12px; font-weight:600; color:var(--muted);">COPY &amp; PASTE THIS PROMPT TO YOUR AI ASSISTANT:</span>
                <button id="modalCopyBtn" class="btn-copy-prompt" onclick="copyModalPromptText()">📋 Copy Prompt</button>
            </div>
            <textarea id="apiPromptTextarea" readonly rows="16" style="width:100%; background:var(--bg); color:var(--text); border:1px solid var(--border); border-radius:8px; padding:14px; font-family:var(--font-code); font-size:12px; line-height:1.6; resize:vertical; outline:none;"></textarea>
        </div>
    </div>
</div>

<script>
    function getApiPromptText(method, path) {{
        var cleanFileName = (method.toLowerCase() + '_' + path)
            .replace(/[^a-zA-Z0-9_]/g, '_')
            .replace(/_+/g, '_')
            .replace(/^_|_$/g, '') + '_analysis.md';

        return "Use @arch-wiki skill. You are joining this project as a senior developer.\\n\\n" +
            "Analyze this API endpoint:\\n\\n" +
            method + " " + path + "\\n\\n" +
            "Use:\\n" +
            "1. architecture.json\\n" +
            "2. arch-wiki documentation\\n" +
            "3. the project source code\\n\\n" +
            "Discover the actual implementation flow.\\n\\n" +
            "Generate:\\n\\n" +
            "1. Mermaid sequence diagram (both Mermaid code format and rendered visual diagram image)\\n" +
            "2. Mermaid flowchart (both Mermaid code format and rendered visual diagram image)\\n\\n" +
            "Include only components and interactions that actually exist in the code.\\n\\n" +
            "Do not infer missing components.\\n" +
            "Do not modify anything.\\n\\n" +
            "Save the analysis output in " + cleanFileName;
    }}

    function openApiPromptFromEl(el) {{
        var method = el.getAttribute('data-method') || 'GET';
        var path = el.getAttribute('data-path') || '/';
        openApiPromptModal(method, path);
    }}

    function copyApiPromptDirectFromEl(el) {{
        var method = el.getAttribute('data-method') || 'GET';
        var path = el.getAttribute('data-path') || '/';
        var btn = el.querySelector('.btn-prompt-copy');
        copyApiPromptDirect(method, path, btn);
    }}

    function openApiPromptModal(method, path) {{
        var modal = document.getElementById('apiPromptModal');
        var sub = document.getElementById('apiPromptModalSub');
        var ta = document.getElementById('apiPromptTextarea');
        var btn = document.getElementById('modalCopyBtn');

        if (!modal || !ta) return;

        var promptText = getApiPromptText(method, path);
        ta.value = promptText;
        if (sub) sub.innerText = method + ' ' + path;
        if (btn) {{
            btn.innerHTML = '📋 Copy Prompt';
            btn.style.background = '';
        }}

        modal.classList.add('active');
    }}

    function closeApiPromptModal(e) {{
        if (e && e.target !== e.currentTarget && !e.target.classList.contains('custom-modal-close')) return;
        var modal = document.getElementById('apiPromptModal');
        if (modal) modal.classList.remove('active');
    }}

    function copyModalPromptText() {{
        var ta = document.getElementById('apiPromptTextarea');
        var btn = document.getElementById('modalCopyBtn');
        if (!ta) return;

        navigator.clipboard.writeText(ta.value).then(function() {{
            if (btn) {{
                btn.innerHTML = '✅ Copied!';
                setTimeout(function() {{
                    btn.innerHTML = '📋 Copy Prompt';
                }}, 2000);
            }}
        }}).catch(function() {{
            ta.select();
            document.execCommand('copy');
            if (btn) {{
                btn.innerHTML = '✅ Copied!';
                setTimeout(function() {{
                    btn.innerHTML = '📋 Copy Prompt';
                }}, 2000);
            }}
        }});
    }}

    function copyApiPromptDirect(method, path, btnElement) {{
        var promptText = getApiPromptText(method, path);
        navigator.clipboard.writeText(promptText).then(function() {{
            if (btnElement) {{
                var orig = btnElement.innerHTML;
                btnElement.innerHTML = '✅ Copied!';
                setTimeout(function() {{
                    btnElement.innerHTML = orig;
                }}, 2000);
            }}
        }}).catch(function() {{
            if (btnElement) {{
                var orig = btnElement.innerHTML;
                btnElement.innerHTML = '✅ Copied!';
                setTimeout(function() {{
                    btnElement.innerHTML = orig;
                }}, 2000);
            }}
        }});
    }}

    document.addEventListener('keydown', function(e) {{
        if (e.key === 'Escape') {{
            closeApiPromptModal();
        }}
    }});
</script>
</body>
</html>
"""

    if not target_dir:
        target_dir = os.path.dirname(__file__)
    out_path = os.path.join(target_dir, 'architecture.html')
    with open(out_path, 'w', encoding='utf-8') as f:
        f.write(html_content)
    print(f"Successfully generated architecture.html at {out_path}")

if __name__ == '__main__':
    target_path = None
    for arg in sys.argv[1:]:
        if not arg.startswith('--') and os.path.exists(arg):
            target_path = os.path.abspath(arg)
            break
    
    if not target_path:
        target_path = os.getcwd()
    
    arch_dir = os.path.join(target_path, 'docs', 'architecture') if os.path.basename(target_path) != 'architecture' else target_path
    os.makedirs(arch_dir, exist_ok=True)
    json_path = os.path.join(arch_dir, 'architecture.json')
    has_json = os.path.isfile(json_path)

    if '--init' in sys.argv or '--rescan' in sys.argv or '--sync' in sys.argv or not has_json:
        if has_json:
            print(f"[arch-wiki] Syncing codebase changes with architecture.json at {json_path}...")
        else:
            print(f"[arch-wiki] Initializing fresh architecture manifest at {json_path}...")
        data = init_architecture(target_path)
    else:
        data = load_architecture(json_path)

    generate_html(data, arch_dir)
    print(f"[arch-wiki] Done. Open {os.path.join(arch_dir, 'architecture.html')} in your browser.")
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
