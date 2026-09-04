import importlib.util
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "templates" / "build_html.py"
spec = importlib.util.spec_from_file_location("build_html", SCRIPT)
build_html = importlib.util.module_from_spec(spec)
spec.loader.exec_module(build_html)

SAMPLE_DIR = str(ROOT / "tests" / "fixtures" / "embedded-sample")

def test_embedded_manifest_contains_requested_sections():
    data = build_html.init_architecture(SAMPLE_DIR)
    expected_sections = {
        "meta", "readme", "readmes", "brief", "hardware", "configurations", "memoryLayout",
        "modules", "components", "dataTypes", "objects", "diagrams", "dataPipelines", "build",
        "functions", "macros", "callGraph", "fileIndex", "symbolIndex", "dependencies", "tools"
    }
    assert expected_sections.issubset(set(data))
    assert data["readme"]["exists"] is True
    assert data["build"]["system"]["type"] == "PlatformIO"

def test_only_project_defined_types_are_documented():
    data = build_html.init_architecture(SAMPLE_DIR)
    names = {item["name"] for item in data["dataTypes"]}
    assert "SensorReading" in names
    assert "SensorState" in names
    assert "uint16_t" not in names
    assert all(item["userDefined"] and item["ownership"] == "project" for item in data["dataTypes"])

def test_static_object_has_lifetime_and_ownership():
    data = build_html.init_architecture(SAMPLE_DIR)
    obj = next(item for item in data["objects"] if item["name"] == "current_reading")
    assert obj["lifetime"]["scope"] == "firmware"
    assert obj["ownership"]["model"] == "static"
    assert obj["files"][0]["path"] == "src/sensor.c"

def test_html_contains_readme_and_embedded_navigation():
    data = build_html.init_architecture(SAMPLE_DIR)
    output = build_html.render(data)
    assert "Firmware for a sensor node." in output
    for label in (
        "Project README", "Hardware", "Configurations", "Memory Layout",
        "Modules &amp; Components", "Dependencies", "Files", "Functions",
        "Macros", "Call Graph", "Tools &amp; Scripts", "Data Pipelines",
        "Build", "Symbol Index"
    ):
        assert label in output
    assert "Swagger &amp; OpenAPI" not in output

def test_functions_extracted():
    data = build_html.init_architecture(SAMPLE_DIR)
    func_names = {f["name"] for f in data["functions"]}
    assert "sensor_init" in func_names
    assert "sensor_read" in func_names
    assert "main" in func_names
    sensor_init = next(f for f in data["functions"] if f["name"] == "sensor_init")
    assert "sensor_init" in sensor_init["signature"]
    assert sensor_init["file"] == "src/sensor.c"

def test_call_graph_built():
    data = build_html.init_architecture(SAMPLE_DIR)
    edges = data["callGraph"]["edges"]
    edge_pairs = {(e["caller"], e["callee"]) for e in edges}
    assert ("main", "sensor_init") in edge_pairs
    assert ("main", "sensor_process") in edge_pairs
    assert ("bsp_init", "system_clock_config") in edge_pairs
    assert "flowchart LR" in data["callGraph"]["mermaid"]

def test_macros_extracted():
    data = build_html.init_architecture(SAMPLE_DIR)
    macro_names = {m["name"] for m in data["macros"]}
    assert "SYS_CLOCK_HZ" in macro_names
    assert "SENSOR_MAX_CHANNELS" in macro_names
    assert "SENSOR_CALIBRATION_OFFSET" in macro_names

def test_file_index_built():
    data = build_html.init_architecture(SAMPLE_DIR)
    files = {f["path"]: f for f in data["fileIndex"]}
    assert "src/sensor.c" in files
    assert "src/main.c" in files
    assert "src/sensor.h" in files
    assert "sensor_init" in files["src/sensor.c"]["functions"]
    assert "SensorReading" in files["src/sensor.h"]["types"]

def test_symbol_index_complete():
    data = build_html.init_architecture(SAMPLE_DIR)
    sym_kinds = {s["kind"] for s in data["symbolIndex"]}
    assert "function" in sym_kinds
    assert "macro" in sym_kinds
    assert "struct" in sym_kinds
    sym_names = {s["name"] for s in data["symbolIndex"]}
    assert "sensor_init" in sym_names
    assert "SensorReading" in sym_names

def test_state_machine_from_source():
    data = build_html.init_architecture(SAMPLE_DIR)
    sms = data["diagrams"]["stateMachines"]
    sensor_sm = next((sm for sm in sms if "SensorState" in sm["title"]), None)
    assert sensor_sm is not None
    assert "SENSOR_STATE_IDLE" in sensor_sm["states"]
    assert "stateDiagram-v2" in sensor_sm["mermaid"]
    trans_pairs = {(t["from"], t["to"]) for t in sensor_sm["transitions"]}
    assert ("SENSOR_STATE_IDLE", "SENSOR_STATE_SAMPLING") in trans_pairs

def test_cross_component_dependencies():
    data = build_html.init_architecture(SAMPLE_DIR)
    edges = data["dependencies"]["edges"]
    dep_pairs = {(e["from"], e["to"]) for e in edges}
    assert ("main", "sensor") in dep_pairs
    assert "flowchart TD" in data["dependencies"]["mermaid"]

def test_config_params_categorized():
    data = build_html.init_architecture(SAMPLE_DIR)
    cats = data["configurations"]["parametersByCategory"]
    assert "clock" in cats
    assert "feature" in cats
    assert any(p["name"] == "SYS_CLOCK_HZ" for p in cats["clock"])
    assert any(p["name"] == "ENABLE_SENSOR" for p in cats["feature"])

def test_makefile_role_detected():
    data = build_html.init_architecture(SAMPLE_DIR)
    makefiles = data["build"]["makefiles"]
    assert len(makefiles) > 0
    mf = makefiles[0]
    assert mf["path"] == "Makefile"
    assert mf["role"] in {"utility", "wrapper"}
    target_names = {t["name"] for t in mf["targets"]}
    assert "flash" in target_names
    assert "clean" in target_names

def test_utility_tools_detected():
    data = build_html.init_architecture(SAMPLE_DIR)
    tool_paths = {t["path"] for t in data["tools"]}
    assert "scripts/flash.sh" in tool_paths
    flash_tool = next(t for t in data["tools"] if t["path"] == "scripts/flash.sh")
    assert flash_tool["category"] == "flash"

def test_multi_readme_discovery():
    data = build_html.init_architecture(SAMPLE_DIR)
    readme_paths = [r["path"] for r in data["readmes"]]
    assert "README.md" in readme_paths
    assert "docs/README.md" in readme_paths
    assert data["readme"]["exists"] is True

def test_interactive_ai_prompts_in_html():
    data = build_html.init_architecture(SAMPLE_DIR)
    html_output = build_html.render(data)
    assert "AI Senior Embedded Developer Prompt" in html_output
    assert "copyFuncPromptDirect" in html_output
    assert "promptModal" in html_output
    assert "data-sig=" in html_output

def test_cli_sync_execution(monkeypatch):
    import sys
    test_args = ["build_html.py", "--sync", SAMPLE_DIR]
    monkeypatch.setattr(sys, "argv", test_args)
    build_html.main()
    arch_json = Path(SAMPLE_DIR) / "docs" / "architecture" / "architecture.json"
    arch_html = Path(SAMPLE_DIR) / "docs" / "architecture" / "architecture.html"
    assert arch_json.exists()
    assert arch_html.exists()
    # clean up
    import shutil
    shutil.rmtree(Path(SAMPLE_DIR) / "docs" / "architecture", ignore_errors=True)

def test_gitignore_respected(tmp_path):
    # Setup a mock project with a .gitignore
    (tmp_path / ".gitignore").write_text("build/\n*.ignored.c\nsecrets.h\n", encoding="utf-8")
    
    src = tmp_path / "src"
    src.mkdir()
    (src / "main.c").write_text("int main(void) { return 0; }", encoding="utf-8")
    (src / "sensor.c").write_text("void sensor_init(void) {}", encoding="utf-8")
    (src / "test.ignored.c").write_text("void ignored_fn(void) {}", encoding="utf-8")
    (src / "secrets.h").write_text("#define SECRET_KEY 12345", encoding="utf-8")
    
    build_dir = tmp_path / "build"
    build_dir.mkdir()
    (build_dir / "generated.c").write_text("void gen_fn(void) {}", encoding="utf-8")
    
    scanned_files = [p.name for p in build_html.files(tmp_path)]
    assert "main.c" in scanned_files
    assert "sensor.c" in scanned_files
    assert "test.ignored.c" not in scanned_files
    assert "secrets.h" not in scanned_files
    assert "generated.c" not in scanned_files

def test_ai_agent_ignore_files_respected(tmp_path):
    # Setup .cursorignore, .claudeignore, .geminiignore, .agentignore
    (tmp_path / ".cursorignore").write_text("cursor_dir/\n*.cursor.c\n", encoding="utf-8")
    (tmp_path / ".claudeignore").write_text("claude_secret.h\n", encoding="utf-8")
    (tmp_path / ".geminiignore").write_text("gemini_temp/\n", encoding="utf-8")
    (tmp_path / ".agentignore").write_text("agent_mock.c\n", encoding="utf-8")

    src = tmp_path / "src"
    src.mkdir()
    (src / "app.c").write_text("void app(void) {}", encoding="utf-8")
    (src / "test.cursor.c").write_text("void c_fn(void) {}", encoding="utf-8")
    (src / "claude_secret.h").write_text("#define CLAUDE_SECRET 1", encoding="utf-8")
    (src / "agent_mock.c").write_text("void mock(void) {}", encoding="utf-8")

    cursor_dir = tmp_path / "cursor_dir"
    cursor_dir.mkdir()
    (cursor_dir / "c1.c").write_text("void c1(void) {}", encoding="utf-8")

    gemini_dir = tmp_path / "gemini_temp"
    gemini_dir.mkdir()
    (gemini_dir / "g1.c").write_text("void g1(void) {}", encoding="utf-8")

    scanned_files = [p.name for p in build_html.files(tmp_path)]
    assert "app.c" in scanned_files
    assert "test.cursor.c" not in scanned_files
    assert "claude_secret.h" not in scanned_files
    assert "agent_mock.c" not in scanned_files
    assert "c1.c" not in scanned_files
    assert "g1.c" not in scanned_files



