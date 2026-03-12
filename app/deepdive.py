"""
deepdive.py - 深掘りリクエストの管理モジュール
LINEから「深掘り」と送られた時のリクエストを保存・取得・クリアする
"""
import os
import json
import logging
from datetime import datetime

logger = logging.getLogger(__name__)

DEEPDIVE_REQUEST_FILE = os.environ.get('DEEPDIVE_REQUEST_FILE', 'deepdive-request.json')


def set_deepdive_request(user_id: str) -> bool:
    """深掘りリクエストを設定する（上書き）"""
    try:
        data = {
            'status': 'pending',
            'requested_at': datetime.utcnow().isoformat(),
            'requested_by': user_id,
        }
        with open(DEEPDIVE_REQUEST_FILE, 'w', encoding='utf-8') as f:
            json.dump(data, f, ensure_ascii=False)
        logger.info(f'深掘りリクエストを設定しました: user_id={user_id}')
        return True
    except Exception as e:
        logger.error(f'深掘りリクエスト設定エラー: {e}')
        return False


def get_deepdive_request() -> dict:
    """現在の深掘りリクエスト状態を取得する"""
    if not os.path.exists(DEEPDIVE_REQUEST_FILE):
        return {'status': 'none'}
    try:
        with open(DEEPDIVE_REQUEST_FILE, encoding='utf-8') as f:
            return json.load(f)
    except Exception as e:
        logger.error(f'深掘りリクエスト取得エラー: {e}')
        return {'status': 'none'}


def clear_deepdive_request() -> bool:
    """深掘りリクエストをクリアする"""
    try:
        if os.path.exists(DEEPDIVE_REQUEST_FILE):
            os.remove(DEEPDIVE_REQUEST_FILE)
        logger.info('深掘りリクエストをクリアしました')
        return True
    except Exception as e:
        logger.error(f'深掘りリクエストクリアエラー: {e}')
        return False
