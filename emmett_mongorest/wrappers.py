# -*- coding: utf-8 -*-
"""
    emmett_mongorest.wrappers
    -------------------------

    Provides wrappers for the MongoREST extension

    :copyright: 2019 Giovanni Barillari
    :license: BSD-3-Clause
"""

from typing import Callable, List, Optional, Type, Union

from emmett import App
from emmett.extensions import Extension
from emmett_mongo.db import Collection
from emmett_rest.typing import ParserType, SerializerType
from pydantic import BaseModel

from .rest import AppModule, MongoRESTModule


def wrap_module_from_app(ext: Extension) -> Callable[..., MongoRESTModule]:
    def rest_module_from_app(
        app: App,
        import_name: str,
        name: str,
        model: Type[BaseModel],
        collection: Collection,
        serializer: Optional[SerializerType] = None,
        parser: Optional[ParserType] = None,
        enabled_methods: Optional[List[str]] = None,
        disabled_methods: Optional[List[str]] = None,
        list_envelope: Optional[str] = None,
        single_envelope: Optional[Union[str, bool]] = None,
        meta_envelope: Optional[str] = None,
        groups_envelope: Optional[str] = None,
        use_envelope_on_parse: Optional[bool] = None,
        serialize_meta: Optional[bool] = None,
        url_prefix: Optional[str] = None,
        hostname: Optional[str] = None,
        module_class: Optional[Type[MongoRESTModule]] = None
    ) -> MongoRESTModule:
        module_class = module_class or ext.config.default_module_class
        return module_class.from_app(
            ext, import_name, name, model, collection, serializer, parser,
            enabled_methods, disabled_methods,
            list_envelope, single_envelope,
            meta_envelope, groups_envelope,
            use_envelope_on_parse, serialize_meta,
            url_prefix, hostname
        )
    return rest_module_from_app


def wrap_module_from_module(ext: Extension) -> Callable[..., MongoRESTModule]:
    def rest_module_from_module(
        mod: AppModule,
        import_name: str,
        name: str,
        model: Type[BaseModel],
        collection: Collection,
        serializer: Optional[SerializerType] = None,
        parser: Optional[ParserType] = None,
        enabled_methods: Optional[List[str]] = None,
        disabled_methods: Optional[List[str]] = None,
        list_envelope: Optional[str] = None,
        single_envelope: Optional[Union[str, bool]] = None,
        meta_envelope: Optional[str] = None,
        groups_envelope: Optional[str] = None,
        use_envelope_on_parse: Optional[bool] = None,
        serialize_meta: Optional[bool] = None,
        url_prefix: Optional[str] = None,
        hostname: Optional[str] = None,
        module_class: Optional[Type[MongoRESTModule]] = None
    ) -> MongoRESTModule:
        module_class = module_class or ext.config.default_module_class
        return module_class.from_module(
            ext, mod, import_name, name, model, collection, serializer, parser,
            enabled_methods, disabled_methods,
            list_envelope, single_envelope,
            meta_envelope, groups_envelope,
            use_envelope_on_parse, serialize_meta,
            url_prefix, hostname
        )
    return rest_module_from_module
