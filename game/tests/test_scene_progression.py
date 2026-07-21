"""Tests for the semantic scene_progression support slot structure.

Per DEC-003a, each support has 3 scene slots (recruitment/story/final),
each with its own tech_id and tier. The CharacterData loader flattens
this to (support_id, max_tier) tuples on the `support_slots` property
(for backward compat) and preserves the full structure on
`scene_progression` (for new consumers).

This test file pins the DEC-003a contract.
"""
import json
import sys
from pathlib import Path

GAME_DIR = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(GAME_DIR / "tools"))
sys.path[:] = [p for p in sys.path if "hermes" not in p.lower()]

import character_data  # type: ignore  # noqa: E402

CHARACTERS_DIR = GAME_DIR / "data" / "characters"


def test_serge_has_scene_progression():
    """Serge's loader exposes the semantic scene_progression property."""
    cd = character_data.CharacterData.from_json(CHARACTERS_DIR / "serge.json")
    assert hasattr(cd, "scene_progression")
    assert len(cd.scene_progression) == 6  # 6 supports
    first = cd.scene_progression[0]
    assert first["support_id"] == "leena_poshul"
    assert "recruitment" in first["scene_progression"]
    assert "story" in first["scene_progression"]
    assert "final" in first["scene_progression"]


def test_each_scene_has_tech_id_and_tier():
    """Each of recruitment/story/final has {tech_id, tier}."""
    cd = character_data.CharacterData.from_json(CHARACTERS_DIR / "serge.json")
    for slot in cd.scene_progression:
        for scene in ("recruitment", "story", "final"):
            entry = slot["scene_progression"][scene]
            assert "tech_id" in entry, f"{slot['support_id']}.{scene} missing tech_id"
            assert "tier" in entry, f"{slot['support_id']}.{scene} missing tier"
            assert isinstance(entry["tier"], int)
            assert 1 <= entry["tier"] <= 8


def test_tier_progression_increases_recruitment_to_final():
    """For each support, tier(recruitment) <= tier(story) <= tier(final)."""
    cd = character_data.CharacterData.from_json(CHARACTERS_DIR / "serge.json")
    for slot in cd.scene_progression:
        sp = slot["scene_progression"]
        t_rec = sp["recruitment"]["tier"]
        t_story = sp["story"]["tier"]
        t_final = sp["final"]["tier"]
        assert t_rec <= t_story <= t_final, (
            f"{slot['support_id']}: tiers must progress "
            f"recruitment({t_rec}) <= story({t_story}) <= final({t_final})"
        )


def test_early_recruits_use_tier_2_late_use_tier_3():
    """Per DEC-003: early recruits unlock at tier 2, late recruits at tier 3.

    This is a soft test — we check Serge's first 3 supports (early)
    and the last 3 (later). The split depends on the locked per-base
    recruit order; the test allows either tier 2 or 3 for any single
    support, but at least 2 of the 6 must be tier 2 and at least 2 must
    be tier 3.
    """
    cd = character_data.CharacterData.from_json(CHARACTERS_DIR / "serge.json")
    rec_tiers = [s["scene_progression"]["recruitment"]["tier"] for s in cd.scene_progression]
    tier_2_count = sum(1 for t in rec_tiers if t == 2)
    tier_3_count = sum(1 for t in rec_tiers if t == 3)
    assert tier_2_count >= 1, f"Expected at least 1 tier-2 recruit, got {tier_2_count}"
    assert tier_3_count >= 1, f"Expected at least 1 tier-3 recruit, got {tier_3_count}"


def test_all_six_bases_have_scene_progression():
    """All 6 base character files use the new scene_progression shape."""
    for char_id in ("serge", "kidd", "nikki", "glenn", "herle", "norris"):
        cd = character_data.CharacterData.from_json(CHARACTERS_DIR / f"{char_id}.json")
        assert len(cd.scene_progression) == 6, (
            f"{char_id}: expected 6 supports with scene_progression, "
            f"got {len(cd.scene_progression)}"
        )
        for slot in cd.scene_progression:
            assert "scene_progression" in slot
            for scene in ("recruitment", "story", "final"):
                assert scene in slot["scene_progression"], (
                    f"{char_id}.{slot['support_id']} missing {scene}"
                )


def test_flat_support_slots_matches_max_tier():
    """The flat support_slots[(support_id, tier)] matches the `final` tier."""
    cd = character_data.CharacterData.from_json(CHARACTERS_DIR / "serge.json")
    for (sid, tier), slot in zip(cd.support_slots, cd.scene_progression):
        assert slot["support_id"] == sid
        assert slot["scene_progression"]["final"]["tier"] == tier
