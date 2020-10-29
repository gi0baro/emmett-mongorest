# -*- coding: utf-8 -*-
"""
    emmett_mongorest.ext
    --------------------

    Provides MongoREST extension for Emmett

    :copyright: 2019 Giovanni Barillari
    :license: BSD-3-Clause
"""

from __future__ import annotations

from typing import Any

from emmett import AppModule
from emmett_rest import REST
from emmett_rest.wrappers import wrap_method_on_obj

from .docs import ApiDocs, ApiDocsModule
from .parsers import Parser
from .rest import MongoRESTModule
from .serializers import Serializer
from .wrappers import wrap_module_from_app, wrap_module_from_module


class MongoREST(REST):
    default_config = {
        **REST.default_config,
        **dict(
            default_module_class=MongoRESTModule,
            default_serializer=Serializer,
            default_parser=Parser,
            id_path="/<str:rid>",
            geo_near_max_distance=250_000
        )
    }

    def on_load(self):
        setattr(AppModule, "mongorest_module", wrap_module_from_module(self))
        self.app.mongorest_module = wrap_method_on_obj(
            wrap_module_from_app(self),
            self.app
        )
        self._docs_modules = {}
        self.docs = ApiDocs(self)

    def docs_module(
        self,
        import_name: str,
        name: str = "api_docs",
        config: str = "api_docs.yml",
        **kwargs: Any
    ) -> ApiDocsModule:
        rv = self.docs.module(
            import_name,
            name,
            config,
            **kwargs
        )
        self._docs_modules[name] = rv
        return rv
