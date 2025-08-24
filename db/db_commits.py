from db import db_base as dbs
import sqlite3

# テーブル名
TB_NAME = "r_commits"
# コミットテーブルの作成SQL
TB_CREATE = f"""
    CREATE TABLE IF NOT EXISTS {TB_NAME} (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        ws_name TEXT NOT NULL,
        commit_id TEXT NOT NULL,
        commit_dt TEXT,
        commit_comment TEXT,
        auther TEXT,
        created_dt TEXT,
        updated_dt TEXT
    );
"""

class DbCommit(dbs.DbBase):
    def __init__(self):
        super().__init__(TB_NAME, TB_CREATE)

    def update_commit_logs(self, ws_name, commits):
        """
        コミット情報の更新
        ワークスペースのコミット情報を一度削除して、最新のコミット情報を登録する
        """
        try:
            # 現在のテーブルからコミット情報を削除する
            delete_sql = f"""
                DELETE FROM {TB_NAME} WHERE ws_name = '{ws_name}';
            """
            conn = sqlite3.connect(self.db_name)
            cursor = conn.cursor()
            cursor.execute(delete_sql)

            # 新しくブランチ情報を追加する
            insert_values = ""

            for commit in commits:
                insert_values += f"('{ws_name}','{commit[0]}','{commit[1]}','{commit[2]}','{commit[3]}', '{self._get_now_string()}', '{self._get_now_string()}')\n,"
            # 最後のカンマだけ取り除く
            insert_values = insert_values[:-1]
            insert_sql = f"""
                INSERT INTO {TB_NAME} (ws_name, commit_id, commit_dt, commit_comment, auther, created_dt, updated_dt) VALUES  
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

    def get_commits(self, ws_name):
        """
        指定のワークスペースのコミット一覧をDBから取得し配列で返す
        """
        try:
            select_sql = f"""
                SELECT commit_id, commit_dt, commit_comment, auther FROM {TB_NAME} WHERE ws_name = '{ws_name}';
            """
            conn = sqlite3.connect(self.db_name)
            cursor = conn.cursor()
            cursor.execute(select_sql)
            result = cursor.fetchall()

            commits = ["HEAD", "HEAD~", "HEAD~2"]
            for b in result:
                commits.append([b[0], b[1], b[2], b[3]])
            return commits
        except Exception as e:
            print(self.location())
            print(f"ERROR:{e}")
        finally:
            conn.close()