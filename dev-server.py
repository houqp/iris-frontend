# Copyright (c) LinkedIn Corporation. All rights reserved. Licensed under the BSD-2 Clause license.
# See LICENSE in the project root for license information.

import gevent.wsgi
import werkzeug.serving


@werkzeug.serving.run_with_reloader
def run_server():
    from iris_frontend.app import init, app, read_config
    app.debug = True
    config = read_config()
    init(config)
    ws = gevent.wsgi.WSGIServer((config['app']['host'], config['app']['port']), app)
    ws.serve_forever()


if __name__ == '__main__':
    run_server()
