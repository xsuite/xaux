# copyright ############################### #
# This file is part of the Xaux package.    #
# Copyright (c) CERN, 2025.                 #
# ######################################### #


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