# -*- coding: utf-8 -*-
"""
    emmett_mongorest.helpers
    ------------------------

    Provides helpers

    :copyright: 2019 Giovanni Barillari
    :license: BSD-3-Clause
"""

from bson.errors import InvalidId
from bson.objectid import ObjectId
from emmett import request, response
from emmett_rest.helpers import (
    ModulePipe,
    FieldPipe as _FieldPipe,
    FieldsPipe as _FieldsPipe,
    SetFetcher as _SetFetcher,
    RecordFetcher as _RecordFetcher
)


class MongoQuery(object):
    __slots__ = ['stack']

    def __init__(self, initial=None):
        self.stack = initial or []

    def where(self, *conditions):
        for condition in conditions:
            self.stack.append(condition)
        return self

    def or_where(self, condition):
        if not self.stack:
            self.stack.append(condition)
        elif len(self.stack) == 1:
            self.stack = [{'$or': [self.stack[0], condition]}]
        else:
            self.stack = [{'$or': [{'$and': list(self.stack)}, condition]}]
        return self

    @property
    def result(self):
        return {'$and': self.stack} if self.stack else {}


class SetFetcher(_SetFetcher):
    async def pipe_request(self, next_pipe, **kwargs):
        kwargs['query'] = self.mod._fetcher_method()
        return await next_pipe(**kwargs)


class RecordQueryBuilder(ModulePipe):
    async def pipe_request(self, next_pipe, **kwargs):
        try:
            kwargs['query'].where({'_id': ObjectId(kwargs['rid'])})
        except (TypeError, InvalidId):
            response.status = 400
            return self.mod.error_400()
        del kwargs['rid']
        return await next_pipe(**kwargs)


class RecordFetcher(_RecordFetcher):
    async def pipe_request(self, next_pipe, **kwargs):
        await self.fetch_record(kwargs)
        if not kwargs['row']:
            response.status = 404
            return self.mod.error_404()
        return await next_pipe(**kwargs)

    async def fetch_record(self, kwargs):
        kwargs['row'] = await self.mod._select_method(kwargs['query'])
        del kwargs['query']


class FieldPipe(_FieldPipe):
    def set_accepted(self):
        self._accepted_dict = {
            val: val for val in getattr(self.mod, self.accepted_attr_name)
        }


class FieldsPipe(_FieldsPipe):
    def parse_fields(self):
        pfields = (
            (
                isinstance(request.query_params[self.param_name], str) and
                request.query_params[self.param_name]
            ) or ''
        ).split(',')
        return list(self._accepted_set & set(pfields))
