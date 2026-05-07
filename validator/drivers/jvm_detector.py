"""Detect JVM (Java + Kotlin) build dependencies and parse pitest XML output."""

# @spec FR-002: Build tool detection (Gradle priority over Maven).
# — .specs/features/022-driver-jvm/spec.md#fr-002
# @spec FR-003: build.gradle / pom.xml parser for plugin and dependency presence.
# — .specs/features/022-driver-jvm/spec.md#fr-003
# @spec FR-004: pitest XML parser exposing KILLED/SURVIVED/TIMED_OUT counts.
# — .specs/features/022-driver-jvm/spec.md#fr-004
# @spec AC-010: Build file detection by file presence; Gradle priority.
# @spec AC-011: Single driver covers Kotlin-first and Java-first projects.

from __future__ import annotations

import re
from pathlib import Path

# Tables / files we consult.
_GRADLE_FILES: tuple[str, ...] = ("build.gradle", "build.gradle.kts")
_MAVEN_FILE: str = "pom.xml"

# pitest emits these status strings inside <mutation status="..."> elements.
# We normalise to lowercase keys; pitest uses uppercase in practice.
_PITEST_STATUSES: tuple[str, ...] = (
    "killed",
    "survived",
    "timed_out",
    "no_coverage",
    "memory_error",
    "run_error",
)

# Recognise common dependency / plugin tokens. Gradle DSL is not parseable as a
# stable grammar, so we match identifier-like tokens (alphanumeric, dot, dash,
# underscore) using a permissive regex.
_TOKEN_RE = re.compile(r"[A-Za-z][A-Za-z0-9._-]*")
# Strip line comments (`//` or `--`) and block comments (`/* ... */`) before
# tokenising — this keeps commented-out plugin lines from polluting detection.
_BLOCK_COMMENT_RE = re.compile(r"/\*.*?\*/", re.DOTALL)
_LINE_COMMENT_RE = re.compile(r"//[^\n]*")

# XML extraction regexes. We avoid xml.etree.ElementTree because some Python
# distributions ship a broken pyexpat (the stdlib XML backend) and the
# information we need from POMs / pitest reports is shallow enough that a
# pair of well-anchored regexes is sufficient and dependency-free.
_ARTIFACT_ID_RE = re.compile(
    r"<\s*artifactId\s*>\s*([^<\s][^<]*?)\s*<\s*/\s*artifactId\s*>",
    re.IGNORECASE,
)
_MUTATION_STATUS_RE = re.compile(
    r"<mutation\b[^>]*\bstatus\s*=\s*[\"']([^\"']+)[\"']",
    re.IGNORECASE,
)
# Sniff for tags that look like XML at all so we can short-circuit malformed
# input back to "no data" rather than emit accidental matches.
_XML_TAG_RE = re.compile(r"<\s*[A-Za-z]")


def _strip_gradle_comments(text: str) -> str:
    """Remove block and line comments from a Gradle DSL source string."""
    without_block = _BLOCK_COMMENT_RE.sub(" ", text)
    return _LINE_COMMENT_RE.sub(" ", without_block)


def _read_text(path: Path) -> str:
    """Read a UTF-8 text file defensively, returning ``""`` on any failure."""
    try:
        return path.read_text(encoding="utf-8")
    except (OSError, UnicodeDecodeError):
        # Treat unreadable build files as "feature not detected" so discovery
        # degrades safely instead of crashing on filesystem or encoding issues.
        return ""


def detect_build_tool(project_root: str) -> str | None:
    """Detect which JVM build tool the project uses.

    Args:
        project_root: Path to the project root.

    Returns:
        ``"gradle"`` when ``build.gradle`` or ``build.gradle.kts`` is present
        (taking priority over Maven when both are found, per AC-010);
        ``"maven"`` when only ``pom.xml`` is present; ``None`` otherwise.
    """
    root = Path(project_root)
    has_gradle = any((root / fname).is_file() for fname in _GRADLE_FILES)
    if has_gradle:
        return "gradle"
    if (root / _MAVEN_FILE).is_file():
        return "maven"
    return None


def parse_gradle_build(project_root: str) -> list[str]:
    """Parse ``build.gradle`` / ``build.gradle.kts`` for plugin and dependency tokens.

    Walks both Groovy and Kotlin DSL files when present and extracts every
    identifier token after stripping comments. The result is consultative — it
    is used to drive capability skip-decisions, not to produce a faithful AST
    of the build script (Gradle DSL is a Turing-complete script and cannot be
    parsed reliably without invoking Gradle itself).

    Args:
        project_root: Path to the project root.

    Returns:
        Lowercased identifier tokens, deduplicated, in first-seen order.
    """
    root = Path(project_root)
    seen: set[str] = set()
    ordered: list[str] = []
    for fname in _GRADLE_FILES:
        path = root / fname
        if not path.is_file():
            continue
        contents = _strip_gradle_comments(_read_text(path))
        for match in _TOKEN_RE.finditer(contents):
            token = match.group(0).lower()
            if token and token not in seen:
                seen.add(token)
                ordered.append(token)
    return ordered


def parse_maven_pom(project_root: str) -> list[str]:
    """Parse ``pom.xml`` for plugin and dependency artifact ids.

    Uses a regex over ``<artifactId>...</artifactId>`` elements (covering both
    ``<plugin>`` and ``<dependency>`` blocks) regardless of namespace. The
    information we need from Maven POMs is shallow — we never traverse the
    XML tree — so this avoids depending on the stdlib XML backend (which
    requires pyexpat and is unavailable on some Python distributions).

    Args:
        project_root: Path to the project root.

    Returns:
        Lowercased artifact ids, deduplicated, in document order. Returns
        ``[]`` when the POM is missing, unreadable or contains no
        ``<artifactId>`` markers.
    """
    pom_path = Path(project_root) / _MAVEN_FILE
    if not pom_path.is_file():
        return []
    contents = _read_text(pom_path)
    if not contents:
        return []
    # Reject input that doesn't look like XML at all (matches the
    # "malformed -> empty" contract without raising).
    if not _XML_TAG_RE.search(contents):
        return []

    seen: set[str] = set()
    ordered: list[str] = []
    for match in _ARTIFACT_ID_RE.finditer(contents):
        normalised = match.group(1).strip().lower()
        if normalised and normalised not in seen:
            seen.add(normalised)
            ordered.append(normalised)
    return ordered


def parse_jvm_dependencies(project_root: str) -> list[str]:
    """Return declared dependencies for the detected JVM build tool.

    Dispatches to :func:`parse_gradle_build` or :func:`parse_maven_pom` based
    on which build files the project ships. When both Gradle and Maven build
    files are present, Gradle takes priority (AC-010), but Maven artifact ids
    are also included so callers can detect cross-tool migrations.

    Args:
        project_root: Path to the project root.

    Returns:
        Lowercased identifier tokens (Gradle) and artifact ids (Maven),
        deduplicated, in first-seen order.
    """
    seen: set[str] = set()
    ordered: list[str] = []
    for token in parse_gradle_build(project_root):
        if token not in seen:
            seen.add(token)
            ordered.append(token)
    for token in parse_maven_pom(project_root):
        if token not in seen:
            seen.add(token)
            ordered.append(token)
    return ordered


def has_jvm_dependency(project_root: str, name: str) -> bool:
    """Check whether ``name`` appears in any JVM build file.

    The match is case-insensitive substring, because Maven artifact ids and
    Gradle plugin coordinates frequently appear as dotted strings (e.g.
    ``info.solidsoft.pitest``) and callers usually look up short names
    (``pitest``).

    Args:
        project_root: Path to the project root.
        name: Token to look up (e.g. ``jacoco``, ``pitest``, ``kotest-property``).

    Returns:
        ``True`` when any declared dependency contains ``name`` as a substring.
    """
    needle = name.strip().lower()
    if not needle:
        return False
    return any(needle in token for token in parse_jvm_dependencies(project_root))


def parse_pitest_xml(xml_text: str) -> dict[str, int]:
    """Extract mutation counts from a pitest ``mutations.xml`` report.

    pitest emits one ``<mutation status="...">`` element per mutation under a
    root ``<mutations>`` document. Recognised status strings (case-insensitive)
    are KILLED, SURVIVED, TIMED_OUT, NO_COVERAGE, MEMORY_ERROR, RUN_ERROR.

    The parser is regex-based — pitest XML is shallow (no nested information
    we care about) and the stdlib ElementTree backend depends on pyexpat
    which is unavailable on some Python distributions.

    Args:
        xml_text: Captured contents of ``mutations.xml``.

    Returns:
        A dictionary with integer counts for every recognised status. Missing
        statuses default to ``0``. Returns all-zero counts when the input is
        empty, doesn't look like XML, or has no recognised status attributes.
    """
    counts: dict[str, int] = {status: 0 for status in _PITEST_STATUSES}
    text = xml_text.strip()
    if not text:
        return counts
    # Bail when the input contains no XML-shaped tags at all so junk strings
    # never accidentally produce non-zero counts.
    if not _XML_TAG_RE.search(text):
        return counts

    for match in _MUTATION_STATUS_RE.finditer(text):
        normalised = match.group(1).strip().lower()
        if normalised in counts:
            counts[normalised] += 1

    return counts
