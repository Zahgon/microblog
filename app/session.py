"""Signed cookie sessions.

Based on Starlette's session middleware, with the addition of a per session
cookie lifetime, which is what makes the "remember me" option of the login
form work: sessions that are not remembered expire when the browser is closed.
"""
import json
from base64 import b64decode, b64encode

import itsdangerous
from itsdangerous.exc import BadSignature
from starlette.datastructures import MutableHeaders
from starlette.requests import HTTPConnection

REMEMBER_KEY = '_remember'


class SessionMiddleware:
    def __init__(self, app, secret_key, session_cookie='session',
                 max_age=365 * 24 * 60 * 60, path='/', same_site='lax',
                 https_only=False, domain=None):
        self.app = app
        self.signer = itsdangerous.TimestampSigner(str(secret_key))
        self.session_cookie = session_cookie
        self.max_age = max_age
        self.path = path
        self.security_flags = 'httponly; samesite=' + same_site
        if https_only:
            self.security_flags += '; secure'
        if domain is not None:
            self.security_flags += f'; domain={domain}'

    async def __call__(self, scope, receive, send):
        if scope['type'] not in ('http', 'websocket'):
            await self.app(scope, receive, send)
            return

        connection = HTTPConnection(scope)
        initial_session_was_empty = True

        if self.session_cookie in connection.cookies:
            data = connection.cookies[self.session_cookie].encode('utf-8')
            try:
                data = self.signer.unsign(data, max_age=self.max_age)
                scope['session'] = json.loads(b64decode(data))
                initial_session_was_empty = False
            except BadSignature:
                scope['session'] = {}
        else:
            scope['session'] = {}

        async def send_wrapper(message):
            if message['type'] == 'http.response.start':
                if scope['session']:
                    data = b64encode(json.dumps(scope['session']).encode(
                        'utf-8'))
                    data = self.signer.sign(data)
                    max_age = ''
                    if scope['session'].get(REMEMBER_KEY):
                        max_age = f'Max-Age={self.max_age}; '
                    headers = MutableHeaders(scope=message)
                    header_value = (
                        f'{self.session_cookie}={data.decode("utf-8")}; '
                        f'path={self.path}; {max_age}{self.security_flags}')
                    headers.append('Set-Cookie', header_value)
                elif not initial_session_was_empty:
                    headers = MutableHeaders(scope=message)
                    header_value = (
                        f'{self.session_cookie}=null; path={self.path}; '
                        'expires=Thu, 01 Jan 1970 00:00:00 GMT; '
                        f'{self.security_flags}')
                    headers.append('Set-Cookie', header_value)
            await send(message)

        await self.app(scope, receive, send_wrapper)
