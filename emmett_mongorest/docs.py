# -*- coding: utf-8 -*-
"""
    emmett_mongorest.docs
    ---------------------

    Provides docs utils

    :copyright: 2019 Giovanni Barillari
    :license: BSD-3-Clause
"""

from __future__ import annotations

import os
import uuid

from types import MethodType
from typing import Any, Dict, get_type_hints

import click
import rapidjson

from emmett import AppModule, response, url
from emmett._internal import get_root_path
from emmett.app import ymlload, ymlLoader
from emmett.ctx import current
from emmett.html import asis
from emmett.http import HTTPFile
from emmett.serializers import _json_default
from emmett.utils import cachedprop
from markdown2 import markdown
from renoir import Renoir


class ApiDocs:
    def __init__(self, ext):
        self.ext = ext
        self.app = self.ext.app
        self.root_path = get_root_path(__name__)
        self.assets_path = os.path.join(self.root_path, "assets")
        self.templates_path = os.path.join(self.root_path, "templates")
        self.dist_path = os.path.join(self.app.root_path, "assets", "mongorest_docs")
        self.app.templater.register_namespace("mongorest_docs", self.templates_path)
        self.app.command("mongorest_docs", help="Build api docs assets")(
            click.argument("module")(_build_cmd_wrapper(self))
        )

    def module(self, import_name, name, config, **kwargs):
        rv = self.app.module(
            import_name,
            name,
            module_class=ApiDocsModule,
            **kwargs
        )
        rv._init(self, config)
        return rv


class DocsBuilder:
    _types_map = {
        "bool": "boolean",
        "int": "integer",
        "str": "string"
    }
    _example_values = {
        "string": "example value",
        "integer": 88,
        "float": 1.21,
        "any": None,
        "datetime": "1955-11-12T22:04:00+00:00"
    }

    def __init__(self, docs: ApiDocs, module: ApiDocsModule):
        self.docs = docs
        self.rest_ext = docs.ext
        self.module = module
        self.templater = Renoir(path=os.path.join(self.docs.assets_path, "templates"))

    def _json_dumps(self, data: Dict[str, Any]) -> bytes:
        return rapidjson.dumps(
            data,
            default=_json_default,
            datetime_mode=rapidjson.DM_ISO8601 | rapidjson.DM_NAIVE_IS_UTC,
            number_mode=rapidjson.NM_NATIVE | rapidjson.NM_DECIMAL,
            indent=2
        )

    def _build_object_example(
        self,
        fields: Dict[str, str],
        config: Dict[str, Any]
    ) -> Dict[str, Any]:
        rv = {}
        for attr_name, attr_type in fields.items():
            attr_val = config.get("example", {}).get(
                attr_name, self._example_values.get(attr_type)
            )
            if attr_val is not None:
                rv[attr_name] = attr_val
        return rv

    def _remap_types(self, attributes: Dict[str, Any]) -> Dict[str, str]:
        rv = {}
        for key, val in attributes.items():
            element = str(val)
            for rmatch, rsub in self._types_map.items():
                element = element.replace(rmatch, rsub)
            for rmatch, rsub in self.module.config.get("types", {}).items():
                element = element.replace(rmatch, rsub)
            rv[key] = element.lower()
        return rv

    def _get_type_from_obj(self, obj: Any, key: str) -> Any:
        element = getattr(obj, key)
        if isinstance(element, MethodType):
            annotations = get_type_hints(element)
            rv = annotations.get("return", "Any")
        else:
            annotations = get_type_hints(obj)
            rv = annotations.get(key) or "Any"
        if not isinstance(rv, str):
            rv = rv.__name__
        return rv

    def _ctx_module(
        self,
        module: ApiDocsModule,
        config: Dict[str, Any]
    ) -> Dict[str, Any]:
        name = module.name.split(".")[-1]
        attr_s, attr_p = {}, {}
        for attr_key in module.serializer.attributes:
            if attr_key in module.model.__fields__:
                attr_s[attr_key] = module.model.__fields__[attr_key]._type_display()
            elif hasattr(module.model, attr_key):
                attr_s[attr_key] = self._get_type_from_obj(module.model, attr_key)
        for attr_key in module.serializer._attrs_override_:
            if hasattr(module.serializer, attr_key):
                attr_s[attr_key] = self._get_type_from_obj(module.serializer, attr_key)
        for attr_key in module.parser.attributes:
            if attr_key in module.model.__fields__:
                attr_p[attr_key] = module.model.__fields__[attr_key]._type_display()
            elif hasattr(module.model, attr_key):
                attr_p[attr_key] = self._get_type_from_obj(module.model, attr_key)

        return {
            "name": name,
            "description": config.get(
                "description", f"Exposes {name} resources"
            ),
            "path": (
                f"/{module.url_prefix}" if not (module.url_prefix or "").startswith("/")
                else module.url_prefix
            ),
            "hostname": (
                (module.hostname and f"https://{module.hostname}") or
                self.module.config.get("main_url") or ""
            ),
            "headers": self.module.config.get("headers", {}),
            "obj_name": module.model.__name__.lower(),
            "attributes": {
                "serializer": self._remap_types(attr_s),
                "parser": self._remap_types(attr_p),
                "description": config.get("descriptions", {})
            },
            "filters": list(module.query_allowed_fields),
            "sorts": list(module.allowed_sorts),
            "example": {
                "parser": self._build_object_example(
                    self._remap_types(attr_p), config
                ),
                "serializer": self._build_object_example(
                    self._remap_types(attr_s), config
                ),
                "response": self._json_dumps(
                    self._build_object_example(self._remap_types(attr_s), config)
                ),
                "list": self._json_dumps({
                    "data": [
                        self._build_object_example(self._remap_types(attr_s), config)
                    ],
                    "meta": {
                        "object": "list",
                        "total_objects": 1,
                        "has_more": False
                    }
                })
            },
            "enabled_methods": module.enabled_methods
        }

    def _render(self) -> str:
        rendered = []
        for element in self.module.config["tree"]:
            if "default" in element:
                rendered.append(
                    self.templater.render(
                        f"{element['default']}.html",
                        {
                            **self.module.config,
                            **{
                                "page_size": self.rest_ext.config.default_pagesize
                            }
                        }
                    )
                )
            elif "module" in element:
                rendered.append(
                    self.templater.render(
                        "module.html",
                        self._ctx_module(
                            self.docs.app._modules[element["module"]], element
                        )
                    )
                )
            elif "markdown" in element:
                rendered.append(
                    self.templater.render(
                        "markdown.html", {
                            "asis": asis,
                            "content": markdown(
                                element["markdown"],
                                extras=["tables", "fenced-code-blocks", "header-ids"]
                            )
                        }
                    )
                )
        return "\n".join(rendered)

    def build(self):
        contents = self._render()
        if not os.path.exists(self.docs.dist_path):
            os.mkdir(self.docs.dist_path)
        with open(
            os.path.join(self.docs.dist_path, f"{self.module.name}.dist.html"), "w"
        ) as f:
            f.write(contents)


class ApiDocsModule(AppModule):
    def _init(self, ext, config_file):
        self.ext = ext
        self.hash = uuid.uuid4().hex[:7]
        with open(os.path.join(self.app.config_path, config_file), "r") as f:
            self.config = ymlload(f.read(), Loader=ymlLoader)
        self.route("/", name="render", output="str")(self._render)
        self.route(f"/static/<str:hash>/<any:path>", name="static", output="bytes")(
            self._serve_file
        )

    @cachedprop
    def _template_contents(self) -> str:
        with open(os.path.join(self.ext.dist_path, f"{self.name}.dist.html")) as f:
            contents = f.read()
        return contents

    def _render(self):
        response.content_type = "text/html; charset=utf-8"
        return self.app.templater.render(
            "mongorest_docs:docs.html", {
                "current": current,
                "asis": asis,
                "url": url,
                "contents": self._template_contents,
                "title": self.config["title"],
                "code_langs": ["curl", "python"],
                "hash": self.hash
            }
        )

    def _serve_file(self, hash, path):
        full_path = os.path.join(self.ext.assets_path, "public", path)
        raise HTTPFile(
            full_path,
            headers=response.headers,
            cookies=response.cookies
        )


def _build_cmd_wrapper(obj):
    def cmd(module):
        try:
            mod = obj.ext._docs_modules[module]
        except KeyError:
            mod = obj.app._modules[module]
        DocsBuilder(obj, mod).build()
    return cmd
