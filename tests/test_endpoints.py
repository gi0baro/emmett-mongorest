# -*- coding: utf-8 -*-

import pytest

from datetime import datetime
from emmett import sdict
from pydantic import BaseModel


class Sample(BaseModel):
    string: str = ""
    number: int
    precise: float
    dt: datetime


@pytest.fixture(scope='function')
def rest_app(app, db):
    app.pipeline = [db.pipe]
    app.mongorest_module(
        __name__, 'sample', Sample, db.samples, url_prefix='sample'
    )
    return app


@pytest.fixture(scope='function', autouse=True)
def db_sample(db):
    with db.connection():
        db.samples.insert_one(
            Sample(
                string="foo",
                number=1,
                precise=3.14,
                dt=datetime(1955, 11, 12)
            ).dict()
        )


@pytest.fixture(scope='function')
def client(rest_app):
    return rest_app.test_client()


@pytest.fixture(scope='function')
def row(db):
    with db.connection():
        row = db.samples.find_one({})
    return row


def test_index(client, json_load):
    req = client.get('/sample')
    assert req.status == 200

    data = json_load(req.data)
    assert {'data', 'meta'} == set(data.keys())
    assert {'id', 'string', 'number', 'precise', 'dt'} == set(
        data['data'][0].keys())
    assert data['meta']['total_objects'] == 1
    assert not data['meta']['has_more']


def test_get(client, json_load, row):
    req = client.get(f"/sample/{row['_id']}")
    assert req.status == 200

    data = json_load(req.data)
    assert {'id', 'string', 'number', 'precise', 'dt'} == set(
        data.keys())


def test_create(client, json_load, json_dump):
    body = sdict(
        string='bar',
        number=2,
        precise=1.1,
        dt=datetime(2000, 1, 1)
    )
    req = client.post(
        '/sample',
        data=json_dump(body),
        headers=[('content-type', 'application/json')]
    )
    assert req.status == 201

    data = json_load(req.data)
    assert data['id']
    assert data['string'] == 'bar'

    #: validation tests
    body = sdict(
        string='bar',
        number='foo',
        precise=1.1,
        dt=datetime(2000, 1, 1)
    )
    req = client.post(
        '/sample',
        data=json_dump(body),
        headers=[('content-type', 'application/json')]
    )
    assert req.status == 422

    data = json_load(req.data)
    assert data['errors']['number']


def test_update(client, json_load, json_dump):
    body = sdict(
        string='bar',
        number=2,
        precise=1.1,
        dt=datetime(2000, 1, 1)
    )
    req = client.post(
        '/sample',
        data=json_dump(body),
        headers=[('content-type', 'application/json')]
    )

    data = json_load(req.data)
    rid = data['id']

    change = sdict(
        string='baz'
    )
    req = client.put(
        f'/sample/{rid}',
        data=json_dump(change),
        headers=[('content-type', 'application/json')]
    )
    assert req.status == 200

    data = json_load(req.data)
    assert data['string'] == 'baz'

    #: validation tests
    change = sdict(
        number='baz'
    )
    req = client.put(
        f'/sample/{rid}',
        data=json_dump(change),
        headers=[('content-type', 'application/json')]
    )
    assert req.status == 422

    data = json_load(req.data)
    assert data['errors']['number']


def test_delete(client, db, row):
    req = client.delete(
        f"/sample/{row['_id']}",
        headers=[('content-type', 'application/json')]
    )
    assert req.status == 200

    with db.connection():
        assert not db.samples.count({})
