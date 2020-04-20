# -*- coding: utf-8 -*-
"""
    emmett_mongorest.queries.helpers
    --------------------------------

    Provides REST query language helpers

    :copyright: 2019 Giovanni Barillari
    :license: BSD-3-Clause
"""

from emmett import request, response, sdict
from emmett_rest.queries.errors import QueryError
from emmett_rest.queries.helpers import JSONQueryPipe as _JSONQueryPipe

from .parser import (
    OuterCollector,
    parse_conditions as _parse_conditions,
    parse_aggregate_conditions as _parse_aggregate_conditions
)


class JSONQueryPipe(_JSONQueryPipe):
    def _build_query_ctx(self):
        return sdict()

    def _build_query(self, query, param, ctx):
        return _parse_conditions(query, param, self._accepted_set, **ctx)

    def _apply_query(self, query, ctx, params):
        params['query'] = query

    def _after_query(self, query, ctx, params):
        pass

    async def pipe_request(self, next_pipe, **kwargs):
        if request.query_params[self.query_param] and self._accepted_set:
            try:
                input_condition = self._parse_where_param(
                    request.query_params[self.query_param]
                )
            except ValueError:
                response.status = 400
                return self.mod.error_400({'where': 'invalid value'})
            ctx = self._build_query_ctx()
            try:
                query = self._build_query(
                    kwargs['query'], input_condition, ctx
                )
            except QueryError as exc:
                response.status = 400
                return self.mod.error_400({'where': exc.gen_msg()})
            try:
                self._apply_query(query, ctx, kwargs)
                self._after_query(query, ctx, kwargs)
            except ValueError:
                response.status = 400
                return self.mod.error_400({'where': 'invalid value'})
        return await next_pipe(**kwargs)


class AggregateJSONQueryPipe(JSONQueryPipe):
    _aggr_remaps = {
        '$near': '$geoNear'
    }

    def _remap_outer(self, data):
        rv = []
        for key in set(data.keys()) & set(self._aggr_remaps.keys()):
            for field, q in data[key]:
                op_key = self._aggr_remaps[key]
                q['key'] = field
                rv.append({op_key: q})
        return rv

    def _build_query_ctx(self):
        return sdict(outer=OuterCollector())

    def _build_query(self, query, param, ctx):
        return _parse_aggregate_conditions(
            query, param, self._accepted_set, **ctx
        )

    def _after_query(self, query, ctx, params):
        params['aggregation_steps'] = self._remap_outer(ctx.outer.data)

    def pipe_request(self, next_pipe, **kwargs):
        kwargs['aggregation_steps'] = []
        return super().pipe_request(next_pipe, **kwargs)
