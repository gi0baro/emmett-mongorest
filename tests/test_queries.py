# -*- coding: utf-8 -*-

import pytest

from bson.objectid import ObjectId
from datetime import datetime
from emmett import sdict, current, now
from emmett_mongorest.queries.helpers import (
    JSONQueryPipe,
    AggregateJSONQueryPipe,
    OuterCollector
)
from emmett_mongorest.queries.parser import (
    MongoQuery,
    QueryError,
    parse_conditions,
    parse_aggregate_conditions
)
from pydantic import BaseModel


class Sample(BaseModel):
    string: str = ""
    number: int
    precise: float
    dt: datetime


def test_parse_fields():
    qdict = {
        'string': 'foo'
    }
    parsed = parse_conditions(MongoQuery(), qdict, {'string'})
    assert parsed.result == {'$and': [{'string': 'foo'}]}

    qdict = {
        'string': {'$regex': 'foo'}
    }
    parsed = parse_conditions(MongoQuery(), qdict, {'string'})
    assert parsed.result == {'$and': [{'string': {'$regex': 'foo'}}]}

    qdict = {
        'string': {'$iregex': 'foo'}
    }
    parsed = parse_conditions(MongoQuery(), qdict, {'string'})
    assert parsed.result == {
        '$and': [{'string': {'$regex': 'foo', '$options': 'i'}}]
    }

    qdict = {
        'number': 2
    }
    parsed = parse_conditions(MongoQuery(), qdict, {'number'})
    assert parsed.result == {'$and': [{'number': 2}]}

    qdict = {
        'number': {'$gte': 0, '$lt': 2}
    }
    parsed = parse_conditions(MongoQuery(), qdict, {'number'})
    assert parsed.result == {'$and': [{'number': {'$gte': 0, '$lt': 2}}]}

    qdict = {
        'precise': 2.3
    }
    parsed = parse_conditions(MongoQuery(), qdict, {'precise'})
    assert parsed.result == {'$and': [{'precise': 2.3}]}

    qdict = {
        'precise': {'$gte': 2, '$lt': 5.5}
    }
    parsed = parse_conditions(MongoQuery(), qdict, {'precise'})
    assert parsed.result == {'$and': [{'precise': {'$gte': 2, '$lt': 5.5}}]}

    dt1, dt2 = now(), now().add(days=1)
    qdict = {
        'dt': dt1
    }
    parsed = parse_conditions(MongoQuery(), qdict, {'dt'})
    assert parsed.result == {'$and': [{'dt': dt1}]}

    qdict = {
        'dt': {'$gte': dt1, '$lt': dt2}
    }
    parsed = parse_conditions(MongoQuery(), qdict, {'dt'})
    assert parsed.result == {'$and': [{'dt': {'$gte': dt1, '$lt': dt2}}]}

    qdict = {
        '_id': {'$id': '0' * 24}
    }
    parsed = parse_conditions(MongoQuery(), qdict, {'_id'})
    assert parsed.result == {'$and': [{'_id': {'$eq': ObjectId('0' * 24)}}]}


def test_parse_combined():
    dt1, dt2 = now(), now().add(days=1)
    qdict = {
        'string': 'foo',
        'number': {'$gt': 2},
        '$not': {'number': {'$in': [4, 5]}},
        '$or': [
            {'precise': 3.2},
            {'dt': {'$gte': dt1, '$lt': dt2}}
        ]
    }
    parsed = parse_conditions(
        MongoQuery(), qdict, {'string', 'number', 'precise', 'dt'}
    )
    assert parsed.result == {
        '$and': [{
            'string': 'foo',
            'number': {'$gt': 2},
            '$not': {'number': {'$in': [4, 5]}},
            '$or': [{'precise': 3.2}, {'dt': {'$gte': dt1, '$lt': dt2}}]
        }]
    }

    qdict = {
        '$or': [
            {'precise': 3.2},
            {'dt': {'$gte': dt1, '$lt': dt2}}
        ]
    }
    parsed = parse_conditions(
        MongoQuery(), qdict, {'string', 'number', 'precise', 'dt'}
    )
    assert parsed.result == {
        '$and': [{
            '$or': [
                {'precise': 3.2},
                {'dt': {'$gte': dt1, '$lt': dt2}}
            ]
        }]
    }


def test_parse_geo():
    qdict = {
        '$or': [
            {'string': 'foo'},
            {'geo': {
                '$geo.near': {
                    'coordinates': {'lat': 44.10, 'lon': 16.10},
                    'distance': {'min': 2000, 'max': 5000}}}}
        ]
    }
    parsed = parse_conditions(MongoQuery(), qdict, {'string', 'geo'})
    assert parsed.result == {'$and': [{
        '$or': [
            {'string': 'foo'},
            {'geo': {
                '$near': {
                    '$geometry': {
                        'type': 'Point', 'coordinates': [16.10, 44.10]},
                    '$minDistance': 2000,
                    '$maxDistance': 5000}}}
        ]
    }]}

    qdict = {
        '$or': [
            {'string': 'foo'},
            {'geo': {
                '$geo.within': {
                    'coordinates': [
                        {'lat': 40.0, 'lon': 10.0},
                        {'lat': 40.0, 'lon': 11.0},
                        {'lat': 41.0, 'lon': 11.0},
                        {'lat': 41.0, 'lon': 10.0},
                        {'lat': 40.0, 'lon': 10.0}
                    ]
                }
            }}
        ]
    }
    parsed = parse_conditions(MongoQuery(), qdict, {'string', 'geo'})
    assert parsed.result == {'$and': [{
        '$or': [
            {'string': 'foo'},
            {'geo': {
                '$geoWithin': {
                    '$geometry': {
                        'type': 'Polygon',
                        'coordinates': [[
                            [10.0, 40.0],
                            [11.0, 40.0],
                            [11.0, 41.0],
                            [10.0, 41.0],
                            [10.0, 40.0]
                        ]]
                    },
                }
            }}
        ]
    }]}

    qdict = {
        '$or': [
            {'string': 'foo'},
            {'geo': {
                '$geo.box': {
                    'nw': {'lat': 40.0, 'lon': 10.0},
                    'se': {'lat': 41.0, 'lon': 11.0}
                }
            }}
        ]
    }
    parsed = parse_conditions(MongoQuery(), qdict, {'string', 'geo'})
    assert parsed.result == {'$and': [{
        '$or': [
            {'string': 'foo'},
            {'geo': {
                '$geoWithin': {
                    '$geometry': {
                        'type': 'Polygon',
                        'coordinates': [[
                            [10.0, 40.0],
                            [11.0, 40.0],
                            [11.0, 41.0],
                            [10.0, 41.0],
                            [10.0, 40.0]
                        ]]
                    },
                }
            }}
        ]
    }]}


def test_parse_aggregate_geo():
    qdict = {
        'string': 'foo',
        'geo': {
            '$geo.near': {
                'coordinates': {'lat': 44.10, 'lon': 16.10},
                'distance': {'min': 2000, 'max': 5000}
            }
        }
    }
    outer = OuterCollector()
    parsed = parse_aggregate_conditions(
        MongoQuery(), qdict, {'string', 'geo'}, outer
    )
    assert parsed.result == {'$and': [{'string': 'foo'}]}
    assert outer.data == {
        '$near': [
            ('geo', {
                'near': {
                    'type': 'Point', 'coordinates': [16.1, 44.1]
                },
                'spherical': False,
                'distanceField': 'distance',
                'maxDistance': 5000,
                'minDistance': 2000
            })
        ]
    }

    qdict = {
        '$or': [
            {'string': 'foo'},
            {'geo': {
                '$geo.near': {
                    'coordinates': {'lat': 44.10, 'lon': 16.10},
                    'distance': {'min': 2000, 'max': 5000}}}}
        ]
    }
    with pytest.raises(QueryError) as exc:
        parse_aggregate_conditions(MongoQuery(), qdict, {'string', 'geo'})
    assert exc.value.op == '$geo.near'

    qdict = {
        'string': 'foo',
        'geo': {
            '$geo.within': {
                'coordinates': [
                    {'lat': 40.0, 'lon': 10.0},
                    {'lat': 40.0, 'lon': 11.0},
                    {'lat': 41.0, 'lon': 11.0},
                    {'lat': 41.0, 'lon': 10.0},
                    {'lat': 40.0, 'lon': 10.0}
                ]
            }
        }
    }
    outer = OuterCollector()
    parsed = parse_aggregate_conditions(
        MongoQuery(), qdict, {'string', 'geo'}, outer
    )
    assert not outer.data
    assert parsed.result == {
        '$and': [{
            'string': 'foo',
            'geo': {
                '$geoWithin': {
                    '$geometry': {
                        'type': 'Polygon',
                        'coordinates': [[
                            [10.0, 40.0],
                            [11.0, 40.0],
                            [11.0, 41.0],
                            [10.0, 41.0],
                            [10.0, 40.0]
                        ]]
                    }
                }
            }
        }]
    }

    qdict = {
        'string': 'foo',
        'geo': {
            '$geo.box': {
                'nw': {'lat': 40.0, 'lon': 10.0},
                'se': {'lat': 41.0, 'lon': 11.0}
            }
        }
    }
    outer = OuterCollector()
    parsed = parse_aggregate_conditions(
        MongoQuery(), qdict, {'string', 'geo'}, outer
    )
    assert not outer.data
    assert parsed.result == {
        '$and': [{
            'string': 'foo',
            'geo': {
                '$geoWithin': {
                    '$geometry': {
                        'type': 'Polygon',
                        'coordinates': [[
                            [10.0, 40.0],
                            [11.0, 40.0],
                            [11.0, 41.0],
                            [10.0, 41.0],
                            [10.0, 40.0]
                        ]]
                    },
                }
            }
        }]
    }


async def _fake_pipe(**kwargs):
    return kwargs


@pytest.mark.asyncio
async def test_pipes(db, json_dump):
    fake_mod = sdict(
        _queryable_fields=['string', 'number', 'geo'],
        model=Sample,
        ext=sdict(
            config=sdict(
                query_param='where'
            )
        )
    )
    pipe = JSONQueryPipe(fake_mod)
    pipe_aggr = AggregateJSONQueryPipe(fake_mod)

    qdict = {
        '$or': [
            {'string': 'bar'},
            {'number': {'$gt': 0}},
            {'geo': {
                '$geo.near': {
                    'coordinates': {'lat': 44.10, 'lon': 16.10},
                    'distance': {'min': 2000, 'max': 5000}
                }
            }}
        ]
    }
    current.request = sdict(
        query_params=sdict(
            where=json_dump(qdict)
        )
    )
    res = await pipe.pipe_request(_fake_pipe, query=MongoQuery())
    assert res['query'].result == {'$and': [{
        '$or': [
            {'string': 'bar'},
            {'number': {'$gt': 0}},
            {'geo': {
                '$near': {
                    '$geometry': {
                        'type': 'Point', 'coordinates': [16.10, 44.10]},
                    '$minDistance': 2000,
                    '$maxDistance': 5000}}}
        ]
    }]}
    assert 'aggregation_steps' not in res

    qdict = {
        'string': 'foo',
        'number': {'$gt': 0},
        'geo': {
            '$geo.near': {
                'coordinates': {'lat': 44.10, 'lon': 16.10},
                'distance': {'min': 2000, 'max': 5000}
            }
        }
    }
    current.request = sdict(
        query_params=sdict(
            where=json_dump(qdict)
        )
    )
    res = await pipe_aggr.pipe_request(_fake_pipe, query=MongoQuery())
    assert res['query'].result == {'$and': [{
        'string': 'foo',
        'number': {'$gt': 0}
    }]}
    assert res['aggregation_steps'] == [{
        '$geoNear': {
            'key': 'geo',
            'near': {
                'type': 'Point', 'coordinates': [16.1, 44.1]
            },
            'spherical': False,
            'distanceField': 'distance',
            'maxDistance': 5000,
            'minDistance': 2000
        }
    }]
