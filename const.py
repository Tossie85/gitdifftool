APP_NAME = 'ぎっとさぶん (diff and copy tool for git project)'
VERSION = '0.2.8'

# 取得する差分コミット数の上限
DIFF_FILE_NUM_LIMIT = 50
# 確認対象とする差分ファイル数の上限
DIFF_FILE_CONFIRM_LINES = 20
# マージコミットを含む
WITH_MERGE_COMMITS = 0
# マージコミットを除外する
WITHOUT_MERGE_COMMITS = 1

LOCAL_CHANGE = 'local_change'

EXCEPT_PATH = [
    'Zone.Identifier',
]

# TITLE
TITLE_WORKSPACE = 'ワークスペース'
TITLE_EXCLUDE_SETTING = 'コピー対象外設定'
TITLE_SELECT_WORKSPACE = 'ワークスペース選択'
TITLE_USER_SETTINGS = 'ユーザー設定'
# LABEL
LABEL_USER_SETTINGS_COMMIT_NUM = '取得する差分コミット数の上限'
LABEL_USER_SETTINGS_DIFF_FILE_NUM = '確認をせずに実行する差分ファイル数の上限'
LABEL_USER_SETTINGS_NO_MERGE = 'マージコミットを除外する'
BUTTON_SAVE = '保存'

# user_settingsのキー名
US_KEY_CURRENT_WS = 'current_workspace'
US_KEY_DEFAULT_WS = 'default_workspace'
US_KEY_COMMIT_NUM = 'commit_nums'
US_KEY_DIFF_FILE_NUM = 'diff_file_confirm_lines'
US_KEY_NO_MERGE = 'no_merge_commits'

# 除外パスタイプ
EXCLUDE_PATH_TYPE_COPY_ONLY = 0 # コピーのみ対象外
EXCLUDE_PATH_TYPE_ALSO_DIFF = 1 # 比較も対象外 TODO

MAIN_GEO = {'width': 800, 'height': 600, 'x': 100, 'y': 100}
EXC_GEO = {'width': 600, 'height': 400, 'x': 0, 'y': 0}
WS_GEO = {'width': 400, 'height': 200, 'x': 0, 'y': 0}
US_GEO = {'width': 400, 'height': 200, 'x': 0, 'y': 0}