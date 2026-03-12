# task-chase-system

LINEにメッセージを送ると、タスクとして保存・調査し、HTMLレポートを自動生成するシステム。

## ファイル構成と役割

```
task-chase-system/
├── app/
│   ├── __init__.py        # Pythonパッケージ認識用（空ファイル）
│   ├── main.py            # Flaskサーバー本体・全APIルート定義
│   ├── line_handler.py    # LINEメッセージの受信・返信処理
│   ├── database.py        # SQLiteによるタスクの保存・取得・更新
│   ├── html_generator.py  # コーラル×スカイブルーのHTMLレポート生成
│   ├── researcher.py      # URLの内容取得・テキスト抽出
│   └── google_tasks.py    # Google Tasks API連携（任意）
├── reports/               # 生成されたHTMLレポートの保存先
├── requirements.txt       # 必要なPythonパッケージ一覧
├── Procfile               # Railway起動設定
├── .env.example           # 環境変数テンプレート（値は自分でコピペ）
└── README.md              # このファイル
```

## セットアップ手順

### 1. 環境変数の設定

`.env.example` をコピーして `.env` を作成し、値を自分でコピペする。

```bash
cp .env.example .env
```

**⚠️ APIキー・トークンはコンソールに貼らず、.envファイルに直接記入すること。**

### 2. ローカル動作確認

```bash
pip install -r requirements.txt
python -c "from app.database import init_db; init_db()"
python app/main.py
```

### 3. Railwayへのデプロイ

1. GitHubにpush
2. Railwayで新しいプロジェクト作成 → GitHubリポジトリを接続
3. 環境変数を Railway ダッシュボードで設定
4. デプロイ完了後、表示されたURLをLINEのWebhook URLに設定

## APIエンドポイント一覧

| メソッド | パス | 説明 |
|---------|------|------|
| POST | /webhook | LINE Webhook受信 |
| GET | /reports/<filename> | HTMLレポート配信 |
| GET | /api/tasks | タスク一覧取得 |
| POST | /api/tasks/<id>/upload | HTMLアップロード |
| POST | /api/tasks/<id>/skip | タスクスキップ |
| POST | /api/notify | LINE通知送信 |
| GET | /api/dashboard/tasks | ダッシュボード用タスク一覧 |
| POST | /api/dashboard/update-status | ステータス変更 |
| POST | /api/dashboard/update-task | ジャンル・種別変更 |
| POST | /api/dashboard/toggle-working | 作業中フラグ切替 |
| POST | /api/dashboard/reclassify | 全タスク自動再分類 |
| POST | /api/reports/upload | 汎用HTMLアップロード |

## タスクのステータス順序

`unconfirmed` → `confirmed` → `reinvestigate` → `execute` → `done`
