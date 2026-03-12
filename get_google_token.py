"""
get_google_token.py - Google Tasks認証トークン取得スクリプト
このスクリプトを一度だけ実行して、.envに貼るトークン情報を取得する
"""
import json
import sys
from pathlib import Path

try:
    from google_auth_oauthlib.flow import InstalledAppFlow
except ImportError:
    print('エラー: 必要なパッケージがインストールされていません。')
    print('以下のコマンドを先に実行してください:')
    print('  pip install google-auth-oauthlib')
    sys.exit(1)

SCOPES = ['https://www.googleapis.com/auth/tasks']

# ダウンロードフォルダのJSONファイルを自動で探す
downloads = Path.home() / 'Downloads'
candidates = list(downloads.glob('client_secret*.json'))

if not candidates:
    print('エラー: ダウンロードフォルダに client_secret_*.json が見つかりません。')
    print('ファイル名を確認して、このスクリプトと同じフォルダに置いてください。')
    sys.exit(1)

credentials_file = str(candidates[0])
print(f'認証ファイルを使用: {credentials_file}')
print()
print('ブラウザが開きます。Googleアカウントでログインして許可してください。')
print()

flow = InstalledAppFlow.from_client_secrets_file(credentials_file, SCOPES)
creds = flow.run_local_server(
    port=8080,
    open_browser=False,
    authorization_prompt_message='以下のURLをブラウザで開いてください:\n{url}\n',
    success_message='認証完了！このタブを閉じてターミナルに戻ってください。',
)

# .envに貼る用のJSON文字列を生成
token_data = {
    'token': creds.token,
    'refresh_token': creds.refresh_token,
    'token_uri': creds.token_uri,
    'client_id': creds.client_id,
    'client_secret': creds.client_secret,
}
token_json = json.dumps(token_data)

print()
print('=' * 60)
print('✅ 取得成功！以下の1行を .env の')
print('   GOOGLE_TASKS_CREDENTIALS_JSON= の後ろに貼ってください')
print('=' * 60)
print()
print(f'GOOGLE_TASKS_CREDENTIALS_JSON={token_json}')
print()
print('=' * 60)
print('⚠️  この情報は他人に見せないでください')
print('=' * 60)
