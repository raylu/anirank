import binascii
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

	def shared_anime(self, other_user):
		anime = session.query(Animelist).filter(
			Animelist.score != None,
			Animelist.seriousness != None,
			(Animelist.user_id==self.id) | (Animelist.user_id==other_user.id))
		t1, t2 = tee(anime)
		pred = lambda x: x.user_id == self.id
		l1 = list(filter(pred, t2))
		l2 = list(filterfalse(pred, t1))
		l1_ids = map(lambda x: x.anime_id, l1)
		l2_ids = map(lambda x: x.anime_id, l2)
		shared_anime_ids = [i for i in l1_ids if i in l2_ids]
		list1 = [a for a in l1 if a.anime_id in shared_anime_ids]
		list2 = [a for a in l2 if a.anime_id in shared_anime_ids]
		return list1, list2

	def get_vectors(self, animelist):
		vectors = {}
		for i, anime in enumerate(animelist):
			for other_anime in animelist[i:]:
				vector = Animelist.get_vector(anime, other_anime)
				vectors[(anime.anime_id, other_anime.anime_id)] = vector
		return vectors

	def compare_vectors(self, other_user):
		l1, l2 = self.shared_anime(other_user)
		if not (l1 and l2):
			return
		vectors1 = self.get_vectors(l1)
		vectors2 = other_user.get_vectors(l2)
		vector_diffs = []
		for key, value in vectors1.items():
			value2 = vectors2[key]
			diff = Animelist.vectors_diff(value, value2)
			vector_diffs.append(diff)
		scores = [v[0] for v in vector_diffs]
		seriousnesses = [v[1] for v in vector_diffs]
		avg_score = sum(scores) / len(scores)
		avg_seriousness = sum(seriousnesses) / len(seriousnesses)
		return avg_score, avg_seriousness

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
	def get_vector(a, b):
		new_score = b.score - a.score
		new_seriousness = b.seriousness - a.seriousness
		return new_score, new_seriousness

	@staticmethod
	def vectors_diff(u, v):
		return u[0] - v[0], u[1] - v[1]

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
