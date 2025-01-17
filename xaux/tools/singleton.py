# copyright ############################### #
# This file is part of the Xaux package.    #
# Copyright (c) CERN, 2025.                 #
# ######################################### #

import sys
import functools

from .function_tools import count_required_arguments


# TODO: allow_underscore_vars_in_init=False is not very robust. Do we need it for ClassProperty?

def singleton(_cls=None, *, allow_underscore_vars_in_init=True):
    """Singleton decorator.
    This decorator will redefine a class such that only one instance exists and the same
    instance is returned every time the class is instantiated.
    - Each re-initialisation of the singleton will keep the class attributes, and for this
      reason, the __init__ method should not have any required arguments. This is asserted
      at the class creation time.
    - By default, the singleton will not allow setting private attributes in the constructor,
      but this can be overridden by setting 'allow_underscore_vars_in_init=True'.
    - This decorator is fully compatible with inheritance, and each child of a singleton
      class will be its own singleton.
    - The singleton can be reset by calling the 'delete()' method of the class, which will
      invalidate any existing instances.
    - The decorator provides a get_self method, which is a class method that is more relaxed
      than the constructor, as it allows passing any kwargs even if they aren't attributes
      for the singleton (these  will then just be ignored). This is useful for kwargs
      filtering in getters or specific functions.
    """
    # Caveat I: whenever any monkey-patched method is called, the super method should be 
    # called on the original singleton class (not the current class), to avoid infinite
    # loops (it would just call the same method again).
    # Caveat II: When we need to get the current class of an instance,
    # we should use type(self) instead of self.__class__, as the latter will get into an
    # infinite loop because of the __getattribute__ method.

    # Internal decorator definition to used without arguments
    def decorator_singleton(cls):
        # Monkey-patch __new__ to create a singleton
        original_new = cls.__dict__.get('__new__', None)
        @functools.wraps(cls.__new__)
        def singleton_new(this_cls, *args, **kwargs):
            # If the singleton instance does not exist, create it
            if '_singleton_instance' not in this_cls.__dict__:
                if original_new:
                    # This NEEDS to call 'this_cls' instead of 'cls' to avoid always spawning a cls instance
                    if sys.version_info >= (3, 10):
                        inst = original_new(this_cls, *args, **kwargs)
                    else:
                        inst = original_new.__func__(this_cls, *args, **kwargs)
                else:
                    try:
                        inst = super(cls, cls).__new__(this_cls, *args, **kwargs)
                    except TypeError:
                        inst = super(cls, cls).__new__(this_cls)
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
        @functools.wraps(cls.__init__)
        def singleton_init(self, *args, **kwargs):
            this_cls = type(self)
            # Validate kwargs
            kwargs.pop('_initialised', None)
            for kk in list(kwargs.keys()) + list(args):
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
        @functools.wraps(cls.__getattribute__)
        def singleton_getattribute(self, name):
            this_cls = type(self)
            def _patch_getattribute(obj, this_name):
                if original_getattribute:
                    return original_getattribute(obj, this_name)
                else:
                    return super(cls, obj).__getattribute__(this_name)
            if not hasattr(this_cls, '_singleton_instance') \
            or not _patch_getattribute(self, '_valid'):
                raise RuntimeError(f"This instance of the singleton {this_cls.__name__} "
                                  + "has been invalidated!")
            return _patch_getattribute(self, name)
        cls.__getattribute__ = singleton_getattribute

        # Add the get_self method to the class
        if cls.__dict__.get('get_self', None) is not None:
            raise ValueError(f"Class {cls} provides a 'get_self' method. This is not compatible "
                            + "with the singleton decorator!")
        @classmethod
        def get_self(this_cls, **kwargs):
            """The get_self(**kwargs) method returns the singleton instance, allowing to pass
            any kwargs to the constructor, even if they are not attributes of the singleton.
            This is useful for kwargs filtering in getters or specific functions.
            """
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

        # Add the delete method to the class
        if cls.__dict__.get('delete', None) is not None:
            raise ValueError(f"Class {cls} provides a 'delete' method. This is not compatible "
                            + "with the singleton decorator!")
        @classmethod
        def delete(this_cls):
            """The delete() method removes the singleton and invalidates any existing instances,
            allowing to create a new instance the next time the class is instantiated. This is
            useful for resetting the singleton to its default values.
            """
            if hasattr(this_cls, '_singleton_instance'):
                # Invalidate (pointers to) existing instances!
                this_cls._singleton_instance._valid = False
                del this_cls._singleton_instance
        cls.delete = delete

        return cls

    # Hack to allow the decorator to be used with or without arguments
    if _cls is None:
        return decorator_singleton
    else:
        return decorator_singleton(_cls)
