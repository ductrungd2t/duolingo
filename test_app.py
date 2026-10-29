import base64
from datetime import datetime, timezone
import io
import json
import os
import unittest
from unittest.mock import patch
import app

TOKEN = 'test.' + base64.urlsafe_b64encode(b'{"sub":787468231}').decode().rstrip('=') + '.test'


class WebTests(unittest.TestCase):
    def call(self, path, method='POST', auth=TOKEN, origin=''):
        result = {}
        env = {'PATH_INFO':path, 'REQUEST_METHOD':method, 'HTTP_HOST':'localhost:8080',
               'wsgi.url_scheme':'http', 'wsgi.input':io.BytesIO(), 'HTTP_ORIGIN':origin}
        if auth is not None:
            env['HTTP_AUTHORIZATION'] = 'Bearer ' + auth
        def start(status, headers):
            result.update(status=int(status.split()[0]), headers=dict(headers))
        result['body'] = b''.join(app.app(env, start))
        return result

    def test_static_and_health(self):
        for path in ('/', '/app.js', '/runner.js', '/styles.css', '/icon.png', '/health'):
            self.assertEqual(self.call(path, 'GET')['status'], 200)
        self.assertEqual(self.call('/../app.py', 'GET')['status'], 404)

    def test_no_token_or_wrong_account(self):
        self.assertEqual(self.call('/api/xp', auth=None)['status'], 401)
        self.assertEqual(self.call('/api/xp', auth='invalid')['status'], 400)
        wrong = 'test.' + base64.urlsafe_b64encode(b'{"sub":123}').decode() + '.test'
        self.assertEqual(self.call('/api/xp', auth=wrong)['status'], 400)

    def test_zero_and_date(self):
        day = datetime.now(app.VN).date().isoformat()
        stamp = datetime.fromisoformat(day).replace(tzinfo=timezone.utc).timestamp()
        for label in (day, stamp):
            with patch('app.upstream', return_value={'summaries':[{'date':label,'gainedXp':0,'numSessions':0}]}):
                result = self.call('/api/xp')
                self.assertEqual(result['status'], 200)
                self.assertEqual(json.loads(result['body'])['xp'], 0)

    def test_missing_is_not_zero(self):
        with patch('app.upstream', return_value={'summaries':[]}):
            self.assertEqual(self.call('/api/xp')['status'], 502)

    def test_complete_and_failure(self):
        app.LAST_RUN = 0
        with patch('app.upstream', return_value={'success':True}) as sender:
            self.assertEqual(self.call('/api/complete')['status'], 200)
            self.assertEqual(sender.call_args.args[2]['score'], 60)
            self.assertEqual(self.call('/api/complete')['status'], 429)
        app.LAST_RUN = 0
        with patch('app.upstream', side_effect=app.ApiError('Mock network error', 502)):
            self.assertEqual(self.call('/api/complete')['status'], 502)
        self.assertFalse(app.LOCK.locked())

    def test_cors(self):
        self.assertEqual(self.call('/api/xp', 'OPTIONS', origin='https://other.invalid')['status'], 403)
        with patch.dict(os.environ, {'ALLOWED_ORIGINS':'https://example.github.io'}):
            result = self.call('/api/xp', 'OPTIONS', origin='https://example.github.io')
            self.assertEqual(result['status'], 204)
            self.assertEqual(result['headers']['Access-Control-Allow-Origin'], 'https://example.github.io')


if __name__ == '__main__':
    unittest.main()
