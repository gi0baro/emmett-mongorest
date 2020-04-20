# -*- coding: utf-8 -*-

import os
import pytest

from emmett import App, sdict
from emmett.asgi.loops import loops
from emmett.parsers import Parsers
from emmett.serializers import Serializers
from emmett_mongo import Database
from emmett_mongorest import MongoREST


@pytest.fixture(scope='session')
def json_dump():
    return Serializers.get_for('json')


@pytest.fixture(scope='session')
def json_load():
    return Parsers.get_for('json')


@pytest.yield_fixture(scope='session')
def event_loop():
    loop = loops.get_loop('auto')
    yield loop
    loop.close()


@pytest.fixture(scope='session')
def db_config():
    config = sdict()
    config.adapter = 'mongodb'
    config.host = os.environ.get('MONGO_HOST', 'localhost')
    config.port = int(os.environ.get('MONGO_PORT', '27017'))
    config.database = os.environ.get('MONGO_DB', 'test')
    return config


@pytest.fixture(scope='session')
def app(db_config):
    rv = App(__name__)
    rv.config.db = db_config
    rv.use_extension(MongoREST)
    return rv


def _db_teardown_generator(db):
    def teardown():
        with db.connection():
            for name in db.raw.list_collection_names():
                try:
                    db.raw.drop_collection(name)
                except Exception:
                    pass
    return teardown


@pytest.fixture(scope='function')
def db(request, app):
    rv = Database(app)
    rv.define_collections('samples')
    request.addfinalizer(_db_teardown_generator(rv))
    return rv
