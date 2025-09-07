import os
import tkinter as tk
from tkinter import messagebox, ttk,scrolledtext, messagebox

import difftool
import db.db_workspaces as dbws
import db.db_user_settings as dbus
import db.db_excluded_path as dbexp
import const

class SettingWorkspaceModal(tk.Toplevel):
    def __init__(self, parent, callback):
        super().__init__(parent)
        self.title(f"{const.APP_NAME}：{const.TITLE_EXCLUDE_SETTING}")
        # self.geometry("500x150")
        self.transient(parent)
        self.callback = callback
        self.grab_set()

        self._crate_widgets()
        self._load_settings()

        # バツボタンクリック時のハンドラ
        self.protocol("WM_DELETE_WINDOW", self._click_close)
        self.wait_window()

    def _crate_widgets(self):
        tk.Label(self, text="対象外とするパスの一部を改行区切りで入力してください。").grid(row=0, column=0, columnspan=5, padx=5,pady=5)
        self.exclude_list = scrolledtext.ScrolledText(self, height=20)
        self.exclude_list.grid(row=1, column=0,columnspan=10, padx=5,pady=5)

        ws_select_button = ttk.Button(self, text="設定", command=self._set_workspace_settings)
        ws_select_button.grid(row=2, column=9, padx=5,pady=5)

    def _get_ws_list(self):
        db = dbws.DbWorkspace()
        return db.get_workspace_name_list()

    def _set_workspace_settings(self):
        dbu = dbus.DbUserSettings()
        ws_name = dbu.get_user_setting(key=const.US_KEY_CURRENT_WS)
        
        if ws_name != "":
            excludes_raw = self.exclude_list.get("1.0", "end").strip().splitlines()

            db = dbexp.DbExcludedPath()
            db.update_excluded_paths(ws_name,excludes_raw)
        self.destroy()
        self.callback(difftool.CALLBACK_SET_WS)

    def _load_settings(self):
        dbu = dbus.DbUserSettings()
        ws_name = dbu.get_user_setting(key=const.US_KEY_CURRENT_WS)
        
        if ws_name != "":
            db = dbexp.DbExcludedPath()
            excludes = db.get_excluded_paths(ws_name)
            for ex in excludes:
                self.exclude_list.insert(tk.END,f"{ex}\n")

    def _click_close(self):
        """
        バツボタンクリックイベント
        """
        self.destroy()
        self.callback(difftool.CALLBACK_UNSET_WS)
