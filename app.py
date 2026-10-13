from flask import Flask, render_template, g, jsonify, request
import hashlib
import hmac
import json
import logging
import sqlite3
import os
from pathlib import Path
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen

app = Flask(__name__)
BASE_DIR = Path(__file__).resolve().parent
DATABASE = BASE_DIR / 'concert.sqlite'
CONTACT_ORIGINS = {
    'https://trombonanza-page.uc.r.appspot.com',
    'https://trombonanza.org',
    'https://www.trombonanza.org',
    'http://127.0.0.1:5001',
    'http://localhost:5001',
}

@app.context_processor
def inject_public_config():
    """Values embedded in both Flask previews and generated static HTML."""
    return {'contact_api_url': '/api/contact'}


def normalize(value):
    return value.strip() if isinstance(value, str) else ''


def valid_email(value):
    if not value or len(value) > 254 or value.count('@') != 1:
        return False
    local, domain = value.rsplit('@', 1)
    return bool(local and '.' in domain and not any(character.isspace() for character in value))


def send_contact_email(name, email, message):
    """Ask the private Apps Script web app endpoint to send the email."""
    url = os.environ.get('APPS_SCRIPT_WEB_APP_URL', '')
    secret = os.environ.get('APPS_SCRIPT_SHARED_SECRET', '')
    if not url or not secret:
        raise RuntimeError('Apps Script contact settings are missing')

    forwarded_for = request.headers.get('X-Forwarded-For', '')
    client_ip = forwarded_for.split(',', 1)[0].strip() or request.remote_addr or 'unknown'
    rate_key = hmac.new(
        secret.encode('utf-8'),
        client_ip.encode('utf-8'),
        hashlib.sha256,
    ).hexdigest()
    payload = json.dumps({
        'secret': secret,
        'name': name,
        'email': email,
        'message': message,
        'rateKey': rate_key,
    }).encode('utf-8')
    outbound = Request(
        url,
        data=payload,
        headers={'Content-Type': 'application/json; charset=utf-8'},
        method='POST',
    )
    with urlopen(outbound, timeout=15) as response:
        result = json.loads(response.read().decode('utf-8'))
    if result.get('error') == 'rate_limited':
        raise ContactRateLimited()
    if result.get('ok') is not True:
        raise RuntimeError('Apps Script rejected the contact request')


class ContactRateLimited(RuntimeError):
    pass


@app.post('/api/contact')
def contact():
    origin = request.headers.get('Origin', '')
    if origin not in CONTACT_ORIGINS:
        return jsonify(message='不正な送信元です。'), 403
    if request.content_length and request.content_length > 20_000:
        return jsonify(message='送信内容が大きすぎます。'), 413

    data = request.get_json(silent=True)
    if not isinstance(data, dict):
        return jsonify(message='送信内容を読み取れませんでした。'), 400

    # This field is hidden from visitors and is commonly filled by simple bots.
    if normalize(data.get('website')):
        return jsonify(message='お問い合わせを送信しました。ありがとうございます。')

    name = normalize(data.get('name'))
    email = normalize(data.get('email'))
    message = normalize(data.get('message'))
    if not name or len(name) > 80 or not valid_email(email) or not 5 <= len(message) <= 4000:
        return jsonify(message='入力内容を確認してください。'), 400

    try:
        send_contact_email(name, email, message)
    except ContactRateLimited:
        return jsonify(message='送信回数が多すぎます。しばらく待ってからお試しください。'), 429
    except (HTTPError, URLError, TimeoutError, ValueError, RuntimeError):
        logging.exception('Contact email delivery failed')
        return jsonify(message='送信に失敗しました。時間をおいて再度お試しください。'), 502

    return jsonify(message='お問い合わせを送信しました。ありがとうございます。')

def get_db():
    db = getattr(g, '_database', None)
    if db is None:
        db = g._database = sqlite3.connect(DATABASE)
        db.row_factory = sqlite3.Row
    return db

@app.teardown_appcontext
def close_connection(exception):
    db = getattr(g, '_database', None)
    if db is not None:
        db.close()

def julian_to_datetime(jdn):
    # ユリウス通日から日付への変換（簡易版、sqliteのjuliandayを想定）
    # sqliteのjuliandayは、紀元前4713年1月1日正午からの経過日数
    # ここでは、sqliteのdate関数に任せるのが安全
    return jdn

@app.template_filter('format_jdn')
def format_jdn(jdn):
    # SQLiteのjuliandayを日付文字列に変換する
    db = get_db()
    cur = db.execute("SELECT date(?, 'localtime') as d, strftime('%w', ?, 'localtime') as w", (jdn, jdn))
    row = cur.fetchone()
    if row:
        date_str = row['d']
        weekday_idx = int(row['w'])
        weekdays = ["日", "月", "火", "水", "木", "金", "土"]
        return f"{date_str}({weekdays[weekday_idx]})"
    return jdn

@app.route('/')
def index():
    # 本来は直近の演奏会を取得するが、一旦既存のindex.htmlの内容を表示するようにする
    # 必要に応じてDBからデータを取得して埋め込む
    return render_template('index.html')

@app.route('/archive')
def archive():
    db = get_db()
    query = """
        SELECT s.id, s.name, h.hall, s.date, s.page, 
               (SELECT name FROM piece WHERE concertid = s.id AND main = 1 LIMIT 1) AS main_piece
        FROM stage s
        LEFT JOIN hall h ON s.place = h.id
        ORDER BY s.id DESC
    """
    concerts = db.execute(query).fetchall()
    return render_template('archive.html', concerts=concerts)

@app.route('/archive/<page>')
@app.route('/concert/<page>')
def concert_detail(page):
    db = get_db()
    # 演奏会情報を取得
    stage_query = """
        SELECT s.id, s.name, h.hall, s.date, s.imageurl
        FROM stage s
        LEFT JOIN hall h ON s.place = h.id
        WHERE s.page = ?
    """
    stage = db.execute(stage_query, (page,)).fetchone()
    
    if not stage:
        return "Concert not found", 404
        
    # 曲目情報を取得
    pieces_query = """
        SELECT name, composer, arranger, innerid
        FROM piece
        WHERE concertid = ?
        ORDER BY innerid ASC
    """
    pieces = db.execute(pieces_query, (stage['id'],)).fetchall()

    # 作曲者ごとに他演奏会情報を取得
    composer_links = {}
    composers = set([piece['composer'] for piece in pieces if piece['composer']])
    for composer in composers:
        # この演奏会以外で同作曲者の曲が演奏された情報を取得
        query = '''
            SELECT s.page, s.name AS concert_name, p.name AS piece_name
            FROM piece p
            JOIN stage s ON p.concertid = s.id
            WHERE p.composer = ? AND s.id != ?
            ORDER BY s.date DESC
        '''
        rows = db.execute(query, (composer, stage['id'])).fetchall()
        composer_links[composer] = rows

    return render_template('concert_detail.html', stage=stage, pieces=pieces, composer_links=composer_links)

if __name__ == '__main__':
    app.run(debug=True, port=5001)
