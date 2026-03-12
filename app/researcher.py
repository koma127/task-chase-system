"""
researcher.py - Web調査モジュール
URLが含まれているメッセージのページ内容を取得し、
レポート生成に使えるテキストを抽出する
"""
import re
import requests
from bs4 import BeautifulSoup

HEADERS = {
    'User-Agent': (
        'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) '
        'AppleWebKit/537.36 (KHTML, like Gecko) '
        'Chrome/120.0.0.0 Safari/537.36'
    )
}
TIMEOUT = 10  # 秒


def extract_urls(text: str) -> list[str]:
    """テキストからURLを全て抽出する"""
    pattern = r'https?://[^\s\u3000\u300c\u300d\uff08\uff09\u300a\u300b]+'
    return re.findall(pattern, text)


def fetch_url_content(url: str) -> dict:
    """
    URLのページを取得してタイトル・本文テキストを返す
    戻り値: {'title': str, 'text': str, 'url': str, 'error': str|None}
    """
    result = {'title': '', 'text': '', 'url': url, 'error': None}
    try:
        resp = requests.get(url, headers=HEADERS, timeout=TIMEOUT)
        resp.raise_for_status()
        soup = BeautifulSoup(resp.text, 'lxml')

        # タイトル取得
        title_tag = soup.find('title')
        result['title'] = title_tag.get_text(strip=True) if title_tag else ''

        # 本文取得（scriptやstyleを除外）
        for tag in soup(['script', 'style', 'nav', 'footer', 'header']):
            tag.decompose()

        # メインコンテンツを優先的に取得
        main = soup.find('main') or soup.find('article') or soup.find('body')
        if main:
            text = main.get_text(separator='\n', strip=True)
        else:
            text = soup.get_text(separator='\n', strip=True)

        # 連続する空行を1行にまとめる
        lines = [line for line in text.splitlines() if line.strip()]
        result['text'] = '\n'.join(lines[:200])  # 最大200行

    except requests.exceptions.Timeout:
        result['error'] = 'ページの読み込みがタイムアウトしました'
    except requests.exceptions.ConnectionError:
        result['error'] = 'ページに接続できませんでした'
    except requests.exceptions.HTTPError as e:
        result['error'] = f'HTTPエラー: {e.response.status_code}'
    except Exception as e:
        result['error'] = f'取得エラー: {str(e)}'

    return result


def research(message: str, url: str = None) -> dict:
    """
    メッセージ（とオプションのURL）を受け取って調査結果をまとめて返す
    戻り値: {'message': str, 'url_results': list, 'summary': str}
    """
    url_results = []

    # メッセージ内のURLも含めて全URL調査
    urls = extract_urls(message)
    if url and url not in urls:
        urls.insert(0, url)

    for u in urls[:3]:  # 最大3件のみ調査
        content = fetch_url_content(u)
        url_results.append(content)

    # サマリー（最初のURL or メッセージ本文）
    summary = message
    if url_results and url_results[0]['title']:
        summary = url_results[0]['title']

    return {
        'message': message,
        'url_results': url_results,
        'summary': summary,
    }
