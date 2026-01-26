import os
import tkinter as tk
from tkinter import messagebox, ttk,scrolledtext, messagebox

import difftool
import db.db_workspaces as dbws
import db.db_user_settings as dbus
import db.db_excluded_path as dbexp
import const

class UserSettingsModal(tk.Toplevel):
    def __init__(self, parent, callback, xpos, ypos):
        super().__init__(parent)
        self.title(f"{const.TITLE_USER_SETTINGS}")
        # self.geometry("500x150")
        self.transient(parent)
        self.callback = callback
        self.grab_set()

        self._crate_widgets(xpos, ypos)
        self._load_settings()

        # バツボタンクリック時のハンドラ
        self.protocol("WM_DELETE_WINDOW", self._click_close)
        self.wait_window()

    def _crate_widgets(self, xpos, ypos):

        # コミット数設定
        frmCommitNum = tk.Frame(self)
        frmCommitNum.pack(fill=tk.X,expand=False)
        self.label_commit_num = tk.Label(frmCommitNum, text=const.LABEL_USER_SETTINGS_COMMIT_NUM,anchor=tk.W,justify=tk.LEFT,width=30)
        self.text_commit_num = tk.Text(frmCommitNum, height=1, width=10)
        self.label_commit_num.pack(side=tk.LEFT,fill=tk.X,expand=True, padx=5, pady=2)
        self.text_commit_num.pack(side=tk.RIGHT,fill=tk.X,expand=True, padx=5, pady=2)
        # 差分ファイル行数設定
        frmDiffFileNum = tk.Frame(self)
        frmDiffFileNum.pack(fill=tk.X,expand=False)
        self.label_diff_file_num = tk.Label(frmDiffFileNum, text=const.LABEL_USER_SETTINGS_DIFF_FILE_NUM,anchor=tk.W,justify=tk.LEFT,width=30)
        self.text_diff_file_num = tk.Text(frmDiffFileNum, height=1, width=10)
        self.label_diff_file_num.pack(side=tk.LEFT,fill=tk.X,expand=True, padx=5, pady=2)
        self.text_diff_file_num.pack(side=tk.RIGHT,fill=tk.X,expand=True, padx=5, pady=2)
        # マージコミット除外設定
        frmNoMerge = tk.Frame(self)
        frmNoMerge.pack(fill=tk.X,expand=False)
        self.is_no_merge_var = tk.IntVar()
        self.label_no_merge = tk.Label(frmNoMerge, text=const.LABEL_USER_SETTINGS_NO_MERGE,anchor=tk.W,justify=tk.LEFT,width=30)
        self.checkbox_no_merge = tk.Checkbutton(frmNoMerge, variable=self.is_no_merge_var)
        self.label_no_merge.pack(side=tk.LEFT,fill=tk.X,expand=True, padx=5, pady=2)
        self.checkbox_no_merge.pack(side=tk.RIGHT,fill=tk.X,expand=True, padx=5, pady=2)
        self.text_diff_file_num.pack(side=tk.RIGHT,fill=tk.X,expand=True, padx=5, pady=2)
        # 保存ボタン
        frmButton = tk.Frame(self)
        frmButton.pack(fill=tk.X, expand=False)
        btn_save = ttk.Button(frmButton, text=const.BUTTON_SAVE, command=self._on_save)
        btn_save.pack(side=tk.RIGHT, padx=5, pady=5)

        # ウィンドウサイズと位置の設定
        self.geometry(f"{const.US_GEO['width']}x{const.US_GEO['height']}+{xpos}+{ypos}")

    def _on_save(self):
        """
        保存ボタンクリックイベント
        """
        commit_nums_str = self.text_commit_num.get("1.0", "end").strip()
        diff_file_nums_str = self.text_diff_file_num.get("1.0", "end").strip()
        try:
            commit_nums = int(commit_nums_str)
            diff_file_nums = int(diff_file_nums_str)
        except ValueError:
            messagebox.showerror("エラー", "数値を入力してください。")
            return

        dbu = dbus.DbUserSettings()
        dbu.update_or_insert_user_settings(const.US_KEY_COMMIT_NUM, commit_nums)
        dbu.update_or_insert_user_settings(const.US_KEY_DIFF_FILE_NUM, diff_file_nums)
        dbu.update_or_insert_user_settings(const.US_KEY_NO_MERGE, self.is_no_merge_var.get())

        self.destroy()
        self.callback(difftool.CALLBACK_SET_WS)

    def _load_settings(self):
        dbu = dbus.DbUserSettings()
        # 取得コミット数設定
        if dbu.exists_user_setting_info(const.US_KEY_COMMIT_NUM):
            commit_nums = dbu.get_user_setting(key=const.US_KEY_COMMIT_NUM)
        else:
            commit_nums = const.DIFF_FILE_NUM_LIMIT
        # 差分ファイル行数設定
        if dbu.exists_user_setting_info(const.US_KEY_DIFF_FILE_NUM):
            diff_file_nums = dbu.get_user_setting(key=const.US_KEY_DIFF_FILE_NUM)
        else:
            diff_file_nums = const.DIFF_FILE_CONFIRM_LINES
        # マージコミット除外設定
        if dbu.exists_user_setting_info(const.US_KEY_NO_MERGE):
            no_merge = dbu.get_user_setting(key=const.US_KEY_NO_MERGE)
        else:
            no_merge = const.WITH_MERGE_COMMITS

        self.text_commit_num.delete("1.0", tk.END)
        self.text_commit_num.insert("1.0", str(commit_nums))
        self.text_diff_file_num.delete("1.0", tk.END)  
        self.text_diff_file_num.insert("1.0", str(diff_file_nums))
        self.is_no_merge_var.set(no_merge)

    def _click_close(self):
        """
        バツボタンクリックイベント
        """
        self.destroy()
        self.callback(difftool.CALLBACK_UNSET_WS)
