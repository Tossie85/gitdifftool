from db import db_base as dbs
import sqlite3

# テーブル名
TB_NAME = "r_branches"
# ブランチテーブルの作成SQL
TB_CREATE = f"""
    CREATE TABLE IF NOT EXISTS {TB_NAME} (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        ws_name TEXT NOT NULL,
        branch_name TEXT NOT NULL,
        created_dt TEXT,
        updated_dt TEXT
    );
"""

class DbBranch(dbs.DbBase):
    def __init__(self):
        super().__init__(TB_NAME, TB_CREATE)

    def update_branches(self, ws_name, branches):
        """
        ブランチ情報の更新
        ワークスペースのブランチ情報を一度削除して、最新のブランチ情報を登録する
        """
        try:
            # 現在のテーブルからブランチ情報を削除する
            delete_sql = f"""
                DELETE FROM {TB_NAME} WHERE ws_name = '{ws_name}';
            """
            conn = sqlite3.connect(self.db_name)
            cursor = conn.cursor()
            cursor.execute(delete_sql)

            # 新しくブランチ情報を追加する
            insert_values = ""

            for branch in branches:
                insert_values += f"('{ws_name}','{branch}', '{self.get_now_string()}', '{self.get_now_string()}')\n,"
            # 最後のカンマだけ取り除く
            insert_values = insert_values[:-1]
            insert_sql = f"""
                INSERT INTO {TB_NAME} (ws_name, branch_name, created_dt, updated_dt) VALUES  
                {insert_values};
            """
            cursor.execute(insert_sql)
            conn.commit()
        except Exception as e:
            # エラー時はロールバックする
            conn.rollback()
            print(self.location())
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
            print(self.location())
            print(f"ERROR:{e}")
        finally:
            conn.close()