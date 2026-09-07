"""Lossless shared-token transport for bounded review synthesis (078 FR-002, FR-004)."""

from __future__ import annotations

import json
import re
from collections import Counter
from typing import Any

from validator.semantic.review_context import PreparedReview

SYNTHESIS_TRANSPORT_VERSION = "3"
_LIST_FIELD = re.compile(r'"(?:reviewed_section_ids|searched_plan_sections)"\s*:\s*')
_JSON_STRING = re.compile(r'"(?:[^"\\]|\\.)*"')


def _list_spans(raw: str) -> list[tuple[int, int, str]]:
    """Locate only long string inventories, retaining their exact original JSON bytes."""
    decoder = json.JSONDecoder()
    spans = []
    for match in _LIST_FIELD.finditer(raw):
        try:
            value, length = decoder.raw_decode(raw[match.end() :])
        except ValueError:
            continue
        if length >= 256 and isinstance(value, list) and all(isinstance(v, str) for v in value):
            spans.append((match.end(), match.end() + length, raw[match.end() :][:length]))
    return spans


def _pack_lists(raw_results: list[str]) -> dict[str, Any]:
    """Replace repeated exact list literals; every other character stays in ordered chunks."""
    spans = [_list_spans(raw) for raw in raw_results]
    counts = Counter(text for group in spans for _, _, text in group)
    identities = {text: f"list-{index}" for index, (text, n) in enumerate(counts.items()) if n > 1}
    packed = []
    for raw, group in zip(raw_results, spans, strict=True):
        chunks: list[str | dict[str, str]] = []
        start = 0
        for left, right, text in group:
            if text not in identities:
                continue
            chunks.extend([raw[start:left], {"shared_list": identities[text]}])
            start = right
        chunks.append(raw[start:])
        packed.append({"raw_chunks": chunks})
    return {
        "shared_lists": {identity: text for text, identity in identities.items()},
        "batch_results": packed,
    }


def _string_chunks(text: str, identities: dict[str, int]) -> list[str | int]:
    """Replace complete exact JSON string tokens without parsing or normalizing them."""
    chunks: list[str | int] = []
    start = 0
    for match in _JSON_STRING.finditer(text):
        if match.group() not in identities:
            continue
        chunks.extend([text[start : match.start()], identities[match.group()]])
        start = match.end()
    chunks.append(text[start:])
    return chunks


def pack_synthesis_raws(
    raw_results: list[str], *, shared_texts: list[str] | None = None
) -> dict[str, Any]:
    """Share repeated lists and exact string tokens, retaining every original character."""
    packed = _pack_lists(raw_results)
    texts = [*packed["shared_lists"].values(), *(shared_texts or [])]
    texts.extend(
        part
        for row in packed["batch_results"]
        for part in row["raw_chunks"]
        if isinstance(part, str)
    )
    counts = Counter(
        match.group()
        for text in texts
        for match in _JSON_STRING.finditer(text)
        if len(match.group()) >= 48
    )
    identities = {text: i for i, text in enumerate(text for text, n in counts.items() if n > 1)}
    packed["shared_strings"] = list(identities)
    packed["shared_texts"] = [_string_chunks(text, identities) for text in shared_texts or []]
    packed["shared_lists"] = {
        identity: _string_chunks(text, identities)
        for identity, text in packed["shared_lists"].items()
    }
    for row in packed["batch_results"]:
        row["raw_chunks"] = [
            chunk
            for part in row["raw_chunks"]
            for chunk in (_string_chunks(part, identities) if isinstance(part, str) else [part])
        ]
    _pack_string_prefixes(packed)
    return packed


def _pack_string_prefixes(packed: dict[str, Any]) -> None:
    """Share exact path prefixes inside tokens without changing quotes, escapes or suffixes."""
    tokens = packed["shared_strings"]
    prefixes = [text[: text.rfind("/") + 1] for text in tokens]
    counts = Counter(prefix for prefix in prefixes if len(prefix) >= 32)
    identities = {prefix: i for i, prefix in enumerate(p for p, n in counts.items() if n > 1)}
    packed["shared_prefixes"] = list(identities)
    packed["shared_strings"] = [
        [identities[prefix], token[len(prefix) :]] if prefix in identities else token
        for prefix, token in zip(prefixes, tokens, strict=True)
    ]


def _expanded_string_table(payload: dict[str, Any]) -> list[str]:
    return [
        token if isinstance(token, str) else payload["shared_prefixes"][token[0]] + token[1]
        for token in payload["shared_strings"]
    ]


def _expand_strings(chunks: list[str | int], strings: list[str]) -> str:
    return "".join(part if isinstance(part, str) else strings[part] for part in chunks)


def expand_synthesis_raws(payload: dict[str, Any]) -> list[str]:
    """Reconstruct exact original JSON bytes from the two explicitly ordered reference levels."""
    strings = _expanded_string_table(payload)
    lists = {
        identity: _expand_strings(chunks, strings)
        for identity, chunks in payload["shared_lists"].items()
    }
    return [
        "".join(
            part
            if isinstance(part, str)
            else (strings[part] if isinstance(part, int) else lists[part["shared_list"]])
            for part in row["raw_chunks"]
        )
        for row in payload["batch_results"]
    ]


def expand_synthesis_sections(payload: dict[str, Any]) -> list[str]:
    """Restore the complete ordered global section inventory from its exact JSON text."""
    return json.loads(_expand_strings(payload["section_ids"], _expanded_string_table(payload)))


def synthesis_payload(prepared: PreparedReview, raw_results: list[str]) -> dict[str, Any]:
    """Keep all judgments, citations and issue ledgers while sharing repeated inventories."""
    from pydantic import ValidationError

    from validator.semantic.review_contract import ReviewResponse
    from validator.semantic.review_synthesis import issue_ledger

    ledgers = []
    for raw in raw_results:
        try:
            ledgers.append(issue_ledger(ReviewResponse.model_validate_json(raw)))
        except ValidationError:
            ledgers.append({"malformed_batch": {}})
    sections = [s.section_id for s in prepared.sections]
    section_text = json.dumps(sections, ensure_ascii=False)
    packed = pack_synthesis_raws(raw_results, shared_texts=[section_text])
    section_chunks = packed.pop("shared_texts")[0]
    if (
        expand_synthesis_raws(packed) != raw_results
        or _expand_strings(section_chunks, _expanded_string_table(packed)) != section_text
    ):
        raise ValueError("synthesis_transport_reconstruction_failed")
    return {
        "synthesis_transport_version": SYNTHESIS_TRANSPORT_VERSION,
        "batch_ids": [b.batch_id for b in prepared.batches],
        "section_ids": section_chunks,
        "requirements": [r.model_dump() for r in prepared.requirements],
        "invariants": [
            s.model_dump()
            for s in prepared.sections
            if s.role in ("constitution", "stack", "project")
        ],
        **packed,
        "issue_ledgers": ledgers,
    }


def synthesis_prompt(prepared: PreparedReview, raw_results: list[str]) -> str:
    """Build the same bounded transport for producer and consumer verification."""
    return (
        "Synthesize all batches: resolve cross-batch contradictions, missing coverage, "
        "ambiguities and extra scope. Retain each blocking issue or explicitly resolve it "
        "with issue_key, rationale and exact source citations. Judge exact batch excerpts, "
        "not summaries. Lossless transport3: shared_strings tokens are literal strings or "
        "[prefix_index,suffix]; join shared_prefixes[prefix_index]+suffix first. Tokens retain "
        "original JSON quotes/escapes. Concatenate chunks in order: "
        "strings are literal text; integers select shared_strings tokens. First expand "
        "shared_lists and section_ids this way. Then expand each batch_results.raw_chunks "
        "likewise, additionally replacing {shared_list: ID} with that expanded shared_lists "
        "entry. Parse the reconstructed original JSON; preserve every list entry, whitespace, "
        "judgment and issue ledger. Return strict review JSON: batch_id=synthesis, all "
        "reviewed_section_ids, every qualified requirement once, synthesized_batch_ids "
        "in order and exact citations.\n"
        + json.dumps(
            synthesis_payload(prepared, raw_results), ensure_ascii=False, separators=(",", ":")
        )
    )
