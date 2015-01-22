import flask

app = flask.Blueprint(__name__, __name__)

@app.route('/')
def home():
	return flask.render_template('home.html')
