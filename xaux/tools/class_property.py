# copyright ############################### #
# This file is part of the Xaux package.    #
# Copyright (c) CERN, 2025.                 #
# ######################################### #

import functools


class ClassProperty:
    """Descriptor to define class properties.
    Similar to the built-in property, but for classes instead of instances.
    - Contrary to a regular property, a __set__ or __delete__ call on the
      owner class would not be intercepted. For this reason, it is necessary
      to use a dedicated metaclass, the ClassPropertyMeta, to intercept these
      calls, even when no setter or deleter is defined (as otherwise the
      attribute would not be read-only and could still be overwritten).
    - The ClassProperty class keeps a registry of ClassProperties for each
      class, which is accessible with the 'get_properties' method.
    - Whenever a class has ClassProperties, a ClassPropertyAccessor named
      'classproperty' will be attached to it, providing an attribute-like
      interface to the ClassProperty attributes of a class for introspection.
      Use like ?MyClass.classproperty.my_class_property to get the introspect.
    - An important caveat is that regular class attributes do not always behave
      as expected when inherited, which might be an issue when a ClassProperty
      uses such a regular class attribute (for instance as the private attribute
      it is encapsulating). Indeed, when the parent has a class attribute '_prop'
      it will not be copied unto the child, and any ClassProperty.setter applied
      on the child will inevitably update the parent's attributes as well. To
      handle this, one can define a dict '_classproperty_dependencies' in the
      class to declare all dependent regular class attributes and their initial
      values. The 'ClassPropertyMeta' then copies these attributes to the child.

    Example usage:

    class MyClass(metaclass=ClassPropertyMeta):
        _classproperty_dependencies = {
            '_my_classproperty': 0
        }

        @ClassProperty
        def my_class_property(cls):
            return cls._my_classproperty

        @my_class_property.setter
        def my_class_property(cls, value):
            cls._my_classproperty = value

        @my_class_property.deleter
        def my_class_property(cls):
            cls._my_classproperty = 0
    """

    _registry = {}  # Registry to store ClassProperty names for each class

    @classmethod
    def get_properties(cls, owner, parents=True):
        """Return the ClassProperty attributes of a class, optionally including those of
        its parents."""
        if not parents:
            return cls._registry.get(owner, {})
        else:
            return {name: prop for parent in owner.__mro__
                         for name, prop in cls._registry.get(parent, {}).items()}

    def __repr__(self):
        """Return repr(self)."""
        return f"<ClassProperty at {hex(id(self))}>"

    def __init__(self, fget=None, fset=None, fdel=None, doc=None):
        """Initialize self. See help(type(self)) for accurate signature."""
        self._fget = fget
        self._fset = fset
        self._fdel = fdel
        if doc is None and fget is not None:
            doc = fget.__doc__
        self.__doc__ = doc

    def __set_name__(self, owner, name):
        """Method to set name of a ClassProperty. Also asserts that the correct metaclass
        is used, adds the property to the registry, and creates default getter, setter, and
        deleter functions."""
        self.name = name
        self.owner = owner
        # Check if we have the correct metaclass
        self._assert_metaclass()
        # Add the property name to the registry for the class
        if owner not in ClassProperty._registry:
            ClassProperty._registry[owner] = {}
        ClassProperty._registry[owner][name] = self
        # Create default getter, setter, and deleter
        if self.fget is None:
            def _getter(this_owner):
                raise AttributeError(f"Unreadable attribute '{name}' of {this_owner.__name__} "
                                    + "class!")
            self._fget = _getter
        if self.fset is None:
            def _setter(this_owner, value):
                raise AttributeError(f"ClassProperty '{name}' of '{this_owner.__name__}' class "
                                    + "has no setter")
            self._fset = _setter
        if self.fdel is None:
            def _deleter(this_owner):
                raise AttributeError(f"ClassProperty '{name}' of '{this_owner.__name__}' class "
                                    + "has no deleter")
            self._fdel = _deleter
        # Attach an accessor to the parent class to inspect ClassProperties
        if not 'classproperty' in owner.__dict__:
            owner.classproperty = ClassPropertyAccessor()
        elif not isinstance(owner.__dict__['classproperty'], ClassPropertyAccessor):
            raise TypeError(f"Class '{owner.__name__}' already has an attribute 'classproperty' "
                          + f"of type {type(owner.__dict__['classproperty']).__name__}! This is "
                          + "incompatible with the ClassProperty descriptor.")

    @property
    def fget(self):
        """Return the getter function of the ClassProperty."""
        # The fget function can only be set at initialisation, or with the getter method.
        return self._fget

    @property
    def fset(self):
        """Return the setter function of the ClassProperty."""
        # The fset function can only be set at initialisation, or with the setter method.
        return self._fset

    @property
    def fdel(self):
        """Return the deleter function of the ClassProperty."""
        # The fdel function can only be set at initialisation, or with the deleter method.
        return self._fdel

    def __get__(self, instance, owner):
        """Return an attribute of owner."""
        if owner is None:
            owner = type(instance)
        try:
            return self.fget(owner)
        except ValueError:
            # Return a fallback if initialisation fails
            return None

    def __set__(self, owner, value):
        """Set a class attribute of owner to value."""
        self.fset(owner, value)

    def __delete__(self, owner):
        """Delete an attribute of owner."""
        self.fdel(owner)

    def getter(self, fget):
        """Decorator to set the ClassProperty's getter fget."""
        self._fget = fget
        return self

    def setter(self, fset):
        """Decorator to set the ClassProperty's setter fset. Need ClassPropertyMeta for this."""
        # We check the metaclass, even though this is already done in __set_name__, for the
        # rare edge case where one would call the setter method directly after the class
        # definition.
        self._assert_metaclass()
        self._fset = fset
        return self

    def deleter(self, fdel):
        """Decorator to set the ClassProperty's deleter fdel. Need ClassPropertyMeta for this."""
        self._assert_metaclass()
        self._fdel = fdel
        return self

    def _assert_metaclass(self):
        # Verify that the metaclass is a subclass of ClassPropertyMeta, needed for fset and fdel
        if hasattr(self, 'owner'):
            if ClassPropertyMeta not in type(self.owner).__mro__:
                raise TypeError(f"Class '{self.owner.__name__}' must have ClassPropertyMeta "
                            + f"as a metaclass to be able to use ClassProperties!")


class ClassPropertyMeta(type):
    """Metaclass for classes with ClassProperty attributes.
    This metaclass intercepts __setattr__ and __delattr__ calls, such that
    setting or deleting a ClassProperty attribute on the class itself works
    as expected. Both functions are defined at the metaclass level (to be
    able to intercept calls to the class properties), but are also defined/
    overwritten at the class level to be able to intercept the same calls
    but on instances.
    """

    def __new__(cls, name, bases, data, new_class=None):
        """Define the new class. By allowing the new_class argument, we can
        easily combine the metaclass with other metaclasses that define the
        __new__ method.
        """

        if new_class is None:
            new_class = type.__new__(cls, name, bases, data)

        # Overwrite the __setattr__ method in the class
        original_setattr = new_class.__dict__.get('__setattr__', None)
        def __setattr__(self, key, value):
            """The __setattr__ method is expanded by the ClassProperty metaclass."""
            # This is the __setattr__ method when called on an INSTANCE of the class.

            this_cls = type(self)
            # Check if the attribute is a ClassProperty
            for parent in this_cls.__mro__:
                if key in parent.__dict__ and isinstance(parent.__dict__[key], ClassProperty):
                    return parent.__dict__[key].__set__(this_cls, value)
            # If not, call the original __setattr__ method.
            # However, there is still a potential issue. If we are setting a regular class
            # attribute (like the underscore variable that goes with the ClassProperty),
            # we need to set it on the class (this_cls) instead of on this instance (self);
            # otherwise the attribute would be created newly on the instance (desynced from
            # the class attribute). So we check if this attribute exists in the class dict.
            # If yes, call the metaclass __setattr__ method to set it on the class. If not,
            # call the original __setattr__ method to set it on the instance.
            # Final caveat: if the attribute is a descriptor (like a property), we DO want
            # to set it on the instance (as this is how descriptors are implemented). We
            # can recognise this by checking if the attribute has a __get__ method.
            if key in this_cls.__dict__ and not hasattr(this_cls.__dict__[key], '__get__'):
                # Set the attribute on the class
                return super(ClassPropertyMeta, this_cls).__setattr__(key, value)
            else:
                # Set the attribute on the instance
                if original_setattr is not None:
                    return original_setattr(self, key, value)
                else:
                    # We have to call super on new_class, i.e. the class this method is
                    # attached to. Otherwise we will end up in infinite loops in case of
                    # inheritance.
                    return super(new_class, self).__setattr__(key, value)
        new_class.__setattr__ = functools.wraps(ClassPropertyMeta.__setattr__)(__setattr__)

        # Overwrite the __delattr__ method in the class
        original_delattr = new_class.__dict__.get('__delattr__', None)
        def __delattr__(self, key):
            """The __delattr__ method is expanded by the ClassProperty metaclass."""
            # This is the __delattr__ method when called on an INSTANCE of the class.

            this_cls = type(self)
            # Check if the attribute is a ClassProperty
            for parent in this_cls.__mro__:
                if key in parent.__dict__ and isinstance(parent.__dict__[key], ClassProperty):
                    return parent.__dict__[key].__delete__(this_cls)
            # If not, call the original __delattr__ method.
            # The logic here is the same as in the __setattr__ method above.
            if key in this_cls.__dict__ and not hasattr(this_cls.__dict__[key], '__get__'):
                return super(ClassPropertyMeta, this_cls).__delattr__(key)
            else:
                if original_delattr is not None:
                    return original_delattr(self, key)
                else:
                    return super(new_class, self).__delattr__(key)
        new_class.__delattr__ = functools.wraps(ClassPropertyMeta.__delattr__)(__delattr__)

        # Get all dependencies that are used by the ClassProperties from the parents into the class
        for parent in new_class.__mro__:
            if '_classproperty_dependencies' in parent.__dict__:
                for key, value in parent.__dict__['_classproperty_dependencies'].items():
                    setattr(new_class, key, value)

        return new_class

    # Define __setattr__  at the metaclass level to intercept setter calls on the class
    def __setattr__(cls, key, value):
        """Set an attribute on the instance or the class, handling ClassProperty if needed."""
        # This is the __setattr__ method when called on the class ITSELF (not an instance).

        # Check if the attribute is a ClassProperty
        for parent in cls.__mro__:
            if key in parent.__dict__ and isinstance(parent.__dict__[key], ClassProperty):
                return parent.__dict__[key].__set__(cls, value)
        # If not, call the original __setattr__ method
        return super(ClassPropertyMeta, cls).__setattr__(key, value)

    # Define __delattr__  at the metaclass level to intercept deleter calls on the class
    def __delattr__(cls, key):
        """Delete an attribute from the instance or the class, handling ClassProperty if needed."""
        # This is the __delattr__ method when called on the class ITSELF (not an instance).

        # Check if the attribute is a ClassProperty
        for parent in cls.__mro__:
            if key in parent.__dict__ and isinstance(parent.__dict__[key], ClassProperty):
                return parent.__dict__[key].__delete__(cls)
        # If not, call the original __delattr__ method
        return super(ClassPropertyMeta, cls).__delattr__(key)


class ClassPropertyAccessor:
    """Helper class to introspect the ClassProperty attributes of a class and
    their docstrings."""

    def __repr__(self):
        """Return repr(self)."""
        return f"<ClassPropertyAccessor at {hex(id(self))}>"

    def __get__(self, instance, owner):
        """Return a ClassPropertyDict object for the owner class."""
        return ClassPropertyDict(owner)


class ClassPropertyDict:
    """Helper class to provide an attribute-like interface to the ClassProperty
    attributes of a class. This way, one can do e.g. ?MyClass.classproperty.cprop1
    to get the introspect info of cprop1."""

    def __init__(self, owner):
        """Initialize self. See help(type(self)) for accurate signature."""
        self.owner = owner
        self._cprops = ClassProperty.get_properties(owner, parents=True)

    @property
    def names(self):
        """Return the names of the ClassProperty attributes of the owner class."""
        return tuple(self._cprops.keys())

    def __repr__(self):
        """Return repr(self)."""
        num_props = len(self)
        props = "ClassProperties" if num_props != 1 else "ClassProperty"
        return f"<ClassPropertyDict on class {self.owner.__name__} ({num_props} "\
             + f"{props}) at {hex(id(self))}>"

    def __iter__(self):
        """Implement iter(self)."""
        return self._cprops.__iter__()

    def keys(self):
        """A set-like object providing a view on the ClassProperty names."""
        return self._cprops.keys()

    def values(self):
        """A set-like object providing a view on the ClassProperties."""
        return self._cprops.values()

    def items(self):
        """A set-like object providing a view on the ClassProperties and their names."""
        return self._cprops.items()

    def __len__(self):
        """Return len(self)."""
        return len(self._cprops)

    def __contains__(self, key):
        """Return key in self."""
        return key in self._cprops

    def __getattr__(self, name):
        """Access the ClassProperty attributes of the owner class."""
        if name not in self._cprops:
            raise AttributeError(f"Class '{self.owner.__name__}' has no ClassProperty '{name}'")
        return self._cprops.get(name)
