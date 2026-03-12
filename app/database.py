"""
database.py - データベース操作モジュール
SQLiteを使ってタスクの保存・取得・更新を行う
"""
import os
import sqlite3
import json
from datetime import datetime

DATABASE_PATH = os.environ.get('DATABASE_PATH', 'tasks.db')

# タスクのステータス順序
STATUS_ORDER = ['unconfirmed', 'confirmed', 'reinvestigate', 'execute', 'done']

# ジャンル自動分類キーワード
GENRE_KEYWORDS = {
    '仕事': ['会議', 'ミーティング', '資料', '報告', '提案', 'メール', '電話', '締切', 'クライアント', 'プロジェクト'],
    '学習': ['勉強', '読書', '本', '講座', '学習', '調査', 'リサーチ', '研究'],
    '買い物': ['買う', '購入', '注文', 'amazon', '楽天', 'ショッピング'],
    '個人': ['掃除', '洗濯', '料理', '運動', '健康', '病院', '家族'],
}

TASK_TYPE_KEYWORDS = {
    'リサーチ': ['調べる', '調査', 'リサーチ', '検索', 'なぜ', 'どうして', '方法', 'やり方'],
    'アイデア': ['アイデア', 'ひらめき', '案', '提案', '企画'],
    'メモ': ['メモ', '覚え書き', '忘れないで', '記録'],
}


def get_connection():
    conn = sqlite3.connect(DATABASE_PATH)
    conn.row_factory = sqlite3.Row
    return conn


def init_db():
    """データベースとテーブルを初期化する"""
    conn = get_connection()
    conn.execute('''
        CREATE TABLE IF NOT EXISTS tasks (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            line_user_id TEXT NOT NULL,
            message TEXT NOT NULL,
            url TEXT,
            status TEXT NOT NULL DEFAULT 'unconfirmed',
            genre TEXT DEFAULT 'その他',
            task_type TEXT DEFAULT 'タスク',
            is_working INTEGER NOT NULL DEFAULT 0,
            report_filename TEXT,
            report_url TEXT,
            google_task_id TEXT,
            created_at TEXT NOT NULL,
            updated_at TEXT NOT NULL
        )
    ''')
    conn.commit()
    conn.close()


def _row_to_dict(row):
    if row is None:
        return None
    return dict(row)


def save_task(line_user_id: str, message: str, url: str = None) -> int:
    """新しいタスクをDBに保存し、IDを返す"""
    now = datetime.now().isoformat()
    genre = _classify_genre(message)
    task_type = _classify_task_type(message)
    conn = get_connection()
    cursor = conn.execute(
        '''INSERT INTO tasks (line_user_id, message, url, status, genre, task_type, created_at, updated_at)
           VALUES (?, ?, ?, 'unconfirmed', ?, ?, ?, ?)''',
        (line_user_id, message, url, genre, task_type, now, now)
    )
    task_id = cursor.lastrowid
    conn.commit()
    conn.close()
    return task_id


def get_all_tasks() -> list:
    """全タスクを新しい順で取得する"""
    conn = get_connection()
    rows = conn.execute(
        'SELECT * FROM tasks ORDER BY created_at DESC'
    ).fetchall()
    conn.close()
    return [_row_to_dict(r) for r in rows]


def get_task_by_id(task_id: int) -> dict:
    """IDでタスクを1件取得する"""
    conn = get_connection()
    row = conn.execute('SELECT * FROM tasks WHERE id = ?', (task_id,)).fetchone()
    conn.close()
    return _row_to_dict(row)


def update_report(task_id: int, report_filename: str, report_url: str):
    """タスクにレポートのファイル名とURLをセットする"""
    now = datetime.now().isoformat()
    conn = get_connection()
    conn.execute(
        'UPDATE tasks SET report_filename=?, report_url=?, updated_at=? WHERE id=?',
        (report_filename, report_url, now, task_id)
    )
    conn.commit()
    conn.close()


def update_task_status(task_id: int, status: str) -> dict:
    """タスクのステータスを更新する"""
    if status not in STATUS_ORDER:
        raise ValueError(f'無効なステータス: {status}')
    now = datetime.now().isoformat()
    conn = get_connection()
    conn.execute(
        'UPDATE tasks SET status=?, updated_at=? WHERE id=?',
        (status, now, task_id)
    )
    conn.commit()
    row = conn.execute('SELECT * FROM tasks WHERE id=?', (task_id,)).fetchone()
    conn.close()
    return _row_to_dict(row)


def advance_task_status(task_id: int) -> dict:
    """タスクのステータスを1段階進める"""
    task = get_task_by_id(task_id)
    if task is None:
        return None
    current = task['status']
    if current in STATUS_ORDER:
        idx = STATUS_ORDER.index(current)
        next_status = STATUS_ORDER[min(idx + 1, len(STATUS_ORDER) - 1)]
    else:
        next_status = 'confirmed'
    return update_task_status(task_id, next_status)


def update_task(task_id: int, genre: str = None, task_type: str = None, message: str = None) -> dict:
    """タスクのジャンル・種別・本文を更新する"""
    now = datetime.now().isoformat()
    task = get_task_by_id(task_id)
    if task is None:
        return None
    new_genre = genre if genre is not None else task['genre']
    new_type = task_type if task_type is not None else task['task_type']
    new_message = message if message is not None else task['message']
    conn = get_connection()
    conn.execute(
        'UPDATE tasks SET genre=?, task_type=?, message=?, updated_at=? WHERE id=?',
        (new_genre, new_type, new_message, now, task_id)
    )
    conn.commit()
    row = conn.execute('SELECT * FROM tasks WHERE id=?', (task_id,)).fetchone()
    conn.close()
    return _row_to_dict(row)


def toggle_working(task_id: int) -> dict:
    """「今やってるよ」フラグを切り替える"""
    task = get_task_by_id(task_id)
    if task is None:
        return None
    new_val = 0 if task['is_working'] else 1
    now = datetime.now().isoformat()
    conn = get_connection()
    conn.execute(
        'UPDATE tasks SET is_working=?, updated_at=? WHERE id=?',
        (new_val, now, task_id)
    )
    conn.commit()
    row = conn.execute('SELECT * FROM tasks WHERE id=?', (task_id,)).fetchone()
    conn.close()
    return _row_to_dict(row)


def skip_task(task_id: int) -> dict:
    """タスクをスキップ（doneに）する"""
    return update_task_status(task_id, 'done')


def reclassify_tasks() -> int:
    """全タスクをキーワードベースで再分類する。変更件数を返す"""
    tasks = get_all_tasks()
    count = 0
    for task in tasks:
        new_genre = _classify_genre(task['message'])
        new_type = _classify_task_type(task['message'])
        if new_genre != task['genre'] or new_type != task['task_type']:
            update_task(task['id'], genre=new_genre, task_type=new_type)
            count += 1
    return count


def set_google_task_id(task_id: int, google_task_id: str):
    """Google Tasks のタスクIDをDBに保存する"""
    now = datetime.now().isoformat()
    conn = get_connection()
    conn.execute(
        'UPDATE tasks SET google_task_id=?, updated_at=? WHERE id=?',
        (google_task_id, now, task_id)
    )
    conn.commit()
    conn.close()


def _classify_genre(message: str) -> str:
    msg = message.lower()
    for genre, keywords in GENRE_KEYWORDS.items():
        if any(kw in msg for kw in keywords):
            return genre
    return 'その他'


def _classify_task_type(message: str) -> str:
    msg = message.lower()
    for task_type, keywords in TASK_TYPE_KEYWORDS.items():
        if any(kw in msg for kw in keywords):
            return task_type
    return 'タスク'
