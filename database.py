import inspect
import os
import json
import sqlite3
import datetime

# database設定ファイル
DB_CONFIG = os.path.join(os.path.dirname(__file__), 'db.json')
# ワークスペーステーブルのテーブル名
TB_WORKSPACE = "m_workspace"
# ワークスペーステーブルの作成SQL
CREATE_TB_WORKSPACE = f"""
    CREATE TABLE IF NOT EXISTS {TB_WORKSPACE} (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        ws_name TEXT UNIQUE NOT NULL,
        repo_path TEXT,
        output_path TEXT,
        created_dt TEXT,
        updated_dt TEXT
    );
"""
# ブランチテーブルのテーブル名
TB_BRABCHES = "r_branches"
# ブランチテーブルの作成SQL
CREATE_TB_BRABCHES = f"""
    CREATE TABLE IF NOT EXISTS {TB_BRABCHES} (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        ws_name TEXT NOT NULL,
        branch_name TEXT NOT NULL,
        created_dt TEXT,
        updated_dt TEXT
    );
"""
# ユーザ設定テーブルのテーブル名
TB_USER_SETTINGS = "m_user_settings"
# ユーザ設定テーブルの作成SQL
CREATE_TB_USER_SETTINGS = f"""
    CREATE TABLE IF NOT EXISTS {TB_USER_SETTINGS} (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        key TEXT NOT NULL,
        value TEXT NOT NULL,
        created_dt TEXT,
        updated_dt TEXT
    );
"""
KEY_WORKSPACE = 'current_workspace'
KEY_REPO_PATH = 'repo_path'
KEY_OUTPUT_PATH = 'output_path'

class Database():
    """
    データベース管理用のクラス
    """
    def __init__(self):
        super().__init__()
        self.db_name = ''
        # DB情報の設定を読み込む
        self.load_settings()
        # DBを初期化する
        self.db_init()
    
    def get_db_name(self):
        return self.db_name

    def load_settings(self):
        if os.path.exists(DB_CONFIG):
            try:
                with open(DB_CONFIG, 'r', encoding='utf-8') as f:
                    config = json.load(f)
                    self.db_name = config.get("db_name", '')
            except Exception:
                pass
    
    def db_init(self):
        self.create_table_if_not_exists(CREATE_TB_WORKSPACE)
        self.create_table_if_not_exists(CREATE_TB_BRABCHES)
        self.create_table_if_not_exists(CREATE_TB_USER_SETTINGS)
    
    def create_table_if_not_exists(self, create_table_sql):
        try:
            conn = sqlite3.connect(self.db_name)
            cursor = conn.cursor()
            cursor.execute(create_table_sql)
            conn.commit()
        except Exception as e:
            print(self._location())
            print(f"ERROR:{e}")
        finally:
            conn.close()

    def update_branches(self, ws_name, branches):
        """
        ブランチ情報の更新
        ワークスペースのブランチ情報を一度削除して、最新のブランチ情報を登録する
        """
        try:
            # 現在のテーブルからブランチ情報を削除する
            delete_sql = f"""
                DELETE FROM {TB_BRABCHES} WHERE ws_name = '{ws_name}';
            """
            conn = sqlite3.connect(self.db_name)
            cursor = conn.cursor()
            cursor.execute(delete_sql)

            # 新しくブランチ情報を追加する
            insert_values = ""
            
            for branch in branches:
                insert_values += f"('{ws_name}','{branch}', '{self._get_now_string()}', '{self._get_now_string()}')\n,"
            # 最後のカンマだけ取り除く
            insert_values = insert_values[:-1]
            insert_sql = f"""
                INSERT INTO {TB_BRABCHES} (ws_name, branch_name, created_dt, updated_dt) VALUES  
                {insert_values};
            """
            cursor.execute(insert_sql)
            conn.commit()
        except Exception as e:
            # エラー時はロールバックする
            conn.rollback()
            print(self._location())
            print(f"ERROR:{e}")
        finally:
            conn.close()
    
    def get_branches(self, ws_name):
        """
        指定のワークスペースのブランチ一覧をDBから取得し配列で返す
        """
        try:
            select_sql = f"""
                SELECT branch_name FROM r_branches WHERE ws_name = '{ws_name}';
            """
            conn = sqlite3.connect(self.db_name)
            cursor = conn.cursor()
            cursor.execute(select_sql)
            result = cursor.fetchall()

            branches = []
            for b in result:
                branches.append(b[0])
            return branches
        except Exception as e:
            print(self._location())
            print(f"ERROR:{e}")
        finally:
            conn.close()
    
    def get_workspace_settings(self, ws_name):
        """
        指定のワークスペースの設定をDBから取得
        """
        try:
            select_sql = f"""
                SELECT {KEY_REPO_PATH}, {KEY_OUTPUT_PATH} FROM m_workspace WHERE ws_name = '{ws_name}';
            """
            conn = sqlite3.connect(self.db_name)
            cursor = conn.cursor()
            cursor.execute(select_sql)
            result = cursor.fetchall()

            ws_settings = {KEY_REPO_PATH:None, KEY_OUTPUT_PATH:None}
            if len(result) > 0:
                ws_settings[KEY_REPO_PATH] = result[0][0] 
                ws_settings[KEY_OUTPUT_PATH] = result[0][1]
            return ws_settings
        except Exception as e:
            print(self._location())
            print(f"ERROR:{e}")
        finally:
            conn.close()

    def update_or_insert_workspace_settings(self, ws_name, repo_path, output_path):
        """
        ワークスペース情報の登録または更新
        すでにワークスペース情報がある場合は更新、ない場合は登録をする
        """
        try:
            conn = sqlite3.connect(self.db_name)
            cursor = conn.cursor()
            sql = ""
            if (self.exists_workspace_info(ws_name)):
                sql = f"""
                update m_workspace 
                    set repo_path = '{repo_path}', 
                    output_path = '{output_path}',
                    updated_dt = '{self._get_now_string()}'
                where ws_name = '{ws_name}';
                """
            else:
                sql = f"""
                insert into m_workspace 
                    (ws_name, repo_path, output_path, created_dt, updated_dt)
                    values 
                    ('{ws_name}','{repo_path}','{output_path}','{self._get_now_string()}','{self._get_now_string()}')
                ;
                """
            cursor.execute(sql)
            conn.commit()
        except Exception as e:
            print(self._location())
            print(f"ERROR:{e}")
        finally:
            conn.close()

    def get_workspace_name_list(self):
        """
        ワークスペース名一覧を取得する
        """
        result = []
        try:
            select_sql = f"""
                SELECT ws_name FROM m_workspace order by id asc;
            """
            conn = sqlite3.connect(self.db_name)
            cursor = conn.cursor()
            cursor.execute(select_sql)
            result = cursor.fetchall()
        except Exception as e:
            print(self._location())
            print(f"ERROR:{e}")
        finally:
            conn.close()

        ret = []
        # 取得結果を整形して返す
        for ws in result:
            ret.append(ws[0])
        return ret

    def exists_workspace_info(self, ws_name):
        """
        引数のワークスペース名のワークスペースがすでに登録済みか確認する
        """
        result = None
        # ワークスペースの登録数をチェックする
        try:
            select_sql = f"""
                SELECT count(*) FROM m_workspace WHERE ws_name = '{ws_name}';
            """
            conn = sqlite3.connect(self.db_name)
            cursor = conn.cursor()
            cursor.execute(select_sql)
            result = cursor.fetchone()
        except Exception as e:
            print(self._location())
            print(f"ERROR:{e}")
        finally:
            conn.close()
        # 結果を真理値で返す
        if(result[0]):
            return True
        else:
            return False
    
    def count_workspaces(self):
        """
        登録済みのワークスペース数を確認する
        """
        try:
            count_sql = f"""
                SELECT count(*) FROM m_workspace;
            """
            conn = sqlite3.connect(self.db_name)
            cursor = conn.cursor()
            cursor.execute(count_sql)
            result = cursor.fetchone()[0]
        except Exception as e:
            print(self._location())
            print(f"ERROR:{e}")
        finally:
            conn.close()
        
        return result

    def update_or_insert_user_settings(self, key, value):
        """
        ユーザー設定の記録
        すでにユーザー情報がある場合は更新、ない場合は登録をする
        """
        try:
            conn = sqlite3.connect(self.db_name)
            cursor = conn.cursor()
            sql = ""
            if (self.exists_user_setting_info(key)):
                sql = f"""
                update m_user_settings 
                    set value = '{value}', 
                    updated_dt = '{self._get_now_string()}'
                    where key = '{key}'
                ;
                """
            else:
                sql = f"""
                insert into m_user_settings 
                    (key, value, created_dt, updated_dt)
                    values 
                    ('{key}','{value}','{self._get_now_string()}','{self._get_now_string()}')
                ;
                """
            cursor.execute(sql)
            conn.commit()
        except Exception as e:
            print(self._location())
            print(f"ERROR:{e}")
        finally:
            conn.close()
    
    def exists_user_setting_info(self, key_name):
        """
        引数のキー名のユーザ設定がすでに登録済みか確認する
        """
        result = None
        # ユーザ設定の登録数をチェックする
        try:
            select_sql = f"""
                SELECT count(*) FROM m_user_settings WHERE key = '{key_name}';
            """
            conn = sqlite3.connect(self.db_name)
            cursor = conn.cursor()
            cursor.execute(select_sql)
            result = cursor.fetchone()
        except Exception as e:
            print(self._location())
            print(f"ERROR:{e}")
        finally:
            conn.close()
        # 結果を真理値で返す
        if(result[0]):
            return True
        else:
            return False

    def get_user_setting(self, key):
        """
        ユーザー設定を取得する
        """
        result = []
        try:
            select_sql = f"""
                SELECT value FROM m_user_settings where key = '{key}';
            """
            conn = sqlite3.connect(self.db_name)
            cursor = conn.cursor()
            cursor.execute(select_sql)
            result = cursor.fetchone()
        except Exception as e:
            print(self._location())
            print(f"ERROR:{e}")
        finally:
            conn.close()

        # 取得結果を整形して返す
        return result[0]
    
    def _get_now_string(self):
        """
        現在時刻をyyyy-mm-dd hh:dd:mm形式で取得する
        """
        # 時刻差分
        T_DELTA = datetime.timedelta(hours=9)
        # JST時刻
        JST = datetime.timezone(T_DELTA, 'JST')
        now = datetime.datetime.now(JST)
        return now.strftime('%Y-%m-%d %H:%M:%S')
    
    def _location(self,depth=0):
        frame = inspect.currentframe().f_back
        return os.path.basename(frame.f_code.co_filename), frame.f_code.co_name, frame.f_lineno