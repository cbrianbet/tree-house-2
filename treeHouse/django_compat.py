"""Compatibility shims for running supported Django LTS on newer Python releases."""

from __future__ import annotations

import sys


def patch_base_context_copy_for_python_314() -> None:
    """
    Django 4.2's BaseContext.__copy__ uses ``copy(super())``, which on Python
    3.14+ can yield a copied *super* proxy (no ``dicts``), breaking admin and
    any view that copies template contexts. Upstream fixed this in Django 5.2+.
    """
    if sys.version_info < (3, 14):
        return

    from copy import copy as copy_fn
    from django.template.context import BaseContext

    def __copy__(self):
        duplicate = BaseContext()
        duplicate.__class__ = self.__class__
        duplicate.__dict__ = copy_fn(self.__dict__)
        duplicate.dicts = self.dicts[:]
        return duplicate

    BaseContext.__copy__ = __copy__
