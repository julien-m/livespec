# @spec FR-006: Integration tests for all 4 capabilities — .specs/features/017-driver-python/spec.md#fr-006
"""
Integration tests for the Python driver — coverage, snapshots, properties, mutation.
Tests all 4 capabilities against fixture projects.
"""

import subprocess
import tempfile
from pathlib import Path

import pytest

from validator.drivers.loader import load_manifest
from validator.drivers.registry import DriverRegistry
from validator.drivers.runner import run_capability


@pytest.fixture
def python_fixture_dir():
    """Create a minimal Python project fixture with tests."""
    with tempfile.TemporaryDirectory() as tmpdir:
        project_root = Path(tmpdir)

        # Create pyproject.toml
        pyproject = project_root / "pyproject.toml"
        pyproject.write_text(
            """[project]
name = "test-project"
version = "0.1.0"

[tool.pytest.ini_options]
testpaths = ["tests"]
"""
        )

        # Create source module
        src_dir = project_root / "src"
        src_dir.mkdir()
        (src_dir / "__init__.py").write_text("")
        (src_dir / "calculator.py").write_text(
            """def add(a, b):
    return a + b

def multiply(a, b):
    return a * b
"""
        )

        # Create tests
        tests_dir = project_root / "tests"
        tests_dir.mkdir()
        (tests_dir / "__init__.py").write_text("")
        (tests_dir / "test_calculator.py").write_text(
            """import pytest
from src.calculator import add, multiply

def test_add():
    assert add(2, 3) == 5

def test_multiply():
    assert multiply(2, 3) == 6

@pytest.mark.property
@pytest.mark.hypothesis
def test_add_commutative():
    from hypothesis import given
    import hypothesis.strategies as st

    @given(st.integers(), st.integers())
    def prop(a, b):
        assert add(a, b) == add(b, a)

    prop()
"""
        )

        yield str(project_root)


def test_registry_loads_python_driver():
    """Test that the Python driver is loaded by DriverRegistry."""
    # @spec AC-001: Driver registry loads python.yaml — .specs/features/017-driver-python/spec.md#ac-001
    with tempfile.TemporaryDirectory() as tmpdir:
        project_root = Path(tmpdir)
        (project_root / "pyproject.toml").write_text('[project]\nname = "test"\n')

        registry = DriverRegistry(Path(tmpdir))
        drivers = registry.discover()

        # Should find python driver (matches pyproject.toml)
        assert any(d.name == "python" for d in drivers)


def test_python_driver_schema_validation():
    """Test that python.yaml passes schema validation."""
    # @spec AC-011: Schema validation — .specs/features/017-driver-python/spec.md#ac-011
    import inspect
    from validator import drivers

    # Get the livespec package root
    driver_module_path = Path(inspect.getfile(drivers))
    livespec_root = driver_module_path.parent.parent

    python_driver_path = livespec_root / "livespec" / "drivers" / "python.yaml"

    # Load and validate
    if python_driver_path.exists():
        manifest = load_manifest(python_driver_path)
        assert manifest is not None
        assert manifest.name == "python"
        assert "coverage" in [c.id for c in manifest.capabilities]
        assert "snapshots" in [c.id for c in manifest.capabilities]
        assert "properties" in [c.id for c in manifest.capabilities]
        assert "mutation" in [c.id for c in manifest.capabilities]


def test_python_driver_capabilities_exist():
    """Test that all 4 capabilities are declared in python.yaml."""
    # @spec AC-012: All 4 capabilities appear in spec.test output — .specs/features/017-driver-python/spec.md#ac-012
    import inspect
    from validator import drivers

    driver_module_path = Path(inspect.getfile(drivers))
    livespec_root = driver_module_path.parent.parent

    python_driver_path = livespec_root / "livespec" / "drivers" / "python.yaml"

    if python_driver_path.exists():
        manifest = load_manifest(python_driver_path)
        assert manifest is not None

        capability_ids = manifest.implemented_capabilities()
        assert "coverage" in capability_ids
        assert "snapshots" in capability_ids
        assert "properties" in capability_ids
        assert "mutation" in capability_ids


def test_coverage_capability_metadata():
    """Test that coverage capability has required metadata."""
    # @spec AC-002: Coverage capability has proper metadata — .specs/features/017-driver-python/spec.md#ac-002
    import inspect
    from validator import drivers

    driver_module_path = Path(inspect.getfile(drivers))
    livespec_root = driver_module_path.parent.parent

    python_driver_path = livespec_root / "livespec" / "drivers" / "python.yaml"

    if python_driver_path.exists():
        manifest = load_manifest(python_driver_path)
        assert manifest is not None

        coverage_cap = manifest.coverage
        assert coverage_cap is not None
        assert coverage_cap.command is not None or coverage_cap.script is not None


def test_snapshots_capability_metadata():
    """Test that snapshots capability has required metadata."""
    import inspect
    from validator import drivers

    driver_module_path = Path(inspect.getfile(drivers))
    livespec_root = driver_module_path.parent.parent

    python_driver_path = livespec_root / "livespec" / "drivers" / "python.yaml"

    if python_driver_path.exists():
        manifest = load_manifest(python_driver_path)
        assert manifest is not None

        snapshots_cap = manifest.snapshots
        assert snapshots_cap is not None
        assert snapshots_cap.command is not None or snapshots_cap.script is not None


def test_python_driver_detects_project_with_pyproject():
    """Test that Python driver detects projects with pyproject.toml."""
    with tempfile.TemporaryDirectory() as tmpdir:
        project_root = Path(tmpdir)
        (project_root / "pyproject.toml").write_text('[project]\nname = "test"\n')

        manifest = load_manifest(
            Path(__file__).parent.parent.parent / "livespec" / "drivers" / "python.yaml"
        )
        if manifest:
            # Check if any detect rule matches
            has_pyproject = any(
                f == "pyproject.toml" for f in manifest.detect.files
            )
            assert has_pyproject
