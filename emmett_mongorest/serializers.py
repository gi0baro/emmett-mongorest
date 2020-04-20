# -*- coding: utf-8 -*-
"""
    emmett_mongorest.serializers
    ----------------------------

    Provides REST serialization tools

    :copyright: 2019 Giovanni Barillari
    :license: BSD-3-Clause
"""

from emmett_rest.serializers import Serializer as _Serializer


class Serializer(_Serializer):
    def __init__(self, model):
        self._model = model
        if not self.attributes:
            self.attributes = []
            for fieldname in self._model.__fields__.keys():
                self.attributes.append(fieldname)
            self.attributes += self.include
            for el in self.exclude:
                if el in self.attributes:
                    self.attributes.remove(el)
        _attrs_override_ = []
        for key in dir(self):
            if not key.startswith('_') and callable(getattr(self, key)):
                _attrs_override_.append(key)
        self._attrs_override_ = _attrs_override_
        self._init()

    def id(self, obj):
        return str(obj['_id'])
