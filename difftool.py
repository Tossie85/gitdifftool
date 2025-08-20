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
import database
import ws_modal

CALLBACK_SELECTED_WS = 'selected_ws'
CALLBACK_UNSELECTED_WS = 'unselected_ws'

class GitDiffApp(tk.Tk):
    def __init__(self):
        self.root = super()
        super().__init__()
        # self.root = root
        self.title('Git Branch Diff Tool')
        # キュー（ログや進行状況をスレッドから受け取る）
        self.log_queue = queue.Queue()
        # データベースインスタンスの生成
        self.db = database.Database()
        # ウィジットの生成
        self._create_widgets()
        # データ初期化
        self._data_init()
        # ワークスペース選択モーダルの表示
        self.default_ws = ''
        if self.db.exists_user_setting_info('default_workspace'):
            self.default_ws = self.db.get_user_setting('default_workspace')
        if self.default_ws == '':
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
        self.repo_path = ''
        self.output_path = ''
        self.branches = []
        self.diff_dir = ''
        self.db_name = ''
        self.ws_name = ''
        self.branch1_combo.set('')
        self.branch2_combo.set('')

    def load_settings(self):
        """
        設定の読み込み
        """
        # 読み込む前にいったん初期化
        self._data_init()
        self.db_name = self.db.get_db_name
        if self.db_name != '':
            self.ws_name = self.db.get_user_setting(database.KEY_WORKSPACE)
            if self.ws_name != '':
                # ワークスペース名をキーにブランチ情報を取得する
                self.branches = self.db.get_branches(self.ws_name)
                # ブランチ情報をコンボボックスにセットする
                self.branch1_combo['values'] = self.branches
                self.branch2_combo['values'] = self.branches
                ws_info = self.db.get_workspace_settings(self.ws_name)
                self.repo_path = ws_info[database.KEY_REPO_PATH]
                if self.repo_path:
                    self.git_folder_entry.delete(0, tk.END)
                    self.git_folder_entry.insert(0, self.repo_path)

                self.output_path = ws_info[database.KEY_OUTPUT_PATH]
                if self.output_path:
                    self.output_folder_entry.delete(0, tk.END)
                    self.output_folder_entry.insert(0, self.output_path)

    def save_settings(self):
        """
        ワークスペース設定を保存する
        """
        self.db.update_or_insert_workspace_settings(self.ws_name,self.repo_path,self.output_path)

    def _create_widgets(self):
        """
        ウィジットを生成する
        """
        tk.Button(self, text="Gitフォルダ選択", command=self.select_git_folder).grid(row=0, column=0)
        self.git_folder_entry = tk.Entry(self, width=80)
        self.git_folder_entry.grid(row=0, column=1, columnspan=4)

        tk.Button(self, text="出力フォルダ選択", command=self.select_output_folder).grid(row=1, column=0)
        self.output_folder_entry = tk.Entry(self, width=80)
        self.output_folder_entry.grid(row=1, column=1, columnspan=4)

        tk.Button(self, text="ブランチ更新", command=self.update_branches).grid(row=2, column=0)
        self.branch1_combo = ttk.Combobox(self)
        self.branch1_combo.grid(row=2, column=1)
        self.branch2_combo = ttk.Combobox(self)
        self.branch2_combo.grid(row=2, column=2)

        tk.Button(self, text="実行", command=self.execute).grid(row=2, column=3)

        # ログ表示（リアルタイム追記用）
        self.log_text = scrolledtext.ScrolledText(self, height=20, state="disabled")
        self.log_text.grid(row=3, column=0, columnspan=5, padx=5, pady=5)

        tk.Button(self, text="ログクリア", command=self.clear_log).grid(row=4, column=3)
        tk.Button(self, text="ログ保存", command=self.save_log).grid(row=4, column=4)

        # メニューの設定
        menubar = tk.Menu(self)
        self.config(menu=menubar)
        setting_menu = tk.Menu(menubar, tearoff=False)
        menubar.add_cascade(label='設定', menu=setting_menu)
        # メニュにアクションを追加
        setting_menu.add_command(label='ワークスペース',command=self.show_select_workspace_modal)

    def show_select_workspace_modal(self):
        """
        ワークスペース選択モーダルを開く
        """
        self.ws_modal = ws_modal.SelectWorkspaceModal(self, self.after_ws_modal)
    
    def after_ws_modal(self, value):
        """
        ワークスペース選択モーダルコールバック
        """
        if value == CALLBACK_SELECTED_WS:
            self.load_settings()
        if value == CALLBACK_UNSELECTED_WS:
            if self.ws_name == '':
                self.destroy()
    
   
    def log(self, message):
        """
        UIスレッドからログ書き込み
        """
        self.log_text.config(state="normal")
        print(f"message:{message}")
        self.log_text.insert(tk.END, message + "\n")
        self.log_text.yview(tk.END)
        self.log_text.config(state="disabled")
        self.log_text.update_idletasks()

    def update_log(self):
        """スレッドからのメッセージを処理"""
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
        """
        if not self.repo_path:
            messagebox.showerror("エラー", "Gitフォルダを選択してください")
            return
        try:
            result = subprocess.check_output(["git", "branch"], cwd=self.repo_path, text=True)
            self.branches = [line.strip().lstrip('* ').strip() for line in result.splitlines()]
            self.branch1_combo['values'] = self.branches
            self.branch2_combo['values'] = self.branches
            self.db.update_branches(self.ws_name,self.branches)
            self.log_queue.put("ブランチ一覧を更新しました")
        except Exception as e:
            messagebox.showerror("エラー", str(e))
            self.log_queue.put(f"ブランチ取得エラー: {e}")

    def execute(self):
        """
        差分一覧と差分ファイル一式のコピー
        TODO: gitコマンドの実行ログを出力する
        TODO: gitコマンドの実行でエラーが発生したときのエラー処理を追加する
        """
        try:
            self.repo_path = self.git_folder_entry.get()
            self.output_path = self.output_folder_entry.get()
            self.save_settings()
            branch1, branch2 = self.branch1_combo.get(), self.branch2_combo.get()

            if not os.path.isdir(self.repo_path):
                raise ValueError("Gitフォルダが無効です")
            if not os.path.isdir(os.path.join(self.repo_path, ".git")):
                raise ValueError(".gitが存在しません")
            if not os.path.isdir(self.output_path):
                raise ValueError("出力フォルダが無効です")
            if branch1 == branch2:
                raise ValueError("異なるブランチを選択してください")

            now = datetime.now().strftime("%Y%m%d_%H%M%S")
            self.diff_dir = os.path.join(self.output_path, now)
            os.makedirs(self.diff_dir, exist_ok=True)

            safe_branch1 = re.sub(r'[^\w.-]', '-', branch1)
            safe_branch2 = re.sub(r'[^\w.-]', '-', branch2)
            diff_file = os.path.join(self.diff_dir, f"diff_{safe_branch1}_{safe_branch2}.txt")

            # 重い処理は別スレッドで実行
            threading.Thread(
                target=self._execute_worker,
                args=(branch1, branch2, diff_file),
                daemon=True
            ).start()

        except Exception as e:
            messagebox.showerror("エラー", str(e))
            self.log_queue.put(f"実行エラー: {e}")

    def _execute_worker(self, branch1, branch2, diff_file):
        try:
            # 差分一覧ファイルを作成
            with open(diff_file, "w", encoding="utf-8") as df:
                subprocess.run(["git", "diff", "--name-only", branch1, branch2], cwd=self.repo_path, text=True, stdout=df, check=False)
            self.log_queue.put(f"差分ファイル出力: {diff_file}")

            # ブランチ1のコピー
            self.file_copy_from_branch(branch1, diff_file)
            # ブランチ2のコピー
            self.file_copy_from_branch(branch2, diff_file)

            # 完了通知
            self.log_queue.put("完了しました")
            self.log_queue.put(self.diff_dir)

            if messagebox.askyesno("完了", f"作業フォルダを開きますか？\n{self.diff_dir}"):
                os.startfile(self.diff_dir)
        except Exception as e:
            self.log_queue.put(str(e))

    def file_copy_from_branch(self, branch, diff_file):
        """
        ブランチを切り替えずに差分ファイル記載のファイルをブランチからコピー
        """
        safe_branch = re.sub(r'[^\w.-]', '-', branch)
        branch_dir = os.path.join(self.diff_dir, safe_branch)
        os.makedirs(branch_dir, exist_ok=True)

        with open(diff_file, encoding='utf-8') as f:
            for line in f:
                rel_path = line.strip()
                branch_src = f"{branch}:{rel_path}"
                dest = os.path.join(branch_dir, rel_path)

                try:
                    ret = (subprocess.run(["git", "ls-tree", "--name-only", branch, "--", rel_path], cwd=self.repo_path, capture_output=True, text=True).stdout or "").strip()
                    if ret == rel_path:
                        os.makedirs(os.path.dirname(dest), exist_ok=True)
                        subprocess.run(["git", "show", branch_src], cwd=self.repo_path, text=True, stdout=open(dest, "w"))
                        self.log_queue.put(f"{branch}: コピー成功 - {rel_path}")
                    else:
                        self.log_queue.put(f"{branch}: スキップ - {rel_path} (存在しません)")
                except Exception as e:
                    self.log_queue.put(f"{branch}: コピー失敗 - {rel_path} ({e})")

    def checkout_and_copy(self, branch, diff_file):
        """
        ブランチを切り替えて差分ファイル記載のファイルをコピー
        """
        safe_branch = re.sub(r'[^\w.-]', '-', branch)
        branch_dir = os.path.join(self.diff_dir, safe_branch)
        os.makedirs(branch_dir, exist_ok=True)

        subprocess.run(["git", "switch", branch], cwd=self.repo_path)

        with open(diff_file, encoding='utf-8') as f:
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
                        self.log_queue.put(f"{branch}: スキップ - {rel_path} (存在しません)")
                except Exception as e:
                    self.log_queue.put(f"{branch}: コピー失敗 - {rel_path} ({e})")

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
        log_file = os.path.join(self.diff_dir, datetime.now().strftime("%Y%m%d%H%M%S") + ".log")
        with open(log_file, "w", encoding="utf-8") as f:
            f.write(self.log_text.get("1.0", tk.END))
        self.log_queue.put(f"ログ出力: {log_file}")

    def _get_current_branch(self):
        """
        現在のブランチを取得
        """
        ret = subprocess.run(["git", "branch", "--contains"], cwd=self.repo_path, capture_output=True)
        tmp = ret.stdout
        return tmp.strip(b"* \n").decode('utf-8')

if __name__ == '__main__':
    app = GitDiffApp()
    app.mainloop()
