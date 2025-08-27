import tkinter as tk
from tkinter import messagebox, ttk

import difftool
import db.db_workspaces as dbws
import db.db_user_settings as dbus
import const

class SelectWorkspaceModal(tk.Toplevel):
    def __init__(self, parent, callback):
        super().__init__(parent)
        self.title(f"{const.APP_NAME}：ワークスペースの選択")
        self.geometry("500x150")
        self.transient(parent)
        self.callback = callback
        self.grab_set()

        label = ttk.Label(
            self,
            text="ワークスペースを選択してください\n新しいワークスペースを利用する場合は、ワークスペース名を入力してください",
        )
        label.pack(expand=True)

        self.workspace_combo = ttk.Combobox(self)
        self.workspace_combo.pack(expand=True)
        self.workspace_combo["values"] = self._get_ws_list()

        self.default_ws_selected = tk.BooleanVar()
        self.checkbox = tk.Checkbutton(
            self,
            text="起動時のデフォルトのワークスペースとする",
            variable=self.default_ws_selected,
        )
        self.checkbox.pack()

        ws_select_button = ttk.Button(self, text="選択", command=self._select_workspace)
        ws_select_button.pack(expand=True)
        # バツボタンクリック時のハンドラ
        self.protocol("WM_DELETE_WINDOW", self._click_close)
        self.wait_window()

    def _get_ws_list(self):
        db = dbws.DbWorkspace()
        return db.get_workspace_name_list()

    def _select_workspace(self):
        ws_name = self.workspace_combo.get()
        if ws_name != "":
            # ワークスペースを名前だけ保存
            dbw = dbws.DbWorkspace()
            dbw.insert_workspace_name(
                ws_name
            )
            db = dbus.DbUserSettings()
            db.update_or_insert_user_settings("current_workspace", ws_name)

            # チェックがあるときはデフォルトワークスペースとしてDBのユーザ設定に登録
            if self.default_ws_selected.get():
                db.update_or_insert_user_settings("default_workspace", ws_name)
            else:
                db.update_or_insert_user_settings("default_workspace", "")
            # メインウィンドウにワークスペース選択をコールバック
            self.callback(difftool.CALLBACK_SELECTED_WS)
            self.destroy()
        else:
            messagebox.showerror(
                "エラー", "ワークスペース名を選択するか入力してください！"
            )

    def _click_close(self):
        """
        バツボタンクリックイベント
        """
        self.destroy()
        self.callback(difftool.CALLBACK_UNSELECTED_WS)
