# copyright ############################### #
# This file is part of the Xcoll Package.   #
# Copyright (c) CERN, 2024.                 #
# ######################################### #

import functools
from pathlib import Path


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
        # Need to initialise class once to get the allowed fields on the instance
        # TODO: this does not work if the __init__ has obligatory arguments
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
