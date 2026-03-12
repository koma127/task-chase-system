"""
html_generator.py - HTMLレポート生成モジュール
タスクの内容を受け取り、コーラル×スカイブルーのデザインで
HTMLレポートファイルを生成してreports/ディレクトリに保存する
"""
import os
import re
from datetime import datetime

REPORTS_DIR = os.environ.get('REPORTS_DIR', 'reports')


def _safe_filename(text: str, task_id: int) -> str:
    """タスクIDと日時からファイル名を生成する"""
    now = datetime.now().strftime('%Y%m%d_%H%M%S')
    return f'report_{task_id}_{now}.html'


def _escape(text: str) -> str:
    """HTMLエスケープ"""
    return (
        str(text)
        .replace('&', '&amp;')
        .replace('<', '&lt;')
        .replace('>', '&gt;')
        .replace('"', '&quot;')
    )


def _make_url_link(text: str) -> str:
    """テキスト内のURLを<a>タグに変換する"""
    pattern = r'(https?://[^\s<>"\']+)'
    return re.sub(pattern, r'<a href="\1" target="_blank" rel="noopener noreferrer">\1</a>', text)


def generate_report(task_id: int, message: str, research_result: dict = None) -> str:
    """
    HTMLレポートを生成してファイル名を返す
    research_result: researcher.research() の戻り値（省略可）
    """
    os.makedirs(REPORTS_DIR, exist_ok=True)
    filename = _safe_filename(message, task_id)
    filepath = os.path.join(REPORTS_DIR, filename)

    title = _escape(message[:60] + ('...' if len(message) > 60 else ''))
    created_at = datetime.now().strftime('%Y年%m月%d日 %H:%M')

    # URL調査結果のカード生成
    url_cards_html = ''
    if research_result and research_result.get('url_results'):
        for r in research_result['url_results']:
            if r.get('error'):
                url_cards_html += f'''
            <div class="card">
                <div class="card-label">🔗 URL調査</div>
                <p class="url-link"><a href="{_escape(r["url"])}" target="_blank" rel="noopener noreferrer">{_escape(r["url"][:60])}</a></p>
                <p class="error-text">⚠️ {_escape(r["error"])}</p>
            </div>'''
            else:
                page_title = _escape(r.get('title', ''))
                page_text = _escape(r.get('text', '')[:800])
                url_cards_html += f'''
            <div class="card">
                <div class="card-label">🔗 URL調査</div>
                <p class="url-link"><a href="{_escape(r["url"])}" target="_blank" rel="noopener noreferrer">{_escape(r["url"][:60])}</a></p>
                {"<h3 class='page-title'>" + page_title + "</h3>" if page_title else ""}
                <p class="page-text">{page_text.replace(chr(10), "<br>")}</p>
            </div>'''

    message_html = _make_url_link(_escape(message)).replace('\n', '<br>')

    html = f'''<!DOCTYPE html>
<html lang="ja">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>{title}</title>
<style>
  *, *::before, *::after {{ box-sizing: border-box; margin: 0; padding: 0; }}

  body {{
    font-family: -apple-system, BlinkMacSystemFont, 'Hiragino Sans', 'Yu Gothic', sans-serif;
    background: #0f1923;
    color: #e8f0fe;
    min-height: 100vh;
    overflow-x: hidden;
  }}

  canvas#bg {{
    position: fixed;
    top: 0; left: 0;
    width: 100%; height: 100%;
    z-index: 0;
    pointer-events: none;
  }}

  .container {{
    position: relative;
    z-index: 1;
    max-width: 720px;
    margin: 0 auto;
    padding: 24px 16px 60px;
  }}

  header {{
    text-align: center;
    padding: 40px 0 32px;
  }}

  header .badge {{
    display: inline-block;
    background: linear-gradient(135deg, #ea8768, #e85d3a);
    color: #fff;
    font-size: 11px;
    font-weight: 700;
    letter-spacing: 2px;
    text-transform: uppercase;
    padding: 4px 12px;
    border-radius: 20px;
    margin-bottom: 16px;
  }}

  header h1 {{
    font-size: clamp(18px, 5vw, 26px);
    font-weight: 800;
    line-height: 1.4;
    background: linear-gradient(135deg, #ea8768 0%, #33b6de 100%);
    -webkit-background-clip: text;
    -webkit-text-fill-color: transparent;
    background-clip: text;
    margin-bottom: 8px;
  }}

  header .meta {{
    font-size: 12px;
    color: rgba(255,255,255,0.45);
  }}

  .card {{
    background: rgba(255,255,255,0.06);
    backdrop-filter: blur(20px);
    -webkit-backdrop-filter: blur(20px);
    border: 1px solid rgba(255,255,255,0.12);
    border-radius: 16px;
    padding: 20px 22px;
    margin-bottom: 16px;
    position: relative;
    overflow: hidden;
    transition: transform 0.2s, box-shadow 0.2s;
  }}

  .card::before {{
    content: '';
    position: absolute;
    top: 0; left: -60%;
    width: 40%;
    height: 100%;
    background: linear-gradient(
      90deg,
      transparent,
      rgba(255,255,255,0.06),
      transparent
    );
    transform: skewX(-15deg);
    animation: shimmer 4s infinite;
  }}

  @keyframes shimmer {{
    0%   {{ left: -60%; }}
    100% {{ left: 140%; }}
  }}

  .card-label {{
    font-size: 11px;
    font-weight: 700;
    letter-spacing: 1.5px;
    color: #33b6de;
    text-transform: uppercase;
    margin-bottom: 10px;
  }}

  .card p, .card .message-body {{
    font-size: 15px;
    line-height: 1.75;
    color: rgba(255,255,255,0.85);
  }}

  .url-link a {{
    color: #33b6de;
    word-break: break-all;
    text-decoration: none;
  }}
  .url-link a:hover {{ text-decoration: underline; }}

  .page-title {{
    font-size: 16px;
    font-weight: 700;
    color: #fff;
    margin: 10px 0 8px;
  }}

  .page-text {{
    font-size: 13px;
    line-height: 1.7;
    color: rgba(255,255,255,0.65);
    max-height: 300px;
    overflow-y: auto;
  }}

  .error-text {{
    color: #ea8768;
    font-size: 13px;
  }}

  .card a {{
    color: #33b6de;
    text-decoration: none;
  }}
  .card a:hover {{ text-decoration: underline; }}

  footer {{
    text-align: center;
    padding: 40px 0 0;
    font-size: 11px;
    color: rgba(255,255,255,0.25);
  }}
</style>
</head>
<body>
<canvas id="bg"></canvas>

<div class="container">
  <header>
    <div class="badge">Task Report</div>
    <h1>{title}</h1>
    <p class="meta">生成日時: {created_at}　／　Task ID: {task_id}</p>
  </header>

  <div class="card">
    <div class="card-label">📝 受信メッセージ</div>
    <p class="message-body">{message_html}</p>
  </div>

  {url_cards_html}

  <footer>
    <p>powered by task-chase-system</p>
  </footer>
</div>

<script>
(function() {{
  const canvas = document.getElementById('bg');
  const ctx = canvas.getContext('2d');

  function resize() {{
    canvas.width = window.innerWidth;
    canvas.height = window.innerHeight;
  }}
  window.addEventListener('resize', resize);
  resize();

  // Blob設定
  const blobs = [
    {{ x: 0.2, y: 0.3, r: 0.35, color: 'rgba(234,135,104,0.18)', vx: 0.0003, vy: 0.0002 }},
    {{ x: 0.8, y: 0.6, r: 0.40, color: 'rgba(51,182,222,0.15)',  vx: -0.0002, vy: 0.0003 }},
    {{ x: 0.5, y: 0.8, r: 0.28, color: 'rgba(234,135,104,0.10)', vx: 0.0002, vy: -0.0002 }},
  ];

  // ラインノード設定
  const NODE_COUNT = 40;
  const nodes = Array.from({{ length: NODE_COUNT }}, () => ({{
    x: Math.random(),
    y: Math.random(),
    vx: (Math.random() - 0.5) * 0.0004,
    vy: (Math.random() - 0.5) * 0.0004,
  }}));

  let t = 0;
  function draw() {{
    const W = canvas.width, H = canvas.height;
    ctx.clearRect(0, 0, W, H);
    ctx.fillStyle = '#0f1923';
    ctx.fillRect(0, 0, W, H);

    // Blobを描画
    blobs.forEach(b => {{
      const x = (b.x + Math.sin(t * b.vx * 100) * 0.1) * W;
      const y = (b.y + Math.cos(t * b.vy * 100) * 0.1) * H;
      const r = b.r * Math.min(W, H);
      const grad = ctx.createRadialGradient(x, y, 0, x, y, r);
      grad.addColorStop(0, b.color);
      grad.addColorStop(1, 'transparent');
      ctx.beginPath();
      ctx.arc(x, y, r, 0, Math.PI * 2);
      ctx.fillStyle = grad;
      ctx.fill();
    }});

    // ノードを移動
    nodes.forEach(n => {{
      n.x += n.vx;
      n.y += n.vy;
      if (n.x < 0 || n.x > 1) n.vx *= -1;
      if (n.y < 0 || n.y > 1) n.vy *= -1;
    }});

    // ノード間にラインを描画
    for (let i = 0; i < nodes.length; i++) {{
      for (let j = i + 1; j < nodes.length; j++) {{
        const dx = (nodes[i].x - nodes[j].x) * W;
        const dy = (nodes[i].y - nodes[j].y) * H;
        const dist = Math.sqrt(dx * dx + dy * dy);
        if (dist < 180) {{
          const alpha = (1 - dist / 180) * 0.15;
          ctx.beginPath();
          ctx.moveTo(nodes[i].x * W, nodes[i].y * H);
          ctx.lineTo(nodes[j].x * W, nodes[j].y * H);
          ctx.strokeStyle = `rgba(255,255,255,${{alpha}})`;
          ctx.lineWidth = 0.8;
          ctx.stroke();
        }}
      }}
    }}

    t++;
    requestAnimationFrame(draw);
  }}

  draw();
}})();
</script>
</body>
</html>'''

    with open(filepath, 'w', encoding='utf-8') as f:
        f.write(html)

    return filename
