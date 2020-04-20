# -*- coding: utf-8 -*-
"""
    emmett_mongorest.queries.validation
    -----------------------------------

    Provides REST query language validation

    :copyright: 2019 Giovanni Barillari
    :license: BSD-3-Clause
"""

from __future__ import annotations

from datetime import datetime
from typing import Any, Dict

from emmett.ctx import current
from emmett_rest.queries.validation import (
    op_validation_generator,
    validate_default,
    validate_glue
)


def validate_geo_set(v: Any) -> Dict[str, Any]:
    assert isinstance(v, dict)
    assert 'coordinates' in v
    assert isinstance(v['coordinates'], list)
    coords = []
    for coord_dict in v['coordinates']:
        assert isinstance(coord_dict, dict)
        lat, lon = coord_dict.get('lat'), coord_dict.get('lon')
        assert isinstance(lat, float)
        assert isinstance(lon, float)
        coords.append([lon, lat])
    return {'$geometry': {'type': 'Polygon', 'coordinates': [coords]}}


def validate_geo_near(v: Any) -> Dict[str, Any]:
    assert isinstance(v, dict)
    rv = {'$geometry': {'type': 'Point'}}
    assert 'coordinates' in v
    assert isinstance(v['coordinates'], dict)
    lat, lon = v['coordinates'].get('lat'), v['coordinates'].get('lon')
    assert isinstance(lat, float)
    assert isinstance(lon, float)
    rv['$geometry']['coordinates'] = [lon, lat]
    if 'distance' in v:
        assert isinstance(v['distance'], dict)
        if 'max' in v['distance']:
            assert isinstance(v['distance']['max'], int)
            rv['$maxDistance'] = min(
                v['distance']['max'],
                current.app.ext.MongoREST.config.geo_near_max_distance
            )
        if 'min' in v['distance']:
            assert isinstance(v['distance']['min'], int)
            rv['$minDistance'] = v['distance']['min']
    return rv


def validate_geo_near_aggregate(v: Any) -> Dict[str, Any]:
    assert isinstance(v, dict)
    rv = {
        'near': {'type': 'Point'},
        'spherical': False,
        'distanceField': 'distance'}
    assert 'coordinates' in v
    assert isinstance(v['coordinates'], dict)
    lat, lon = v['coordinates'].get('lat'), v['coordinates'].get('lon')
    assert isinstance(lat, float)
    assert isinstance(lon, float)
    rv['near']['coordinates'] = [lon, lat]
    if 'distance' in v:
        assert isinstance(v['distance'], dict)
        if 'max' in v['distance']:
            assert isinstance(v['distance']['max'], int)
            rv['maxDistance'] = min(
                v['distance']['max'],
                current.app.ext.MongoREST.config.geo_near_max_distance
            )
        if 'min' in v['distance']:
            assert isinstance(v['distance']['min'], int)
            rv['minDistance'] = v['distance']['min']
    return rv


def validate_geo_box(v: Any) -> Dict[str, Any]:
    assert isinstance(v, dict)
    assert set(v.keys()) == {'nw', 'se'}
    points = []
    for key in ['nw', 'se']:
        assert isinstance(v[key], dict)
        lat, lon = v[key].get('lat'), v[key].get('lon')
        assert isinstance(lat, float)
        assert isinstance(lon, float)
        points.append([lon, lat])
    points.insert(1, [points[1][0], points[0][1]])
    points.append([points[0][0], points[-1][1]])
    points.append([points[0][0], points[0][1]])
    return {'$geometry': {'type': 'Polygon', 'coordinates': [points]}}


op_validators = {
    '$and': validate_glue,
    '$or': validate_glue,
    '$nor': validate_glue,
    '$eq': validate_default,
    '$not': op_validation_generator(dict),
    '$ne': validate_default,
    '$in': op_validation_generator(list),
    '$nin': op_validation_generator(list),
    '$lt': op_validation_generator(int, float, datetime),
    '$gt': op_validation_generator(int, float, datetime),
    '$lte': op_validation_generator(int, float, datetime),
    '$gte': op_validation_generator(int, float, datetime),
    '$exists': op_validation_generator(bool),
    '$regex': validate_default,
    '$iregex': validate_default,
    '$id': validate_default,
    '$id.in': op_validation_generator(list),
    '$all': op_validation_generator(list),
    '$match': op_validation_generator(dict),
    '$size': op_validation_generator(int),
    '$geo.intersect': validate_geo_set,
    '$geo.within': validate_geo_set,
    '$geo.near': validate_geo_near,
    '$geo.box': validate_geo_box
}

op_validators_aggregate = {key: val for key, val in op_validators.items()}
op_validators_aggregate['$geo.near'] = validate_geo_near_aggregate
