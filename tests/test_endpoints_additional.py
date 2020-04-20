# -*- coding: utf-8 -*-

import pytest

from pydantic import BaseModel
from typing import Optional


class Sample(BaseModel):
    string: Optional[str] = None
    number: int = 0
    precise: float = 0.0


@pytest.fixture(scope='function')
def rest_app(app, db):
    app.pipeline = [db.pipe]
    mod = app.mongorest_module(
        __name__, 'sample', Sample, db.samples, url_prefix='sample',
        enabled_methods=['group', 'stats', 'sample']
    )
    mod.grouping_allowed_fields = ['string']
    mod.stats_allowed_fields = ['number', 'precise']
    return app


@pytest.fixture(scope='function', autouse=True)
def db_sample(db):
    with db.connection():
        db.samples.insert_many([
            Sample(string='foo').dict(),
            Sample(string='foo', number=5, precise=5.0).dict(),
            Sample(string='bar', number=10, precise=10.0).dict()
        ])


@pytest.fixture(scope='function')
def client(rest_app):
    return rest_app.test_client()


def test_grouping(client, json_load):
    req = client.get(
        '/sample/group/string',
        query_string={'sort_by': '-count'}
    )
    assert req.status == 200

    data = json_load(req.data)
    assert data['meta']['total_objects'] == 2

    assert data['data'][0]['value'] == 'foo'
    assert data['data'][0]['count'] == 2
    assert data['data'][1]['value'] == 'bar'
    assert data['data'][1]['count'] == 1


def test_stats(client, json_load):
    req = client.get(
        '/sample/stats',
        query_string={'fields': 'number,precise'}
    )
    assert req.status == 200

    data = json_load(req.data)
    assert data['number']['min'] == 0
    assert data['number']['max'] == 10
    assert data['number']['avg'] == 5
    assert data['precise']['min'] == 0.0
    assert data['precise']['max'] == 10.0
    assert data['precise']['avg'] == 5.0


def test_sample(client, json_load):
    req = client.get('/sample/sample')
    assert req.status == 200

    data = json_load(req.data)
    assert data['meta']['total_objects'] == 3
    assert not data['meta']['has_more']
