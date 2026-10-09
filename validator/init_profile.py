"""Detect independent source-backed stack families without executing manifests."""

from __future__ import annotations

import hashlib
import json
import shlex
import tomllib
from dataclasses import dataclass
from pathlib import Path
from typing import cast

UNKNOWN = "Unknown"
MANAGERS = frozenset({"bun", "npm", "pnpm", "yarn"})
LOCKFILES = {
    "bun.lock": "bun",
    "bun.lockb": "bun",
    "package-lock.json": "npm",
    "npm-shrinkwrap.json": "npm",
    "pnpm-lock.yaml": "pnpm",
    "yarn.lock": "yarn",
}


class InitError(Exception):
    """Reject unsupported evidence, unsafe paths or unsuccessful initialization."""


@dataclass(frozen=True)
class Fact:
    """Observed stack value with manifest provenance."""

    name: str
    version: str
    evidence: str


@dataclass(frozen=True)
class Source:
    """Content identity of an input used to detect a profile."""

    path: str
    sha256: str


@dataclass(frozen=True)
class ObservedProfile:
    """Immutable facts, names and required tools observed in a selected root."""

    product_name: str
    technical_names: tuple[str, ...]
    package_manager: str
    facts: tuple[Fact, ...]
    sources: tuple[Source, ...]
    tools: tuple[str, ...]
    testing_tools: tuple[str, ...]
    test_commands: tuple[str, ...]


def _read_mapping(root: Path, relative: str) -> dict[str, object]:
    path = root / relative
    if not path.exists():
        return {}
    if not path.resolve().is_relative_to(root):
        raise InitError(f"{relative}: manifest escapes selected project")
    try:
        raw = path.read_text(encoding="utf-8")
        value: object = json.loads(raw) if relative.endswith(".json") else tomllib.loads(raw)
    except (ValueError, OSError) as error:
        raise InitError(f"{relative}: malformed manifest: {error}") from error
    if not isinstance(value, dict) or not all(isinstance(key, str) for key in value):
        raise InitError(f"{relative}: expected manifest object")
    return cast(dict[str, object], value)


def _mapping(value: object, context: str) -> dict[str, object]:
    if not isinstance(value, dict) or not all(isinstance(key, str) for key in value):
        raise InitError(f"{context}: expected object")
    return cast(dict[str, object], value)


def _string(value: object, context: str) -> str:
    if not isinstance(value, str) or not value.strip():
        raise InitError(f"{context}: expected nonempty string")
    return value


def _manager(package: dict[str, object], config: dict[str, object], root: Path) -> str:
    evidence: list[tuple[str, str]] = []
    if "packageManager" in package:
        declared = _string(package["packageManager"], "package.json packageManager").split("@", 1)[
            0
        ]
        if declared not in MANAGERS:
            raise InitError(f"package.json: unsupported packageManager {declared}")
        evidence.append((declared, "package.json"))
    build = _mapping(config.get("build", {}), "tauri.conf.json build")
    for key in ("beforeDevCommand", "beforeBuildCommand"):
        command = build.get(key)
        if isinstance(command, dict):
            command = _mapping(command, key).get("script")
        if command is not None:
            try:
                tokens = shlex.split(_string(command, f"tauri.conf.json {key}"))
            except ValueError as error:
                raise InitError(f"tauri.conf.json {key}: {error}") from error
            # Recognize command words without executing untrusted manifest scripts.
            evidence.extend(
                (token, f"tauri.conf.json {key}") for token in tokens if token in MANAGERS
            )
    evidence.extend(
        (manager, lock) for lock, manager in LOCKFILES.items() if (root / lock).exists()
    )
    if len({manager for manager, _ in evidence}) > 1:
        raise InitError(f"package manager conflict: {evidence}")
    return evidence[0][0] if evidence else UNKNOWN


def _package_facts(
    package: dict[str, object], root: Path
) -> tuple[list[Fact], list[str], list[str]]:
    dependencies = _mapping(
        package.get("dependencies", {}), "package.json dependencies"
    ) | _mapping(package.get("devDependencies", {}), "package.json devDependencies")
    facts = [Fact("JavaScript", UNKNOWN, "package.json")] if package else []
    markers = {"react": "React", "vite": "Vite", "typescript": "TypeScript"}
    for key, name in markers.items():
        if key in dependencies:
            facts.append(
                Fact(name, _string(dependencies[key], f"package.json {key}"), "package.json")
            )
    if (root / "tsconfig.json").exists() and "typescript" not in dependencies:
        _read_mapping(root, "tsconfig.json")
        facts.append(Fact("TypeScript", UNKNOWN, "tsconfig.json"))
    tests = sorted(
        key for key in ("vitest", "@playwright/test", "playwright", "jest") if key in dependencies
    )
    scripts = _mapping(package.get("scripts", {}), "package.json scripts")
    # Declared scripts are documentation only; initialization never runs package scripts.
    commands = [
        _string(value, f"package.json script {key}")
        for key, value in scripts.items()
        if key.startswith("test")
    ]
    return facts, tests, list(dict.fromkeys(commands))


def _cargo_facts(root: Path, relative: str) -> tuple[list[Fact], str | None]:
    cargo = _read_mapping(root, relative)
    if not cargo:
        return [], None
    package = _mapping(cargo.get("package", {}), f"{relative} package")
    name = _string(package["name"], f"{relative} name") if "name" in package else None
    facts = [Fact("Rust", UNKNOWN, relative)]
    dependency = _mapping(cargo.get("dependencies", {}), f"{relative} dependencies").get("tauri")
    if dependency is not None:
        version = (
            _mapping(dependency, f"{relative} tauri").get("version", UNKNOWN)
            if isinstance(dependency, dict)
            else dependency
        )
        facts.append(Fact("Tauri", _string(version, f"{relative} tauri version"), relative))
    return facts, name


# @spec FR-001: Independent manifest facts
#   — .specs/features/080-autonomous-from-code-recovery/spec.md#fr-001
def detect_profile(project: Path) -> ObservedProfile:
    """Read supported manifests and return facts without modifying the project.

    Args:
        project: Existing selected project directory.
    Returns:
        Independent stack evidence and required version-probe tool names.
    Raises:
        InitError: Manifests are malformed, unsupported or contradictory.
    """
    root = project.resolve()
    if not root.is_dir():
        raise InitError(f"{project}: project directory not found")
    for unsupported in ("src-tauri/tauri.conf.json5", "src-tauri/Tauri.toml"):
        if (root / unsupported).exists():
            raise InitError(f"{unsupported}: unsupported manifest format; provide tauri.conf.json")
    package = _read_mapping(root, "package.json")
    config = _read_mapping(root, "src-tauri/tauri.conf.json")
    python = _read_mapping(root, "pyproject.toml")
    facts, tests, commands = _package_facts(package, root)
    names: list[str] = [_string(package["name"], "package.json name")] if "name" in package else []
    for relative in ("Cargo.toml", "src-tauri/Cargo.toml"):
        cargo_facts, name = _cargo_facts(root, relative)
        facts.extend(cargo_facts)
        if name:
            names.append(name)
    if config and not any(fact.name == "Tauri" for fact in facts):
        raise InitError("src-tauri/tauri.conf.json: Tauri dependency missing from Cargo.toml")
    if python:
        facts.append(Fact("Python", UNKNOWN, "pyproject.toml"))
        details = _mapping(python.get("project", {}), "pyproject.toml project")
        if "name" in details:
            names.append(_string(details["name"], "pyproject.toml name"))
        tools = _mapping(python.get("tool", {}), "pyproject.toml tool")
        if "pytest" in tools:
            tests.append("pytest")
            commands.append("pytest")
    if not facts:
        raise InitError("No supported package.json, pyproject.toml or Cargo.toml manifest found")
    manager = _manager(package, config, root) if package else UNKNOWN
    required = [manager] if manager != UNKNOWN else []
    if any(fact.name == "Rust" for fact in facts):
        required.append("cargo")
    if python:
        required.append("python3")
    paths = (
        "package.json",
        "tsconfig.json",
        "pyproject.toml",
        "Cargo.toml",
        "Cargo.lock",
        "src-tauri/Cargo.toml",
        "src-tauri/Cargo.lock",
        "src-tauri/tauri.conf.json",
        *LOCKFILES,
    )
    for path in paths:
        if (root / path).exists() and not (root / path).resolve().is_relative_to(root):
            raise InitError(f"{path}: manifest/lock evidence escapes selected project")
    sources = tuple(
        Source(path, hashlib.sha256((root / path).read_bytes()).hexdigest())
        for path in paths
        if (root / path).is_file()
    )
    product = (
        _string(config["productName"], "tauri.conf.json productName")
        if "productName" in config
        else names[0]
        if names
        else UNKNOWN
    )
    return ObservedProfile(
        product,
        tuple(dict.fromkeys(names)),
        manager,
        tuple(dict.fromkeys(facts)),
        sources,
        tuple(required),
        tuple(dict.fromkeys(tests)),
        tuple(dict.fromkeys(commands)),
    )
