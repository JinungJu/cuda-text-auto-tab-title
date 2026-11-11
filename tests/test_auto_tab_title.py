import configparser
import importlib
import json
import sys
import tempfile
import types
import unittest
from pathlib import Path
from unittest.mock import patch


PROJECT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT))
app = types.ModuleType("cudatext")
for name in (
    "APP_DIR_SETTINGS", "APPSTATE_SESSION_LOAD", "APPSTATE_SESSION_SAVE_BEFORE",
    "EDSTATE_TAB_TITLE", "PROP_TAB_ID", "PROP_KIND", "PROP_FN", "PROP_IN_SESSION",
    "PROP_EDITORS_LINKED", "PROP_TAB_TITLE", "PROP_TAB_TITLE_REASON",
):
    setattr(app, name, name)
with patch.dict(sys.modules, {"cudatext": app}):
    plugin = importlib.import_module("cuda_auto_tab_title")
    session = importlib.import_module("cuda_auto_tab_title.session")
    from cuda_auto_tab_title.titles import MAX_LINE_SIZE, Settings


class FakeEditor:
    def __init__(self, host, tab_id, **props):
        self.host = host
        self.props = {
            app.PROP_TAB_ID: tab_id,
            app.PROP_KIND: "text",
            app.PROP_FN: "",
            app.PROP_IN_SESSION: False,
            app.PROP_EDITORS_LINKED: True,
            app.PROP_TAB_TITLE: "Untitled" + str(tab_id),
            app.PROP_TAB_TITLE_REASON: "u",
        }
        self.props.update(props)
        self.lines = [""]
        self.reads = []
        self.writes = []

    def get_prop(self, name):
        value = self.props[name]
        return value.lstrip("*") if name == app.PROP_TAB_TITLE else value

    def set_prop(self, name, value):
        if name != app.PROP_TAB_TITLE:
            raise AssertionError("unexpected write to " + name)
        self.writes.append(value)
        previous = self.props[name]
        if value:
            self.props[app.PROP_TAB_TITLE_REASON] = "p"
            self.props[name] = value
            if previous != value:
                self.host.command.on_state_ed(self, app.EDSTATE_TAB_TITLE)
        elif self.props[app.PROP_TAB_TITLE_REASON] == "p":
            self.props[name] = "Untitled" + str(self.props[app.PROP_TAB_ID])
            if previous != self.props[name]:
                self.host.command.on_state_ed(self, app.EDSTATE_TAB_TITLE)
            self.props[app.PROP_TAB_TITLE_REASON] = "u"

    def get_text_line(self, index, max_len):
        self.reads.append((index, max_len))
        if index < len(self.lines):
            line = self.lines[index]
            return line if len(line.encode("utf-8")) <= max_len else ""

    @property
    def title(self):
        return self.props[app.PROP_TAB_TITLE]


class AutoTabTitleTests(unittest.TestCase):
    def setUp(self):
        directory = tempfile.TemporaryDirectory()
        self.addCleanup(directory.cleanup)
        self.directory = Path(directory.name)
        self.tabs = {}
        self.messages = []
        self.prompt = []
        self.answer = None
        app.app_path = lambda _: self.directory
        app.ed_handles = lambda: tuple(self.tabs)
        app.Editor = self.tabs.__getitem__
        app.msg_status = self.messages.append
        app.dlg_input = self.dialog
        self.config_path = self.directory / "cuda_auto_tab_title.json"
        self.command = plugin.Command()

    def dialog(self, label, default):
        self.prompt.append((label, default))
        return self.answer

    def new_tab(self, tab_id=1, **props):
        editor = FakeEditor(self, tab_id, **props)
        self.tabs[tab_id] = editor
        app.ed = editor
        return editor

    def save_session(self):
        self.command.on_state(None, app.APPSTATE_SESSION_SAVE_BEFORE)

    def restore_session(self):
        for editor in self.tabs.values():
            editor.props[app.PROP_IN_SESSION] = True
        self.command = plugin.Command()
        self.command.on_state(None, app.APPSTATE_SESSION_LOAD)

    def test_blank_tab_preserves_native_caption_without_writing(self):
        editor = self.new_tab()
        self.command.on_tab_change(editor)
        self.assertEqual(editor.title, "Untitled1")
        self.assertEqual(editor.writes, [])

    def test_typing_editing_deleting_and_clearing(self):
        editor = self.new_tab()
        for lines, expected in (
            (["# Mac mini SSH 설정", "키 인증 구성"], "Mac mini SSH 설정"),
            (["# SSH 키 재설정", "키 인증 구성"], "SSH 키 재설정"),
            (["", "키 인증 구성"], "키 인증 구성"),
            (["", "   "], "Untitled1"),
        ):
            editor.lines = lines
            self.command.on_change_slow(editor)
            self.assertEqual(editor.title, expected)
            self.assertEqual(editor.lines, lines)

    def test_markdown_whitespace_unicode_and_symbols(self):
        editor = self.new_tab()
        editor.lines = ["\t", " ## ", "   ### 한글 \t SSH 🔑 & C#  ## "]
        self.command.on_change_slow(editor)
        self.assertEqual(editor.title, "한글 SSH 🔑 & C#")
        editor.lines = ["  #해시태그  "]
        self.command.on_change_slow(editor)
        self.assertEqual(editor.title, "#해시태그")

    def test_truncation_includes_ellipsis_in_limit(self):
        editor = self.new_tab()
        editor.lines = ["🔑" * 40]
        self.command.on_change_slow(editor)
        self.assertEqual(editor.title, "🔑" * 27 + "…")
        self.command.settings = Settings(max_title_length=1)
        self.command.on_change_slow(editor)
        self.assertEqual(editor.title, "…")

    def test_scan_and_transfer_bounds_on_large_document(self):
        editor = self.new_tab()
        editor.lines = ["x" * (MAX_LINE_SIZE + 1)] + [" "] * 9 + ["Outside"]
        editor.lines.extend(["body"] * 200000)
        self.command.on_change_slow(editor)
        self.assertEqual(editor.title, "Untitled1")
        self.assertEqual(editor.reads, [(index, MAX_LINE_SIZE) for index in range(10)])
        editor.reads.clear()
        editor.lines[1] = "Inside"
        self.command.on_change_slow(editor)
        self.assertEqual(editor.title, "Inside")
        self.assertEqual(editor.reads, [(0, MAX_LINE_SIZE), (1, MAX_LINE_SIZE)])

    def test_tabs_update_independently_and_unchanged_title_is_not_rewritten(self):
        first, second = self.new_tab(), self.new_tab(2)
        first.lines, second.lines = ["첫 메모"], ["Second"]
        self.command.on_change_slow(first)
        self.command.on_tab_change(second)
        self.command.on_tab_change(first)
        self.assertEqual(first.writes, ["첫 메모"])
        self.assertEqual(second.writes, ["Second"])

    def test_manual_title_then_reset(self):
        editor = self.new_tab()
        editor.lines = ["Auto"]
        self.command.on_tab_change(editor)
        self.answer = "**수동 이름  🔑"
        self.command.rename_current_tab()
        self.assertEqual(self.prompt[-1], ("Rename Current Tab", "Auto"))
        editor.lines = ["Changed"]
        self.command.on_change_slow(editor)
        self.assertEqual(editor.title, "**수동 이름  🔑")
        self.answer = None
        self.command.rename_current_tab()
        self.assertEqual(self.prompt[-1][1], "**수동 이름  🔑")
        self.command.reset_tab_title_to_auto()
        self.assertEqual(editor.title, "Changed")

    def test_empty_input_cancel_and_reset_to_default(self):
        editor = self.new_tab()
        self.command.rename_current_tab()
        self.answer = "  "
        self.command.rename_current_tab()
        self.assertEqual(editor.writes, [])
        self.answer = "Manual"
        self.command.rename_current_tab()
        self.command.reset_tab_title_to_auto()
        self.assertEqual(editor.title, "Untitled1")

    def test_manual_command_rechecks_ownership_after_dialog(self):
        editor = self.new_tab()

        def change_title_during_dialog(label, default):
            editor.set_prop(app.PROP_TAB_TITLE, "External")
            return "Manual"

        app.dlg_input = change_title_during_dialog
        self.command.rename_current_tab()
        self.assertEqual(editor.title, "External")

    def test_saved_special_and_independent_split_tabs_are_excluded(self):
        for props in (
            {app.PROP_FN: "C:/notes.md", app.PROP_TAB_TITLE_REASON: "f"},
            {app.PROP_KIND: "bin"},
            {app.PROP_KIND: "pic"},
            {app.PROP_TAB_TITLE_REASON: "s"},
            {app.PROP_TAB_TITLE_REASON: "p"},
            {app.PROP_EDITORS_LINKED: False},
        ):
            editor = self.new_tab(**props)
            editor.lines = ["Do not use"]
            self.command.on_change_slow(editor)
            self.command.rename_current_tab()
            self.command.reset_tab_title_to_auto()
            self.assertEqual((editor.reads, editor.writes, self.prompt), ([], [], []))

    def test_external_title_change_relinquishes_ownership_even_with_same_api_text(self):
        editor = self.new_tab()
        editor.lines = ["Auto"]
        self.command.on_change_slow(editor)
        editor.set_prop(app.PROP_TAB_TITLE, "*Auto")
        editor.lines = ["Changed"]
        self.command.on_change_slow(editor)
        self.command.reset_tab_title_to_auto()
        self.assertEqual(editor.title, "*Auto")
        self.assertEqual(self.command.owned, {})

    def test_save_releases_ownership_without_touching_filename_caption(self):
        editor = self.new_tab()
        editor.lines = ["SSH 설정"]
        self.command.on_change_slow(editor)
        editor.props.update(PROP_FN="C:/ssh_notes.md", PROP_TAB_TITLE="ssh_notes.md",
                            PROP_TAB_TITLE_REASON="f")
        self.command.on_save(editor)
        self.command.on_change_slow(editor)
        self.assertEqual(editor.title, "ssh_notes.md")
        self.assertEqual(editor.writes, ["SSH 설정"])
        self.assertEqual(self.command.owned, {})

    def test_restart_restores_both_modes_and_does_not_adopt_other_titles(self):
        auto, manual, foreign = self.new_tab(), self.new_tab(2), self.new_tab(3)
        auto.lines = ["Auto"]
        self.command.on_change_slow(auto)
        app.ed = manual
        self.answer = "Manual"
        self.command.rename_current_tab()
        foreign.set_prop(app.PROP_TAB_TITLE, "Foreign")
        self.save_session()
        self.assertNotIn("Manual", self.command.state_path.read_text(encoding="utf-8"))
        self.restore_session()
        for editor in (auto, manual, foreign):
            editor.lines = ["Changed"]
            self.command.on_change_slow(editor)
        self.assertEqual([auto.title, manual.title, foreign.title],
                         ["Changed", "Manual", "Foreign"])
        self.assertTrue(self.command.owned["2"].manual)

    def test_restore_requires_matching_title_and_id(self):
        editor = self.new_tab()
        editor.lines = ["Original"]
        self.command.on_tab_change(editor)
        self.save_session()
        editor.props[app.PROP_TAB_TITLE] = "External"
        other = self.new_tab(2, PROP_TAB_TITLE="Original", PROP_TAB_TITLE_REASON="p")
        self.restore_session()
        for tab in (editor, other):
            tab.lines = ["Changed"]
            self.command.on_change_slow(tab)
        self.assertEqual((editor.title, other.title), ("External", "Original"))
        self.assertEqual(self.command.owned, {})

    def test_closed_tabs_leave_live_state_and_inactive_cache_is_bounded(self):
        with patch.object(session, "INACTIVE_LIMIT", 2):
            for tab_id in range(1, 6):
                editor = self.new_tab(tab_id)
                editor.lines = [str(tab_id)]
                self.command.on_change_slow(editor)
                self.save_session()
                del self.tabs[tab_id]
                self.command.on_tab_move(None)
                self.assertNotIn(str(tab_id), self.command.owned)
            self.save_session()
        self.assertEqual(list(session.load_records(self.command.state_path)), ["4", "5"])

    def test_cleanup_resets_owned_titles_and_pauses_automation(self):
        editor = self.new_tab()
        editor.lines = ["Auto"]
        self.command.on_change_slow(editor)
        foreign = self.new_tab(2, PROP_TAB_TITLE="Foreign", PROP_TAB_TITLE_REASON="p")
        self.command.restore_default_titles()
        self.command.on_tab_change(editor)
        self.assertEqual(editor.title, "Untitled1")
        self.assertEqual(foreign.writes, [])

    def test_settings_defaults_and_validation(self):
        for text in ("{bad", "[]", '{"enabled": 1, "scan_lines": -1, "max_title_length": true}'):
            self.config_path.write_text(text, encoding="utf-8")
            self.assertEqual(Settings.load(self.config_path), Settings())
        self.config_path.write_text(json.dumps({
            "max_title_length": 12, "scan_lines": 3, "strip_markdown": False,
            "rename_saved_files": True,
        }), encoding="utf-8-sig")
        self.assertEqual(Settings.load(self.config_path), Settings(
            max_title_length=12, scan_lines=3, strip_markdown=False))
        example = PROJECT / "cuda_auto_tab_title" / "settings.example.json"
        self.assertEqual(Settings.load(example), Settings())

    def test_disabled_and_explicit_reset_when_auto_rename_is_off(self):
        editor = self.new_tab()
        editor.lines = ["# Keep hash"]
        self.command.settings = Settings(enabled=False)
        self.command.on_change_slow(editor)
        self.command.rename_current_tab()
        self.command.reset_tab_title_to_auto()
        self.assertEqual(editor.writes, [])
        self.command.settings = Settings(auto_rename=False, strip_markdown=False)
        self.command.on_change_slow(editor)
        self.assertEqual(editor.writes, [])
        self.command.reset_tab_title_to_auto()
        self.assertEqual(editor.title, "# Keep hash")

    def test_registration_uses_unique_supported_handlers_and_no_default_hotkey(self):
        manifest = configparser.ConfigParser()
        manifest.read(PROJECT / "cuda_auto_tab_title" / "install.inf", encoding="utf-8")
        events = manifest["item1"]["events"].split(",")
        self.assertEqual(len(events), len(set(events)))
        self.assertIn("on_change_slow", events)
        self.assertNotIn("on_change", events)
        self.assertNotIn("on_close", events)
        for event in events:
            self.assertTrue(callable(getattr(plugin.Command, event)))
        for item in ("item2", "item3", "item4"):
            self.assertNotIn("hotkey", manifest[item])
            self.assertTrue(callable(getattr(plugin.Command, manifest[item]["method"])))


if __name__ == "__main__":
    unittest.main()
