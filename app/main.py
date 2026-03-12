"""
main.py - Flaskサーバーのメインファイル
全てのAPIエンドポイントをここで定義し、
アプリケーションの起動もここから行う
"""
import os
import logging
from functools import wraps
from flask import Flask, request, jsonify, send_from_directory, abort
from dotenv import load_dotenv

load_dotenv()

from app.database import (
    init_db, get_all_tasks, get_task_by_id,
    update_report, update_task_status, advance_task_status,
    update_task, toggle_working, skip_task, reclassify_tasks,
)
from app.line_handler import handle_webhook, send_line_message
from app.html_generator import generate_report
from app.google_tasks import complete_google_task, reopen_google_task

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = Flask(__name__)

REPORTS_DIR = os.environ.get('REPORTS_DIR', 'reports')
API_KEY = os.environ.get('API_KEY', '')
BASE_URL = os.environ.get('BASE_URL', 'http://localhost:5000')

os.makedirs(REPORTS_DIR, exist_ok=True)


# ── 認証デコレーター ──────────────────────────────────────────
def require_api_key(f):
    """X-API-Key ヘッダーでAPIキー認証を行うデコレーター"""
    @wraps(f)
    def decorated(*args, **kwargs):
        if not API_KEY:
            # APIキー未設定の場合はローカル開発用として通す
            logger.warning('API_KEY が未設定です。本番環境では必ず設定してください。')
            return f(*args, **kwargs)
        key = request.headers.get('X-API-Key', '')
        if key != API_KEY:
            return jsonify({'error': 'Unauthorized'}), 401
        return f(*args, **kwargs)
    return decorated


# ── LINE Webhook ──────────────────────────────────────────────
@app.route('/webhook', methods=['POST'])
def webhook():
    """LINE からのメッセージを受け取るエンドポイント"""
    return handle_webhook(request)


# ── レポート配信 ──────────────────────────────────────────────
@app.route('/reports/<path:filename>')
def serve_report(filename):
    """生成済みHTMLレポートをブラウザに配信する"""
    return send_from_directory(REPORTS_DIR, filename)


# ── deepdive クライアント向けAPI ─────────────────────────────
@app.route('/api/tasks', methods=['GET'])
@require_api_key
def api_tasks():
    """全タスクの一覧をJSON形式で返す（deepdiveクライアント用）"""
    tasks = get_all_tasks()
    return jsonify(tasks)


@app.route('/api/tasks/<int:task_id>/upload', methods=['POST'])
@require_api_key
def api_task_upload(task_id):
    """
    タスクにHTMLレポートをアップロードする（deepdiveクライアント用）
    リクエストボディ: multipart/form-data で "file" フィールドにHTMLを添付
    または JSON で {"html": "...", "filename": "..."}
    """
    task = get_task_by_id(task_id)
    if task is None:
        return jsonify({'error': 'タスクが見つかりません'}), 404

    # JSONでHTMLを受け取るパターン
    if request.is_json:
        data = request.get_json()
        html_content = data.get('html', '')
        filename = data.get('filename', f'report_{task_id}.html')
    else:
        # ファイルアップロードパターン
        f = request.files.get('file')
        if f is None:
            return jsonify({'error': 'fileが必要です'}), 400
        filename = f.filename or f'report_{task_id}.html'
        html_content = f.read().decode('utf-8')

    # reports/ に保存
    os.makedirs(REPORTS_DIR, exist_ok=True)
    filepath = os.path.join(REPORTS_DIR, filename)
    with open(filepath, 'w', encoding='utf-8') as fp:
        fp.write(html_content)

    report_url = f'{BASE_URL}/reports/{filename}'
    update_report(task_id, filename, report_url)

    return jsonify({'ok': True, 'report_url': report_url})


@app.route('/api/tasks/<int:task_id>/skip', methods=['POST'])
@require_api_key
def api_task_skip(task_id):
    """タスクをスキップ（完了）にする（deepdiveクライアント用）"""
    task = skip_task(task_id)
    if task is None:
        return jsonify({'error': 'タスクが見つかりません'}), 404
    return jsonify(task)


@app.route('/api/notify', methods=['POST'])
@require_api_key
def api_notify():
    """
    LINE通知を送る（deepdiveクライアント用）
    リクエストボディ: {"user_id": "...", "message": "..."}
    """
    data = request.get_json() or {}
    user_id = data.get('user_id', '')
    message = data.get('message', '')
    if not user_id or not message:
        return jsonify({'error': 'user_id と message が必要です'}), 400
    ok = send_line_message(user_id, message)
    return jsonify({'ok': ok})


# ── ダッシュボード API ───────────────────────────────────────
@app.route('/api/dashboard/tasks', methods=['GET'])
@require_api_key
def dashboard_tasks():
    """ダッシュボード用：全タスクの一覧を返す"""
    tasks = get_all_tasks()
    return jsonify(tasks)


@app.route('/api/dashboard/update-status', methods=['POST'])
@require_api_key
def dashboard_update_status():
    """
    タスクのステータスを変更する
    リクエストボディ: {"task_id": 1, "status": "confirmed"}
    status は unconfirmed → confirmed → reinvestigate → execute → done の順
    statusを省略すると1段階自動で進む
    """
    data = request.get_json() or {}
    task_id = data.get('task_id')
    if task_id is None:
        return jsonify({'error': 'task_id が必要です'}), 400

    status = data.get('status')
    if status:
        try:
            task = update_task_status(task_id, status)
        except ValueError as e:
            return jsonify({'error': str(e)}), 400
    else:
        task = advance_task_status(task_id)

    if task is None:
        return jsonify({'error': 'タスクが見つかりません'}), 404

    # doneになった場合はGoogle Tasksにも同期
    if task.get('status') == 'done' and task.get('google_task_id'):
        complete_google_task(task['google_task_id'])

    # doneから戻した場合はGoogle Tasksも未完了に戻す
    if status and status != 'done' and task.get('google_task_id'):
        reopen_google_task(task['google_task_id'])

    return jsonify(task)


@app.route('/api/dashboard/update-task', methods=['POST'])
@require_api_key
def dashboard_update_task():
    """
    タスクのジャンル・種別・本文を変更する
    リクエストボディ: {"task_id": 1, "genre": "仕事", "task_type": "タスク", "message": "..."}
    """
    data = request.get_json() or {}
    task_id = data.get('task_id')
    if task_id is None:
        return jsonify({'error': 'task_id が必要です'}), 400

    task = update_task(
        task_id,
        genre=data.get('genre'),
        task_type=data.get('task_type'),
        message=data.get('message'),
    )
    if task is None:
        return jsonify({'error': 'タスクが見つかりません'}), 404
    return jsonify(task)


@app.route('/api/dashboard/toggle-working', methods=['POST'])
@require_api_key
def dashboard_toggle_working():
    """
    「今やってるよ」フラグを切り替える
    リクエストボディ: {"task_id": 1}
    """
    data = request.get_json() or {}
    task_id = data.get('task_id')
    if task_id is None:
        return jsonify({'error': 'task_id が必要です'}), 400
    task = toggle_working(task_id)
    if task is None:
        return jsonify({'error': 'タスクが見つかりません'}), 404
    return jsonify(task)


@app.route('/api/dashboard/reclassify', methods=['POST'])
@require_api_key
def dashboard_reclassify():
    """全タスクをキーワードベースで自動再分類する"""
    count = reclassify_tasks()
    return jsonify({'ok': True, 'updated_count': count})


# ── 汎用HTMLアップロード ─────────────────────────────────────
@app.route('/api/reports/upload', methods=['POST'])
@require_api_key
def api_reports_upload():
    """
    任意のHTMLファイルをreports/に保存する（ダッシュボード・WBS等）
    リクエストボディ: multipart/form-data で "file" フィールド（ファイル名を保持）
    または JSON で {"html": "...", "filename": "xxx.html"}
    """
    os.makedirs(REPORTS_DIR, exist_ok=True)

    if request.is_json:
        data = request.get_json()
        html_content = data.get('html', '')
        filename = data.get('filename', 'upload.html')
    else:
        f = request.files.get('file')
        if f is None:
            return jsonify({'error': 'fileが必要です'}), 400
        filename = f.filename or 'upload.html'
        html_content = f.read().decode('utf-8')

    filepath = os.path.join(REPORTS_DIR, filename)
    with open(filepath, 'w', encoding='utf-8') as fp:
        fp.write(html_content)

    report_url = f'{BASE_URL}/reports/{filename}'
    return jsonify({'ok': True, 'url': report_url, 'filename': filename})


# ── 起動 ─────────────────────────────────────────────────────
if __name__ == '__main__':
    init_db()
    port = int(os.environ.get('PORT', 5000))
    app.run(host='0.0.0.0', port=port, debug=False)
