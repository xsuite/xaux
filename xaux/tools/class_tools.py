# copyright ############################### #
# This file is part of the Xcoll Package.   #
# Copyright (c) CERN, 2024.                 #
# ######################################### #

import functools
from pathlib import Path

from .function_tools import count_required_arguments


# Singleton decorator.
# This decorator will make a class a singleton, i.e. it will only allow one instance,
# and will return the same instance every time it is called. The singleton can be
# reset by calling the delete method of the class, which will invalidate any existing
# instances. Each re-initialisation of the singleton will keep the class attributes,
# and for this reason, the __init__ method should not have any required arguments.
# This is asserted at the class creation time. Furthermore, by default the singleton
# will not allow setting private attributes in the constructor, but this can be
# overridden by setting allow_underscore_vars_in_init=True in the decorator.
# This is fully compatible with inheritance, and each child of a singleton class will
# be its own singleton.
# Lastly, the decorator provides a get_self method, which is a class method that is
# more relaxed than the constructor, as it allows passing any kwargs, even if they
# aren't attributes for the singleton (these  will then just be ignored). This is
# useful for kwargs filtering in getters or specific functions.
#
# Caveat I in the implementation: whenever any monkey-patched method is called, the
# super method should be called on the original singleton class (not the current class),
# to avoid infinite loops (it would just call the same method again).
# Caveat II in the implementation: When we need to get the current class of an instance,
# we should use type(self) instead of self.__class__, as the latter will get into an
# infinite loop because of the __getattribute__ method.


def singleton(_cls=None, *, allow_underscore_vars_in_init=False):
    def decorator_singleton(cls):
        # Monkey-patch __new__ to create a singleton
        original_new = cls.__dict__.get('__new__', None)
        @functools.wraps(cls)
        def singleton_new(this_cls, *args, **kwargs):
            print(f"In singleton_new: {this_cls}")
            # If the singleton instance does not exist, create it
            if '_singleton_instance' not in this_cls.__dict__:
                if original_new:
                    inst = original_new(cls_to_call, *args, **kwargs)
                else:
                    try:
                        inst = super(cls, cls).__new__(this_cls, *args, **kwargs)
                    except TypeError:
                        inst = super(cls, cls).__new__(this_cls)
                print(inst)
                inst._initialised = False
                inst._valid = True
                this_cls._singleton_instance = inst
            return this_cls._singleton_instance
        cls.__new__ = singleton_new

        # Monkey-patch __init__ to set the singleton fields
        original_init = cls.__dict__.get('__init__', None)
        if original_init:
            if count_required_arguments(original_init) > 1:
                raise ValueError(f"Cannot create a singleton with an __init__ method that "
                            + "has more than one required argument (only 'self' is allowed)!")
        @functools.wraps(cls)
        def singleton_init(self, *args, **kwargs):
            this_cls = type(self)
            print(f"In singleton_init: {this_cls}")
            # Validate kwargs
            kwargs.pop('_initialised', None)
            for kk, vv in kwargs.items():
                if not allow_underscore_vars_in_init and kk.startswith('_'):
                    raise ValueError(f"Cannot set private attribute {kk} for {this_cls.__name__}! "
                                    + "Use the appropriate setter method instead. However, if you "
                                    + "really want to be able to set this attribute in the "
                                    + "constructor, use 'allow_underscore_vars_in_init=True' "
                                    + "in the singleton decorator.")
            # Initialise the singleton if it has not been initialised yet
            if not self._initialised:
                if original_init:
                    original_init(self, *args, **kwargs)
                else:
                    super(cls, self).__init__(*args, **kwargs)
                self._initialised = True
            # Set the attributes; only attributes defined in the class, custom init, or properties
            # are allowed
            for kk, vv in kwargs.items():
                if not hasattr(self, kk) and not hasattr(this_cls, kk):
                    raise ValueError(f"Invalid attribute {kk} for {this_cls.__name__}!")
                setattr(self, kk, vv)
        cls.__init__ = singleton_init

        # Monkey-patch __getattribute__ to assert the instance belongs to the current singleton
        original_getattribute = cls.__dict__.get('__getattribute__', None)
        @functools.wraps(cls)
        def singleton_getattribute(self, name):
            this_cls = type(self)
            if not hasattr(this_cls, '_singleton_instance') or not super(cls, self).__getattribute__('_valid'):
                raise RuntimeError(f"This instance of the singleton {this_cls.__name__} has been "
                                + "invalidated!")
            if original_getattribute:
                return original_getattribute(self, name)
            else:
                return super(cls, self).__getattribute__(name)
        cls.__getattribute__ = singleton_getattribute

        @classmethod
        @functools.wraps(cls)
        def get_self(this_cls, **kwargs):
            # Need to initialise in case the instance does not yet exist
            # (to recognise the allowed fields)
            this_cls()
            filtered_kwargs = {key: value for key, value in kwargs.items()
                            if hasattr(this_cls, key) \
                            or hasattr(this_cls._singleton_instance, key)}
            if not allow_underscore_vars_in_init:
                filtered_kwargs = {key: value for key, value in filtered_kwargs.items()
                                if not key.startswith('_')}
            return this_cls(**filtered_kwargs)
        cls.get_self = get_self

        @classmethod
        @functools.wraps(cls)
        def delete(this_cls):
            if hasattr(this_cls, '_singleton_instance'):
                # Invalidate (pointers to) existing instances!
                this_cls._singleton_instance._valid = False
                del this_cls._singleton_instance
        cls.delete = delete

        return cls

    if _cls is None:
        return decorator_singleton
    else:
        return decorator_singleton(_cls)


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
