"""Auto Tab Title for CudaText API 1.0.483 or later."""

from pathlib import Path

import cudatext as app

from .session import TitleRecord, load_records, save_records
from .titles import Settings, extract_title


class Command:
    def __init__(self):
        directory = Path(app.app_path(app.APP_DIR_SETTINGS))
        self.settings = Settings.load(directory / "cuda_auto_tab_title.json")
        self.state_path = directory / "cuda_auto_tab_title_state.json"
        self.owned = {}
        self.setting_title = set()
        self.paused = False

    @staticmethod
    def _tab_id(editor):
        tab_id = editor.get_prop(app.PROP_TAB_ID)
        return str(tab_id) if tab_id else None

    @staticmethod
    def _is_memo(editor):
        return (editor.get_prop(app.PROP_KIND) == "text"
                and editor.get_prop(app.PROP_FN) == ""
                and editor.get_prop(app.PROP_EDITORS_LINKED))

    def _owned_title(self, editor, tab_id):
        record = self.owned.get(tab_id)
        if record is None:
            return None
        if (editor.get_prop(app.PROP_TAB_TITLE_REASON) == "p"
                and record.matches(editor.get_prop(app.PROP_TAB_TITLE))):
            return record
        self.owned.pop(tab_id, None)
        return None

    def _target(self, editor):
        if not self._is_memo(editor):
            return None
        tab_id = self._tab_id(editor)
        if tab_id is None or tab_id in self.setting_title:
            return None
        record = self._owned_title(editor, tab_id)
        if record is not None or editor.get_prop(app.PROP_TAB_TITLE_REASON) == "u":
            return tab_id, record
        return None

    def _set_title(self, editor, tab_id, old_record, title, manual=False):
        new_record = TitleRecord.from_title(title, manual) if title else None
        if new_record is None and old_record is None:
            return
        same_title = (old_record is not None and new_record is not None
                      and (old_record.digest, old_record.stars)
                      == (new_record.digest, new_record.stars))
        if not same_title:
            self.setting_title.add(tab_id)
            try:
                editor.set_prop(app.PROP_TAB_TITLE, title)
            finally:
                self.setting_title.discard(tab_id)
        self.owned.pop(tab_id, None)
        if (new_record is not None
                and editor.get_prop(app.PROP_TAB_TITLE_REASON) == "p"
                and new_record.matches(editor.get_prop(app.PROP_TAB_TITLE))):
            self.owned[tab_id] = new_record

    def _refresh(self, editor):
        if self.paused or not (self.settings.enabled and self.settings.auto_rename):
            return
        target = self._target(editor)
        if target is None:
            return
        tab_id, record = target
        if record is None or not record.manual:
            title = extract_title(editor.get_text_line, self.settings)
            self._set_title(editor, tab_id, record, title)

    def _restore(self):
        # Only adopt captions belonging to tabs that CudaText restored.
        saved = load_records(self.state_path)
        for handle in app.ed_handles():
            editor = app.Editor(handle)
            tab_id = self._tab_id(editor)
            record = saved.get(tab_id)
            if (record is not None and self._is_memo(editor)
                    and editor.get_prop(app.PROP_IN_SESSION)
                    and editor.get_prop(app.PROP_TAB_TITLE_REASON) == "p"
                    and record.matches(editor.get_prop(app.PROP_TAB_TITLE))):
                self.owned[tab_id] = record
            self._refresh(editor)

    def _save_session(self):
        live_ids = set()
        owned = {}
        for handle in app.ed_handles():
            editor = app.Editor(handle)
            tab_id = self._tab_id(editor)
            if tab_id is None:
                continue
            live_ids.add(tab_id)
            self._refresh(editor)
            if self._is_memo(editor):
                record = self._owned_title(editor, tab_id)
                if record is not None:
                    owned[tab_id] = record
        self.owned = owned
        try:
            save_records(self.state_path, live_ids, owned)
        except OSError as error:
            print("Auto Tab Title: could not save session metadata:", error)

    def on_start2(self, editor):
        self._restore()

    def on_change_slow(self, editor):
        self._refresh(editor)

    def on_tab_change(self, editor):
        self._refresh(editor)

    def on_tab_move(self, editor):
        # on_close also fires during shutdown, before the session is saved.
        # on_tab_move runs after actual removal from the tab bar.
        if self.owned:
            live_ids = {self._tab_id(app.Editor(handle)) for handle in app.ed_handles()}
            self.owned = {tab_id: record for tab_id, record in self.owned.items()
                          if tab_id in live_ids}

    def on_state(self, editor, state):
        if state == app.APPSTATE_SESSION_LOAD:
            self.owned.clear()
            self._restore()
        elif state == app.APPSTATE_SESSION_SAVE_BEFORE:
            self._save_session()

    def on_state_ed(self, editor, state):
        if state == app.EDSTATE_TAB_TITLE:
            tab_id = self._tab_id(editor)
            if tab_id not in self.setting_title:
                self.owned.pop(tab_id, None)

    def on_save(self, editor):
        # CudaText has already switched a newly saved tab to its filename.
        if editor.get_prop(app.PROP_FN):
            self.owned.pop(self._tab_id(editor), None)

    def _command_target(self, editor):
        if self.paused or not self.settings.enabled:
            app.msg_status("Auto Tab Title is disabled.")
            return None
        target = self._target(editor)
        if target is None:
            app.msg_status("Auto Tab Title: select an unsaved memo without another custom title.")
        return target

    def rename_current_tab(self):
        target = self._command_target(app.ed)
        if target is None:
            return
        tab_id, record = target
        default = app.ed.get_prop(app.PROP_TAB_TITLE)
        if record is not None:
            default = "*" * record.stars + default
        title = app.dlg_input("Rename Current Tab", default)
        if title is None:
            return
        title = " ".join(title.splitlines()).replace("\x00", "").strip()
        if not title:
            app.msg_status("Auto Tab Title: enter a non-empty title.")
            return
        # The modal dialog can run other plugin callbacks.
        if self._target(app.ed) == target:
            self._set_title(app.ed, tab_id, record, title, manual=True)

    def reset_tab_title_to_auto(self):
        target = self._command_target(app.ed)
        if target is None:
            return
        tab_id, record = target
        title = extract_title(app.ed.get_text_line, self.settings)
        self._set_title(app.ed, tab_id, record, title)

    def restore_default_titles(self):
        self.paused = True
        for handle in app.ed_handles():
            editor = app.Editor(handle)
            if self._is_memo(editor):
                tab_id = self._tab_id(editor)
                self._set_title(editor, tab_id, self._owned_title(editor, tab_id), "")
        app.msg_status("Auto Tab Title: default titles restored. Automatic updates paused until restart.")
