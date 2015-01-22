On a Debian(-based) system, install `python3-flask python3-sqlalchemy python3-postgresql python3-greenlet postgresql`

In `pg_hba.conf` (usually at `/etc/postgresql/9.4/main/`), set local access to `trust` (as opposed to the default `peer`)

```bash
git submodule init && git submodule update

sudo -u postgres psql
> create user anirank;
> create database anirank;
> grant all privileges on database anirank to anirank;
sudo invoke-rc.d postgresql restart # for pg_hba.conf change
cp config.py.example config.py

python3 db.py init
./anirank.py
```

Visit http://localhost:9000/
