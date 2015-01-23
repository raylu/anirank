import string

import flask
from flask import request, session
from sqlalchemy import desc
from sqlalchemy.orm import joinedload

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
			session['username'] = user.username
			return flask.redirect('/')
		else:
			flask.flash('Invalid username/password combination.')
			return flask.redirect('/login')

@app.route('/logout')
def logout():
	try:
		del session['user_id']
		del session['username']
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
		session['username'] = username
		return flask.redirect('/')

@app.route('/animelist/<username>')
def animelist(username):
	user = db.session.query(db.User).filter(db.User.username==username).one()
	anime = db.session.query(db.Animelist).options(joinedload(db.Animelist.anime)) \
			.filter(db.Animelist.user_id==user.id).order_by(desc(db.Animelist.last_updated))

	statuses = db.Animelist.status.property.columns[0].type.enums
	entries = {}
	for status in statuses:
		entries[status] = []
	for entry in anime:
		entries[entry.status].append(entry)
	return flask.render_template('animelist.html', animelist=entries, statuses=statuses)

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
		# preload the Anime so merging doesn't result in a SELECT for every row
		preload = db.session.query(db.Anime).join(db.Animelist) \
				.filter(db.Animelist.user_id==session['user_id']).all()
		for anime_args, user_status in mal.animelist(username):
			anime = db.Anime(**anime_args)
			if len(preload):
				db.session.merge(anime)
			else:
				db.session.add(anime)
			list_entry = db.Animelist(user_id=session['user_id'], anime_id=anime_args['id'], **user_status)
			list_entries.append(list_entry)
		db.session.commit()
		preload = db.session.query(db.Animelist).filter(db.Animelist.user_id==session['user_id']).all()
		if len(preload):
			for list_entry in list_entries:
				db.session.merge(list_entry)
		else:
			db.session.add_all(list_entries)
		db.session.commit()
		return flask.redirect('/animelist/' + session['username'])
