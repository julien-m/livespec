"""Different source inventories share exact tokens without losing any reviewer evidence."""

import hashlib
import json

from tests.test_review_batching import judgments, long_context, synthesis
from validator.semantic.review_contract import validate_review_result
from validator.semantic.review_receipts import load_review_receipt, verify_review_receipt
from validator.semantic.review_synthesis_transport import (
    expand_synthesis_raws,
    expand_synthesis_sections,
    pack_synthesis_raws,
)


def test_different_overlapping_lists_share_tokens_and_preserve_original_bytes():
    identities = [
        f'.specs/source-é/{i:03}/very-long-section-identity-with-quotes-"-界' for i in range(80)
    ]
    rows = [
        {
            "reviewed_section_ids": identities[index : index + 60],
            "searched_plan_sections": list(reversed(identities[index : index + 55])),
            "citation": {"section_id": identities[index], "excerpt": "Échec\n exact\\texte"},
            "rationale": "Keep every character, even duplicate IDs.",
        }
        for index in range(4)
    ]
    raws = [
        json.dumps(row, ensure_ascii=index % 2 == 0, indent=2 if index % 2 else None) + " \n\t"
        for index, row in enumerate(rows)
    ]
    packed = pack_synthesis_raws(raws)
    assert not packed["shared_lists"] and packed["shared_strings"]
    restored = expand_synthesis_raws(packed)
    assert restored == raws
    assert [hashlib.sha256(raw.encode()).hexdigest() for raw in restored] == [
        hashlib.sha256(raw.encode()).hexdigest() for raw in raws
    ]
    assert [json.loads(raw) for raw in restored] == rows
    assert len(json.dumps(packed, ensure_ascii=False)) < len(json.dumps(raws, ensure_ascii=False))


def test_shared_list_and_string_references_preserve_duplicates_and_order():
    ids = ["long-source-path/" + "x" * 80, "long-source-path/" + "y" * 80]
    row = {"reviewed_section_ids": ids * 3, "searched_plan_sections": ids * 3}
    other = {"reviewed_section_ids": [*ids, ids[0]], "citation": ids[1]}
    raws = [json.dumps(row), json.dumps(other)]
    packed = pack_synthesis_raws(raws)
    assert packed["shared_lists"] and packed["shared_strings"]
    assert expand_synthesis_raws(packed) == raws
    assert json.loads(expand_synthesis_raws(packed)[0])["reviewed_section_ids"] == ids * 3


def test_global_inventory_shares_exact_path_prefixes_with_distinct_batch_ids():
    prefix = '.specs/features/078/.reviews/évidence/after/source-with-escaped-"-value/'
    ids = [f"{prefix}spec.md:L{i}-L{i + 1}" for i in range(30)]
    raws = [
        json.dumps({"reviewed_section_ids": ids[i : i + 10]}, ensure_ascii=False)
        for i in range(0, 30, 10)
    ]
    section_text = json.dumps(ids, ensure_ascii=False)
    packed = pack_synthesis_raws(raws, shared_texts=[section_text])
    packed["section_ids"] = packed.pop("shared_texts")[0]
    assert packed["shared_prefixes"]
    assert any(isinstance(token, list) for token in packed["shared_strings"])
    assert expand_synthesis_sections(packed) == ids
    assert expand_synthesis_raws(packed) == raws
    assert len(json.dumps(packed, ensure_ascii=False)) < len(json.dumps([section_text, *raws]))


def test_version2_receipt_stays_readable_but_needs_current_ingestion(tmp_path):
    context = long_context()
    responses = judgments(context)
    raws = [json.dumps(response) for response in responses]
    final = json.dumps(synthesis(context, responses))
    current = validate_review_result(context, raws, final)
    assert current.ready and current.synthesis_transport_version == "3"
    historical = current.model_copy(update={"synthesis_transport_version": "2"})
    path = tmp_path / "historical.json"
    path.write_text(historical.model_dump_json())
    loaded = load_review_receipt(path)
    assert loaded.raw_results == raws and loaded.synthesis == final
    assert not verify_review_receipt(loaded, context)
    assert verify_review_receipt(current, context)
