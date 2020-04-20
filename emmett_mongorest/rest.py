# -*- coding: utf-8 -*-
"""
    emmett_mongorest.rest
    ---------------------

    Provides main REST logics

    :copyright: 2019 Giovanni Barillari
    :license: BSD-3-Clause
"""

from __future__ import annotations

import copy

from typing import Any, Awaitable, Callable, Dict, List, Optional, Union, Type

from emmett import AppModule, request, response, sdict
from emmett.extensions import Extension
from emmett.pipeline import Pipe
from emmett_mongo.db import Collection
from emmett_rest.rest import RESTModule as _RESTModule
from emmett_rest.typing import ParserType, SerializerType
from pydantic import BaseModel, ValidationError
from pymongo.errors import OperationFailure, DuplicateKeyError

from .helpers import (
    MongoQuery,
    SetFetcher,
    RecordQueryBuilder,
    RecordFetcher,
    FieldPipe,
    FieldsPipe
)
from .queries import JSONQueryPipe, AggregateJSONQueryPipe


class MongoRESTModule(_RESTModule):
    @classmethod
    def from_app(
        cls,
        ext: Extension,
        import_name: str,
        name: str,
        model: Type[BaseModel],
        collection: Collection,
        serializer: Optional[SerializerType] = None,
        parser: Optional[ParserType] = None,
        enabled_methods: Optional[List] = None,
        disabled_methods: Optional[List] = None,
        list_envelope: Optional[str] = None,
        single_envelope: Optional[Union[str, bool]] = None,
        meta_envelope: Optional[str] = None,
        groups_envelope: Optional[str] = None,
        use_envelope_on_parse: Optional[bool] = None,
        serialize_meta: Optional[bool] = None,
        url_prefix: Optional[str] = None,
        hostname: Optional[str] = None
    ) -> MongoRESTModule:
        return cls(
            ext, name, import_name, model, collection, serializer, parser,
            enabled_methods, disabled_methods,
            list_envelope, single_envelope,
            meta_envelope, groups_envelope,
            use_envelope_on_parse, serialize_meta,
            url_prefix, hostname
        )

    @classmethod
    def from_module(
        cls,
        ext: Extension,
        mod: AppModule,
        import_name: str,
        name: str,
        model: Type[BaseModel],
        collection: Collection,
        serializer: Optional[SerializerType] = None,
        parser: Optional[ParserType] = None,
        enabled_methods: Optional[List] = None,
        disabled_methods: Optional[List] = None,
        list_envelope: Optional[str] = None,
        single_envelope: Optional[Union[str, bool]] = None,
        meta_envelope: Optional[str] = None,
        groups_envelope: Optional[str] = None,
        use_envelope_on_parse: Optional[bool] = None,
        serialize_meta: Optional[bool] = None,
        url_prefix: Optional[str] = None,
        hostname: Optional[str] = None
    ) -> MongoRESTModule:
        if '.' in name:
            raise RuntimeError(
                "Nested app modules' names should not contains dots"
            )
        name = mod.name + '.' + name
        if url_prefix and not url_prefix.startswith('/'):
            url_prefix = '/' + url_prefix
        module_url_prefix = (mod.url_prefix + (url_prefix or '')) \
            if mod.url_prefix else url_prefix
        hostname = hostname or mod.hostname
        return cls(
            ext, name, import_name, model, collection, serializer, parser,
            enabled_methods, disabled_methods,
            list_envelope, single_envelope,
            meta_envelope, groups_envelope,
            use_envelope_on_parse, serialize_meta,
            module_url_prefix, hostname,
            mod.pipeline
        )

    def __init__(
        self,
        ext: Extension,
        name: str,
        import_name: str,
        model: Type[BaseModel],
        collection: Collection,
        serializer: Optional[SerializerType] = None,
        parser: Optional[ParserType] = None,
        enabled_methods: Optional[List] = None,
        disabled_methods: Optional[List] = None,
        list_envelope: Optional[str] = None,
        single_envelope: Optional[Union[str, bool]] = None,
        meta_envelope: Optional[str] = None,
        groups_envelope: Optional[str] = None,
        use_envelope_on_parse: Optional[bool] = None,
        serialize_meta: Optional[bool] = None,
        url_prefix: Optional[str] = None,
        hostname: Optional[str] = None,
        pipeline: List[Pipe] = []
    ):
        self.collection = collection
        super().__init__(
            ext, name, import_name, model, serializer, parser,
            enabled_methods, disabled_methods,
            list_envelope, single_envelope,
            meta_envelope, groups_envelope,
            use_envelope_on_parse, serialize_meta,
            url_prefix, hostname,
            pipeline
        )

    def _init_pipelines(self):
        self._json_query_pipe = JSONQueryPipe(self)
        self._json_aggr_query_pipe = AggregateJSONQueryPipe(self)
        self._group_field_pipe = FieldPipe(self, '_groupable_fields')
        self._stats_field_pipe = FieldsPipe(self, '_statsable_fields')
        self._obj_pipeline = [
            SetFetcher(self),
            RecordQueryBuilder(self),
            RecordFetcher(self)
        ]
        self.index_pipeline = [SetFetcher(self), self._json_query_pipe]
        self.create_pipeline = []
        self.read_pipeline = list(self._obj_pipeline)
        self.update_pipeline = list(self._obj_pipeline)
        self.delete_pipeline = list(self._obj_pipeline)
        self.group_pipeline = [
            self._group_field_pipe,
            SetFetcher(self),
            self._json_aggr_query_pipe
        ]
        self.stats_pipeline = [
            self._stats_field_pipe,
            SetFetcher(self),
            self._json_aggr_query_pipe
        ]
        self.sample_pipeline = [SetFetcher(self), self._json_aggr_query_pipe]


    def _get_dbset(self):
        return MongoQuery()

    async def _get_row(self, query):
        return await self.collection.find_one(query.result)

    @staticmethod
    def get_cursor_pagination(pagination):
        return (pagination[0] - 1) * pagination[1], pagination[1]

    def get_sort(self, default=None, allowed_fields=None):
        pfields = (
            (
                isinstance(request.query_params.sort_by, str) and
                request.query_params.sort_by
            ) or default or self.default_sort
        ).split(',')
        rv = []
        allowed_fields = allowed_fields or self._sortable_dict
        for pfield in pfields:
            direction = 1
            if pfield.startswith('-'):
                pfield = pfield[1:]
                direction = -1
            field = allowed_fields.get(pfield)
            if not field:
                continue
            rv.append((field, direction))
        return rv

    def build_error_422(self, errors=None):
        if errors:
            return {'errors': errors}
        return {'errors': {'request': 'unprocessable entity'}}

    def _build_meta(self, count, pagination):
        page, page_size = pagination
        return {
            'object': 'list',
            'has_more': count > (page * page_size),
            'total_objects': count
        }

    def serialize_with_list_envelope(self, data, pagination, **extras):
        return {self.list_envelope: self.serialize(data, **extras)}

    def serialize_with_list_envelope_and_meta(
        self, data, pagination, count, **extras
    ):
        return {
            self.list_envelope: self.serialize(data, **extras),
            self.meta_envelope: self.build_meta(count, pagination)
        }

    def pack_with_list_envelope_and_meta(self, envelope, data, **extras):
        count = len(data)
        return {
            envelope: data,
            self.meta_envelope: self.build_meta(count, (1, count)),
            **extras
        }

    @staticmethod
    def _reparse_validation_errors(errors, exc):
        for error in exc.errors():
            field = '.'.join([str(loc) for loc in error['loc']])
            errors[field] = error['msg']

    async def validate_creation(self, attrs):
        obj, errors = None, {}
        try:
            for callback in self._before_create_callbacks:
                await callback(attrs)
            obj = self.model(**attrs)
            # await self._after_validate_creation(obj)
        except ValidationError as exc:
            self._reparse_validation_errors(errors, exc)
        # except CustomValidationError as exc:
        #     errors = {exc.field: exc.validation_message}
        return obj, errors

    async def validate_update(self, row, attrs):
        obj, errors = None, {}
        try:
            for callback in self._before_update_callbacks:
                await callback(row, attrs)
            _row = copy.deepcopy(row)
            _row.update(attrs)
            obj = self.model(**_row)
            # await self._after_validate_update(obj, row)
        except ValidationError as exc:
            self._reparse_validation_errors(errors, exc)
        # except CustomValidationError as exc:
        #     errors = {exc.field: exc.validation_message}
        return obj, errors

    async def _index(self, query):
        pagination = self.get_pagination()
        skip, limit = self.get_cursor_pagination(pagination)
        sort = self.get_sort()
        cursor = self.collection.find(query.result, sort=sort)
        try:
            count = await cursor.count()
            rows = await cursor.skip(skip).limit(limit).to_list(length=None)
        except OperationFailure:
            pass
        return self.serialize_many(rows, pagination, count=count)

    async def _create(self):
        response.status = 201
        attrs = await self.parse_params()
        obj, errors = await self.validate_creation(attrs)
        if errors:
            response.status = 422
            return self.error_422(errors=errors)
        try:
            res = await self.collection.insert_one(obj.dict())
        except DuplicateKeyError:
            response.status = 422
            return self.error_422(errors={'record': 'duplicated'})
        row_new = await self.collection.find_one({'_id': res.inserted_id})
        for callback in self._after_create_callbacks:
            await callback(row_new)
        return self.serialize_one(row_new)

    async def _update(self, row):
        attrs = await self.parse_params()
        obj, errors = await self.validate_update(row, attrs)
        if errors:
            response.status = 422
            return self.error_422(errors=errors)
        try:
            row_new = await self.collection.find_one_and_update(
                {'_id': row['_id']},
                {'$set': obj.dict()}
            )
        except DuplicateKeyError:
            response.status = 422
            return self.error_422(errors={'record': 'duplicated'})
        if not row_new:
            response.status = 404
            return self.error_404()
        for callback in self._after_update_callbacks:
            await callback(row, row_new)
        return self.serialize_one(row_new)

    async def _delete(self, row):
        res = await self.collection.delete_one({'_id': row['_id']})
        if not res.deleted_count:
            response.status = 404
            return self.error_404()
        for callback in self._after_delete_callbacks:
            await callback(row)
        return {}

    #: additional routes
    async def _group(self, query, aggregation_steps, field):
        match = query.result
        sort = self.get_sort(
            default='count',
            allowed_fields={'count': 'count'}
        )
        match_steps = [{'$match': match}] if match else []
        steps = aggregation_steps + match_steps + [
            {'$group': {'_id': '${}'.format(field), 'count': {'$sum': 1}}},
            {'$project': {'_id': 0, 'value': '$_id', 'count': 1}},
            {'$sort': {key: val for key, val in sort}}
        ]
        rows = await self.collection.aggregate(steps).to_list(length=None)
        return self.pack_data(self.groups_envelope, rows)

    async def _stats(self, query, aggregation_steps, fields):
        match = query.result
        match_steps = [{'$match': match}] if match else []
        grouper = {'_id': None}
        project = {'_id': 0}
        for field in fields:
            field_no_dots = field.replace('.', '__')
            grouper.update({
                '{}_min'.format(field_no_dots): {'$min': '${}'.format(field)},
                '{}_max'.format(field_no_dots): {'$max': '${}'.format(field)},
                '{}_avg'.format(field_no_dots): {'$avg': '${}'.format(field)}
            })
            project[field] = {
                'min': '${}_min'.format(field_no_dots),
                'max': '${}_max'.format(field_no_dots),
                'avg': '${}_avg'.format(field_no_dots)
            }
        steps = aggregation_steps + match_steps + [
            {'$group': grouper},
            {'$project': project}
        ]
        rows = await self.collection.aggregate(steps).to_list(length=None)
        return rows[0] if rows else {
            field: {'mix': 0, 'max': 0, 'avg': 0} for field in fields
        }

    async def _sample(self, query, aggregation_steps):
        match = query.result
        _, page_size = self.get_pagination()
        match_steps = [{'$match': match}] if match else []
        steps = aggregation_steps + match_steps + [
            {'$sample': {'size': page_size}}
        ]
        rows = await self.collection.aggregate(steps).to_list(length=None)
        return self.serialize_many(rows, (1, page_size), count=len(rows))

    @property
    def allowed_sorts(self) -> List[str]:
        return self._sortable_fields

    @allowed_sorts.setter
    def allowed_sorts(self, val: List[str]):
        self._sortable_fields = val
        self._sortable_dict = {field: field for field in self._sortable_fields}

    def get_dbset(
        self,
        f: Callable[[], MongoQuery]
    ) -> Callable[[], MongoQuery]:
        self._fetcher_method = f
        return f

    def get_row(
        self,
        f: Callable[[MongoQuery], Awaitable[Optional[Dict[str, Any]]]]
    ) -> Callable[[MongoQuery], Awaitable[Optional[Dict[str, Any]]]]:
        self._select_method = f
        return f

    def before_create(
        self,
        f: Callable[[sdict], Awaitable[None]]
    ) -> Callable[[sdict], Awaitable[None]]:
        self._before_create_callbacks.append(f)
        return f

    def before_update(
        self,
        f: Callable[[Dict[str, Any], sdict], Awaitable[None]]
    ) -> Callable[[Dict[str, Any], sdict], Awaitable[None]]:
        self._before_update_callbacks.append(f)
        return f

    def after_create(
        self,
        f: Callable[[Dict[str, Any]], Awaitable[None]]
    ) -> Callable[[Dict[str, Any]], Awaitable[None]]:
        self._after_create_callbacks.append(f)
        return f

    def after_update(
        self,
        f: Callable[[Dict[str, Any], Dict[str, Any]], Awaitable[None]]
    ) -> Callable[[Dict[str, Any], Dict[str, Any]], Awaitable[None]]:
        self._after_update_callbacks.append(f)
        return f

    def after_delete(
        self,
        f: Callable[[Dict[str, Any]], Awaitable[None]]
    ) -> Callable[[Dict[str, Any]], Awaitable[None]]:
        self._after_delete_callbacks.append(f)
        return f
