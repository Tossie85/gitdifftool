import inspect
import os
import sqlite3
import datetime

DB_NAME = "git_tool.db"


class DbBase:
    tb_name = ""

    def __init__(self, tb_name, tb_create):
        self.db_name = DB_NAME
        self.tb_name = tb_name
        # DBテーブルを作成する
        self.create_table_if_not_exists(tb_create)

    def create_table_if_not_exists(self, tb_create):
        try:
            conn = sqlite3.connect(self.db_name)
            cursor = conn.cursor()
            cursor.execute(tb_create)
            conn.commit()
        except Exception as e:
            print(self.location())
            print(f"ERROR:{e}")
        finally:
            conn.close()

    def get_now_string(self):
        """
        現在時刻をyyyy-mm-dd hh:dd:mm形式で取得する
        """
        # 時刻差分
        T_DELTA = datetime.timedelta(hours=9)
        # JST時刻
        JST = datetime.timezone(T_DELTA, "JST")
        now = datetime.datetime.now(JST)
        return now.strftime("%Y-%m-%d %H:%M:%S")

    def location(self, depth=0):
        frame = inspect.currentframe().f_back
        return (
            os.path.basename(frame.f_code.co_filename),
            frame.f_code.co_name,
            frame.f_lineno,
        )
