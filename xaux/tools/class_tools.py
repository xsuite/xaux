# copyright ############################### #
# This file is part of the Xcoll Package.   #
# Copyright (c) CERN, 2024.                 #
# ######################################### #

import functools
from pathlib import Path

from .function_tools import count_required_arguments


def singleton(cls, allow_underscore_vars_in_init=False):
    # Monkey-patch the __new__ method to create a singleton
    original_new = cls.__new__ if '__new__' in cls.__dict__ else None
    def singleton_new(cls, *args, **kwargs):
        if not hasattr(cls, 'instance'):
            cls.instance = (original_new(cls, *args, **kwargs) \
                            if original_new \
                            else super(cls, cls).__new__(cls))
            cls.instance._initialised = False
            cls.instance._valid = True
        return cls.instance
    cls.__new__ = singleton_new

    # Monkey-patch the __init__ method to set the singleton fields
    original_init = cls.__init__ if '__init__' in cls.__dict__ else None
    if original_init:
        if count_required_arguments(original_init) > 1:
            raise ValueError(f"Cannot create a singleton with an __init__ method that "
                           + "has more than one required argument (only 'self' is allowed)!")
    def singleton_init(self, *args, **kwargs):
        kwargs.pop('_initialised', None)
        if not self._initialised:
            if original_init:
                original_init(self, *args, **kwargs)
            else:
                super(cls, self).__init__(*args, **kwargs)
            self._initialised = True
        for kk, vv in kwargs.items():
            if not allow_underscore_vars_in_init and kk.startswith('_'):
                raise ValueError(f"Cannot set private attribute {kk} for {cls.__name__}!")
            if not hasattr(self, kk) and not hasattr(cls, kk):
                raise ValueError(f"Invalid attribute {kk} for {cls.__name__}!")
            setattr(self, kk, vv)
    cls.__init__ = singleton_init

    # Define the get_self method
    @classmethod
    def get_self(cls, **kwargs):
        # Need to initialise class in case the instance does not yet exist
        # (to recognise get the allowed fields)
        cls()
        filtered_kwargs = {key: value for key, value in kwargs.items()
                           if hasattr(cls, key) or hasattr(cls.instance, key)}
        if not allow_underscore_vars_in_init:
            filtered_kwargs = {key: value for key, value in filtered_kwargs.items()
                               if not key.startswith('_')}
        return cls(**filtered_kwargs)
    cls.get_self = get_self

    # Define the delete method
    @classmethod
    def delete(cls):
        if hasattr(cls, 'instance'):
            cls.instance._valid = False # Invalidate existing instances
            del cls.instance
    cls.delete = delete

    # Monkey-patch the __getattribute__ method to assert the instance belongs to the current singleton
    original_getattribute = cls.__getattribute__ if '__getattribute__' in cls.__dict__ else None
    def singleton_getattribute(self, name):
        if not super(cls, self).__getattribute__('_valid'):
            raise RuntimeError(f"This instance of the singleton {cls.__name__} has been invalidated!")
        if original_getattribute:
            return original_getattribute(self, name)
        else:
            return super(cls, self).__getattribute__(name)
    cls.__getattribute__ = singleton_getattribute

    return cls


class ClassPropertyMeta(type):
    def __setattr__(cls, key, value):
        # Check if the attribute is a ClassProperty
        for parent in cls.__mro__:
            if key in parent.__dict__ and isinstance(parent.__dict__[key], ClassProperty):
                return parent.__dict__[key].__set__(cls, value)
        return super(ClassPropertyMeta, cls).__setattr__(key, value)


class ClassProperty:
    _registry = {}  # Registry to store ClassProperty names for each class

    @classmethod
    def get_properties(cls, owner, parents=True):
        if not parents:
            return cls._registry.get(owner, [])
        else:
            return [prop for parent in owner.__mro__
                         for prop in cls._registry.get(parent, [])]

    def __init__(self, fget=None, fset=None, fdel=None, doc=None):
        functools.update_wrapper(self, fget)
        self.fget = fget
        self.fset = fset
        self.fdel = fdel
        if doc is None and fget is not None:
            doc = fget.__doc__
        self.__doc__ = doc

    def __set_name__(self, owner, name):
        self.name = name
        # Verify that the class is a subclass of ClassPropertyMeta
        if ClassPropertyMeta not in type(owner).__mro__:
            raise AttributeError(f"Class `{owner.__name__}` must be have ClassPropertyMeta "
                               + f"as a metaclass to be able to use ClassProperties!")
        # Add the property name to the registry for the class
        if owner not in ClassProperty._registry:
            ClassProperty._registry[owner] = []
        ClassProperty._registry[owner].append(name)
        # Create default getter, setter, and deleter
        if self.fget is None:
            def _getter(*args, **kwargs):
                raise AttributeError(f"Unreadable attribute '{name}' of {owner.__name__} class!")
            self.fget = _getter
        if self.fset is None:
            def _setter(self, *args, **kwargs):
                raise AttributeError(f"ClassProperty '{name}' of {owner.__name__} class has no setter")
            self.fset = _setter
        if self.fdel is None:
            def _deleter(*args, **kwargs):
                raise AttributeError(f"ClassProperty '{name}' of {owner.__name__} class has no deleter")
            self.fdel = _deleter

    def __get__(self, instance, owner):
        if owner is None:
            owner = type(instance)
        try:
            return self.fget(owner)
        except ValueError:
            # Return a fallback if initialisation fails
            return None

    def __set__(self, cls, value):
        self.fset(cls, value)

    def __delete__(self, instance):
        self.fdel(instance.__class__)

    def getter(self, fget):
        self.fget = fget
        return self

    def setter(self, fset):
        self.fset = fset
        return self

    def deleter(self, fdel):
        self.fdel = fdel
        return self
