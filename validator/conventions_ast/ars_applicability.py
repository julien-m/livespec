# @spec FR-004: Framework applicability for ARS rules
#   .specs/features/082-conventions-gate-signal/spec.md#fr-004

"""Per-file applicability of executable ARS rules: language suffixes and framework evidence."""

from __future__ import annotations

import re
from dataclasses import dataclass
from pathlib import PurePosixPath

from validator.conventions_feature_scope import SOURCE_SUFFIXES

LANGUAGE_AGNOSTIC = "language-agnostic"
SOURCE_PREFIX = "ai-ressources/"

LANGUAGE_SUFFIXES: dict[str, tuple[str, ...]] = {
    "css": (".css",),
    "delphi": (".pas", ".dpr", ".dproj"),
    "go": (".go",),
    "javascript": (".js", ".jsx", ".mjs", ".cjs", ".ts", ".tsx"),
    "kotlin": (".kt", ".kts"),
    "python": (".py",),
    "rust": (".rs",),
    "shell": (".sh", ".bash", ".zsh"),
    "sql": (".sql",),
    "typescript": (".ts", ".tsx"),
}

# Module specifier after `from`, a side-effect `import`, dynamic `import(` or `require(`:
# captures the quoted package path, e.g. `next/link` in `import Link from "next/link"`.
_MODULE_SPECIFIER = re.compile(
    r"""(?:\bfrom\s+|\bimport\s+|\bimport\s*\(\s*|\brequire\s*\(\s*)["']([^"'\n]+)["']"""
)


@dataclass(frozen=True)
class FrameworkEvidence:
    """Deterministic markers proving that one file belongs to a framework."""

    name: str
    packages: tuple[str, ...] = ()
    prefixes: tuple[str, ...] = ()
    suffixes: tuple[str, ...] = ()
    path_segments: tuple[str, ...] = ()
    directive: str = ""

    def matches(self, rel: str, text: str) -> bool:
        """Return True when the file shows any marker of this framework."""
        path = PurePosixPath(rel)
        if path.suffix.lower() in self.suffixes:
            return True
        if any(segment in path.parts[:-1] for segment in self.path_segments):
            return True
        if self.directive and re.search(self.directive, text, re.MULTILINE):
            return True
        return any(self._imports(spec) for spec in module_specifiers(text))

    def _imports(self, spec: str) -> bool:
        if any(spec == package or spec.startswith(f"{package}/") for package in self.packages):
            return True
        return any(spec.startswith(prefix) for prefix in self.prefixes)


# Framework Evidence table of feature 082, keyed by the rule's source document.
FRAMEWORK_EVIDENCE: dict[str, FrameworkEvidence] = {
    "code-conventions/astro.md": FrameworkEvidence(
        "Astro", packages=("astro",), prefixes=("astro:", "@astrojs/")
    ),
    "code-conventions/nextjs.md": FrameworkEvidence("Next.js", packages=("next",)),
    "code-conventions/react.md": FrameworkEvidence(
        "React", packages=("react", "react-dom"), suffixes=(".jsx", ".tsx")
    ),
    "code-conventions/remotion.md": FrameworkEvidence(
        "Remotion", packages=("remotion",), prefixes=("@remotion/",)
    ),
    "code-conventions/shadcn.md": FrameworkEvidence(
        "shadcn/ui",
        packages=("class-variance-authority",),
        prefixes=("@/components/ui/", "@radix-ui/"),
    ),
    "code-conventions/tanstack.md": FrameworkEvidence("TanStack", prefixes=("@tanstack/",)),
    "code-conventions/drizzle.md": FrameworkEvidence(
        "Drizzle", packages=("drizzle-orm", "drizzle-kit"), path_segments=("drizzle",)
    ),
    "code-conventions/prisma.md": FrameworkEvidence(
        "Prisma", packages=("@prisma/client",), path_segments=("prisma",)
    ),
    # CSS directives owned by Tailwind: `@tailwind`, `@apply`, `@theme`, `@config`
    # or the v4 entry `@import "tailwindcss"`.
    "code-conventions/tailwind.md": FrameworkEvidence(
        "Tailwind",
        directive=r"@(?:tailwind|apply|theme|config)\b|@import\s+[\"']tailwindcss[\"']",
    ),
    "code-conventions/cloudflare.md": FrameworkEvidence(
        "Cloudflare", packages=("wrangler",), prefixes=("cloudflare:", "@cloudflare/")
    ),
}


def module_specifiers(text: str) -> frozenset[str]:
    """Return every imported or required module specifier in a source text."""
    return frozenset(_MODULE_SPECIFIER.findall(text))


def framework_for_source(source_path: str) -> FrameworkEvidence | None:
    """Return the framework evidence required by a rule source document, if any."""
    return FRAMEWORK_EVIDENCE.get(source_path.removeprefix(SOURCE_PREFIX))


def language_applies(language: str, rel: str) -> bool:
    """Return True when a rule language covers the file suffix."""
    if language == LANGUAGE_AGNOSTIC:
        return True
    return PurePosixPath(rel).suffix.lower() in LANGUAGE_SUFFIXES.get(language, ())


def language_unreachable(language: str) -> bool:
    """Return True when no suffix of a rule language is collected by the source scope."""
    if language == LANGUAGE_AGNOSTIC:
        return False
    return not set(LANGUAGE_SUFFIXES.get(language, ())).issubset(SOURCE_SUFFIXES)


def framework_applies(source_path: str, rel: str, text: str) -> bool:
    """Return True when a rule is not framework-sourced or the file shows that framework."""
    evidence = framework_for_source(source_path)
    return evidence is None or evidence.matches(rel, text)
