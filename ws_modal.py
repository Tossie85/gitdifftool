import tkinter as tk
from tkinter import filedialog, messagebox, ttk

import database

class SelectWorkspaceModal(tk.Toplevel):
    def __init__(self, parent):
        super().__init__(parent)
        self.title('git差分ファイルツール：ワークスペースの選択')
        self.geometry("500x150")
        self.transient(parent)
        self.grab_set()

        label = ttk.Label(self, text="ワークスペースを選択してください\n新しいワークスペースを利用する場合は、ワークスペース名を入力してください")
        label.pack(expand=True)

        self.workspace_combo = ttk.Combobox(self)
        self.workspace_combo.pack(expand=True)
        self.workspace_combo['values'] = self._get_ws_list()

        ws_select_button = ttk.Button(self, text="選択", command=self._select_workspace)
        ws_select_button.pack(expand=True)
        # バツボタンクリック時のハンドラ
        self.protocol("WM_DELETE_WINDOW", self._click_close)
        self.wait_window()

    def _get_ws_list(self):
        db = database.Database()
        return db.get_workspace_name_list()
    
    def _select_workspace(self):
        ws_name = self.workspace_combo.get()
        if ws_name != '':
            db = database.Database()
            db.update_or_insert_user_settings('current_workspace',ws_name)
            self.destroy()
        else:
            messagebox.showerror("エラー", "ワークスペース名を選択するか入力してください！")
    
    def _click_close(self):
        db = database.Database()
        db.update_or_insert_user_settings('current_workspace','')
        self.destroy()