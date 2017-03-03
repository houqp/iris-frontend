# Copyright (c) LinkedIn Corporation. All rights reserved. Licensed under the BSD-2 Clause license.
# See LICENSE in the project root for license information.

import os
import sys
from client import IrisClient, ApiServerError
import yaml
import ujson as json
from flask import Flask, render_template, request, flash, redirect, abort, url_for, make_response, Response
from flask.ext.assets import Environment, Bundle
from jinja2.sandbox import SandboxedEnvironment
import importlib
import logging

from flask.ext.login import UserMixin, LoginManager, login_required, login_user, logout_user, current_user

STATIC_ROOT = os.environ.get('STATIC_ROOT', os.path.abspath(os.path.dirname(__file__)))
app = Flask(__name__,
            template_folder=os.path.join(STATIC_ROOT, 'templates'),
            static_folder=os.path.join(STATIC_ROOT, 'static'))

env = Environment(app)
env.register('jquery_libs',
    Bundle('js/jquery-2.1.4.min.js', 'js/jquery.dataTables.min.js', 'js/handlebars.min.js',
           'js/hopscotch.min.js', output='bundles/jquery.libs.js'))
env.register('bootstrap_libs',
    Bundle('js/bootstrap.min.js', 'js/typeahead.js', 'js/bootstrap-datetimepicker.js',
           output='bundles/bootstrap.libs.js'))
env.register('iris_js',
    Bundle('js/iris.js', filters='rjsmin', output='bundles/iris.js'))
env.register('css_libs',
    Bundle('css/bootstrap.min.css', 'css/bootstrap-datetimepicker.css',
           'css/jquery.dataTables.min.css', 'css/hopscotch.min.css', filters="cssmin",
           output='bundles/libs.css'))
env.register('iris_css', Bundle('css/iris.css', filters="cssmin", output='bundles/iris.css'))
assets_logger = logging.getLogger('webassets')
assets_logger.addHandler(logging.StreamHandler())
assets_logger.setLevel(logging.DEBUG)

auth_manager = None
client = None
client_methods = None


login_manager = LoginManager()
login_manager.init_app(app)
login_manager.login_view = 'login'


def https_redirect():
    if request.path.startswith('/healthcheck'):
        return
    if request.url.startswith('http://'):
        url = request.url.replace('http://', 'https://', 1)
        code = 301
        return redirect(url, code=code)


def build_assets():
    from webassets.script import CommandLineEnvironment
    CommandLineEnvironment(env, assets_logger).build()


def init(config):
    global auth_manager
    global client
    global client_methods
    global healthcheck_path
    healthcheck_path = config.get('healthcheck_path')
    auth_module = config.get('auth', {'module': 'iris_frontend.auth.noauth'})['module']
    auth = importlib.import_module(auth_module)
    auth_manager = getattr(auth, 'Authenticator')(config)

    app.config.update(config['flask'])

    client = IrisClient(**config['api'])
    client_methods = {
        'POST': client.post,
        'GET': client.get,
        'DELETE': client.delete,
        'PUT': client.put
    }

    if not config.get('debug'):
        app.config['SESSION_COOKIE_SECURE'] = True
        app.before_request(https_redirect)
    else:
        build_assets()


def read_config():
    config_path = os.environ.get('CONFIG', sys.argv[1])
    with open(config_path, 'r') as config_file:
        config = yaml.safe_load(config_file)

    if 'init_config_hook' in config:
        try:
            module = config['init_config_hook']
            logging.info('Bootstrapping config using %s' % module)
            getattr(importlib.import_module(module), module.split('.')[-1])(config)
        except ImportError:
            logging.exception('Failed loading config hook %s' % module)

    return config


class User(UserMixin):
    def __init__(self, name):
        self.id = name


@app.errorhandler(ApiServerError)
def handle_server_error(error):
    resp = error.resp
    page = render_template('error.html', path='error', error_code="500",
                           error_status="Internal Server Error",
                           error_text="Received [%s] from iris-api: %s" % (resp.status, resp.reason))
    return make_response(page, 500)

@app.errorhandler(404)
def page_not_found(e):
    return render_template('error.html', path='error', error_code="404", error_status="Not Found"), 404

@app.after_request
def apply_security_headers(response):
    response.headers['X-Frame-Options'] = 'SAMEORIGIN'
    response.headers['X-Content-Type-Options'] = 'nosniff'
    response.headers['X-XSS-Protection'] = '1; mode=block'
    return response


@login_manager.user_loader
def load_user(user):
    return User(user)


@app.route('/login/', methods=['GET', 'POST'])
def login():
    if current_user.is_authenticated:
        return redirect(url_for('index'))

    if request.method == 'GET':
        return render_template('login.html', path="login")
    else:
        username = request.form['username']
        password = request.form['password']

        if auth_manager.authenticate(username, password):
            login_user(User(username))
        else:
            flash('Username or password incorrect')
            return redirect(url_for('login'))

        url = request.args.get('next', '')

        if not url or url.startswith('/'):
            return redirect(url or url_for('index'))
        else:
            return abort(400)


@app.route('/logout/')
@login_required
def logout():
    logout_user()
    return redirect(url_for('login'))


@app.route('/api/v0/<path:endpoint>', methods=['GET', 'POST', 'DELETE', 'PUT'])
@login_required
def post_api_proxy(endpoint):
    qs = request.environ.get('QUERY_STRING')
    try:
        if request.method == 'GET':
            response = client_methods[request.method](endpoint, qs)
        else:
            response = client_methods[request.method](endpoint, qs, **request.get_json())
    except ApiServerError as err:
        return err.resp.data, err.resp.status, [(k, err.resp.headers[k]) for k in err.resp.headers]
    else:
        return response.data, response.status, [('Content-Type', 'application/json;charset=UTF-8')]


@app.route('/')
@login_required
def index():
    return redirect(url_for('incidents'))


@app.route('/plans/')
@app.route('/plans/<name>')
@login_required
def plans(name=None):
    user = current_user.id
    if name:
        modes = json.loads(client.get('modes').data)
        priorities = json.loads(client.get('priorities').data)
        templates = json.loads(client.get('templates').data)
        applications = json.loads(client.get('applications').data)
        return render_template('plan.html', user=user, modes=modes, priorities=priorities, templates=templates, applications=applications)
    else:
        return render_template('plans.html')


@app.route('/user/')
@login_required
def user(methods=['GET']):
    name = current_user.id
    response = client.get('users/' + name)
    if response.status != 200:
        response = client.post('users', name=name)

    user = json.loads(response.data)

    priorities = json.loads(client.get('priorities').data)
    modes = json.loads(client.get('modes').data)
    applications = json.loads(client.get('applications').data)

    for priority in priorities:
        pri = priority['name']
        if pri in user['modes']:
            user['modes'][pri] = {'mode': user['modes'][pri], 'default': False}
        else:
            user['modes'][pri] = {'mode': priority['default_mode'], 'default': True}

    user_modes = user['modes']
    return render_template('user.html', user=name, user_modes=user_modes, priorities=priorities, modes=modes, applications=applications)


@app.route('/users/modes/<action>', methods=['GET', 'POST'])
@login_required
def modes(action):
    # TODO: only allow editing if current_user == name
    return repr(request.form)


@app.route('/incidents/')
@app.route('/incidents/<name>')
@login_required
def incidents(name=None):
    user = current_user.id
    if name:
        return render_template('incident.html', user=user)
    else:
        applications = json.loads(client.get('applications').data)
        return render_template('incidents.html', user=user, applications=applications)


@app.route('/templates/')
@app.route('/templates/<name>')
@login_required
def templates(name=None):
    user = current_user.id
    applications = json.loads(client.get('applications').data)
    modes = json.loads(client.get('modes').data)
    if name:
        return render_template('template.html', user=user, applications=applications, modes=modes)
    else:
        return render_template('templates.html', user=user, applications=applications, modes=modes)


@app.route('/messages/')
@app.route('/messages/<name>')
@login_required
def messages(name=None):
    user = current_user.id
    applications = json.loads(client.get('applications').data)
    if name:
        return render_template('message.html', user=user, applications=applications)
    else:
        priorities = json.loads(client.get('priorities').data)
        return render_template('messages.html', user=user, applications=applications, priorities=priorities)


@app.route('/stats')
def stats():
    return render_template('stats.html')


@app.route('/healthcheck')
def health_check():
    if not healthcheck_path:
        logging.error('healthcheck path not set')
        return Response(status=404, mimetype='text/plain')

    try:
        with open(healthcheck_path) as h:
            return Response(h.read().strip(), mimetype='text/plain')
    except IOError:
        logging.exception('Failed reading healthcheck file')
        return Response(status=404, mimetype='text/plain')


@app.route('/validate/jinja', methods=['POST'])
def validate():
    template_subject = request.form['templateSubject']
    template_body = request.form['templateBody']
    application = request.form['application']
    if not application:
        return json.dumps({'error': 'No application found'}), 400

    app_data = client.get('applications/%s' % application).data
    try:
        app_json = json.loads(app_data)
    except Exception:
        return json.dumps({'error': 'Invalid application config in API'}), 400
    sample_context_str = app_json.get('sample_context')
    if not sample_context_str:
        return json.dumps({'error': 'Missing sample_context from application config'}), 400
    try:
        sample_context = json.loads(sample_context_str)
    except Exception:
        return json.dumps({'error': 'Invalid application sample_context'}), 400

    # TODO: also move iris meta var to api
    iris_sample_context = {
        "message_id": 5456900,
        "target": "user",
        "priority": "Urgent",
        "application": "Autoalerts",
        "plan": "default plan",
        "plan_id": 1843,
        "incident_id": 178293332,
        "template": "default template"
    }
    sample_context['iris'] = iris_sample_context

    environment = SandboxedEnvironment()

    try:
        subject_template = environment.from_string(template_subject)
        body_template = environment.from_string(template_body)
    except Exception as e:
        return json.dumps({'error': str(e), 'lineno': e.lineno}), 500
    else:
        return json.dumps({
            'template_subject': subject_template.render(sample_context),
            'template_body': body_template.render(sample_context)
        })


@app.route('/applications/')
@app.route('/applications/<name>')
@login_required
def applications(name=None):
    user = current_user.id
    applications = json.loads(client.get('applications').data)
    if name:
        return render_template('application.html', user=user, applications=applications)
    else:
        return render_template('applications.html', user=user, applications=applications)


def hms(seconds):
    m, s = divmod(seconds, 60)
    h, m = divmod(m, 60)
    return '%dh %02dm %02ds' % (h, m, s)


app.jinja_env.filters['hms'] = hms

@app.context_processor
def add_extra_footer_items():
    return dict(extra_footer_items=app.config.get('extra_footer_items', ''))


def get_fe_app():
    init(read_config())
    logging.basicConfig()
    return app


if __name__ == '__main__':
    app.debug = True
    app.run(**read_config()['app'])
