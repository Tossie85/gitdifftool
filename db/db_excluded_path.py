from db import db_base as dbs
import sqlite3
import const

# テーブル名
TB_NAME = "m_excluded_path"
# 除外パステーブルの作成SQL
TB_CREATE = f"""
    CREATE TABLE IF NOT EXISTS {TB_NAME} (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        ws_name TEXT NOT NULL,
        excluded_path TEXT NOT NULL,    -- パスの一部（部分一致でチェックする）
        type INTEGER default 0,         -- 0:コピー除外, 1:比較も除外
        created_dt TEXT,
        updated_dt TEXT
    );
"""


class DbExcludedPath(dbs.DbBase):
    def __init__(self):
        super().__init__(TB_NAME, TB_CREATE)

    def update_excluded_paths(self, ws_name, excluded_paths, type=const.EXCLUDE_PATH_TYPE_COPY_ONLY):
        """
        除外パス情報の更新
        ワークスペースの除外パス情報を一度削除して、最新の除外パス情報を登録する
        """
        try:
            # 現在のテーブルから除外パス情報を削除する
            delete_sql = f"""
                DELETE FROM {TB_NAME} WHERE ws_name = '{ws_name}';
            """
            conn = sqlite3.connect(self.db_name)
            cursor = conn.cursor()
            cursor.execute(delete_sql)

            # 新しく除外パス情報を追加する
            insert_values = ""

            for path in excluded_paths:
                insert_values += f"('{ws_name}','{path}', {type}, '{self.get_now_string()}', '{self.get_now_string()}')\n,"
            # 最後のカンマだけ取り除く
            insert_values = insert_values[:-1]
            if insert_values:
                insert_sql = f"""
                    INSERT INTO {TB_NAME} (ws_name, excluded_path, type, created_dt, updated_dt) VALUES  
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

    def get_excluded_paths(self, ws_name):
        """
        指定のワークスペースの除外パス一覧をDBから取得し配列で返す
        """
        try:
            select_sql = f"""
                SELECT excluded_path FROM {TB_NAME} WHERE ws_name = '{ws_name}';
            """
            conn = sqlite3.connect(self.db_name)
            cursor = conn.cursor()
            cursor.execute(select_sql)
            result = cursor.fetchall()

            excluded_paths = []
            for b in result:
                excluded_paths.append(b[0])
            return excluded_paths
        except Exception as e:
            print(self.location())
            print(f"ERROR:{e}")
        finally:
            conn.close()
