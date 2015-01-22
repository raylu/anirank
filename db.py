import binascii
import hashlib
import os

import sqlalchemy
from sqlalchemy import Column, Integer, String
import sqlalchemy.ext.declarative

import config

import postgresql.clientparameters
postgresql.clientparameters.default_host = None
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
