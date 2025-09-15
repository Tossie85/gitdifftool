APP_NAME = 'ぎっとさぶん (diff and copy tool for git project)'
VERSION = '0.2.3'

COMMIT_NUMS = 50
LOCAL_CHANGE = 'local_change'

EXCEPT_PATH = [
    'Zone.Identifier',
]

# TITLE
TITLE_EXCLUDE_SETTING = 'コピー対象外設定'
TITLE_SELECT_WORKSPACE = 'ワークスペース選択'
# user_settingsのキー名
US_KEY_CURRENT_WS = 'current_workspace'
US_KEY_DEFAULT_WS = 'default_workspace'

# 除外パスタイプ
EXCLUDE_PATH_TYPE_COPY_ONLY = 0 # コピーのみ対象外
EXCLUDE_PATH_TYPE_ALSO_DIFF = 1 # 比較も対象外 TODO

MAIN_GEO = {'width': 800, 'height': 600, 'x': 100, 'y': 100}
EXC_GEO = {'width': 600, 'height': 400, 'x': 150, 'y': 150}
WS_GEO = {'width': 400, 'height': 200, 'x': 200, 'y': 200}