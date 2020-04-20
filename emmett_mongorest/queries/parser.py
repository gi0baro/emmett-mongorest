# -*- coding: utf-8 -*-
"""
    emmett_mongorest.queries.parser
    -------------------------------

    Provides REST query language parser

    :copyright: 2019 Giovanni Barillari
    :license: BSD-3-Clause
"""

from __future__ import annotations

from collections import defaultdict
from contextlib import contextmanager
from typing import Any, Callable, Dict, List, Optional, Set

from bson.objectid import ObjectId
from emmett import sdict
from emmett_rest.queries.errors import QueryError

from ..helpers import MongoQuery
from .validation import op_validators, op_validators_aggregate


class OuterCollector:
    __slots__ = ['data']

    def __init__(self, data=None):
        self.data = data if data is not None else defaultdict(list)

    @contextmanager
    def ctx(self, field_key: str):
        inner = self.__class__()
        yield inner
        for key, values in inner.data.items():
            self.data[key].extend([(field_key, val) for val in values])


def _glue_op_parser(
    key: str,
    value: Any,
    result: Dict[str, Any],
    ctx: sdict
) -> List[Dict[str, Any]]:
    if not isinstance(value, list):
        raise QueryError(op=key, value=value)
    return [
        rv for rv in map(
            lambda v: _conditions_parser(
                ctx.op_set,
                ctx.op_validators,
                ctx.op_parsers,
                ctx.op_remap,
                ctx.op_outer,
                v,
                ctx.accepted_set,
                outer=ctx.outer,
                parent=key
            ), value
        ) if rv
    ]


def _dict_op_parser(
    key: str,
    value: Any,
    result: Dict[str, Any],
    ctx: sdict
) -> Dict[str, Any]:
    if not isinstance(value, dict):
        raise QueryError(op=key, value=value)
    return _conditions_parser(
        ctx.op_set,
        ctx.op_validators,
        ctx.op_parsers,
        ctx.op_remap,
        ctx.op_outer,
        value,
        ctx.accepted_set,
        outer=ctx.outer,
        parent=key
    )


def _object_id_parser(
    key: str,
    value: Any,
    result: Dict[str, Any],
    ctx: sdict
) -> ObjectId:
    try:
        value = ObjectId(value)
    except Exception:
        raise QueryError(op=key, value=value)
    return value


def _object_id_list_parser(
    key: str,
    value: Any,
    result: Dict[str, Any],
    ctx: sdict
) -> List[ObjectId]:
    return [
        _object_id_parser(key, element, result, ctx)
        for element in value
    ]


def _iregex_parser(
    key: str,
    value: Any,
    result: Dict[str, Any],
    ctx: sdict
) -> Any:
    result['$options'] = 'i'
    return value


def _geonear_aggr_parser(
    key: str,
    value: Any,
    result: Dict[str, Any],
    ctx: sdict
) -> Any:
    if ctx.parent in ['$or', '$nor']:
        raise QueryError(op=key, value=value)
    return _generic_op_parser(key, value, result, ctx)


def _generic_op_parser(
    key: str,
    value: Any,
    result: Dict[str, Any],
    ctx: sdict
) -> Any:
    op_validator = ctx.op_validators[key]
    try:
        value = op_validator(value)
    except AssertionError as e:
        raise QueryError(op=key, value=value)
    return value


op_parsers = {key: _generic_op_parser for key in op_validators.keys()}
op_parsers.update({
    '$or': _glue_op_parser,
    '$and': _glue_op_parser,
    '$nor': _glue_op_parser,
    '$not': _dict_op_parser,
    '$match': _dict_op_parser,
    '$id': _object_id_parser,
    '$id.in': _object_id_list_parser,
    '$iregex': _iregex_parser
})
op_parsers_aggregate = {key: val for key, val in op_parsers.items()}
op_parsers_aggregate.update({
    '$geo.near': _geonear_aggr_parser
})
op_remap = {key: key for key in op_validators.keys()}
op_remap.update({
    '$match': '$elemMatch',
    '$geo.near': '$near',
    '$geo.within': '$geoWithin',
    '$geo.box': '$geoWithin',
    '$geo.intersect': '$geoIntersect',
    '$id': '$eq',
    '$id.in': '$in',
    '$iregex': '$regex'
})


def _conditions_parser(
    op_set: Set[str],
    op_validators: Dict[str, Callable[[Any], Any]],
    op_parsers: Dict[str, Callable[[str, Any, sdict], Any]],
    op_remap: Dict[str, str],
    op_outer: Set[str],
    query_dict: Dict[str, Any],
    accepted_set: Set[str],
    outer: OuterCollector,
    parent: Optional[str] = None
) -> Dict[str, Any]:
    query, ctx = {}, sdict(
        op_set=op_set,
        op_validators=op_validators,
        op_parsers=op_parsers,
        op_remap=op_remap,
        op_outer=op_outer,
        accepted_set=accepted_set,
        outer=outer,
        parent=parent
    )
    query_key_set = set(query_dict.keys())
    fields_keys = defaultdict(list)
    for key in query_key_set:
        fields_keys[key.split(".")[0]].append((key, query_dict[key]))
    for key in query_key_set & op_outer:
        outer.data[op_remap[key]].append(
            op_parsers[key](key, query_dict[key], query, ctx)
        )
        query_key_set.remove(key)
    for key in query_key_set & op_set:
        query[op_remap[key]] = op_parsers[key](
            key, query_dict[key], query, ctx
        )
    for key in accepted_set & set(fields_keys.keys()):
        for original_key, value in fields_keys[key]:
            if isinstance(value, dict):
                with outer.ctx(original_key) as step_outer:
                    parsed = _conditions_parser(
                        op_set,
                        op_validators,
                        op_parsers,
                        op_remap,
                        op_outer,
                        value,
                        accepted_set,
                        outer=step_outer,
                        parent=parent
                    )
                if not parsed:
                    continue
                query[original_key] = parsed
            else:
                query[original_key] = value
    return query


def _build_scoped_conditions_parser(
    op_validators: Dict[str, Callable[[Any], Any]],
    op_parsers: Dict[str, Callable[[str, Any, sdict], Any]],
    op_remap: Dict[str, str],
    op_outer: Optional[Set[str]] = None
) -> Callable[[MongoQuery, Dict[str, Any], Set[str]], MongoQuery]:
    op_set = set(op_validators.keys())
    op_outer = op_outer or set()

    def scoped(
        query: MongoQuery,
        query_dict: Dict[str, Any],
        accepted_set: Set[str],
        outer: Optional[OuterCollector] = None
    ) -> MongoQuery:
        outer = outer or OuterCollector()
        return query.where(
            _conditions_parser(
                op_set, op_validators, op_parsers, op_remap, op_outer,
                query_dict, accepted_set,
                outer=outer
            )
        )
    return scoped


parse_conditions = _build_scoped_conditions_parser(
    op_validators, op_parsers, op_remap
)
parse_aggregate_conditions = _build_scoped_conditions_parser(
    op_validators_aggregate, op_parsers_aggregate, op_remap, {'$geo.near'}
)
