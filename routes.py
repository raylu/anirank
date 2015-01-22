import string

import flask
from flask import request, session

import db
import mal

app = flask.Blueprint(__name__, __name__)

@app.route('/')
def home():
	return flask.render_template('home.html')

@app.route('/login', methods=['GET', 'POST'])
def login():
	if request.method == 'GET':
		return flask.render_template('login.html')
	else:
		user = db.User.login(request.form['username'], request.form['password'])
		if user:
			session['user_id'] = user.id
			return flask.redirect('/')
		else:
			flask.flash('Invalid username/password combination.')
			return flask.redirect('/login')

@app.route('/logout')
def logout():
	try:
		del session['user_id']
	except KeyError:
		pass
	return flask.redirect('/')

@app.route('/register', methods=['GET', 'POST'])
def register():
	if request.method == 'GET':
		return flask.render_template('register.html')
	else:
		username = request.form.get('username')
		password = request.form.get('password')
		email = request.form.get('email')
		if not username or not password or not email:
			flask.flash('You must provide a username, password, and an email address.')
			return flask.redirect('/register')
		for whitespace in string.whitespace:
			if whitespace in username:
				flask.flash('Whitespace is not allowed in usernames.')
				return flask.redirect('/register')
		if '@' not in email or '.' not in email:
				flask.flash("That doesn't look like a valid e-mail address.")
				return flask.redirect('/register')

		user = db.User.register(username, password, email)
		session.permanent = True
		session['user_id'] = user.id
		return flask.redirect('/')

@app.route('/import', methods=['GET', 'POST'])
def import_mal():
	if 'user_id' not in session:
		return flask.redirect('/login')
	if request.method == 'GET':
		return flask.render_template('import.html')
	else:
		username = request.form.get('username')
		if not username:
			flask.flash('You must provide a MAL username.')
			return flask.redirect('/import')

		list_entries = []
		for anime, user_status in mal.animelist(username):
			db.session.merge(db.Anime(**anime))
			list_entry = db.Animelist(user_id=session['user_id'], anime_id=anime['id'], **user_status)
			list_entries.append(list_entry)
		db.session.commit()
		for list_entry in list_entries:
			db.session.merge(list_entry)
		db.session.commit()
		return flask.redirect('/')
