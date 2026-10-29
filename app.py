"""Same-origin website and fixed Duolingo API bridge. No account secrets in source."""
import base64
from datetime import datetime, timedelta, timezone
import json
import mimetypes
import os
from pathlib import Path
import threading
import time
from urllib.error import HTTPError, URLError
from urllib.parse import urlencode
from urllib.request import Request, urlopen, HTTPRedirectHandler, build_opener

ROOT = Path(__file__).resolve().parent / 'public'
USER_ID = '787468231'
VN = timezone(timedelta(hours=7))
LOCK = threading.Lock()
LAST_RUN = 0.0


class ApiError(Exception):
    def __init__(self, text, status=400):
        self.text, self.status = text, status


class NoRedirect(HTTPRedirectHandler):
    def redirect_request(self, req, fp, code, msg, headers, newurl):
        return None


def check_token(token):
    if not isinstance(token, str) or len(token) > 8192:
        raise ApiError('Token không hợp lệ.')
    try:
        parts = token.split('.')
        if len(parts) != 3:
            raise ValueError()
        payload = json.loads(base64.urlsafe_b64decode(parts[1] + '=' * (-len(parts[1]) % 4)))
        if str(payload.get('sub')) != USER_ID:
            raise ApiError('Tool chỉ dùng tài khoản trung.')
    except (ValueError, IndexError, TypeError, AttributeError):
        raise ApiError('Token không đúng định dạng JWT.') from None


def upstream(url, token, payload=None):
    headers = {'Authorization': 'Bearer ' + token, 'Accept': 'application/json',
               'User-Agent': 'DuoTrungWeb/1.0'}
    data = None
    if payload is not None:
        data = json.dumps(payload).encode()
        headers.update({'Content-Type': 'application/json; charset=UTF-8',
                        'Cookie': 'jwt_token=' + token,
                        'Origin': 'https://www.duolingo.com', 'Referer': 'https://www.duolingo.com/'})
    request = Request(url, data=data, headers=headers, method='POST' if data else 'GET')
    try:
        with build_opener(NoRedirect()).open(request, timeout=20) as response:
            if 'json' not in response.headers.get('Content-Type', '').lower():
                raise ApiError('Máy chủ không trả JSON; chưa xác nhận kết quả.', 502)
            result = json.load(response)
            if not isinstance(result, dict):
                raise ApiError('Phản hồi máy chủ không hợp lệ.', 502)
            return result
    except HTTPError as error:
        messages = {401: 'Token hết hiệu lực. Hãy đăng nhập lại.',
                    403: 'Duolingo từ chối truy cập (403).',
                    429: 'Duolingo đang giới hạn yêu cầu (429). Hãy thử lại sau.'}
        raise ApiError(messages.get(error.code, f'Duolingo báo lỗi HTTP {error.code}.'), 502) from None
    except (URLError, TimeoutError, OSError):
        raise ApiError('Lỗi kết nối Duolingo hoặc hết thời gian chờ. Không tự thử lại.', 502) from None
    except (ValueError, UnicodeError):
        raise ApiError('Không đọc được JSON từ Duolingo.', 502) from None


def xp_today(token):
    day = datetime.now(VN).date().isoformat()
    query = urlencode({'startDate': day, 'endDate': day, 'timezone': 'Asia/Ho_Chi_Minh'})
    data = upstream(f'https://www.duolingo.com/2017-06-30/users/{USER_ID}/xp_summaries?{query}', token)
    rows = data.get('summaries')
    if not isinstance(rows, list):
        raise ApiError('Chưa đọc được danh sách XP hôm nay.', 502)
    matches = []
    for row in rows:
        if not isinstance(row, dict):
            raise ApiError('Dữ liệu ngày không hợp lệ.', 502)
        label = row.get('date')
        if type(label) in (int, float):
            try:
                label = datetime.fromtimestamp(label, timezone.utc).date().isoformat()
            except (ValueError, OverflowError, OSError):
                raise ApiError('Ngày API không hợp lệ.', 502) from None
        if label == day:
            matches.append(row)
    if len(matches) != 1:
        raise ApiError('Chưa có bản tổng hợp hôm nay. Thử lại sau; chưa thể kết luận 0 XP.', 502)
    row = matches[0]
    if type(row.get('gainedXp')) is not int or row['gainedXp'] < 0:
        raise ApiError('Dữ liệu XP không hợp lệ.', 502)
    return {'day': day, 'xp': row['gainedXp'],
            'sessions': row.get('numSessions') if type(row.get('numSessions')) is int else None}


def complete_story(token):
    global LAST_RUN
    if not LOCK.acquire(blocking=False):
        raise ApiError('Đang có một yêu cầu chạy điểm. Chờ yêu cầu đó hoàn tất.', 409)
    try:
        now = time.monotonic()
        if now - LAST_RUN < 1:
            raise ApiError('Các lượt chạy cần cách nhau ít nhất 1 giây.', 429)
        LAST_RUN = now
        payload = {
            'awardXp': True, 'completedBonusChallenge': False, 'dailyRefreshInfo': None,
            'fromLanguage': 'vi', 'hasXpBoost': False, 'illustrationFormat': 'svg',
            'isFeaturedStoryInPracticeHub': False, 'isLegendaryMode': False,
            'isV2Redo': True, 'isV2Story': True, 'learningLanguage': 'en',
            'masterVersion': False, 'maxScore': 60, 'mode': 'READ', 'numHintsUsed': 0,
            'score': 60, 'pathLevelSpecifics': {'storyId': 'en-vi-the-passport',
                                            'mode': 'read', 'treeId': 'd0ad5fadbcebad14d0e7656356708486'},
        }
        result = upstream('https://stories.duolingo.com/api2/stories/en-vi-the-passport/complete', token, payload)
        if not result or result.get('error') or result.get('errors') or result.get('success') is False:
            raise ApiError('API chưa xác nhận hoàn thành bài học.', 502)
        return {'accepted': True, 'message': 'HTTP thành công; chưa xác nhận XP tăng.'}
    finally:
        LOCK.release()


def app(environ, start_response):
    path = environ.get('PATH_INFO', '/')
    method = environ.get('REQUEST_METHOD', 'GET')
    origin = environ.get('HTTP_ORIGIN', '')
    own = f"{environ.get('wsgi.url_scheme', 'http')}://{environ.get('HTTP_HOST', '')}"
    allowed = {x.strip().rstrip('/') for x in os.environ.get('ALLOWED_ORIGINS', '').split(',') if x.strip()}
    # Render terminates TLS before Gunicorn. Compare the configured public URL too.
    public = os.environ.get('RENDER_EXTERNAL_URL', '').rstrip('/')
    origins = allowed | {own, public}
    cors = [('Access-Control-Allow-Origin', origin), ('Vary', 'Origin')] if origin and origin in origins else []

    def respond(status, data, mime='application/json; charset=utf-8'):
        body = json.dumps(data, ensure_ascii=False).encode() if isinstance(data, dict) else data
        headers = [('Content-Type', mime), ('Content-Length', str(len(body))),
                   ('Cache-Control', 'no-store'), ('X-Content-Type-Options', 'nosniff'),
                   ('Referrer-Policy', 'no-referrer'),
                   ('Content-Security-Policy', "default-src 'self'; script-src 'self'; style-src 'self'; img-src 'self' data:; connect-src 'self' https: http://localhost:* http://127.0.0.1:*; object-src 'none'; base-uri 'self'; frame-ancestors 'none'")]
        start_response(f'{status} ' + {200:'OK',204:'No Content',400:'Bad Request',401:'Unauthorized',403:'Forbidden',404:'Not Found',405:'Method Not Allowed',409:'Conflict',429:'Too Many Requests',502:'Bad Gateway',500:'Internal Server Error'}.get(status,'Error'), headers + cors)
        return [body]

    if path.startswith('/api/'):
        if origin and origin not in origins:
            return respond(403, {'error': 'Nguồn truy cập chưa được cho phép.'})
        if method == 'OPTIONS':
            start_response('204 No Content', cors + [('Access-Control-Allow-Methods', 'POST, OPTIONS'),
                           ('Access-Control-Allow-Headers', 'Authorization, Content-Type'), ('Cache-Control','no-store')])
            return [b'']
        if method != 'POST':
            return respond(405, {'error': 'Chỉ chấp nhận POST.'})
        auth = environ.get('HTTP_AUTHORIZATION', '')
        if not auth.startswith('Bearer '):
            return respond(401, {'error': 'Nhập token tài khoản trung trước.'})
        token = auth[7:].strip()
        try:
            check_token(token)
            if path == '/api/xp':
                return respond(200, xp_today(token))
            if path == '/api/complete':
                return respond(200, complete_story(token))
            return respond(404, {'error': 'Không tìm thấy API.'})
        except ApiError as error:
            return respond(error.status, {'error': error.text})
        except Exception:
            return respond(500, {'error': 'Máy chủ chưa xử lý được yêu cầu. Không tự gửi lại.'})
    if path == '/health':
        return respond(200, {'ok': True})
    if method != 'GET':
        return respond(405, {'error': 'Không hỗ trợ phương thức này.'})
    files = {'/': 'index.html', '/index.html':'index.html', '/styles.css':'styles.css',
             '/app.js':'app.js', '/runner.js':'runner.js', '/manifest.webmanifest':'manifest.webmanifest',
             '/icon.png':'icon.png'}
    name = files.get(path)
    if not name:
        return respond(404, {'error':'Không tìm thấy trang.'})
    mime = mimetypes.guess_type(name)[0] or 'application/octet-stream'
    if name.endswith('.js'):
        mime = 'text/javascript'
    return respond(200, (ROOT / name).read_bytes(), mime + ('; charset=utf-8' if not name.endswith('.png') else ''))


if __name__ == '__main__':
    from wsgiref.simple_server import make_server
    port = int(os.environ.get('PORT', 8080))
    print(f'Open http://127.0.0.1:{port} (local development only)', flush=True)
    make_server('127.0.0.1', port, app).serve_forever()
