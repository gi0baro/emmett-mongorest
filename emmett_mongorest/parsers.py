# -*- coding: utf-8 -*-
"""
    emmett_mongorest.parsers
    ------------------------

    Provides REST de-serialization tools

    :copyright: 2019 Giovanni Barillari
    :license: BSD-3-Clause
"""

from emmett_rest.parsers import Parser as _Parser


class Parser(_Parser):
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
        for key in (
            set(dir(self)) - set(self._all_vparsers_.keys()) -
            set(self._all_procs_.keys())
        ):
            if not key.startswith('_') and callable(getattr(self, key)):
                _attrs_override_.append(key)
        self._attrs_override_ = _attrs_override_
        self._init()
