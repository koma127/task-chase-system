"""
line_handler.py - LINE Webhook受信・メッセージ送信モジュール
LINEからのメッセージを受け取り、タスクとして保存して
HTMLレポートを生成し、結果をLINEに返信する
"""
import os
import hmac
import hashlib
import base64
import json
import logging
from flask import Response

from app.database import save_task, update_report, set_google_task_id
from app.researcher import research, extract_urls
from app.html_generator import generate_report
from app.google_tasks import create_google_task
from app.deepdive import set_deepdive_request

logger = logging.getLogger(__name__)

LINE_CHANNEL_ACCESS_TOKEN = os.environ.get('LINE_CHANNEL_ACCESS_TOKEN', '')
LINE_CHANNEL_SECRET = os.environ.get('LINE_CHANNEL_SECRET', '')
BASE_URL = os.environ.get('BASE_URL', 'http://localhost:5000')
REPORTS_DIR = os.environ.get('REPORTS_DIR', 'reports')

LINE_REPLY_API = 'https://api.line.me/v2/bot/message/reply'
LINE_PUSH_API = 'https://api.line.me/v2/bot/message/push'


def _verify_signature(body: bytes, signature: str) -> bool:
    """LINEの署名を検証してなりすましを防ぐ"""
    if not LINE_CHANNEL_SECRET:
        logger.warning('LINE_CHANNEL_SECRET が設定されていません')
        return False
    hash_val = hmac.new(
        LINE_CHANNEL_SECRET.encode('utf-8'),
        body,
        hashlib.sha256
    ).digest()
    expected = base64.b64encode(hash_val).decode('utf-8')
    return hmac.compare_digest(expected, signature)


def handle_webhook(request) -> Response:
    """
    LINE Webhookリクエストを受け取って処理する
    署名検証 → イベント解析 → メッセージ処理の順に実行
    """
    # 署名検証
    signature = request.headers.get('X-Line-Signature', '')
    body = request.get_data()
    if not _verify_signature(body, signature):
        logger.warning('LINE署名検証に失敗しました')
        return Response('Forbidden', status=403)

    try:
        data = json.loads(body.decode('utf-8'))
    except json.JSONDecodeError:
        return Response('Bad Request', status=400)

    for event in data.get('events', []):
        try:
            _process_event(event)
        except Exception as e:
            logger.error(f'イベント処理エラー: {e}', exc_info=True)

    return Response('OK', status=200)


def _process_event(event: dict):
    """イベント1件を処理する"""
    if event.get('type') != 'message':
        return
    msg = event.get('message', {})
    if msg.get('type') != 'text':
        # テキスト以外（画像・スタンプ等）はスキップ
        return

    reply_token = event.get('replyToken')
    user_id = event.get('source', {}).get('userId', '')
    logger.info(f'LINE user_id: {user_id}')
    text = msg.get('text', '').strip()

    if not text:
        return

    # 「深掘り」コマンドの検知
    if text.lower() in ('深掘り', 'deepdive', '深掘'):
        ok = set_deepdive_request(user_id)
        if ok:
            _reply(reply_token,
                   '🔍 深掘りリクエストを受付しました。\n\n'
                   '数分以内にClaude Codeが起動して処理を開始します。\n'
                   '完了したらLINEでお知らせします。')
        else:
            _reply(reply_token, '⚠️ 深掘りリクエストの受付に失敗しました。しばらく待ってから再度お試しください。')
        return

    # URLを抽出
    urls = extract_urls(text)
    url = urls[0] if urls else None

    # DBに保存
    task_id = save_task(line_user_id=user_id, message=text, url=url)

    # 調査実行
    research_result = research(text, url)

    # HTMLレポート生成
    filename = generate_report(task_id=task_id, message=text, research_result=research_result)
    report_url = f'{BASE_URL}/reports/{filename}'

    # DBにレポートURLを保存
    update_report(task_id, filename, report_url)

    # Google Tasksにも作成（設定されている場合のみ）
    google_task_id = create_google_task(
        title=text[:100],
        notes=f'task-chase-system Task ID: {task_id}\nレポート: {report_url}'
    )
    if google_task_id:
        set_google_task_id(task_id, google_task_id)

    # LINEに返信
    reply_text = (
        f'✅ タスクを受け付けました！\n\n'
        f'📋 タスクID: {task_id}\n'
        f'📝 内容: {text[:50]}{"..." if len(text) > 50 else ""}\n\n'
        f'📊 レポートはこちら:\n{report_url}'
    )
    _reply(reply_token, reply_text)


def _reply(reply_token: str, text: str):
    """LINEに返信を送る"""
    import requests as req
    headers = {
        'Content-Type': 'application/json',
        'Authorization': f'Bearer {LINE_CHANNEL_ACCESS_TOKEN}',
    }
    body = {
        'replyToken': reply_token,
        'messages': [{'type': 'text', 'text': text}],
    }
    try:
        resp = req.post(LINE_REPLY_API, headers=headers, json=body, timeout=10)
        resp.raise_for_status()
    except Exception as e:
        logger.error(f'LINE返信エラー: {e}')


def send_line_message(user_id: str, text: str) -> bool:
    """
    任意のユーザーにプッシュメッセージを送る
    成功時True、失敗時Falseを返す
    """
    import requests as req
    headers = {
        'Content-Type': 'application/json',
        'Authorization': f'Bearer {LINE_CHANNEL_ACCESS_TOKEN}',
    }
    body = {
        'to': user_id,
        'messages': [{'type': 'text', 'text': text}],
    }
    try:
        resp = req.post(LINE_PUSH_API, headers=headers, json=body, timeout=10)
        resp.raise_for_status()
        return True
    except Exception as e:
        logger.error(f'LINEプッシュ送信エラー: {e}')
        return False
