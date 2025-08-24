from db import db_base as dbs
import sqlite3

# テーブル名
TB_NAME = "m_workspace"
# ワークスペーステーブルの作成SQL
TB_CREATE = f"""
    CREATE TABLE IF NOT EXISTS {TB_NAME} (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        ws_name TEXT UNIQUE NOT NULL,
        repo_path TEXT,
        output_path TEXT,
        created_dt TEXT,
        updated_dt TEXT
    );
"""
KEY_WORKSPACE = "current_workspace"
KEY_REPO_PATH = "repo_path"
KEY_OUTPUT_PATH = "output_path"

class DbWorkspace(dbs.DbBase):
    def __init__(self):
        super().__init__(TB_NAME, TB_CREATE)

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

            ws_settings = {KEY_REPO_PATH: None, KEY_OUTPUT_PATH: None}
            if len(result) > 0:
                ws_settings[KEY_REPO_PATH] = result[0][0]
                ws_settings[KEY_OUTPUT_PATH] = result[0][1]
            return ws_settings
        except Exception as e:
            print(self.location())
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
            if self.exists_workspace_info(ws_name):
                sql = f"""
                update m_workspace 
                    set repo_path = '{repo_path}', 
                    output_path = '{output_path}',
                    updated_dt = '{self.get_now_string()}'
                where ws_name = '{ws_name}';
                """
            else:
                sql = f"""
                insert into m_workspace 
                    (ws_name, repo_path, output_path, created_dt, updated_dt)
                    values 
                    ('{ws_name}','{repo_path}','{output_path}','{self.get_now_string()}','{self.get_now_string()}')
                ;
                """
            cursor.execute(sql)
            conn.commit()
        except Exception as e:
            print(self.location())
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
            print(self.location())
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
            print(self.location())
            print(f"ERROR:{e}")
        finally:
            conn.close()
        # 結果を真理値で返す
        if result[0]:
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
            print(self.location())
            print(f"ERROR:{e}")
        finally:
            conn.close()

        return result
