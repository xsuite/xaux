# copyright ############################### #
# This file is part of the Xaux package.    #
# Copyright (c) CERN, 2025.                 #
# ######################################### #

import re
import pytest

from xaux import ClassProperty, ClassPropertyMeta, singleton
from xaux.tools.class_property import ClassPropertyDict


# Class definitions
# =================

# We use a few test scenarios:
# ParentCp1(no ClassProperty)   -> ChildCp1(with CP)          -> GrandChildCp1(with extra CP) -> GreatGrandChildCp1(no extra CP)
# ParentCp2(with CP)            -> ChildCp2(no extra CP)      -> GrandChildCp2(with extra CP) -> GreatGrandChildCp2(no extra CP)
# ParentCp3(singleton, with CP) -> ChildCp3(no extra CP)      -> GrandChildCp3(with extra CP) -> GreatGrandChildCp3(no extra CP)
# ParentCp4(singleton, no CP)   -> ChildCp4(with CP)          -> GrandChildCp4(with extra CP) -> GreatGrandChildCp4(no extra CP)
# ParentCp5(with CP)            -> ChildCp5(singleton, no CP) -> GrandChildCp5(with extra CP) -> GreatGrandChildCp5(no extra CP)

class ParentCp1:
    """Test ParentCp1 class for ClassProperty."""

    def __init__(self):
        """ParentCp1 __init__ docstring."""
        self.prop_parent = True


class ChildCp1(ParentCp1, metaclass=ClassPropertyMeta):
    """Test ChildCp1 class for ClassProperty."""

    _classproperty_dependencies = {
        '_cprop1': 1,
        '_cprop2': 2
    }
    rcprop3 = 3 # regular class attribute

    def __init__(self):
        """ChildCp1 __init__ docstring."""
        super().__init__()
        self._prop1 = 10
        self._prop2 = 20
        self.rprop3 = 30 # regular instance attribute

    @ClassProperty
    def cprop1(cls):
        """First class property for ChildCp1."""
        return cls._cprop1

    @ClassProperty
    def cprop2(cls):
        """Second class property for ChildCp1."""
        return cls._cprop2

    @cprop2.setter
    def cprop2(cls, value):
        """Second class property for ChildCp1 (setter)."""
        cls._cprop2 = value

    @cprop2.deleter
    def cprop2(cls):
        """Second class property for ChildCp1 (deleter)."""
        cls._cprop2 = 2

    @property
    def prop1(self):
        """First property for ChildCp1."""
        return self._prop1

    @property
    def prop2(self):
        """Second property for ChildCp1."""
        return self._prop2

    @prop2.setter
    def prop2(self, value):
        """Second property for ChildCp1 (setter)."""
        self._prop2 = value

    @prop2.deleter
    def prop2(self):
        """Second property for ChildCp1 (deleter)."""
        self._prop2 = 20


class GrandChildCp1(ChildCp1):
    """Test GrandChildCp1 class for ClassProperty."""

    _classproperty_dependencies = {
        '_cprop4': -1,
        '_cprop5': -2
    }
    rcprop6 = -3 # regular class attribute

    def __init__(self):
        """GrandChildCp1 __init__ docstring."""
        super().__init__()
        self._prop4 = -10
        self._prop5 = -20
        self.rprop6 = -30 # regular instance attribute

    @ClassProperty
    def cprop4(cls):
        """Fourth class property for GrandChildCp1."""
        return cls._cprop4

    @ClassProperty
    def cprop5(cls):
        """Fifth class property for GrandChildCp1."""
        return cls._cprop5

    @cprop5.setter
    def cprop5(cls, value):
        """Fifth class property for GrandChildCp1 (setter)."""
        cls._cprop5 = value

    @cprop5.deleter
    def cprop5(cls):
        """Fifth class property for GrandChildCp1 (deleter)."""
        cls._cprop5 = -2

    @property
    def prop4(self):
        """Fourth property for GrandChildCp1."""
        return self._prop4

    @property
    def prop5(self):
        """Fifth property for GrandChildCp1."""
        return self._prop5

    @prop5.setter
    def prop5(self, value):
        """Fifth property for GrandChildCp1 (setter)."""
        self._prop5 = value

    @prop5.deleter
    def prop5(self):
        """Fifth property for GrandChildCp1 (deleter)."""
        self._prop5 = -20


class GreatGrandChildCp1(GrandChildCp1):
    """Test GreatGrandChildCp1 class for ClassProperty."""

    def __init__(self):
        """GreatGrandChildCp1 __init__ docstring."""
        super().__init__()
        self.prop_greatgrandchild = True


class ParentCp2(metaclass=ClassPropertyMeta):
    """Test ParentCp2 class for ClassProperty."""

    _classproperty_dependencies = {
        '_cprop1': 1,
        '_cprop2': 2
    }
    rcprop3 = 3 # regular class attribute

    def __init__(self):
        """ParentCp2 __init__ docstring."""
        self._prop1 = 10
        self._prop2 = 20
        self.rprop3 = 30 # regular instance attribute

    @ClassProperty
    def cprop1(cls):
        """First class property for ParentCp2."""
        return cls._cprop1

    @ClassProperty
    def cprop2(cls):
        """Second class property for ParentCp2."""
        return cls._cprop2

    @cprop2.setter
    def cprop2(cls, value):
        """Second class property for ParentCp2 (setter)."""
        cls._cprop2 = value

    @cprop2.deleter
    def cprop2(cls):
        """Second class property for ParentCp2 (deleter)."""
        cls._cprop2 = 2

    @property
    def prop1(self):
        """First property for ParentCp2."""
        return self._prop1

    @property
    def prop2(self):
        """Second property for ParentCp2."""
        return self._prop2

    @prop2.setter
    def prop2(self, value):
        """Second property for ParentCp2 (setter)."""
        self._prop2 = value

    @prop2.deleter
    def prop2(self):
        """Second property for ParentCp2 (deleter)."""
        self._prop2 = 20


class ChildCp2(ParentCp2):
    """Test ChildCp2 class for ClassProperty."""

    def __init__(self):
        """ChildCp2 __init__ docstring."""
        super().__init__()
        self.prop_child = True


class GrandChildCp2(ChildCp2):
    """Test GrandChildCp2 class for ClassProperty."""

    _classproperty_dependencies = {
        '_cprop4': -1,
        '_cprop5': -2
    }
    rcprop6 = -3 # regular class attribute

    def __init__(self):
        """GrandChildCp2 __init__ docstring."""
        super().__init__()
        self._prop4 = -10
        self._prop5 = -20
        self.rprop6 = -30 # regular instance attribute

    @ClassProperty
    def cprop4(cls):
        """Fourth class property for GrandChildCp2."""
        return cls._cprop4

    @ClassProperty
    def cprop5(cls):
        """Fifth class property for GrandChildCp2."""
        return cls._cprop5

    @cprop5.setter
    def cprop5(cls, value):
        """Fifth class property for GrandChildCp2 (setter)."""
        cls._cprop5 = value

    @cprop5.deleter
    def cprop5(cls):
        """Fifth class property for GrandChildCp2 (deleter)."""
        cls._cprop5 = -2

    @property
    def prop4(self):
        """Fourth property for GrandChildCp2."""
        return self._prop4

    @property
    def prop5(self):
        """Fifth property for GrandChildCp2."""
        return self._prop5

    @prop5.setter
    def prop5(self, value):
        """Fifth property for GrandChildCp2 (setter)."""
        self._prop5 = value

    @prop5.deleter
    def prop5(self):
        """Fifth property for GrandChildCp2 (deleter)."""
        self._prop5 = -20


class GreatGrandChildCp2(GrandChildCp2):
    """Test GreatGrandChildCp2 class for ClassProperty."""

    def __init__(self):
        """GreatGrandChildCp2 __init__ docstring."""
        super().__init__()
        self.prop_greatgrandchild = True


@singleton
class ParentCp3(metaclass=ClassPropertyMeta):
    """Test ParentCp3 class for ClassProperty."""

    _classproperty_dependencies = {
        '_cprop1': 1,
        '_cprop2': 2
    }
    rcprop3 = 3 # regular class attribute

    def __init__(self):
        """ParentCp3 __init__ docstring."""
        self._prop1 = 10
        self._prop2 = 20
        self.rprop3 = 30 # regular instance attribute

    @ClassProperty
    def cprop1(cls):
        """First class property for ParentCp3."""
        return cls._cprop1

    @ClassProperty
    def cprop2(cls):
        """Second class property for ParentCp3."""
        return cls._cprop2

    @cprop2.setter
    def cprop2(cls, value):
        """Second class property for ParentCp3 (setter)."""
        cls._cprop2 = value

    @cprop2.deleter
    def cprop2(cls):
        """Second class property for ParentCp3 (deleter)."""
        cls._cprop2 = 2

    @property
    def prop1(self):
        """First property for ParentCp3."""
        return self._prop1

    @property
    def prop2(self):
        """Second property for ParentCp3."""
        return self._prop2

    @prop2.setter
    def prop2(self, value):
        """Second property for ParentCp3 (setter)."""
        self._prop2 = value

    @prop2.deleter
    def prop2(self):
        """Second property for ParentCp3 (deleter)."""
        self._prop2 = 20


class ChildCp3(ParentCp3):
    """Test ChildCp3 class for ClassProperty."""

    def __init__(self):
        """ChildCp3 __init__ docstring."""
        super().__init__()
        self.prop_child = True


class GrandChildCp3(ChildCp3):
    """Test GrandChildCp3 class for ClassProperty."""

    _classproperty_dependencies = {
        '_cprop4': -1,
        '_cprop5': -2
    }
    rcprop6 = -3 # regular class attribute

    def __init__(self):
        """GrandChildCp3 __init__ docstring."""
        super().__init__()
        self._prop4 = -10
        self._prop5 = -20
        self.rprop6 = -30 # regular instance attribute

    @ClassProperty
    def cprop4(cls):
        """Fourth class property for GrandChildCp3."""
        return cls._cprop4

    @ClassProperty
    def cprop5(cls):
        """Fifth class property for GrandChildCp3."""
        return cls._cprop5

    @cprop5.setter
    def cprop5(cls, value):
        """Fifth class property for GrandChildCp3 (setter)."""
        cls._cprop5 = value

    @cprop5.deleter
    def cprop5(cls):
        """Fifth class property for GrandChildCp3 (deleter)."""
        cls._cprop5 = -2

    @property
    def prop4(self):
        """Fourth property for GrandChildCp3."""
        return self._prop4

    @property
    def prop5(self):
        """Fifth property for GrandChildCp3."""
        return self._prop5

    @prop5.setter
    def prop5(self, value):
        """Fifth property for GrandChildCp3 (setter)."""
        self._prop5 = value

    @prop5.deleter
    def prop5(self):
        """Fifth property for GrandChildCp3 (deleter)."""
        self._prop5 = -20


class GreatGrandChildCp3(GrandChildCp3):
    """Test GreatGrandChildCp3 class for ClassProperty."""

    def __init__(self):
        """GreatGrandChildCp3 __init__ docstring."""
        super().__init__()
        self.prop_greatgrandchild = True


@singleton
class ParentCp4:
    """Test ParentCp4 class for ClassProperty."""

    def __init__(self):
        """ParentCp4 __init__ docstring."""
        self.prop_parent = True


class ChildCp4(ParentCp4, metaclass=ClassPropertyMeta):
    """Test ChildCp4 class for ClassProperty."""

    _classproperty_dependencies = {
        '_cprop1': 1,
        '_cprop2': 2
    }
    rcprop3 = 3 # regular class attribute

    def __init__(self):
        """ChildCp4 __init__ docstring."""
        super().__init__()
        self._prop1 = 10
        self._prop2 = 20
        self.rprop3 = 30 # regular instance attribute

    @ClassProperty
    def cprop1(cls):
        """First class property for ChildCp4."""
        return cls._cprop1

    @ClassProperty
    def cprop2(cls):
        """Second class property for ChildCp4."""
        return cls._cprop2

    @cprop2.setter
    def cprop2(cls, value):
        """Second class property for ChildCp4 (setter)."""
        cls._cprop2 = value

    @cprop2.deleter
    def cprop2(cls):
        """Second class property for ChildCp4 (deleter)."""
        cls._cprop2 = 2

    @property
    def prop1(self):
        """First property for ChildCp4."""
        return self._prop1

    @property
    def prop2(self):
        """Second property for ChildCp4."""
        return self._prop2

    @prop2.setter
    def prop2(self, value):
        """Second property for ChildCp4 (setter)."""
        self._prop2 = value

    @prop2.deleter
    def prop2(self):
        """Second property for ChildCp4 (deleter)."""
        self._prop2 = 20


class GrandChildCp4(ChildCp4):
    """Test GrandChildCp4 class for ClassProperty."""

    _classproperty_dependencies = {
        '_cprop4': -1,
        '_cprop5': -2
    }
    rcprop6 = -3 # regular class attribute

    def __init__(self):
        """GrandChildCp4 __init__ docstring."""
        super().__init__()
        self._prop4 = -10
        self._prop5 = -20
        self.rprop6 = -30 # regular instance attribute

    @ClassProperty
    def cprop4(cls):
        """Fourth class property for GrandChildCp4."""
        return cls._cprop4

    @ClassProperty
    def cprop5(cls):
        """Fifth class property for GrandChildCp4."""
        return cls._cprop5

    @cprop5.setter
    def cprop5(cls, value):
        """Fifth class property for GrandChildCp4 (setter)."""
        cls._cprop5 = value

    @cprop5.deleter
    def cprop5(cls):
        """Fifth class property for GrandChildCp4 (deleter)."""
        cls._cprop5 = -2

    @property
    def prop4(self):
        """Fourth property for GrandChildCp4."""
        return self._prop4

    @property
    def prop5(self):
        """Fifth property for GrandChildCp4."""
        return self._prop5

    @prop5.setter
    def prop5(self, value):
        """Fifth property for GrandChildCp4 (setter)."""
        self._prop5 = value

    @prop5.deleter
    def prop5(self):
        """Fifth property for GrandChildCp4 (deleter)."""
        self._prop5 = -20


class GreatGrandChildCp4(GrandChildCp4):
    """Test GreatGrandChildCp4 class for ClassProperty."""

    def __init__(self):
        """GreatGrandChildCp4 __init__ docstring."""
        super().__init__()
        self.prop_greatgrandchild = True


class ParentCp5(metaclass=ClassPropertyMeta):
    """Test ParentCp5 class for ClassProperty."""

    _classproperty_dependencies = {
        '_cprop1': 1,
        '_cprop2': 2
    }
    rcprop3 = 3 # regular class attribute

    def __init__(self):
        """ParentCp5 __init__ docstring."""
        self._prop1 = 10
        self._prop2 = 20
        self.rprop3 = 30 # regular instance attribute

    @ClassProperty
    def cprop1(cls):
        """First class property for ParentCp5."""
        return cls._cprop1

    @ClassProperty
    def cprop2(cls):
        """Second class property for ParentCp5."""
        return cls._cprop2

    @cprop2.setter
    def cprop2(cls, value):
        """Second class property for ParentCp5 (setter)."""
        cls._cprop2 = value

    @cprop2.deleter
    def cprop2(cls):
        """Second class property for ParentCp5 (deleter)."""
        cls._cprop2 = 2

    @property
    def prop1(self):
        """First property for ParentCp5."""
        return self._prop1

    @property
    def prop2(self):
        """Second property for ParentCp5."""
        return self._prop2

    @prop2.setter
    def prop2(self, value):
        """Second property for ParentCp5 (setter)."""
        self._prop2 = value

    @prop2.deleter
    def prop2(self):
        """Second property for ParentCp5 (deleter)."""
        self._prop2 = 20


@singleton
class ChildCp5(ParentCp5):
    """Test ChildCp5 class for ClassProperty."""

    def __init__(self):
        """ChildCp5 __init__ docstring."""
        super().__init__()
        self.prop_child = True


class GrandChildCp5(ChildCp5):
    """Test GrandChildCp5 class for ClassProperty."""

    _classproperty_dependencies = {
        '_cprop4': -1,
        '_cprop5': -2
    }
    rcprop6 = -3 # regular class attribute

    def __init__(self):
        """GrandChildCp5 __init__ docstring."""
        super().__init__()
        self._prop4 = -10
        self._prop5 = -20
        self.rprop6 = -30 # regular instance attribute

    @ClassProperty
    def cprop4(cls):
        """Fourth class property for GrandChildCp5."""
        return cls._cprop4

    @ClassProperty
    def cprop5(cls):
        """Fifth class property for GrandChildCp5."""
        return cls._cprop5

    @cprop5.setter
    def cprop5(cls, value):
        """Fifth class property for GrandChildCp5 (setter)."""
        cls._cprop5 = value

    @cprop5.deleter
    def cprop5(cls):
        """Fifth class property for GrandChildCp5 (deleter)."""
        cls._cprop5 = -2

    @property
    def prop4(self):
        """Fourth property for GrandChildCp5."""
        return self._prop4

    @property
    def prop5(self):
        """Fifth property for GrandChildCp5."""
        return self._prop5

    @prop5.setter
    def prop5(self, value):
        """Fifth property for GrandChildCp5 (setter)."""
        self._prop5 = value

    @prop5.deleter
    def prop5(self):
        """Fifth property for GrandChildCp5 (deleter)."""
        self._prop5 = -20


class GreatGrandChildCp5(GrandChildCp5):
    """Test GreatGrandChildCp5 class for ClassProperty."""

    def __init__(self):
        """GreatGrandChildCp5 __init__ docstring."""
        super().__init__()
        self.prop_greatgrandchild = True



# Tests
# =====

def test_classproperty_1():
    # ParentCp1(no CP) -> ChildCp1(with CP) -> GrandChildCp1(with extra CP) -> GreatGrandChildCp1(no extra CP)
    _unittest_classproperty_class(ParentCp1,          None,     None,          is_singleton=False)
    _unittest_classproperty_class(ChildCp1,           ChildCp1, None,          is_singleton=False)
    _unittest_classproperty_class(GrandChildCp1,      ChildCp1, GrandChildCp1, is_singleton=False)
    _unittest_classproperty_class(GreatGrandChildCp1, ChildCp1, GrandChildCp1, is_singleton=False)


def test_classproperty_2():
    # ParentCp2(with CP) -> ChildCp2(no extra CP) -> GrandChildCp2(with extra CP) -> GreatGrandChildCp2(no extra CP)
    _unittest_classproperty_class(ParentCp2,          ParentCp2, None,         is_singleton=False)
    _unittest_classproperty_class(ChildCp2,           ParentCp2, None,         is_singleton=False)
    _unittest_classproperty_class(GrandChildCp2,      ParentCp2, GrandChildCp2,is_singleton=False)
    _unittest_classproperty_class(GreatGrandChildCp2, ParentCp2, GrandChildCp2,is_singleton=False)


def test_classproperty_3():
    # ParentCp3(singleton, with CP) -> ChildCp3(no extra CP) -> GrandChildCp3(with extra CP) -> GreatGrandChildCp3(no extra CP)
    _unittest_classproperty_class(ParentCp3,          ParentCp3, None,          is_singleton=True)
    _unittest_classproperty_class(ChildCp3,           ParentCp3, None,          is_singleton=True)
    _unittest_classproperty_class(GrandChildCp3,      ParentCp3, GrandChildCp3, is_singleton=True)
    _unittest_classproperty_class(GreatGrandChildCp3, ParentCp3, GrandChildCp3, is_singleton=True)


def test_classproperty_4():
    # ParentCp4(singleton, no CP) -> ChildCp4(with CP) -> GrandChildCp4(with extra CP) -> GreatGrandChildCp4(no extra CP)
    _unittest_classproperty_class(ParentCp4,          None,     None,          is_singleton=True)
    _unittest_classproperty_class(ChildCp4,           ChildCp4, None,          is_singleton=True)
    _unittest_classproperty_class(GrandChildCp4,      ChildCp4, GrandChildCp4, is_singleton=True)
    _unittest_classproperty_class(GreatGrandChildCp4, ChildCp4, GrandChildCp4, is_singleton=True)


def test_classproperty_5():
    # ParentCp5(with CP) -> ChildCp5(singleton, no CP) -> GrandChildCp5(with extra CP) -> GreatGrandChildCp5(no extra CP)
    _unittest_classproperty_class(ParentCp5,          ParentCp5, None,          is_singleton=False)
    _unittest_classproperty_class(ChildCp5,           ParentCp5, None,          is_singleton=True)
    _unittest_classproperty_class(GrandChildCp5,      ParentCp5, GrandChildCp5, is_singleton=True)
    _unittest_classproperty_class(GreatGrandChildCp5, ParentCp5, GrandChildCp5, is_singleton=True)


def test_classproperty_instance_1():
    # ParentCp1(no CP) -> ChildCp1(with CP) -> GrandChildCp1(with extra CP) -> GreatGrandChildCp1(no extra CP)
    _unittest_classproperty_instance(ParentCp1,          None,     None,          is_singleton=False, p_prop=True)
    _unittest_classproperty_instance(ChildCp1,           ChildCp1, None,          is_singleton=False, p_prop=True)
    _unittest_classproperty_instance(GrandChildCp1,      ChildCp1, GrandChildCp1, is_singleton=False, p_prop=True)
    _unittest_classproperty_instance(GreatGrandChildCp1, ChildCp1, GrandChildCp1, is_singleton=False, p_prop=True, ggc_prop=True)


def test_classproperty_instance_2():
    # ParentCp2(with CP) -> ChildCp2(no extra CP) -> GrandChildCp2(with extra CP) -> GreatGrandChildCp2(no extra CP)
    _unittest_classproperty_instance(ParentCp2,          ParentCp2, None,         is_singleton=False)
    _unittest_classproperty_instance(ChildCp2,           ParentCp2, None,         is_singleton=False, c_prop=True)
    _unittest_classproperty_instance(GrandChildCp2,      ParentCp2, GrandChildCp2,is_singleton=False, c_prop=True)
    _unittest_classproperty_instance(GreatGrandChildCp2, ParentCp2, GrandChildCp2,is_singleton=False, c_prop=True, ggc_prop=True)


def test_classproperty_instance_3():
    # ParentCp3(singleton, with CP) -> ChildCp3(no extra CP) -> GrandChildCp3(with extra CP) -> GreatGrandChildCp3(no extra CP)
    _unittest_classproperty_instance(ParentCp3,          ParentCp3, None,          is_singleton=True)
    _unittest_classproperty_instance(ChildCp3,           ParentCp3, None,          is_singleton=True, c_prop=True)
    _unittest_classproperty_instance(GrandChildCp3,      ParentCp3, GrandChildCp3, is_singleton=True, c_prop=True)
    _unittest_classproperty_instance(GreatGrandChildCp3, ParentCp3, GrandChildCp3, is_singleton=True, c_prop=True, ggc_prop=True)


def test_classproperty_instance_4():
    # ParentCp4(singleton, no CP) -> ChildCp4(with CP) -> GrandChildCp4(with extra CP) -> GreatGrandChildCp4(no extra CP)
    _unittest_classproperty_instance(ParentCp4,          None,     None,          is_singleton=True, p_prop=True)
    _unittest_classproperty_instance(ChildCp4,           ChildCp4, None,          is_singleton=True, p_prop=True)
    _unittest_classproperty_instance(GrandChildCp4,      ChildCp4, GrandChildCp4, is_singleton=True, p_prop=True)
    _unittest_classproperty_instance(GreatGrandChildCp4, ChildCp4, GrandChildCp4, is_singleton=True, p_prop=True, ggc_prop=True)


def test_classproperty_instance_5():
    # ParentCp5(with CP) -> ChildCp5(singleton, no CP) -> GrandChildCp5(with extra CP) -> GreatGrandChildCp5(no extra CP)
    _unittest_classproperty_instance(ParentCp5,          ParentCp5, None,          is_singleton=False)
    _unittest_classproperty_instance(ChildCp5,           ParentCp5, None,          is_singleton=True, c_prop=True)
    _unittest_classproperty_instance(GrandChildCp5,      ParentCp5, GrandChildCp5, is_singleton=True, c_prop=True)
    _unittest_classproperty_instance(GreatGrandChildCp5, ParentCp5, GrandChildCp5, is_singleton=True, c_prop=True, ggc_prop=True)


def test_classproperty_accessor():
    _unittest_accessor(ChildCp1)
    _unittest_accessor(GrandChildCp1, True)
    _unittest_accessor(GreatGrandChildCp1, True)
    _unittest_accessor(ParentCp2)
    _unittest_accessor(ChildCp2)
    _unittest_accessor(GrandChildCp2, True)
    _unittest_accessor(GreatGrandChildCp2, True)
    _unittest_accessor(ParentCp3)
    _unittest_accessor(ChildCp3)
    _unittest_accessor(GrandChildCp3, True)
    _unittest_accessor(GreatGrandChildCp3, True)
    _unittest_accessor(ChildCp4)
    _unittest_accessor(GrandChildCp4, True)
    _unittest_accessor(GreatGrandChildCp4, True)
    _unittest_accessor(ParentCp5)
    _unittest_accessor(ChildCp5)
    _unittest_accessor(GrandChildCp5, True)
    _unittest_accessor(GreatGrandChildCp5, True)


def test_docstrings():
    assert ClassProperty.__doc__.startswith("Descriptor to define class properties.")
    _unittest_docstring(ChildCp1, ChildCp1)
    _unittest_docstring(GrandChildCp1, ChildCp1, GrandChildCp1)
    _unittest_docstring(GreatGrandChildCp1, ChildCp1, GrandChildCp1)
    _unittest_docstring(ParentCp2, ParentCp2)
    _unittest_docstring(ChildCp2, ParentCp2)
    _unittest_docstring(GrandChildCp2, ParentCp2, GrandChildCp2)
    _unittest_docstring(GreatGrandChildCp2, ParentCp2, GrandChildCp2)
    _unittest_docstring(ParentCp3, ParentCp3)
    _unittest_docstring(ChildCp3, ParentCp3)
    _unittest_docstring(GrandChildCp3, ParentCp3, GrandChildCp3)
    _unittest_docstring(GreatGrandChildCp3, ParentCp3, GrandChildCp3)
    _unittest_docstring(ChildCp4, ChildCp4)
    _unittest_docstring(GrandChildCp4, ChildCp4, GrandChildCp4)
    _unittest_docstring(GreatGrandChildCp4, ChildCp4, GrandChildCp4)
    _unittest_docstring(ParentCp5, ParentCp5)
    _unittest_docstring(ChildCp5, ParentCp5)
    _unittest_docstring(GrandChildCp5, ParentCp5, GrandChildCp5)
    _unittest_docstring(GreatGrandChildCp5, ParentCp5, GrandChildCp5)


def test_structure():
    with pytest.raises(RuntimeError, match=re.escape("Error calling __set_name__ on "
                        + "'ClassProperty' instance 'cprop' in 'FailingClass'")) as err:
        class FailingClass:
            _cprop = 1
            @ClassProperty
            def cprop(cls):
                return cls._cprop1

            @cprop.setter
            def cprop(cls):
                return cls._cprop1

    original_err = err.value.__cause__
    assert isinstance(original_err, TypeError)
    assert re.search(str(original_err), "Class 'FailingClass' must have ClassPropertyMeta as a "
                                         "metaclass to be able to use ClassProperties!")


def _get_flags_and_names(cls, first_set_from_class, second_set_from_class):
    if first_set_from_class:
        if '__original_nonsingleton_class__' in first_set_from_class.__dict__:
            # The ClassProperty is attached to the original class, not the singleton class
            first_set_origin = first_set_from_class.__original_nonsingleton_class__.__name__
            first_set_inherited = True # Properties are always inherited, from the original class
        else:
            first_set_origin = first_set_from_class.__name__
            first_set_inherited = cls != first_set_from_class
    else:
        first_set_origin = None
        first_set_inherited = False
    if second_set_from_class:
        if '__original_nonsingleton_class__' in second_set_from_class.__dict__:
            # The ClassProperty is attached to the original class, not the singleton class
            second_set_origin = second_set_from_class.__original_nonsingleton_class__.__name__
            second_set_inherited = True # Properties are always inherited, from the original class
        else:
            second_set_origin = second_set_from_class.__name__
            second_set_inherited = cls != second_set_from_class
    else:
        second_set_origin = None
        second_set_inherited = False
    return first_set_origin, first_set_inherited, second_set_origin, second_set_inherited


def _unittest_classproperty_class(cls, first_set_from_class, second_set_from_class, is_singleton):
    # This test checks the functionality of the ClassProperty on a given class, while asserting
    # that regular class attributes, properties, and regular instance attributes are not affected.

    # Some flags and names
    first_set_origin, first_set_inherited, second_set_origin, second_set_inherited = \
        _get_flags_and_names(cls, first_set_from_class, second_set_from_class)

    # Check singleton
    if is_singleton:
        assert hasattr(cls, '__original_nonsingleton_class__')

    # Assert all properties exist.
    def check_existence():
        if first_set_from_class:
            # First the ClassProperties:
            assert hasattr(cls, 'cprop1')
            assert hasattr(cls, 'cprop2')
            assert hasattr(cls, 'rcprop3') # regular class attribute
            assert hasattr(cls, '_cprop1')
            assert hasattr(cls, '_cprop2')
            assert '_cprop1' in cls.__dict__
            assert '_cprop2' in cls.__dict__
            if first_set_inherited:
                assert 'cprop1' not in cls.__dict__
                assert 'cprop2' not in cls.__dict__
                assert 'rcprop3' not in cls.__dict__ # regular class attribute
            else:
                assert 'cprop1' in cls.__dict__
                assert 'cprop2' in cls.__dict__
                assert 'rcprop3' in cls.__dict__ # regular class attribute
            # Then the properties:
            assert hasattr(cls, 'prop1')
            assert hasattr(cls, 'prop2')
            assert not hasattr(cls, 'rprop3') # regular attribute
            assert not hasattr(cls, '_prop1')
            assert not hasattr(cls, '_prop2')
            if first_set_inherited:
                assert 'prop1' not in cls.__dict__
                assert 'prop2' not in cls.__dict__
            else:
                assert 'prop1' in cls.__dict__
                assert 'prop2' in cls.__dict__
        if second_set_from_class:
            # First the ClassProperties:
            assert hasattr(cls, 'cprop4')
            assert hasattr(cls, 'cprop5')
            assert hasattr(cls, 'rcprop6') # regular class attribute
            assert hasattr(cls, '_cprop4')
            assert hasattr(cls, '_cprop5')
            assert '_cprop4' in cls.__dict__
            assert '_cprop5' in cls.__dict__
            if second_set_inherited:
                assert 'cprop4' not in cls.__dict__
                assert 'cprop5' not in cls.__dict__
                assert 'rcprop6' not in cls.__dict__ # regular class attribute
            else:
                assert 'cprop4' in cls.__dict__
                assert 'cprop5' in cls.__dict__
                assert 'rcprop6' in cls.__dict__ # regular class attribute
            # Then the properties:
            assert hasattr(cls, 'prop4')
            assert hasattr(cls, 'prop5')
            assert not hasattr(cls, 'rprop6') # regular attribute
            assert not hasattr(cls, '_prop4')
            assert not hasattr(cls, '_prop5')
            if second_set_inherited:
                assert 'prop4' not in cls.__dict__
                assert 'prop5' not in cls.__dict__
            else:
                assert 'prop4' in cls.__dict__
                assert 'prop5' in cls.__dict__
    check_existence()

    # Test the getters
    if first_set_from_class:
        # First the ClassProperties:
        assert cls.cprop1 == 1
        cls._cprop1 = 9
        assert cls.cprop1 == 9
        assert cls.cprop2 == 2
        cls._cprop2 = 8
        assert cls.cprop2 == 8
        # Then the regular class attributes:
        assert cls.rcprop3 == 3
    if second_set_from_class:
        # First the ClassProperties:
        assert cls.cprop4 == -1
        cls._cprop4 = -9
        assert cls.cprop4 == -9
        assert cls.cprop5 == -2
        cls._cprop5 = -8
        assert cls.cprop5 == -8
        # Then the regular class attributes:
        assert cls.rcprop6 == -3

    # Test the setters
    if first_set_from_class:
        # First the ClassProperties:
        with pytest.raises(AttributeError, match=re.escape("ClassProperty 'cprop1' of "
                                    + f"'{first_set_origin}' class has no setter")):
            cls.cprop1 = 7
        assert cls.cprop1 == 9
        assert cls._cprop1 == 9
        cls.cprop2 = 7
        assert cls.cprop2 == 7
        assert cls._cprop2 == 7
        # Then the regular class attributes:
        if first_set_inherited:
            assert 'rcprop3' not in cls.__dict__
        cls.rcprop3 = 6  # This creates a new rcprop3 and attaches it to cls if inherited
        assert cls.rcprop3 == 6
        assert 'rcprop3' in cls.__dict__
    if second_set_from_class:
        # First the ClassProperties:
        with pytest.raises(AttributeError, match=re.escape("ClassProperty 'cprop4' of "
                                   + f"'{second_set_origin}' class has no setter")):
            cls.cprop4 = -7
        assert cls.cprop4 == -9
        assert cls._cprop4 == -9
        cls.cprop5 = -7
        assert cls.cprop5 == -7
        assert cls._cprop5 == -7
        # Then the regular class attributes:
        if second_set_inherited:
            assert 'rcprop6' not in cls.__dict__
        cls.rcprop6 = -6  # This creates a new rcprop6 and attaches it to cls if inherited
        assert cls.rcprop6 == -6
        assert 'rcprop6' in cls.__dict__

    # Test the deleters
    if first_set_from_class:
        # First the ClassProperties:
        with pytest.raises(AttributeError, match=re.escape("ClassProperty 'cprop1' of "
                                   + f"'{first_set_origin}' class has no deleter")):
            del cls.cprop1
        assert hasattr(cls, 'cprop1')
        assert hasattr(cls, '_cprop1')
        assert cls.cprop1 == 9
        del cls.cprop2
        assert hasattr(cls, 'cprop2')
        assert hasattr(cls, '_cprop2')
        assert cls.cprop2 == 2
        # Then the regular class attributes:
        del cls.rcprop3
        if first_set_inherited:
            assert 'rcprop3' not in cls.__dict__
            assert cls.rcprop3 == 3  # This is the original rcprop3, inherited
            with pytest.raises(AttributeError, match=re.escape("type object "
                            + f"'{cls.__name__}' has no attribute 'rcprop3'")):
                del cls.rcprop3 # Cannot delete an inherited class property
        else:
            assert not hasattr(cls, 'rcprop3')
    if second_set_from_class:
        # First the ClassProperties:
        with pytest.raises(AttributeError, match=re.escape("ClassProperty 'cprop4' of "
                                   + f"'{second_set_origin}' class has no deleter")):
            del cls.cprop4
        assert hasattr(cls, 'cprop4')
        assert hasattr(cls, '_cprop4')
        assert cls.cprop4 == -9
        del cls.cprop5
        assert hasattr(cls, 'cprop5')
        assert hasattr(cls, '_cprop5')
        assert cls.cprop5 == -2
        # Then the regular class attributes:
        del cls.rcprop6
        if second_set_inherited:
            assert 'rcprop6' not in cls.__dict__
            assert cls.rcprop6 == -3  # This is the original rcprop6, inherited
            with pytest.raises(AttributeError, match=re.escape("type object "
                            + f"'{cls.__name__}' has no attribute 'rcprop6'")):
                del cls.rcprop6 # Cannot delete an inherited class property
        else:
            assert not hasattr(cls, 'rcprop6')

    # Reset the properties to defaut values
    if first_set_from_class:
        cls._cprop1 = 1
    if second_set_from_class:
        cls._cprop4 = -1
    if first_set_from_class and not first_set_inherited:
        cls.rcprop3 = 3
    if second_set_from_class and not second_set_inherited:
        cls.rcprop6 = -3

    # Assert no properties got lost
    check_existence()


def _unittest_classproperty_instance(cls, first_set_from_class, second_set_from_class, is_singleton,
                                     p_prop=False, c_prop=False, ggc_prop=False):
    # This test checks the functionality of the ClassProperty on a given instance, while asserting
    # that regular class attributes, properties, and regular instance attributes are not affected.

    # Some flags and names
    first_set_origin, first_set_inherited, second_set_origin, second_set_inherited = \
        _get_flags_and_names(cls, first_set_from_class, second_set_from_class)

    # Spawn the instances
    instance1 = cls()
    instance2 = cls()

    # Check singleton
    if is_singleton:
        assert hasattr(cls, '__original_nonsingleton_class__')
        assert instance1 is instance2

    # Assert all properties exist.
    def check_existence():
        if first_set_from_class:
            # First the ClassProperties:
            assert hasattr(instance1, 'cprop1')
            assert hasattr(instance1, 'cprop2')
            assert hasattr(instance1, 'rcprop3') # regular class attribute
            assert hasattr(instance1, '_cprop1')
            assert hasattr(instance1, '_cprop2')
            assert hasattr(instance2, 'cprop1')
            assert hasattr(instance2, 'cprop2')
            assert hasattr(instance2, 'rcprop3') # regular class attribute
            assert hasattr(instance2, '_cprop1')
            assert hasattr(instance2, '_cprop2')
            # Then the properties:
            assert hasattr(instance1, 'prop1')
            assert hasattr(instance1, 'prop2')
            assert hasattr(instance1, 'rprop3') # regular attribute
            assert hasattr(instance1, '_prop1')
            assert hasattr(instance1, '_prop2')
            assert hasattr(instance2, 'prop1')
            assert hasattr(instance2, 'prop2')
            assert hasattr(instance2, 'rprop3') # regular attribute
            assert hasattr(instance2, '_prop1')
            assert hasattr(instance2, '_prop2')
        if second_set_from_class:
            # First the ClassProperties:
            assert hasattr(instance1, 'cprop4')
            assert hasattr(instance1, 'cprop5')
            assert hasattr(instance1, 'rcprop6') # regular class attribute
            assert hasattr(instance1, '_cprop4')
            assert hasattr(instance1, '_cprop5')
            assert hasattr(instance2, 'cprop4')
            assert hasattr(instance2, 'cprop5')
            assert hasattr(instance2, 'rcprop6') # regular class attribute
            assert hasattr(instance2, '_cprop4')
            assert hasattr(instance2, '_cprop5')
            # Then the properties:
            assert hasattr(instance1, 'prop4')
            assert hasattr(instance1, 'prop5')
            assert hasattr(instance1, 'rprop6') # regular attribute
            assert hasattr(instance1, '_prop4')
            assert hasattr(instance1, '_prop5')
            assert hasattr(instance2, 'prop4')
            assert hasattr(instance2, 'prop5')
            assert hasattr(instance2, 'rprop6') # regular attribute
            assert hasattr(instance2, '_prop4')
            assert hasattr(instance2, '_prop5')
        if p_prop:
            assert hasattr(instance1,'prop_parent')
            assert hasattr(instance2,'prop_parent')
        if c_prop:
            assert hasattr(instance1,'prop_child')
            assert hasattr(instance2,'prop_child')
        if ggc_prop:
            assert hasattr(instance1,'prop_greatgrandchild')
            assert hasattr(instance2,'prop_greatgrandchild')
    check_existence()

    # Test the getters
    if first_set_from_class:
        # First the ClassProperties:
        assert cls.cprop1 == 1
        assert instance1.cprop1 == 1
        assert instance2.cprop1 == 1
        instance1._cprop1 = 9
        assert cls.cprop1 == 9
        assert instance1.cprop1 == 9
        assert instance2.cprop1 == 9
        assert cls._cprop1 == 9
        assert instance1._cprop1 == 9
        assert instance2._cprop1 == 9
        assert cls.cprop2 == 2
        assert instance1.cprop2 == 2
        assert instance2.cprop2 == 2
        instance1._cprop2 = 8
        assert cls.cprop2 == 8
        assert instance1.cprop2 == 8
        assert instance2.cprop2 == 8
        assert cls._cprop2 == 8
        assert instance1._cprop2 == 8
        assert instance2._cprop2 == 8
        # Then the regular class attributes:
        assert cls.rcprop3 == 3
        assert instance1.rcprop3 == 3
        assert instance2.rcprop3 == 3
        # Then the properties (to ensure they are not affected):
        assert instance1.prop1 == 10
        assert instance2.prop1 == 10
        assert instance1._prop1 == 10
        assert instance2._prop1 == 10
        assert instance1.prop2 == 20
        assert instance2.prop2 == 20
        assert instance1._prop2 == 20
        assert instance2._prop2 == 20
        # Finally the regular properties:
        assert instance1.rprop3 == 30
        assert instance2.rprop3 == 30
    if second_set_from_class:
        # First the ClassProperties:
        assert cls.cprop4 == -1
        assert instance1.cprop4 == -1
        assert instance2.cprop4 == -1
        instance1._cprop4 = -9
        assert cls.cprop4 == -9
        assert instance1.cprop4 == -9
        assert instance2.cprop4 == -9
        assert cls._cprop4 == -9
        assert instance1._cprop4 == -9
        assert instance2._cprop4 == -9
        assert cls.cprop5 == -2
        assert instance1.cprop5 == -2
        assert instance2.cprop5 == -2
        instance1._cprop5 = -8
        assert cls.cprop5 == -8
        assert instance1.cprop5 == -8
        assert instance2.cprop5 == -8
        assert cls._cprop5 == -8
        assert instance1._cprop5 == -8
        assert instance2._cprop5 == -8
        # Then the regular class attributes:
        assert cls.rcprop6 == -3
        assert instance1.rcprop6 == -3
        assert instance2.rcprop6 == -3
        # Then the properties (to ensure they are not affected):
        assert instance1.prop4 == -10
        assert instance2.prop4 == -10
        assert instance1._prop4 == -10
        assert instance2._prop4 == -10
        assert instance1.prop5 == -20
        assert instance2.prop5 == -20
        assert instance1._prop5 == -20
        assert instance2._prop5 == -20
        # Finally the regular properties:
        assert instance1.rprop6 == -30
        assert instance2.rprop6 == -30
    if p_prop:
        assert instance1.prop_parent is True
        assert instance2.prop_parent is True
    if c_prop:
        assert instance1.prop_child is True
        assert instance2.prop_child is True
    if ggc_prop:
        assert instance1.prop_greatgrandchild is True
        assert instance2.prop_greatgrandchild is True

    # Test the setters
    if first_set_from_class:
        # First the ClassProperties:
        with pytest.raises(AttributeError, match=re.escape("ClassProperty 'cprop1' of "
                                    + f"'{first_set_origin}' class has no setter")):
            instance1.cprop1 = 7
        with pytest.raises(AttributeError, match=re.escape("ClassProperty 'cprop1' of "
                                    + f"'{first_set_origin}' class has no setter")):
            instance2.cprop1 = 7
        assert cls.cprop1 == 9
        assert instance1.cprop1 == 9
        assert instance2.cprop1 == 9
        assert cls._cprop1 == 9
        assert instance1._cprop1 == 9
        assert instance2._cprop1 == 9
        cls.cprop2 = 7
        assert cls.cprop2 == 7
        assert instance1.cprop2 == 7
        assert instance2.cprop2 == 7
        assert cls._cprop2 == 7
        assert instance1._cprop2 == 7
        assert instance2._cprop2 == 7
        instance1.cprop2 = 6
        assert cls.cprop2 == 6
        assert instance1.cprop2 == 6
        assert instance2.cprop2 == 6
        assert cls._cprop2 == 6
        assert instance1._cprop2 == 6
        assert instance2._cprop2 == 6
        instance2.cprop2 = 5
        assert cls.cprop2 == 5
        assert instance1.cprop2 == 5
        assert instance2.cprop2 == 5
        assert cls._cprop2 == 5
        assert instance1._cprop2 == 5
        assert instance2._cprop2 == 5
        # Regular class attributes are counterintuitive on instances; do not test
        # Then the properties (to ensure they are not affected):
        with pytest.raises(AttributeError, match=re.escape("property 'prop1' of "
                                   + f"'{first_set_origin}' object has no setter")):
            instance1.prop1 = 70
        with pytest.raises(AttributeError, match=re.escape("property 'prop1' of "
                                   + f"'{first_set_origin}' object has no setter")):
            instance2.prop1 = 70
        assert instance1.prop1 == 10
        assert instance2.prop1 == 10
        assert instance1._prop1 == 10
        assert instance2._prop1 == 10
        instance1.prop2 = 70
        assert instance1.prop2 == 70
        assert instance1._prop2 == 70
        if is_singleton:
            assert instance2.prop2 == 70
            assert instance2._prop2 == 70
        else:
            assert instance2.prop2 == 20
            assert instance2._prop2 == 20
        instance2.prop2 = 50
        if is_singleton:
            assert instance1.prop2 == 50
            assert instance1._prop2 == 50
        else:
            assert instance1.prop2 == 70
            assert instance1._prop2 == 70
        assert instance2.prop2 == 50
        assert instance2._prop2 == 50
        # Then the regular properties:
        instance1.rprop3 = 80
        assert instance1.rprop3 == 80
        if is_singleton:
            assert instance2.rprop3 == 80
        else:
            assert instance2.rprop3 == 30
        instance2.rprop3 = 70
        if is_singleton:
            assert instance1.rprop3 == 70
        else:
            assert instance1.rprop3 == 80
        assert instance2.rprop3 == 70
    if second_set_from_class:
        # First the ClassProperties:
        with pytest.raises(AttributeError, match=re.escape("ClassProperty 'cprop4' of "
                                    + f"'{second_set_origin}' class has no setter")):
            instance1.cprop4 = -7
        with pytest.raises(AttributeError, match=re.escape("ClassProperty 'cprop4' of "
                                    + f"'{second_set_origin}' class has no setter")):
            instance2.cprop4 = -7
        assert cls.cprop4 == -9
        assert instance1.cprop4 == -9
        assert instance2.cprop4 == -9
        assert cls._cprop4 == -9
        assert instance1._cprop4 == -9
        assert instance2._cprop4 == -9
        cls.cprop5 = -7
        assert cls.cprop5 == -7
        assert instance1.cprop5 == -7
        assert instance2.cprop5 == -7
        assert cls._cprop5 == -7
        assert instance1._cprop5 == -7
        assert instance2._cprop5 == -7
        instance1.cprop5 = -6
        assert cls.cprop5 == -6
        assert instance1.cprop5 == -6
        assert instance2.cprop5 == -6
        assert cls._cprop5 == -6
        assert instance1._cprop5 == -6
        assert instance2._cprop5 == -6
        instance2.cprop5 = -5
        assert cls.cprop5 == -5
        assert instance1.cprop5 == -5
        assert instance2.cprop5 == -5
        assert cls._cprop5 == -5
        assert instance1._cprop5 == -5
        assert instance2._cprop5 == -5
        # Regular class attributes are counterintuitive on instances; do not test
        # Then the properties (to ensure they are not affected):
        with pytest.raises(AttributeError, match=re.escape("property 'prop4' of "
                                  + f"'{second_set_origin}' object has no setter")):
            instance1.prop4 = -70
        with pytest.raises(AttributeError, match=re.escape("property 'prop4' of "
                                  + f"'{second_set_origin}' object has no setter")):
            instance2.prop4 = -70
        assert instance1.prop4 == -10
        assert instance2.prop4 == -10
        assert instance1._prop4 == -10
        assert instance2._prop4 == -10
        instance1.prop5 = -70
        assert instance1.prop5 == -70
        assert instance1._prop5 == -70
        if is_singleton:
            assert instance2.prop5 == -70
            assert instance2._prop5 == -70
        else:
            assert instance2.prop5 == -20
            assert instance2._prop5 == -20
        instance2.prop5 = -50
        if is_singleton:
            assert instance1.prop5 == -50
            assert instance1._prop5 == -50
        else:
            assert instance1.prop5 == -70
            assert instance1._prop5 == -70
        assert instance2.prop5 == -50
        assert instance2._prop5 == -50
        # Then the regular properties:
        instance1.rprop6 = -80
        assert instance1.rprop6 == -80
        if is_singleton:
            assert instance2.rprop6 == -80
        else:
            assert instance2.rprop6 == -30
        instance2.rprop6 = -70
        if is_singleton:
            assert instance1.rprop6 == -70
        else:
            assert instance1.rprop6 == -80
        assert instance2.rprop6 == -70
    if p_prop:
        assert instance1.prop_parent is True
        assert instance2.prop_parent is True
        instance1.prop_parent = False
        assert instance1.prop_parent is False
        if is_singleton:
            assert instance2.prop_parent is False
        else:
            assert instance2.prop_parent is True
        instance2.prop_parent = False
        assert instance1.prop_parent is False
        assert instance2.prop_parent is False
    if c_prop:
        assert instance1.prop_child is True
        assert instance2.prop_child is True
        instance1.prop_child = False
        assert instance1.prop_child is False
        if is_singleton:
            assert instance2.prop_child is False
        else:
            assert instance2.prop_child is True
        instance2.prop_child = False
        assert instance1.prop_child is False
        assert instance2.prop_child is False
    if ggc_prop:
        assert instance1.prop_greatgrandchild is True
        assert instance2.prop_greatgrandchild is True
        instance1.prop_greatgrandchild = False
        assert instance1.prop_greatgrandchild is False
        if is_singleton:
            assert instance2.prop_greatgrandchild is False
        else:
            assert instance2.prop_greatgrandchild is True
        instance2.prop_greatgrandchild = False
        assert instance1.prop_greatgrandchild is False
        assert instance2.prop_greatgrandchild is False

    # Test the deleters
    if first_set_from_class:
        # First the ClassProperties:
        with pytest.raises(AttributeError, match=re.escape("ClassProperty 'cprop1' of "
                                   + f"'{first_set_origin}' class has no deleter")):
            del instance1.cprop1
        with pytest.raises(AttributeError, match=re.escape("ClassProperty 'cprop1' of "
                                   + f"'{first_set_origin}' class has no deleter")):
            del instance2.cprop1
        assert hasattr(cls, 'cprop1')
        assert hasattr(instance1, 'cprop1')
        assert hasattr(instance2, 'cprop1')
        assert hasattr(cls, '_cprop1')
        assert hasattr(instance1, '_cprop1')
        assert hasattr(instance2, '_cprop1')
        assert cls.cprop1 == 9
        assert instance1.cprop1 == 9
        assert instance2.cprop1 == 9
        assert cls._cprop1 == 9
        assert instance1._cprop1 == 9
        assert instance2._cprop1 == 9
        del cls.cprop2
        assert hasattr(cls, 'cprop2')
        assert hasattr(instance1, 'cprop2')
        assert hasattr(instance2, 'cprop2')
        assert hasattr(cls, '_cprop2')
        assert hasattr(instance1, '_cprop2')
        assert hasattr(instance2, '_cprop2')
        assert cls.cprop2 == 2
        assert instance1.cprop2 == 2
        assert instance2.cprop2 == 2
        assert cls._cprop2 == 2
        assert instance1._cprop2 == 2
        assert instance2._cprop2 == 2
        cls.cprop2 = 5  # reset
        assert cls.cprop2 == 5
        del instance1.cprop2
        assert hasattr(cls, 'cprop2')
        assert hasattr(instance1, 'cprop2')
        assert hasattr(instance2, 'cprop2')
        assert hasattr(cls, '_cprop2')
        assert hasattr(instance1, '_cprop2')
        assert hasattr(instance2, '_cprop2')
        assert cls.cprop2 == 2
        assert instance1.cprop2 == 2
        assert instance2.cprop2 == 2
        assert cls._cprop2 == 2
        assert instance1._cprop2 == 2
        assert instance2._cprop2 == 2
        cls.cprop2 = 5  # reset
        assert cls.cprop2 == 5
        del instance2.cprop2
        assert hasattr(cls, 'cprop2')
        assert hasattr(instance1, 'cprop2')
        assert hasattr(instance2, 'cprop2')
        assert hasattr(cls, '_cprop2')
        assert hasattr(instance1, '_cprop2')
        assert hasattr(instance2, '_cprop2')
        assert cls.cprop2 == 2
        assert instance1.cprop2 == 2
        assert instance2.cprop2 == 2
        assert cls._cprop2 == 2
        assert instance1._cprop2 == 2
        assert instance2._cprop2 == 2
        cls.cprop2 = 5  # reset
        assert cls.cprop2 == 5
        # Regular class attributes are counterintuitive on instances; do not test
        # Then on properties (to ensure they are not affected):
        with pytest.raises(AttributeError, match=re.escape("property 'prop1' of "
                                  + f"'{first_set_origin}' object has no deleter")):
            del instance1.prop1
        with pytest.raises(AttributeError, match=re.escape("property 'prop1' of "
                                  + f"'{first_set_origin}' object has no deleter")):
            del instance2.prop1
        assert hasattr(instance1, 'prop1')
        assert hasattr(instance2, 'prop1')
        assert hasattr(instance1, '_prop1')
        assert hasattr(instance2, '_prop1')
        assert instance1.prop1 == 10
        assert instance2.prop1 == 10
        del instance1.prop2
        assert hasattr(instance1, 'prop2')
        assert hasattr(instance2, 'prop2')
        assert hasattr(instance1, '_prop2')
        assert hasattr(instance2, '_prop2')
        assert instance1.prop2 == 20
        assert instance1._prop2 == 20
        if is_singleton:
            assert instance2.prop2 == 20
            assert instance2._prop2 == 20
        else:
            assert instance2.prop2 == 50
            assert instance2._prop2 == 50
        instance1.prop2 = 70 # reset
        del instance2.prop2
        assert hasattr(instance1, 'prop2')
        assert hasattr(instance2, 'prop2')
        assert hasattr(instance1, '_prop2')
        assert hasattr(instance2, '_prop2')
        if is_singleton:
            assert instance1.prop2 == 20
            assert instance1._prop2 == 20
        else:
            assert instance1.prop2 == 70
            assert instance1._prop2 == 70
        assert instance2._prop2 == 20
        assert instance2._prop2 == 20
        # Finally on regular properties:
        del instance1.rprop3
        assert not hasattr(instance1, 'rprop3')
        if is_singleton:
            assert not hasattr(instance2, 'rprop3')
        else:
            assert hasattr(instance2, 'rprop3')
        instance1.rprop3 = 30 # reset
        del instance2.rprop3
        if is_singleton:
            assert not hasattr(instance1, 'rprop3')
        else:
            assert hasattr(instance1, 'rprop3')
        assert not hasattr(instance2, 'rprop3')
        instance2.rprop3 = 30 # reset
    if second_set_from_class:
        # First the ClassProperties:
        with pytest.raises(AttributeError, match=re.escape("ClassProperty 'cprop4' of "
                                   + f"'{second_set_origin}' class has no deleter")):
            del instance1.cprop4
        with pytest.raises(AttributeError, match=re.escape("ClassProperty 'cprop4' of "
                                   + f"'{second_set_origin}' class has no deleter")):
            del instance2.cprop4
        assert hasattr(cls, 'cprop4')
        assert hasattr(instance1, 'cprop4')
        assert hasattr(instance2, 'cprop4')
        assert hasattr(cls, '_cprop4')
        assert hasattr(instance1, '_cprop4')
        assert hasattr(instance2, '_cprop4')
        assert cls.cprop4 == 9
        assert instance1.cprop4 == 9
        assert instance2.cprop4 == 9
        assert cls._cprop4 == 9
        assert instance1._cprop4 == 9
        assert instance2._cprop4 == 9
        del cls.cprop5
        assert hasattr(cls, 'cprop5')
        assert hasattr(instance1, 'cprop5')
        assert hasattr(instance2, 'cprop5')
        assert hasattr(cls, '_cprop5')
        assert hasattr(instance1, '_cprop5')
        assert hasattr(instance2, '_cprop5')
        assert cls.cprop5 == 2
        assert instance1.cprop5 == 2
        assert instance2.cprop5 == 2
        assert cls._cprop5 == 2
        assert instance1._cprop5 == 2
        assert instance2._cprop5 == 2
        cls.cprop5 = 5  # reset
        assert cls.cprop5 == 5
        del instance1.cprop5
        assert hasattr(cls, 'cprop5')
        assert hasattr(instance1, 'cprop5')
        assert hasattr(instance2, 'cprop5')
        assert hasattr(cls, '_cprop5')
        assert hasattr(instance1, '_cprop5')
        assert hasattr(instance2, '_cprop5')
        assert cls.cprop5 == 2
        assert instance1.cprop5 == 2
        assert instance2.cprop5 == 2
        assert cls._cprop5 == 2
        assert instance1._cprop5 == 2
        assert instance2._cprop5 == 2
        cls.cprop5 = 5  # reset
        assert cls.cprop5 == 5
        del instance2.cprop5
        assert hasattr(cls, 'cprop5')
        assert hasattr(instance1, 'cprop5')
        assert hasattr(instance2, 'cprop5')
        assert hasattr(cls, '_cprop5')
        assert hasattr(instance1, '_cprop5')
        assert hasattr(instance2, '_cprop5')
        assert cls.cprop5 == 2
        assert instance1.cprop5 == 2
        assert instance2.cprop5 == 2
        assert cls._cprop5 == 2
        assert instance1._cprop5 == 2
        assert instance2._cprop5 == 2
        cls.cprop5 = 5  # reset
        assert cls.cprop5 == 5
        # Regular class attributes are counterintuitive on instances; do not test
        # Then on properties (to ensure they are not affected):
        with pytest.raises(AttributeError, match=re.escape("property 'prop4' of "
                                  + f"'{second_set_origin}' object has no deleter")):
            del instance1.prop4
        with pytest.raises(AttributeError, match=re.escape("property 'prop4' of "
                                  + f"'{second_set_origin}' object has no deleter")):
            del instance2.prop4
        assert hasattr(instance1, 'prop4')
        assert hasattr(instance2, 'prop4')
        assert hasattr(instance1, '_prop4')
        assert hasattr(instance2, '_prop4')
        assert instance1.prop4 == -10
        assert instance2.prop4 == -10
        del instance1.prop5
        assert hasattr(instance1, 'prop5')
        assert hasattr(instance2, 'prop5')
        assert hasattr(instance1, '_prop5')
        assert hasattr(instance2, '_prop5')
        assert instance1.prop5 == -20
        assert instance1._prop5 == -20
        if is_singleton:
            assert instance2.prop5 == -20
            assert instance2._prop5 == -20
        else:
            assert instance2.prop5 == -50
            assert instance2._prop5 == -50
        instance1.prop5 = -70 # reset
        del instance2.prop5
        assert hasattr(instance1, 'prop5')
        assert hasattr(instance2, 'prop5')
        assert hasattr(instance1, '_prop5')
        assert hasattr(instance2, '_prop5')
        if is_singleton:
            assert instance1.prop5 == -20
            assert instance1._prop5 == -20
        else:
            assert instance1.prop5 == -70
            assert instance1._prop5 == -70
        assert instance2._prop5 == -20
        assert instance2._prop5 == -20
        # Finally on regular properties:
        del instance1.rprop6
        assert not hasattr(instance1, 'rprop6')
        if is_singleton:
            assert not hasattr(instance2, 'rprop6')
        else:
            assert hasattr(instance2, 'rprop6')
        instance1.rprop6 = -30 # reset
        del instance2.rprop6
        if is_singleton:
            assert not hasattr(instance1, 'rprop6')
        else:
            assert hasattr(instance1, 'rprop6')
        assert not hasattr(instance2, 'rprop6')
        instance2.rprop6 = -30 # reset
    if p_prop:
        del instance1.prop_parent
        assert not hasattr(instance1, 'prop_parent')
        if is_singleton:
            assert not hasattr(instance2, 'prop_parent')
        else:
            assert hasattr(instance2, 'prop_parent')
        instance1.prop_parent = True # reset
        del instance2.prop_parent
        if is_singleton:
            assert not hasattr(instance1, 'prop_parent')
        else:
            assert hasattr(instance1, 'prop_parent')
        assert not hasattr(instance2, 'prop_parent')
        instance2.prop_parent = True # reset
    if c_prop:
        del instance1.prop_child
        assert not hasattr(instance1, 'prop_child')
        if is_singleton:
            assert not hasattr(instance2, 'prop_child')
        else:
            assert hasattr(instance2, 'prop_child')
        instance1.prop_child = True # reset
        del instance2.prop_child
        if is_singleton:
            assert not hasattr(instance1, 'prop_child')
        else:
            assert hasattr(instance1, 'prop_child')
        assert not hasattr(instance2, 'prop_child')
        instance2.prop_child = True # reset
    if ggc_prop:
        del instance1.prop_greatgrandchild
        assert not hasattr(instance1, 'prop_greatgrandchild')
        if is_singleton:
            assert not hasattr(instance2, 'prop_greatgrandchild')
        else:
            assert hasattr(instance2, 'prop_greatgrandchild')
        instance1.prop_greatgrandchild = True # reset
        del instance2.prop_greatgrandchild
        if is_singleton:
            assert not hasattr(instance1, 'prop_greatgrandchild')
        else:
            assert hasattr(instance1, 'prop_greatgrandchild')
        assert not hasattr(instance2, 'prop_greatgrandchild')
        instance2.prop_greatgrandchild = True # reset

    # Reset the class properties to defaut values (we don't care about the instance
    # properties, as the instances are discarded after this test)
    if first_set_from_class:
        cls._cprop1 = 1
    if second_set_from_class:
        cls._cprop4 = -1
    if first_set_from_class and not first_set_inherited:
        cls.rcprop3 = 3
    if second_set_from_class and not second_set_inherited:
        cls.rcprop6 = -3

    # Assert no properties got lost
    check_existence()


def _unittest_accessor(cls, has_second_set=False):
    assert isinstance(cls.classproperty, ClassPropertyDict)
    if has_second_set:
        assert len(cls.classproperty) == 4
        assert len(cls.classproperty.names) == 4
    else:
        assert len(cls.classproperty) == 2
        assert len(cls.classproperty.names) == 2
    assert 'cprop1' in cls.classproperty
    assert 'cprop1' in cls.classproperty.names
    assert isinstance(cls.classproperty.cprop1, ClassProperty)
    assert 'cprop2' in cls.classproperty
    assert 'cprop2' in cls.classproperty.names
    assert isinstance(cls.classproperty.cprop2, ClassProperty)
    if has_second_set:
        assert 'cprop4' in cls.classproperty
        assert 'cprop4' in cls.classproperty.names
        assert isinstance(cls.classproperty.cprop4, ClassProperty)
        assert 'cprop5' in cls.classproperty
        assert 'cprop5' in cls.classproperty.names
        assert isinstance(cls.classproperty.cprop5, ClassProperty)
    for prop in cls.classproperty.values():
        assert isinstance(prop, ClassProperty)
    for prop in cls.classproperty.keys():
        if has_second_set:
            assert prop in ['cprop1', 'cprop2', 'cprop4', 'cprop5']
        else:
            assert prop in ['cprop1', 'cprop2']
    for name, prop in cls.classproperty.items():
        assert isinstance(prop, ClassProperty)
        if has_second_set:
            assert name in ['cprop1', 'cprop2', 'cprop4', 'cprop5']
        else:
            assert name in ['cprop1', 'cprop2']


def _unittest_docstring(cls, first_set_from_class, second_set_from_class=None):
    first_set_from_class = first_set_from_class.__name__
    if second_set_from_class:
        second_set_from_class = second_set_from_class.__name__

    assert cls.__doc__ == f"Test {cls.__name__} class for ClassProperty."
    assert cls.__init__.__doc__ == f"{cls.__name__} __init__ docstring."

    # Workaround for ClassProperty introspection
    assert cls.classproperty.cprop1.__doc__ == f"First class property for {first_set_from_class}."
    assert cls.classproperty.cprop1.fget.__doc__ == f"First class property for {first_set_from_class}."
    assert cls.classproperty.cprop2.__doc__ == f"Second class property for {first_set_from_class}."
    assert cls.classproperty.cprop2.fget.__doc__ == f"Second class property for {first_set_from_class}."
    assert cls.classproperty.cprop2.fset.__doc__ == f"Second class property for {first_set_from_class} (setter)."
    assert cls.classproperty.cprop2.fdel.__doc__ == f"Second class property for {first_set_from_class} (deleter)."
    if second_set_from_class:
        assert cls.classproperty.cprop4.__doc__ == f"Fourth class property for {second_set_from_class}."
        assert cls.classproperty.cprop4.fget.__doc__ == f"Fourth class property for {second_set_from_class}."
        assert cls.classproperty.cprop5.__doc__ == f"Fifth class property for {second_set_from_class}."
        assert cls.classproperty.cprop5.fget.__doc__ == f"Fifth class property for {second_set_from_class}."
        assert cls.classproperty.cprop5.fset.__doc__ == f"Fifth class property for {second_set_from_class} (setter)."
        assert cls.classproperty.cprop5.fdel.__doc__ == f"Fifth class property for {second_set_from_class} (deleter)."

    # Normal property introspection
    assert cls.prop1.__doc__ == f"First property for {first_set_from_class}."
    assert cls.prop1.fget.__doc__ == f"First property for {first_set_from_class}."
    assert cls.prop2.__doc__ == f"Second property for {first_set_from_class}."
    assert cls.prop2.fget.__doc__ == f"Second property for {first_set_from_class}."
    assert cls.prop2.fset.__doc__ == f"Second property for {first_set_from_class} (setter)."
    assert cls.prop2.fdel.__doc__ == f"Second property for {first_set_from_class} (deleter)."
    if second_set_from_class:
        assert cls.prop4.__doc__ == f"Fourth property for {second_set_from_class}."
        assert cls.prop4.fget.__doc__ == f"Fourth property for {second_set_from_class}."
        assert cls.prop5.__doc__ == f"Fifth property for {second_set_from_class}."
        assert cls.prop5.fget.__doc__ == f"Fifth property for {second_set_from_class}."
        assert cls.prop5.fset.__doc__ == f"Fifth property for {second_set_from_class} (setter)."
        assert cls.prop5.fdel.__doc__ == f"Fifth property for {second_set_from_class} (deleter)."
