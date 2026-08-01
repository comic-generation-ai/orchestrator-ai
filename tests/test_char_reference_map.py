"""Unit tests for character_ids reference mapping (story-orchestrator-character-ids)."""

import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from src.clients.story_client import (  # noqa: E402
    _parse_characters,
    _parse_story_panel,
)
from src.workflow.comic_job import (  # noqa: E402
    PanelScriptData,
    _char_id_for_speaker,
    _register_char_references,
    _resolve_panel_reference_url,
    _shares_character_tag,
)


CHARACTERS = {
    "char_001": {
        "name": "Thạch Sanh",
        "visual_tag": "young muscular Vietnamese man, short black hair",
    },
    "char_002": {
        "name": "Lý Thông",
        "visual_tag": "slim Vietnamese man, sly expression, fine silk robe",
    },
}


class CharReferenceMapTests(unittest.TestCase):
    def test_register_first_appearance_per_char_id(self) -> None:
        char_map: dict[str, str] = {}
        _register_char_references(char_map, ["char_001"], "url-panel-1")
        _register_char_references(char_map, ["char_001", "char_002"], "url-panel-2")

        self.assertEqual(char_map["char_001"], "url-panel-1")
        self.assertEqual(char_map["char_002"], "url-panel-2")

    def test_resolve_reference_by_character_ids(self) -> None:
        char_map = {"char_001": "url-panel-1"}
        script = PanelScriptData(
            index=1,
            caption_vi="",
            prompt_en="on the right, slim Vietnamese man",
            scene_description="",
            speaker="Lý Thông",
            character_ids=["char_001", "char_002"],
        )

        ref_url = _resolve_panel_reference_url(
            script,
            characters=CHARACTERS,
            char_reference_map=char_map,
            panel_history=[],
        )
        self.assertEqual(ref_url, "url-panel-1")

    def test_resolve_prefers_speaker_char_id_on_multi_char_panel(self) -> None:
        char_map = {
            "char_001": "url-thach-sanh",
            "char_002": "url-ly-thong",
        }
        script = PanelScriptData(
            index=2,
            caption_vi="",
            prompt_en="two characters facing each other",
            scene_description="",
            speaker="Lý Thông",
            character_ids=["char_001", "char_002"],
        )

        ref_url = _resolve_panel_reference_url(
            script,
            characters=CHARACTERS,
            char_reference_map=char_map,
            panel_history=[],
        )
        self.assertEqual(ref_url, "url-ly-thong")

    def test_resolve_empty_when_character_ids_not_in_map_yet(self) -> None:
        script = PanelScriptData(
            index=0,
            caption_vi="",
            prompt_en="young muscular Vietnamese man in village",
            scene_description="",
            character_ids=["char_001"],
        )

        ref_url = _resolve_panel_reference_url(
            script,
            characters=CHARACTERS,
            char_reference_map={},
            panel_history=[],
        )
        self.assertEqual(ref_url, "")

    def test_fallback_fuzzy_match_when_character_ids_missing(self) -> None:
        shared_prompt = (
            "on the left, young muscular Vietnamese man, short black hair, simple peasant clothing"
        )
        script = PanelScriptData(
            index=1,
            caption_vi="",
            prompt_en=shared_prompt + ", standing in forest",
            scene_description="",
            character_ids=[],
        )
        panel_history = [(shared_prompt + ", village square", "url-fuzzy-ref")]

        ref_url = _resolve_panel_reference_url(
            script,
            characters={},
            char_reference_map={},
            panel_history=panel_history,
        )
        self.assertEqual(ref_url, "url-fuzzy-ref")
        self.assertTrue(_shares_character_tag(panel_history[0][0], script.prompt_en))

    def test_char_id_for_speaker(self) -> None:
        char_id = _char_id_for_speaker(
            "Thạch Sanh",
            CHARACTERS,
            ["char_001", "char_002"],
        )
        self.assertEqual(char_id, "char_001")


class StoryClientParseTests(unittest.TestCase):
    def test_parse_story_panel_scene_description_not_panel_type(self) -> None:
        panel = _parse_story_panel(
            {
                "panel_number": 1,
                "panel_type": "dialogue",
                "scene_description": "village square at dusk",
                "image_prompt": "hero standing",
                "dialogue": "Xin chào",
                "speaker": "Thạch Sanh",
                "speaker_position": "left",
                "character_ids": ["char_001"],
            },
            0,
        )
        self.assertEqual(panel.scene_description, "village square at dusk")
        self.assertEqual(panel.panel_type, "dialogue")
        self.assertEqual(panel.character_ids, ["char_001"])

    def test_parse_characters_and_missing_fields(self) -> None:
        characters = _parse_characters(
            {
                "characters": {
                    "char_001": {"name": "A", "visual_tag": "tag a"},
                }
            }
        )
        self.assertIn("char_001", characters)

        empty_panel = _parse_story_panel({"panel_number": 1, "image_prompt": "x"}, 0)
        self.assertEqual(empty_panel.character_ids, [])
        self.assertEqual(empty_panel.scene_description, "")


if __name__ == "__main__":
    unittest.main()
