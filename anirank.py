#!/usr/bin/env python3

import eventlet
eventlet.monkey_patch()

import os

import cleancss
import flask
import eventlet.wsgi

import config
import db

app = flask.Flask(__name__)
app.secret_key = config.secret_key
flask.Response.autocorrect_location_header = False

css_path = os.path.join(os.path.dirname(__file__), 'static', 'css')
@app.route('/css/<filename>')
def css(filename):
	root, _ = os.path.splitext(filename)
	abs_path = os.path.join(css_path, root) + '.ccss'
	with open(abs_path, 'r') as f:
		return cleancss.convert(f), 200, {'Content-Type': 'text/css'}

@app.teardown_appcontext
def shutdown_session(exception=None):
	db.session.remove()

if __name__ == '__main__':
	import routes
	app.register_blueprint(routes.app)

	if config.debug:
		app.run(host=config.web_host, port=config.web_port, debug=True)
	else:
		listener = eventlet.listen((config.web_host, config.web_port))
		eventlet.wsgi.server(listener, app)
