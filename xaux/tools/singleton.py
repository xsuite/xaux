# copyright ############################### #
# This file is part of the Xaux package.    #
# Copyright (c) CERN, 2025.                 #
# ######################################### #

import functools

from .function_tools import count_required_arguments


# TODO: allow_underscore_vars_in_init=False is not very robust. Do we need it for ClassProperty?


# Stub class for docstrings and logical class naming
class Singleton:
    # Stub for naming
    def __new__(cls, *args, **kwargs):
        """The __new__ method is expanded to implement the singleton."""
    def __init__(self, *args, **kwargs):
        """The __init__ method is expanded to implement the singleton."""
    def __str__(self):
        """This a default __str__ method for the singleton."""
    def __repr__(self):
        """This a default __repr__ method for the singleton."""
    def __getattribute__(self, name):
        """The __getattribute__ method is expanded to implement the singleton."""
    def get_self(cls, **kwargs):
        """The get_self(**kwargs) method returns the singleton instance, allowing to pass
        any kwargs to the constructor, even if they are not attributes of the singleton.
        This is useful for kwargs filtering in getters or specific functions.
        """
    def delete(cls):
        """The delete() method removes the singleton and invalidates any existing instances,
        allowing to create a new instance the next time the class is instantiated. This is
        useful for resetting the singleton to its default values.
        """


def singleton(_cls=None, *, allow_underscore_vars_in_init=True):
    """Singleton decorator.
    This decorator will redefine a class (by letting it inherit from itself and renaming it)
    such that only one instance exists and the same instance is returned every time the
    class is instantiated.
    - Each re-initialisation of the singleton will keep the class attributes, and for this
      reason, the __init__ method should not have any required arguments. This is asserted
      at the class creation time.
    - By default, the singleton allows setting private attributes in the constructor,
      but this can be overridden by setting 'allow_underscore_vars_in_init=False'.
    - This decorator is fully compatible with inheritance, and each child of a singleton
      class will be its own singleton.
    - The singleton can be reset by calling the 'delete()' method of the class, which will
      invalidate any existing instances.
    - The decorator provides a get_self method, which is a class method that is more relaxed
      than the constructor, as it allows passing any kwargs even if they aren't attributes
      for the singleton (these  will then just be ignored). This is useful for kwargs
      filtering in getters or specific functions.
    """
    # Caveat: When we need to get the current class of an instance,
    # we should use type(self) instead of self.__class__, as the latter will get into an
    # infinite loop because of the __getattribute__ method.

    # Internal decorator definition to used without arguments
    def decorator_singleton(cls):
        # Verify any existing __init__ method only has optional values
        original_init = cls.__dict__.get('__init__')
        if original_init is not None and count_required_arguments(original_init) > 1:
            raise TypeError(f"Cannot create a singleton for class {cls.__name__} with an "
                          + f"__init__ method that has more than one required argument (only "
                          + f"'self' is allowed)!")

        # Check the class doesn't already have a get_self method
        if cls.__dict__.get('get_self') is not None:
            raise TypeError(f"Class {cls.__name__} provides a 'get_self' method. This is not "
                            + "compatible with the singleton decorator!")

        # Check the class doesn't already have a delete method
        if cls.__dict__.get('delete') is not None:
            raise TypeError(f"Class {cls.__name__} provides a 'delete' method. This is not "
                            + "compatible with the singleton decorator!")

        # Define wrapper names
        wrap_new = cls.__new__ if cls.__dict__.get('__new__') is not None \
                               else Singleton.__new__
        wrap_init = cls.__init__ if cls.__dict__.get('__init__') is not None \
                                 else Singleton.__init__
        wrap_getattribute = cls.__getattribute__ if cls.__dict__.get('__getattribute__') \
                                               is not None else Singleton.__getattribute__

        @functools.wraps(cls, updated=())
        class LocalSingleton(cls):
            __original_nonsingleton_class__ = cls

            @functools.wraps(wrap_new)
            def __new__(this_cls, *args, **kwargs):
                # If the singleton instance does not exist, create it
                if '_singleton_instance' not in this_cls.__dict__:
                    try:
                        inst = super().__new__(this_cls, *args, **kwargs)
                    except TypeError:
                        # object._new__ does not accept arguments
                        inst = super().__new__(this_cls)
                    inst._initialised = False
                    inst._valid = True
                    this_cls._singleton_instance = inst
                return this_cls._singleton_instance

            @functools.wraps(wrap_init)
            def __init__(self, *args, **kwargs):
                this_cls = type(self)
                # Validate kwargs
                kwargs.pop('_initialised', None)
                for kk in list(kwargs.keys()) + list(args):
                    if not allow_underscore_vars_in_init and kk.startswith('_'):
                        raise AttributeError(f"Cannot set private attribute {kk} for {this_cls.__name__}! "
                                        + "Use the appropriate setter method instead. However, if you "
                                        + "really want to be able to set this attribute in the "
                                        + "constructor, use 'allow_underscore_vars_in_init=True' "
                                        + "in the singleton decorator.")
                # Initialise the singleton if it has not been initialised yet
                if not self._initialised:
                    super().__init__(*args, **kwargs)
                    self._initialised = True
                # Set the attributes; only attributes defined in the class, custom init, or properties
                # are allowed
                for kk, vv in kwargs.items():
                    if not hasattr(self, kk) and not hasattr(this_cls, kk):
                        raise AttributeError(f"Invalid attribute {kk} for {this_cls.__name__}!")
                    setattr(self, kk, vv)

            if cls.__dict__.get('__str__') is None:
                @functools.wraps(Singleton.__str__)
                def __str__(self):
                    return f"<{type(self).__name__} singleton instance>"

            if cls.__dict__.get('__repr__') is None:
                @functools.wraps(Singleton.__repr__)
                def __repr__(self):
                    return f"<{type(self).__name__} singleton instance at {hex(id(self))}>"

            @functools.wraps(wrap_getattribute)
            def __getattribute__(self, name):
                this_cls = type(self)
                if not hasattr(this_cls, '_singleton_instance') \
                or not super().__getattribute__('_valid'):
                    raise RuntimeError(f"This instance of the singleton {this_cls.__name__} "
                                      + "has been invalidated!")
                return super().__getattribute__(name)

            @classmethod
            @functools.wraps(Singleton.get_self)
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

            @classmethod
            @functools.wraps(Singleton.delete)
            def delete(this_cls):
                if hasattr(this_cls, '_singleton_instance'):
                    # Invalidate (pointers to) existing instances!
                    this_cls._singleton_instance._valid = False
                    del this_cls._singleton_instance

        # Rename the original class, for clarity in the __mro__ etc
        cls.__name__ = f"{cls.__name__}Original"
        cls.__qualname__ = f"{cls.__qualname__}Original"

        return LocalSingleton

    # Hack to allow the decorator to be used with or without arguments
    if _cls is None:
        return decorator_singleton
    else:
        return decorator_singleton(_cls)
