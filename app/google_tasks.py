"""
google_tasks.py - Google Tasks連携モジュール
ダッシュボードでタスクを完了にしたとき、
Google Tasksにも反映する（双方向同期）
"""
import os
import json
import logging

logger = logging.getLogger(__name__)

# Google Tasks API は任意機能のため、ライブラリがない場合はスキップ
try:
    from google.oauth2.credentials import Credentials
    from google.auth.transport.requests import Request
    from googleapiclient.discovery import build
    GOOGLE_AVAILABLE = True
except ImportError:
    GOOGLE_AVAILABLE = False
    logger.warning('google-api-python-client がインストールされていません。Google Tasks同期はスキップします。')


def _get_service():
    """Google Tasks APIのサービスオブジェクトを返す"""
    if not GOOGLE_AVAILABLE:
        return None

    creds_json = os.environ.get('GOOGLE_TASKS_CREDENTIALS_JSON')
    if not creds_json:
        logger.warning('GOOGLE_TASKS_CREDENTIALS_JSON が設定されていません')
        return None

    try:
        creds_data = json.loads(creds_json)
        creds = Credentials(
            token=creds_data.get('token'),
            refresh_token=creds_data.get('refresh_token'),
            token_uri='https://oauth2.googleapis.com/token',
            client_id=creds_data.get('client_id'),
            client_secret=creds_data.get('client_secret'),
            scopes=['https://www.googleapis.com/auth/tasks'],
        )
        # トークンが期限切れなら自動更新
        if creds.expired and creds.refresh_token:
            creds.refresh(Request())

        return build('tasks', 'v1', credentials=creds, cache_discovery=False)
    except Exception as e:
        logger.error(f'Google Tasks サービス初期化エラー: {e}')
        return None


def create_google_task(title: str, notes: str = None) -> str | None:
    """
    Google Tasksにタスクを新規作成してIDを返す
    失敗時はNoneを返す
    """
    service = _get_service()
    if service is None:
        return None

    list_id = os.environ.get('GOOGLE_TASKS_LIST_ID', '@default')
    body = {'title': title}
    if notes:
        body['notes'] = notes

    try:
        result = service.tasks().insert(tasklist=list_id, body=body).execute()
        logger.info(f'Google Tasksにタスク作成: {result["id"]}')
        return result['id']
    except Exception as e:
        logger.error(f'Google Tasksタスク作成エラー: {e}')
        return None


def complete_google_task(google_task_id: str) -> bool:
    """
    Google Tasksのタスクを完了にする
    成功時True、失敗時Falseを返す
    """
    service = _get_service()
    if service is None:
        return False

    list_id = os.environ.get('GOOGLE_TASKS_LIST_ID', '@default')
    try:
        task = service.tasks().get(tasklist=list_id, task=google_task_id).execute()
        task['status'] = 'completed'
        service.tasks().update(tasklist=list_id, task=google_task_id, body=task).execute()
        logger.info(f'Google Tasksタスク完了: {google_task_id}')
        return True
    except Exception as e:
        logger.error(f'Google Tasksタスク完了エラー: {e}')
        return False


def reopen_google_task(google_task_id: str) -> bool:
    """
    Google Tasksのタスクを未完了に戻す（逆同期用）
    """
    service = _get_service()
    if service is None:
        return False

    list_id = os.environ.get('GOOGLE_TASKS_LIST_ID', '@default')
    try:
        task = service.tasks().get(tasklist=list_id, task=google_task_id).execute()
        task['status'] = 'needsAction'
        task.pop('completed', None)
        service.tasks().update(tasklist=list_id, task=google_task_id, body=task).execute()
        logger.info(f'Google Tasksタスク再開: {google_task_id}')
        return True
    except Exception as e:
        logger.error(f'Google Tasksタスク再開エラー: {e}')
        return False
