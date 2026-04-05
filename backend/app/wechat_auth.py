import json
import urllib.parse
import urllib.request


class WechatCode2SessionError(Exception):
    pass


class WechatMiniProgramAuthClient:
    def __init__(self, app_id: str, app_secret: str, *, timeout: float = 8.0):
        self.app_id = (app_id or '').strip()
        self.app_secret = (app_secret or '').strip()
        self.timeout = max(1.0, float(timeout))

    def is_configured(self) -> bool:
        return bool(self.app_id and self.app_secret)

    def code_to_session(self, code: str) -> dict:
        normalized_code = (code or '').strip()
        if not normalized_code:
            raise WechatCode2SessionError('wechat login code is required')
        if not self.is_configured():
            raise WechatCode2SessionError('wechat mini program credentials are not configured')

        query = urllib.parse.urlencode({
            'appid': self.app_id,
            'secret': self.app_secret,
            'js_code': normalized_code,
            'grant_type': 'authorization_code',
        })
        url = f'https://api.weixin.qq.com/sns/jscode2session?{query}'
        request = urllib.request.Request(
            url,
            headers={
                'Accept': 'application/json',
                'User-Agent': 'weixin-demo-api/1.0',
            },
            method='GET',
        )

        try:
            with urllib.request.urlopen(request, timeout=self.timeout) as response:
                payload = json.loads(response.read().decode('utf-8'))
        except Exception as error:
            raise WechatCode2SessionError(f'wechat code2session request failed: {error}') from error

        errcode = int(payload.get('errcode') or 0)
        if errcode:
            errmsg = str(payload.get('errmsg') or 'wechat code2session failed').strip()
            raise WechatCode2SessionError(f'wechat code2session failed: {errmsg} ({errcode})')

        openid = str(payload.get('openid') or '').strip()
        session_key = str(payload.get('session_key') or '').strip()
        if not openid or not session_key:
            raise WechatCode2SessionError('wechat code2session returned incomplete identity')

        return {
            'openid': openid,
            'session_key': session_key,
            'unionid': str(payload.get('unionid') or '').strip(),
        }
