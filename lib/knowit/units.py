# -*- coding: utf-8 -*-

from pint import UnitRegistry


def _build_unit_registry():
    registry = UnitRegistry()
    registry.define('FPS = 1 * hertz')

    return registry


units = _build_unit_registry()
