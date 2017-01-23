# Copyright (c) LinkedIn Corporation. All rights reserved. Licensed under the BSD-2 Clause license.
# See LICENSE in the project root for license information.

import ujson as json
import time
import hmac
import hashlib
import base64
import urllib
from urllib3.connectionpool import HTTPConnectionPool


class ApiServerError(Exception):
    def __init__(self, resp):
        self.resp = resp


class IrisClient(HTTPConnectionPool):
    def __init__(self, host, port, user, api_key, version=0, **kwargs):
        super(IrisClient, self).__init__(host, port, **kwargs)
        self.version = version
        self.user = user
        self.HMAC = hmac.new(api_key, '', hashlib.sha512)

    def post(self, endpoint, qs=None, **data):
        HMAC = self.HMAC.copy()
        path_parts = ['/v%s/' % self.version, endpoint]
        if qs:
            path_parts.extend(('?', qs))
        path = ''.join(path_parts)
        method = 'POST'
        body = json.dumps(data)
        window = int(time.time()) // 5
        HMAC.update('%s %s %s %s' % (window, method, path, body))
        digest = base64.urlsafe_b64encode(HMAC.digest())

        headers = {
            'Content-Type': 'application/json',
            'Authorization': 'hmac %s:' % self.user + digest
        }

        path_parts[1] = urllib.quote(path_parts[1])
        path = ''.join(path_parts)
        re = self.urlopen(method, path, headers=headers, body=body)
        if re.status / 100 != 2:
            raise(ApiServerError(re))
        return re

    def get(self, endpoint, qs=None):
        HMAC = self.HMAC.copy()
        path_parts = ['/v%s/' % self.version, endpoint]
        if qs:
            path_parts.extend(('?', qs))
        path = ''.join(path_parts)
        method = 'GET'
        window = int(time.time()) // 5
        body = ''
        text = '%s %s %s %s' % (window, method, path, body)
        HMAC.update(text)
        digest = base64.urlsafe_b64encode(HMAC.digest())

        headers = {
            'Content-Type': 'application/json',
            'Authorization': 'hmac %s:' % self.user + digest
        }

        path_parts[1] = urllib.quote(path_parts[1])
        path = ''.join(path_parts)
        re = self.urlopen(method, path, headers=headers)
        if re.status != 200:
            raise(ApiServerError(re))
        return re

    def delete(self, endpoint, qs=None, **data):
        HMAC = self.HMAC.copy()
        path_parts = ['/v%s/' % self.version, endpoint]
        if qs:
            path_parts.extend(('?', qs))
        path = ''.join(path_parts)
        method = 'DELETE'
        body = json.dumps(data)
        window = int(time.time()) // 5
        HMAC.update('%s %s %s %s' % (window, method, path, body))
        digest = base64.urlsafe_b64encode(HMAC.digest())

        headers = {
            'Content-Type': 'application/json',
            'Authorization': 'hmac %s:' % self.user + digest
        }

        path_parts[1] = urllib.quote(path_parts[1])
        path = ''.join(path_parts)
        re = self.urlopen(method, path, headers=headers, body=body)
        if re.status != 200:
            raise(ApiServerError(re))
        return re
