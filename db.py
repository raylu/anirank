import binascii
from collections import defaultdict
import hashlib
import os
from itertools import filterfalse, tee

import sqlalchemy
from sqlalchemy import Column, Date, DateTime, Enum, ForeignKey, Integer, String, desc
from sqlalchemy.dialects import postgresql
from sqlalchemy.orm import relationship, joinedload
import sqlalchemy.ext.declarative

import config

import postgresql.clientparameters as psqlcp
psqlcp.default_host = None
engine = sqlalchemy.create_engine(sqlalchemy.engine.url.URL(
	drivername='postgresql+pypostgresql',
	username=config.db_user,
	database=config.database,
	query={'unix': '/var/run/postgresql/.s.PGSQL.5432', 'port': None}
), echo=config.debug)
session = sqlalchemy.orm.scoped_session(sqlalchemy.orm.sessionmaker(
		autocommit=False, autoflush=False, bind=engine))
Base = sqlalchemy.ext.declarative.declarative_base()
Base.query = session.query_property()

class User(Base):
	__tablename__ = 'users'
	id = Column(Integer, primary_key=True)
	username = Column(String(64), nullable=False, unique=True)
	password = Column(sqlalchemy.types.CHAR(128), nullable=False)
	salt = Column(sqlalchemy.types.CHAR(32), nullable=False)
	email = Column(String(64), nullable=False, unique=True)
	flags = Column(Integer, nullable=False, default=0)

	def animelist(self):
		return session.query(Animelist).options(joinedload(Animelist.anime)) \
				.filter(Animelist.user_id==self.id).order_by(desc(Animelist.last_updated))

	@staticmethod
	def hash_pw(password, salt=None):
		if salt is None:
			salt = os.urandom(16)
		hashed = hashlib.pbkdf2_hmac('sha512', password.encode('utf-8'), salt, 100000)
		hashed_hex = binascii.hexlify(hashed).decode()
		salt_hex = binascii.hexlify(salt).decode()
		return hashed_hex, salt_hex

	@staticmethod
	def register(username, password, email):
		password, salt = User.hash_pw(password)
		user = User(username=username, password=password, salt=salt, email=email)
		session.add(user)
		session.commit()
		return user

	@staticmethod
	def login(username, password):
		user = session.query(User).filter(User.username==username).first()
		if not user:
			return
		hashed, _ = User.hash_pw(password, binascii.unhexlify(user.salt.encode()))
		if hashed == user.password:
			return user

	def __repr__(self):
		return '<User(id=%r, username=%r)>' % (self.id, self.username)

class Anime(Base):
	__tablename__ = 'anime'
	id = Column(Integer, primary_key=True, autoincrement=False)
	title = Column(String(128), nullable=False)
	synonyms = Column(postgresql.ARRAY(String(128)), nullable=True)
	type = Column(Enum('TV', 'movie', 'OVA', 'ONA', 'special', 'music', name='anime_type'), nullable=False)
	status = Column(Enum('finished', 'airing', 'not yet aired', name='anime_status'), nullable=False)
	start = Column(Date, nullable=True)
	end = Column(Date, nullable=True)
	episodes = Column(Integer, nullable=True)
	image = Column(String(64), nullable=False)

class Animelist(Base):
	__tablename__ = 'animelist'
	user_id = Column(Integer, ForeignKey('users.id'), primary_key=True)
	anime_id = Column(Integer, ForeignKey('anime.id'), primary_key=True)
	status = Column(Enum('watching', 'completed', 'on hold', 'dropped', 'plan to watch',
			name='animelist_status'), nullable=False)
	episodes = Column(Integer, nullable=False)
	mal_score = Column(Integer, nullable=True)
	last_updated = Column(DateTime, nullable=False)
	score = Column(Integer, nullable=True)
	seriousness = Column(Integer, nullable=True)

	anime = relationship('Anime')

	@staticmethod
	def diff(user_id1, user_id2):
		entries = session.query(Animelist).options(joinedload(Animelist.anime)).filter(
			Animelist.user_id.in_([user_id1, user_id2]))
		entry_maps = [{}, {}]
		ratings = defaultdict(int)
		for entry in entries:
			if entry.user_id == user_id1:
				entry_maps[0][entry.anime_id] = entry
			else:
				entry_maps[1][entry.anime_id] = entry
			if entry.score is not None and entry.seriousness is not None:
				ratings[entry.anime_id] += 1
		shared_anime_ids = set(entry_maps[0]).intersection(entry_maps[1].keys())

		unique = [[], []]
		shared = [[], []]
		for i, entry_map in enumerate(entry_maps):
			for anime_id, entry in entry_map.items():
				if anime_id in shared_anime_ids:
					shared[i].append(entry)
				else:
					unique[i].append(entry)
		rated = [[], []]
		for anime_id in shared_anime_ids:
			if ratings[anime_id] == 2:
				for i in range(2):
					rated[i].append(entry_maps[i][anime_id])
		return unique, shared, rated

	@staticmethod
	def get_vector(a, b):
		score_diff = b.score - a.score
		seriousness_diff = b.seriousness - a.seriousness
		return score_diff, seriousness_diff

	@staticmethod
	def get_vectors(entries):
		for i, entry in enumerate(entries):
			for other_entry in entries[i:]:
				yield Animelist.get_vector(entry, other_entry)

	@staticmethod
	def compare_vectors(entries1, entries2):
		user1_score = user1_seriousness = user2_score = user2_seriousness = 0
		for score, seriousness in Animelist.get_vectors(entries1):
			user1_score += score
			user1_seriousness += seriousness
		for score, seriousness in Animelist.get_vectors(entries2):
			user2_score += score
			user2_seriousness += seriousness

		score_diff = abs(user2_score - user1_score) / len(entries1)
		seriousness_diff = abs(user2_seriousness - user1_seriousness) / len(entries1)
		return score_diff, seriousness_diff

	def __repr__(self):
		return '<Animelist(user_id=%r, anime_id=%r)>' % (self.user_id, self.anime_id)

def init_db():
	Base.metadata.create_all(bind=engine)

def drop_db():
	Base.metadata.drop_all(bind=engine)

if __name__ == '__main__':
	import sys
	if len(sys.argv) == 2:
		if sys.argv[1] == 'init':
			init_db()
		elif sys.argv[1] == 'drop':
			drop_db()
