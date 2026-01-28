# -*- coding: utf-8 -*-
import threading
import queue
import os
import shutil
import subprocess
import tkinter as tk
from tkinter import filedialog, messagebox, ttk, scrolledtext
from datetime import datetime
import re
import db.db_workspaces as dbws
import db.db_branches as dbbr
import db.db_commits as dbco
import db.db_user_settings as dbus
import db.db_excluded_path as dbexp
from modal import user_settings_modal
import modal.ws_modal as ws_modal
import modal.copy_ignore_list_modal as copy_ignore_list_modal
import const

CALLBACK_SELECTED_WS = "selected_ws"
CALLBACK_UNSELECTED_WS = "unselected_ws"
CALLBACK_SET_WS = "set_ws"
CALLBACK_UNSET_WS = "unset_ws"

SELECT_DIFF_BRANCH = 0
SELECT_DIFF_COMMIT = 1
SELECT_DIFF_PRECOMMIT = 2


class GitDiffApp(tk.Tk):
    def __init__(self):
        self.root = super()
        super().__init__()
        # self.root = root
        self.title(f"{const.APP_NAME}")
        # キュー（ログや進行状況をスレッドから受け取る）
        self.log_queue = queue.Queue()
        # ウィジットの生成
        self._create_widgets()
        # データ初期化
        self._data_init()
        # ワークスペース選択モーダルの表示
        self.default_ws = ""
        db = dbus.DbUserSettings()
        if db.exists_user_setting_info(const.US_KEY_DEFAULT_WS):
            self.default_ws = db.get_user_setting(const.US_KEY_DEFAULT_WS)
        if self.default_ws == "":
            self.show_select_workspace_modal()
        else:
            self.ws_name = self.default_ws
            self.load_settings()

        self.progress_queue = queue.Queue()
        # 定期的にログをチェック
        self.after(100, self.update_log)

    def _data_init(self):
        """
        各種変数の初期化
        """
        self.repo_path = ""
        self.output_path = ""
        self.diff_dir = ""
        self.ws_name = ""
        self.branch1_combo.set("")
        self.branch2_combo.set("")
        # 処理中フラグ
        self.is_running = False
        # 一時停止処理のためのイベント
        self.paused = threading.Event()
        self.paused.set()
        self.is_abandoned = False # 中断フラグ

    def load_settings(self):
        """
        設定の読み込み
        """
        # 読み込む前にいったん初期化
        self._data_init()

        # データベースの各インスタンスを生成する
        dbb = dbbr.DbBranch()
        dbc = dbco.DbCommit()
        dbw = dbws.DbWorkspace()
        dbu = dbus.DbUserSettings()

        self.ws_name = dbu.get_user_setting(dbws.KEY_WORKSPACE)
        if self.ws_name != "":
            # ワークスペース名をキーにブランチ情報を取得する
            branches = dbb.get_branches(self.ws_name)
            # ブランチ情報をコンボボックスにセットする
            self.branch1_combo["values"] = branches
            self.branch2_combo["values"] = branches
            # ワークスペース名をキーにコミット情報を取得する
            commits = dbc.get_commits(self.ws_name)
            # コミット情報をコンボボックスにセットする
            self.commit1_combo["values"] = commits
            self.commit2_combo["values"] = commits

            ws_info = dbw.get_workspace_settings(self.ws_name)
            # gitフォルダ情報
            self.repo_path = ws_info[dbws.KEY_REPO_PATH]
            self.git_folder_entry.delete(0, tk.END)
            if self.repo_path:
                self.git_folder_entry.insert(0, self.repo_path)
            # 出力フォルダ情報
            self.output_path = ws_info[dbws.KEY_OUTPUT_PATH]
            self.output_folder_entry.delete(0, tk.END)
            if self.output_path:
                self.output_folder_entry.insert(0, self.output_path)

            self.title(f"{const.APP_NAME}(Ver.{const.VERSION}):[{self.ws_name}]")

    def save_settings(self):
        """
        ワークスペース設定を保存する
        """
        dbw = dbws.DbWorkspace()
        dbw.update_or_insert_workspace_settings(
            self.ws_name, self.repo_path, self.output_path
        )

    def _create_widgets(self):
        """
        ウィジットを生成する
        """
        tk.Label(self, text="gitフォルダ", width=12).grid(
            row=0, column=0, padx=5, pady=2
        )
        # gitフォルダ選択テキスト
        self.git_folder_entry = tk.Entry(self, width=74)
        self.git_folder_entry.grid(row=0, column=1, columnspan=5, padx=5, pady=2)
        
        # gitフォルダ選択ボタン
        self.select_git_folder_button = tk.Button(self, text="選択", command=self.select_git_folder, width=10)
        self.select_git_folder_button.grid(row=0, column=6, padx=5, pady=2)

        tk.Label(self, text="出力フォルダ", width=12).grid(row=1, column=0, padx=5, pady=2)

        # 出力先フォルダ選択テキスト
        self.output_folder_entry = tk.Entry(self, width=74)
        self.output_folder_entry.grid(row=1, column=1, columnspan=5, padx=5, pady=2)
        # 出力先フォルダ選択ボタン
        self.select_output_folder_button = tk.Button(self, text="選択", command=self.select_output_folder, width=10)
        self.select_output_folder_button.grid(row=1, column=6, padx=5, pady=2)

        tk.Label(self, text="ブランチ情報", width=12).grid(
            row=3, column=0, padx=5, pady=2
        )
        self.branch1_combo = ttk.Combobox(self, width=74)
        self.branch1_combo.grid(row=3, column=1, columnspan=5, padx=5, pady=2)
        self.branch2_combo = ttk.Combobox(self, width=74)
        self.branch2_combo.grid(row=4, column=1, columnspan=5, padx=5, pady=2)
        # ブランチ更新ボタン
        self.update_branch_button = tk.Button(self, text="ブランチ更新", command=self.update_branches, height=2, width=10)
        self.update_branch_button.grid(row=3, column=6, rowspan=2, padx=5, pady=2)

        tk.Label(self, text="コミット情報", width=12).grid(row=5, column=0, padx=5, pady=2)
        
        self.commit1_combo = ttk.Combobox(self, width=74)
        self.commit1_combo.grid(row=5, column=1, columnspan=5, padx=5, pady=2)
        self.commit2_combo = ttk.Combobox(self, width=74)
        self.commit2_combo.grid(row=6, column=1, columnspan=5, padx=5, pady=2)
        # コミット更新ボタン
        self.update_commit_button = tk.Button(
            self, text="コミット更新", command=self.update_commits, height=2, width=10
        )
        self.update_commit_button.grid(row=5, column=6, rowspan=2, padx=5, pady=2)

        self.diff_radio_value = tk.IntVar(value=SELECT_DIFF_BRANCH)
        tk.Label(self, text="比較", width=12).grid(row=7, column=0, padx=5, pady=2)
        
        self.branch_radio = ttk.Radiobutton(
            self,
            text="ブランチ間比較",
            value=SELECT_DIFF_BRANCH,
            variable=self.diff_radio_value,
        )
        self.branch_radio.grid(row=7, column=1, padx=5, pady=2)
        
        self.commit_radio = ttk.Radiobutton(
            self,
            text="コミット間比較",
            value=SELECT_DIFF_COMMIT,
            variable=self.diff_radio_value,
        )
        self.commit_radio.grid(row=7, column=2, padx=5, pady=2)

        self.uncommitted_radio = ttk.Radiobutton(
            self,
            text="未コミット比較",
            value=SELECT_DIFF_PRECOMMIT,
            variable=self.diff_radio_value,
        )
        self.uncommitted_radio.grid(row=7, column=3, padx=5, pady=2)
        # 一時停止ボタン
        self.pause_button = tk.Button(self, text="一時停止", command=self.pause, width=10)
        self.pause_button.grid(row=8, column=1, padx=5, pady=2)    
        # 再開ボタン
        self.restart_button = tk.Button(self, text="再開", command=self.resume, width=10)
        self.restart_button.grid(row=8, column=2, padx=5, pady=2)
        # 停止ボタン
        self.stop_button = tk.Button(self, text="中断", command=self.stop, width=10)
        self.stop_button.grid(row=8, column=3, padx=5, pady=2)
        # 実行ボタン
        self.execute_button = tk.Button(self, text="実行", command=self.execute, width=10)
        self.execute_button.grid(row=8, column=6, padx=5, pady=2)

        # ログ表示（リアルタイム追記用）
        self.log_text = scrolledtext.ScrolledText(self, height=20, state="disabled")
        self.log_text.grid(row=9, column=0, columnspan=7, padx=5, pady=2)

        # 結果を開くボタン
        self.show_result_button = tk.Button(self, text="結果を開く", command=self.open_result, width=10)
        self.show_result_button.grid(row=10, column=0, padx=5, pady=2)

        # ログクリアボタン
        self.clear_log_button = tk.Button(self, text="ログクリア", command=self.clear_log, width=10)
        self.clear_log_button.grid(row=10, column=5, padx=5, pady=2)

        # ログ保存ボタン
        self.save_log_button = tk.Button(self, text="ログ保存", command=self.save_log, width=10)
        self.save_log_button.grid(row=10, column=6, padx=5, pady=2)

        # メニューの設定
        self.create_menus()

        # ウィンドウサイズ変更抑止
        self.resizable(0, 0)
        # ウィンドウサイズと位置の設定
        self.geometry(f"+{const.MAIN_GEO['x']}+{const.MAIN_GEO['y']}")

        self._set_waiting_status()


    def create_menus(self):
        """
        メニューの設定
        """
        self.menubar = tk.Menu(self)
        self.config(menu=self.menubar)
        self.setting_menu = tk.Menu(self.menubar, tearoff=False)
        self.menubar.add_cascade(label="設定", menu=self.setting_menu)
        # ワークスペースメニュ
        workspace_menu = tk.Menu(self.setting_menu, tearoff=False)
        self.setting_menu.add_cascade(label=const.TITLE_WORKSPACE, menu=workspace_menu)
        # メニュにアクションを追加
        workspace_menu.add_command(
            label=f"{const.TITLE_SELECT_WORKSPACE}",
            command=self.show_select_workspace_modal,
        )
        workspace_menu.add_command(
            label=f"{const.TITLE_EXCLUDE_SETTING}",
            command=self.show_copy_ignore_list_setting_modal,
        )
        self.setting_menu.add_command(
            label=f"{const.TITLE_USER_SETTINGS}",
            command=self.show_user_settings_modal,
        )

    def _set_execute_status(self):
        """
        実行時状態
        """

        self.git_folder_entry.config(state = tk.DISABLED)
        self.select_git_folder_button.config(state = tk.DISABLED)
        
        self.output_folder_entry.config(state = tk.DISABLED)
        self.select_output_folder_button.config(state = tk.DISABLED)
        
        self.branch1_combo.config(state = tk.DISABLED)
        self.branch2_combo.config(state = tk.DISABLED)
        self.update_branch_button.config(state = tk.DISABLED)

        self.commit1_combo.config(state = tk.DISABLED)
        self.commit2_combo.config(state = tk.DISABLED)
        self.update_commit_button.config(state = tk.DISABLED)

        self.branch_radio.config(state = tk.DISABLED)
        self.commit_radio.config(state = tk.DISABLED)
        self.uncommitted_radio.config(state = tk.DISABLED)

        self.pause_button.config(state = tk.NORMAL)
        self.restart_button.config(state = tk.NORMAL)
        self.stop_button.config(state = tk.NORMAL)

        self.execute_button.config(state = tk.DISABLED)
        self.show_result_button.config(state = tk.DISABLED)
        self.clear_log_button.config(state = tk.DISABLED)
        self.save_log_button.config(state = tk.DISABLED)

    def _set_waiting_status(self):
        """
        待機状態
        """
        self.git_folder_entry.config(state = tk.NORMAL)
        self.select_git_folder_button.config(state = tk.NORMAL)
        
        self.output_folder_entry.config(state = tk.NORMAL)
        self.select_output_folder_button.config(state = tk.NORMAL)
        
        self.branch1_combo.config(state = tk.NORMAL)
        self.branch2_combo.config(state = tk.NORMAL)
        self.update_branch_button.config(state = tk.NORMAL)

        self.commit1_combo.config(state = tk.NORMAL)
        self.commit2_combo.config(state = tk.NORMAL)
        self.update_commit_button.config(state = tk.NORMAL)
        
        self.branch_radio.config(state = tk.NORMAL)
        self.commit_radio.config(state = tk.NORMAL)
        self.uncommitted_radio.config(state = tk.NORMAL)

        self.pause_button.config(state = tk.DISABLED)
        self.restart_button.config(state = tk.DISABLED)
        self.stop_button.config(state = tk.DISABLED)

        self.execute_button.config(state = tk.NORMAL)
        self.show_result_button.config(state = tk.NORMAL)
        self.clear_log_button.config(state = tk.NORMAL)
        self.save_log_button.config(state = tk.NORMAL)

    def show_select_workspace_modal(self):
        """
        ワークスペース選択モーダルを開く
        """
        x_origin = self.winfo_x() if self.winfo_x() > 0 else const.MAIN_GEO['x']
        y_origin = self.winfo_y() if self.winfo_y() > 0 else const.MAIN_GEO['y']
        xpos = x_origin + const.MAIN_GEO['width'] // 2 - const.WS_GEO['width'] // 2
        ypos = y_origin + const.MAIN_GEO['height'] // 2 - const.WS_GEO['height'] // 2
        self.ws_modal = ws_modal.SelectWorkspaceModal(self, self.after_ws_modal, xpos, ypos)

    def show_copy_ignore_list_setting_modal(self):
        """
        コピー対象外パス設定モーダルを開く
        """
        x_origin = self.winfo_x() if self.winfo_x() > 0 else const.MAIN_GEO['x']
        y_origin = self.winfo_y() if self.winfo_y() > 0 else const.MAIN_GEO['y']
        xpos = x_origin + const.MAIN_GEO['width'] // 2 - const.EXC_GEO['width'] // 2
        ypos = y_origin + const.MAIN_GEO['height'] // 2 - const.EXC_GEO['height'] // 2
        self.exclude_modal = copy_ignore_list_modal.SettingCopyIgnoreListModal(self, self.after_copy_ignore_list_setting_modal, xpos, ypos)

    def show_user_settings_modal(self):
        """
        ユーザー設定モーダルを開く
        """
        x_origin = self.winfo_x() if self.winfo_x() > 0 else const.MAIN_GEO['x']
        y_origin = self.winfo_y() if self.winfo_y() > 0 else const.MAIN_GEO['y']
        xpos = x_origin + const.MAIN_GEO['width'] // 2 - const.US_GEO['width'] // 2
        ypos = y_origin + const.MAIN_GEO['height'] // 2 - const.US_GEO['height'] // 2
        self.user_modal = user_settings_modal.UserSettingsModal(self, self.after_user_modal,xpos, ypos)
        
    def after_ws_modal(self, value):
        """
        ワークスペース選択モーダルコールバック
        """
        if value == CALLBACK_SELECTED_WS:
            self.load_settings()
        if value == CALLBACK_UNSELECTED_WS:
            if self.ws_name == "":
                self.destroy()

    def after_copy_ignore_list_setting_modal(self, value):
        """
        コピー対象外パス設定モーダルコールバック
        """
        if value == CALLBACK_SET_WS:
            self.log_queue.put(f"インフォ - :除外パス設定完了")
        if value == CALLBACK_UNSET_WS:
            self.log_queue.put(f"インフォ - :除外パス設定キャンセル")

    def after_user_modal(self, value):
        """
        ユーザー設定モーダルコールバック
        """
        if value == CALLBACK_SET_WS:
            self.log_queue.put(f"インフォ - :ユーザー設定完了")
        if value == CALLBACK_UNSET_WS:
            self.log_queue.put(f"インフォ - :ユーザー設定キャンセル")

    def log(self, message):
        """
        UIスレッドからログ書き込み
        """
        self.log_text.config(state="normal")
        self.log_text.insert(tk.END, message + "\n")
        self.log_text.yview(tk.END)
        self.log_text.config(state="disabled")
        self.log_text.update_idletasks()

    def update_log(self):
        """
        スレッドからのメッセージを処理
        """
        while not self.log_queue.empty():
            message = self.log_queue.get()
            self.log(message)
        self.after(100, self.update_log)

    def select_git_folder(self):
        """
        gitディレクトリを選択する
        """
        path = filedialog.askdirectory(initialdir=self.repo_path or os.getcwd())
        if path and os.path.isdir(os.path.join(path, ".git")):
            self.repo_path = path
            self.git_folder_entry.delete(0, tk.END)
            self.git_folder_entry.insert(0, path)
        else:
            messagebox.showerror("エラー", ".gitが見つかりません")

    def select_output_folder(self):
        """
        出力先ディレクトリを選択する
        """
        path = filedialog.askdirectory(initialdir=self.output_path or os.getcwd())
        if path:
            self.output_path = path
            self.output_folder_entry.delete(0, tk.END)
            self.output_folder_entry.insert(0, path)

    def update_branches(self):
        """
        ブランチ情報の更新
        git branchコマンドで取得し、DBに保存する
        """
        if not self.repo_path:
            messagebox.showerror("エラー", "Gitフォルダを選択してください")
            return
        try:
            result = subprocess.check_output(
                ["git", "branch"],
                cwd=self.repo_path,
                text=True,
                creationflags=subprocess.CREATE_NO_WINDOW,
            )
            branches = [
                line.strip().lstrip("* ").strip() for line in result.splitlines()
            ]
            self.branch1_combo["values"] = branches
            self.branch2_combo["values"] = branches
            db = dbbr.DbBranch()
            db.update_branches(self.ws_name, branches)
            self.log_queue.put("ブランチ一覧を更新しました")
        except Exception as e:
            messagebox.showerror("エラー", str(e))
            self.log_queue.put(f"ブランチ取得エラー: {e}")

    def update_commits(self):
        """
        コミット情報の更新
        git logコマンドで取得し、DBに保存する
        """
        if not self.repo_path:
            messagebox.showerror("エラー", "Gitフォルダを選択してください")
            return
        try:
            command = ["git", "log"]
            # マージコミット除外設定
            if dbus.DbUserSettings().exists_user_setting_info(const.US_KEY_MERGE_OPTION):
                merge_option = dbus.DbUserSettings().get_user_setting(const.US_KEY_MERGE_OPTION)
                if int(merge_option) == const.WITHOUT_MERGE_COMMITS:
                    command.append("--no-merges")
                elif int(merge_option) == const.ONLY_MERGE_COMMITS:
                    command.append("--merges")     
            # 出力フォーマット(%h: ハッシュ, %cd: 日付, %s: サマリ, %an: 作者名)
            foption = f"--pretty=format:%h|||%cd|||%s|||%an"
            command.append(foption)
            # 日付のフォーマット(YYYY-MM-DD HH:MM:SS)
            doption = f"--date=format:%Y-%m-%d %H:%M:%S"
            command.append(doption)
            # 取得件数
            noption = f"-n {dbus.DbUserSettings().get_user_setting(const.US_KEY_COMMIT_NUM)}" if dbus.DbUserSettings().exists_user_setting_info(const.US_KEY_COMMIT_NUM) else f"-n {const.DIFF_FILE_NUM_LIMIT}"
            command.append(noption)
            # 全ブランチ
            boption = f"--all"
            command.append(boption)

            # encodingオプションをつけないとエラーになる（cp932）
            result = subprocess.check_output(
                command,
                cwd=self.repo_path,
                text=True,
                encoding="utf-8",
                creationflags=subprocess.CREATE_NO_WINDOW,
            )
            commit_lines = [line for line in result.splitlines()]
            commits = []
            for commit in commit_lines:
                commits.append(commit.split("|||"))

            if commits:
                db = dbco.DbCommit()
                db.update_commit_logs(self.ws_name, commits)
                result = db.get_commits(self.ws_name)
                self.commit1_combo["values"] = result
                self.commit2_combo["values"] = result
                self.log_queue.put("コミット一覧を更新しました")
            else:
                self.log_queue.put("条件に合うコミットが存在しませんでした。ユーザ設定を確認してください。")
        except Exception as e:
            messagebox.showerror("エラー", str(e))
            self.log_queue.put(f"コミットログ取得エラー: {e}")

    def get_commits(self):
        db = dbco.DbCommit()
        commits = db.get_commits(self.ws_name)
        print(commits)

    def execute(self):
        """
        差分一覧と差分ファイル一式のコピー
        TODO: gitコマンドの実行ログを出力する
        TODO: gitコマンドの実行でエラーが発生したときのエラー処理を追加する
        """
        if self.is_running:
            messagebox.showinfo("情報", "現在処理中です。しばらくお待ちください。")
            return
        self._set_execute_status()

        # 処理中フラグを立てる
        self.is_running = True
        self.is_abandoned = False # 中断フラグを解除
        self.paused.set()  # 一時停止解除

        try:
            self.repo_path = self.git_folder_entry.get()
            self.output_path = self.output_folder_entry.get()
            self.save_settings()
            branch1, branch2 = self.branch1_combo.get(), self.branch2_combo.get()
            commit1, commit2 = self.commit1_combo.get(), self.commit2_combo.get()

            if not os.path.isdir(self.repo_path):
                raise ValueError("Gitフォルダが無効です")
            if not os.path.isdir(os.path.join(self.repo_path, ".git")):
                raise ValueError(".gitが存在しません")
            if not os.path.isdir(self.output_path):
                raise ValueError("出力フォルダが無効です")
            diff_ways = self.diff_radio_value.get()
            if diff_ways == SELECT_DIFF_BRANCH:
                if branch1 == branch2:
                    raise ValueError("異なるブランチを選択してください")
            elif diff_ways == SELECT_DIFF_COMMIT:
                if commit1 == commit2:
                    raise ValueError("異なるコミットを選択してください")

            now = datetime.now().strftime("%Y%m%d_%H%M%S")
            self.diff_dir = os.path.join(self.output_path, now)
            os.makedirs(self.diff_dir, exist_ok=True)

            if diff_ways == SELECT_DIFF_BRANCH:
                safe_branch1 = re.sub(r"[^\w.-]", "-", branch1)
                safe_branch2 = re.sub(r"[^\w.-]", "-", branch2)
                diff_file = os.path.join(
                    self.diff_dir, f"diff_{safe_branch1}_{safe_branch2}.txt"
                )
                diff1, diff2 = branch1, branch2
            elif diff_ways == SELECT_DIFF_COMMIT:
                safe_commit1 = commit1[:7].split()
                safe_commit2 = commit2[:7].split()
                diff1, diff2 = safe_commit1[0], safe_commit2[0]
                diff_file = os.path.join(self.diff_dir, f"diff_{diff1}_{diff2}.txt")
            elif diff_ways == SELECT_DIFF_PRECOMMIT:
                # diff1, diff2 = "HEAD", ""
                diff_file = os.path.join(self.diff_dir, f"diff_local_changed.txt")


            # 重い処理は別スレッドで実行
            if diff_ways != SELECT_DIFF_PRECOMMIT:
                print(diff_file)
                threading.Thread(
                    target=self._execute_worker,
                    args=(diff1, diff2, diff_file),
                    daemon=True,
                ).start()
            else:
                threading.Thread(
                    target=self._execute_worker_local, args=(diff_file,), daemon=True
                ).start()
        except Exception as e:
            if self.is_running:
                self.is_running = False
                self.is_abandoned = True # 中断フラグを立てる
                self.paused.set()  # 一時停止解除
                self._set_waiting_status()
            messagebox.showerror("エラー", str(e))
            self.log_queue.put(f"実行エラー: {e}")

    def pause(self):
        """
        処理の一時停止
        """
        if self.is_running:
            self.paused.clear()  # 一時停止
            self.log_queue.put("処理を一時停止しました")
    
    def resume(self):
        """
        処理の再開
        """
        if self.is_running:
            self.paused.set()  # 再開
            self.log_queue.put("処理を再開しました")
    
    def stop(self):
        """
        処理の中断
        """
        if self.is_running:
            self.is_running = False
            self.is_abandoned = True # 中断フラグを立てる
            self.paused.set()  # 一時停止解除
            self.log_queue.put("処理を中断しました")

    def _execute_worker(self, diff1, diff2, diff_file):
        try:
            # 実行時状態にする
            self._set_execute_status()
            # 差分一覧ファイルを作成
            param = ["git", "diff", "--name-only", diff1, diff2]
            with open(diff_file, "w", encoding="utf-8") as df:
                subprocess.run(
                    param,
                    cwd=self.repo_path,
                    text=True,
                    stdout=df,
                    check=False,
                    creationflags=subprocess.CREATE_NO_WINDOW,
                )
            self.log_queue.put(f"差分ファイル出力: {diff_file}")

            # 差分ファイルの行数確認
            lines = self._get_file_lines(diff_file)
            if not self._confirm_get_diff_files(lines):
                return
            # コミット1のコピー
            self.file_copy_from_commit(diff1, diff_file)
            # コミット2のコピー
            self.file_copy_from_commit(diff2, diff_file)

            # 完了通知
            self.is_running = False
            if self.is_abandoned:
                self.log_queue.put("処理が中断されました")
                return
            
            self.log_queue.put("完了しました")
            self.log_queue.put(self.diff_dir)
            # 待機状態に戻す
            self._set_waiting_status()

            if messagebox.askyesno(
                "完了", f"作業フォルダを開きますか？\n{self.diff_dir}"
            ):
                self.open_result()
        except Exception as e:
            self.log_queue.put(str(e))

    def _execute_worker_local(self, diff_file):
        """
        未コミットのローカル差分生成用
        """
        try:
            # 差分一覧ファイルを作成
            param = ["git", "status", "--untracked-files=all", "--porcelain"]

            result = subprocess.run(
                param,
                cwd=self.repo_path,
                text=True,
                check=False,
                capture_output=True,
                creationflags=subprocess.CREATE_NO_WINDOW,
            ).stdout
            files = []
            for line in result.splitlines():
                files.append(line[3:])

            with open(diff_file, "w", encoding="utf-8") as df:
                for f in files:
                    df.write(f + "\n")

            self.log_queue.put(f"差分ファイル出力: {diff_file}")

            # 差分ファイルの行数確認
            lines = self._get_file_lines(diff_file)
            if not self._confirm_get_diff_files(lines):
                return

            # HEADのコピー
            self.file_copy_from_commit("HEAD", diff_file)
            # ローカルのコピー
            self.file_copy_from_local(diff_file)

            # 完了通知
            self.is_running = False
            if self.is_abandoned:
                self.log_queue.put("処理が中断されました")
                return
            self.log_queue.put("完了しました")
            self.log_queue.put(self.diff_dir)
            # 待機状態に戻す
            self._set_waiting_status()

            if messagebox.askyesno(
                "完了", f"作業フォルダを開きますか？\n{self.diff_dir}"
            ):
                self.open_result()
        except Exception as e:
            self.log_queue.put(str(e))

    def file_copy_from_local(self, diff_file):
        """
        ローカルのファイルをそのままコピーする
        未コミットの変更をコピーするため
        """
        with open(diff_file, encoding="utf-8") as f:
            rel_paths = [line.strip() for line in f if line.strip()]
        dbex = dbexp.DbExcludedPath()
        exclude_path = dbex.get_excluded_paths(self.ws_name)
        exclude_path += const.EXCEPT_PATH
        for path in rel_paths:
            if self.is_running is False:
                return
            self.paused.wait()  # 一時停止中はここで待機
            # 除外対象はスキップ
            if any(ex in path for ex in exclude_path):
                self.log_queue.put(f"{const.LOCAL_CHANGE}: スキップ - :除外対象文字列含む({path})")
                continue
            from_path = os.path.join(self.repo_path, path)
            target_file = os.path.join(self.diff_dir, const.LOCAL_CHANGE, path)
            os.makedirs(os.path.dirname(target_file), exist_ok=True)
            try:
                if os.path.exists(from_path):
                    shutil.copy2(from_path, target_file)
                    self.log_queue.put(
                        f"{const.LOCAL_CHANGE}: コピー成功 - {from_path}"
                    )
                else:
                    self.log_queue.put(
                        f"{const.LOCAL_CHANGE}: スキップ - {from_path} (存在しません)"
                    )
            except Exception as e:
                self.log_queue.put(f"スキップ - エラー：{e}({from_path})")

    def file_copy_from_commit(self, commit, diff_file):
        """
        コミット済みの内容からファイルをコピー
        """
        safe_branch = re.sub(r"[^\w.-]", "-", commit)
        branch_dir = os.path.join(self.diff_dir, safe_branch)
        os.makedirs(branch_dir, exist_ok=True)

        with open(diff_file, encoding="utf-8") as f:
            for line in f:
                if self.is_running is False:
                    return
                self.paused.wait()  # 一時停止中はここで待機
                rel_path = line.strip()
                branch_src = f"{commit}:{rel_path}"
                dest = os.path.join(branch_dir, rel_path)

                dbex = dbexp.DbExcludedPath()
                exclude_path = dbex.get_excluded_paths(self.ws_name)
                exclude_path += const.EXCEPT_PATH
                # 除外対象はスキップ
                if any(ex in rel_path for ex in exclude_path):
                    self.log_queue.put(f"{commit}: スキップ - :除外対象文字列含む({rel_path})")
                    continue

                try:
                    ret = (
                        subprocess.run(
                            ["git", "ls-tree", "--name-only", commit, "--", rel_path],
                            cwd=self.repo_path,
                            capture_output=True,
                            text=True,
                            creationflags=subprocess.CREATE_NO_WINDOW,
                        ).stdout
                        or ""
                    ).strip()

                    if ret == rel_path:
                        os.makedirs(os.path.dirname(dest), exist_ok=True)
                        subprocess.run(
                            ["git", "show", branch_src],
                            cwd=self.repo_path,
                            text=True,
                            stdout=open(dest, "w"),
                            creationflags=subprocess.CREATE_NO_WINDOW,
                        )
                        self.log_queue.put(f"{commit}: コピー成功 - {rel_path}")
                    else:
                        self.log_queue.put(
                            f"{commit}: スキップ - {rel_path} (存在しません)"
                        )
                except Exception as e:
                    self.log_queue.put(f"{commit}: コピー失敗 - {rel_path} ({e})")

    def checkout_and_copy(self, branch, diff_file):
        """
        ブランチを切り替えて差分ファイル記載のファイルをコピー
        deprecated : 現在はfile_copy_from_commitを使用
        しているため使用していない
        """
        safe_branch = re.sub(r"[^\w.-]", "-", branch)
        branch_dir = os.path.join(self.diff_dir, safe_branch)
        os.makedirs(branch_dir, exist_ok=True)

        subprocess.run(
            ["git", "switch", branch],
            cwd=self.repo_path,
            creationflags=subprocess.CREATE_NO_WINDOW,
        )

        with open(diff_file, encoding="utf-8") as f:
            for line in f:
                rel_path = line.strip()
                src = os.path.join(self.repo_path, rel_path)
                dest = os.path.join(branch_dir, rel_path)
                try:
                    if os.path.exists(src):
                        os.makedirs(os.path.dirname(dest), exist_ok=True)
                        shutil.copy2(src, dest)
                        self.log_queue.put(f"{branch}: コピー成功 - {rel_path}")
                    else:
                        self.log_queue.put(
                            f"{branch}: スキップ - {rel_path} (存在しません)"
                        )
                except Exception as e:
                    self.log_queue.put(f"{branch}: コピー失敗 - {rel_path} ({e})")

    def open_result(self):
        """
        最後の比較結果フォルダを開く
        """
        if self.diff_dir != "":
            os.startfile(self.diff_dir)
        elif not os.path.isdir(self.diff_dir):
            messagebox.showerror(
                "エラー", f"出力ディレクトリが存在しません\npath:{self.diff_dir}"
            )
            return
        else:
            self.log("まだ比較をしていません")
            messagebox.showerror("エラー", "まだ比較をしていません")

    def clear_log(self):
        """
        実行ログのクリア
        """
        self.log_text.config(state="normal")
        self.log_text.delete("1.0", tk.END)
        self.log_text.config(state="disabled")

    def save_log(self):
        """
        実行ログの保存
        """
        if not self.diff_dir:
            messagebox.showerror("エラー", "出力ディレクトリが未作成です")
            return
        if not os.path.isdir(self.diff_dir):
            messagebox.showerror(
                "エラー", f"出力ディレクトリが存在しません\npath:{self.diff_dir}"
            )
            return
        log_file = os.path.join(
            self.diff_dir, datetime.now().strftime("%Y%m%d%H%M%S") + ".log"
        )
        with open(log_file, "w", encoding="utf-8") as f:
            f.write(self.log_text.get("1.0", tk.END))
        self.log_queue.put(f"ログ出力: {log_file}")

    def _get_current_branch(self):
        """
        現在のブランチを取得
        """
        ret = subprocess.run(
            ["git", "branch", "--contains"],
            cwd=self.repo_path,
            capture_output=True,
            creationflags=subprocess.CREATE_NO_WINDOW,
        )
        tmp = ret.stdout
        return tmp.strip(b"* \n").decode("utf-8")

    def _get_file_lines(self, file_path):
        """
        gitコマンドで取得した差分ファイルの行数を取得
        """
        return sum(1 for line in open(file_path))

    def _confirm_get_diff_files(self, lines):
        """
        差分ファイルの件数を確認し、処理を続行するか確認

        Args:
            lines (int): 差分ファイルの行数 
        """
        limit = dbus.DbUserSettings().get_user_setting(const.US_KEY_DIFF_FILE_NUM) if dbus.DbUserSettings().exists_user_setting_info(const.US_KEY_DIFF_FILE_NUM) else const.DIFF_FILE_NUM_LIMIT
        if lines >= int(limit):
            if messagebox.askyesno(
                "確認", f"{lines}件の差分が見つかりました。処理を続行しますか？"
            ) is False:
                self.is_running = False
                self.is_abandoned = True
                self.log_queue.put("処理が中断されました")
                self._set_waiting_status()
                return False
            return True
        return True

if __name__ == "__main__":
    app = GitDiffApp()
    app.mainloop()
