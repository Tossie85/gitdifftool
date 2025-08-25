from db import db_base as dbs
import sqlite3

# テーブル名
TB_NAME = "m_user_settings"
# ユーザ設定テーブルの作成SQL
TB_CREATE = f"""
    CREATE TABLE IF NOT EXISTS {TB_NAME} (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        key TEXT NOT NULL,
        value TEXT NOT NULL,
        created_dt TEXT,
        updated_dt TEXT
    );
"""


class DbUserSettings(dbs.DbBase):
    def __init__(self):
        super().__init__(TB_NAME, TB_CREATE)

    def update_or_insert_user_settings(self, key, value):
        """
        ユーザー設定の記録
        すでにユーザー情報がある場合は更新、ない場合は登録をする
        """
        try:
            conn = sqlite3.connect(self.db_name)
            cursor = conn.cursor()
            sql = ""
            if self.exists_user_setting_info(key):
                sql = f"""
                update {TB_NAME} 
                    set value = '{value}', 
                    updated_dt = '{self.get_now_string()}'
                    where key = '{key}'
                ;
                """
            else:
                sql = f"""
                insert into {TB_NAME} 
                    (key, value, created_dt, updated_dt)
                    values 
                    ('{key}','{value}','{self.get_now_string()}','{self.get_now_string()}')
                ;
                """
            cursor.execute(sql)
            conn.commit()
        except Exception as e:
            print(self.location())
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
                SELECT count(*) FROM {TB_NAME} WHERE key = '{key_name}';
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

    def get_user_setting(self, key):
        """
        ユーザー設定を取得する
        """
        result = []
        try:
            select_sql = f"""
                SELECT value FROM {TB_NAME} where key = '{key}';
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

        # 取得結果を整形して返す
        return result[0]
