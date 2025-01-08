# copyright ############################### #
# This file is part of the Xaux Package.    #
# Copyright (c) CERN, 2024.                 #
# ######################################### #

import pytest
from xaux import singleton, ClassProperty, ClassPropertyMeta

def test_singleton():
    # Non-singleton example.
    class NonSingletonClass:
        def __init__(self, value=3):
            self.value = value

    instance1 = NonSingletonClass()
    assert instance1.value == 3
    instance2 = NonSingletonClass(value=5)
    assert instance1 is not instance2
    assert id(instance1) != id(instance2)
    assert instance1.value == 3
    assert instance2.value == 5
    instance1.value = 7
    assert instance1.value == 7
    assert instance2.value == 5

    @singleton
    class SingletonClass:
        def __init__(self, value=3):
            self.value = value

    # Initialise with default value
    assert not hasattr(SingletonClass, 'instance')
    instance1 = SingletonClass()
    assert hasattr(SingletonClass, 'instance')
    assert instance1.value == 3

    # Initialise with specific value
    instance2 = SingletonClass(value=5)
    assert instance1 is instance2
    assert id(instance1) == id(instance2)
    assert instance1.value == 5
    assert instance2.value == 5

    # Initialise with default value again - this should not change the value
    instance3 = SingletonClass()
    assert instance1.value == 5
    assert instance2.value == 5
    assert instance3.value == 5

    # Change the value of the instance
    instance1.value = 7
    assert instance1.value == 7
    assert instance2.value == 7
    assert instance3.value == 7

    # Remove the singleton
    SingletonClass.delete()
    assert not hasattr(SingletonClass, 'instance')
    with pytest.raises(RuntimeError, match="This instance of the singleton SingletonClass "
                                         + "has been invalidated!"):
        instance1.value
    with pytest.raises(RuntimeError, match="This instance of the singleton SingletonClass "
                                         + "has been invalidated!"):
        instance2.value
    with pytest.raises(RuntimeError, match="This instance of the singleton SingletonClass "
                                         + "has been invalidated!"):
        instance3.value

    # First initialisation with specific value
    instance4 = SingletonClass(value=8)
    assert hasattr(SingletonClass, 'instance')
    assert instance4.value == 8
    assert instance1 is not instance4
    assert instance2 is not instance4
    assert instance3 is not instance4
    assert id(instance1) != id(instance4)
    assert id(instance2) != id(instance4)
    assert id(instance3) != id(instance4)


def test_get_self():
    @singleton
    class SingletonClass:
        def __init__(self, value=3):
            self.value = value

    # Initialise with default value
    instance = SingletonClass()
    instance.value = 10

    # Get self with default value
    self1 = SingletonClass.get_self()
    assert self1 is instance
    assert id(self1) == id(instance)
    assert self1.value == 10
    assert instance.value == 10

    # Get self with specific value
    self2 = SingletonClass.get_self(value=11)
    assert self2 is instance
    assert self2 is self1
    assert id(self2) == id(instance)
    assert id(self2) == id(self1)
    assert instance.value == 11
    assert self1.value == 11
    assert self2.value == 11

    # Get self with non-existing attribute
    self3 = SingletonClass.get_self(non_existing_attribute=13)
    assert self3 is instance
    assert self3 is self1
    assert self3 is self2
    assert id(self3) == id(instance)
    assert id(self3) == id(self1)
    assert id(self3) == id(self2)
    assert instance.value == 11
    assert self1.value == 11
    assert self2.value == 11
    assert self3.value == 11
    assert not hasattr(SingletonClass, 'non_existing_attribute')
    assert not hasattr(instance, 'non_existing_attribute')
    assert not hasattr(self1, 'non_existing_attribute')
    assert not hasattr(self2, 'non_existing_attribute')
    assert not hasattr(self3, 'non_existing_attribute')

    # Get self with specific value and non-existing attribute
    self4 = SingletonClass.get_self(value=12, non_existing_attribute=13)
    assert self4 is instance
    assert self4 is self1
    assert self4 is self2
    assert self4 is self3
    assert id(self4) == id(instance)
    assert id(self4) == id(self1)
    assert id(self4) == id(self2)
    assert id(self4) == id(self3)
    assert instance.value == 12
    assert self1.value == 12
    assert self2.value == 12
    assert self3.value == 12
    assert self4.value == 12
    assert not hasattr(SingletonClass, 'non_existing_attribute')
    assert not hasattr(instance, 'non_existing_attribute')
    assert not hasattr(self1, 'non_existing_attribute')
    assert not hasattr(self2, 'non_existing_attribute')
    assert not hasattr(self3, 'non_existing_attribute')
    assert not hasattr(self4, 'non_existing_attribute')

    # Remove the singleton
    SingletonClass.delete()

    # Initialise with get self with default value
    self5 = SingletonClass.get_self()
    assert self5 is not instance
    assert self5 is not self1
    assert self5 is not self2
    assert self5 is not self3
    assert self5 is not self4
    assert id(self5) != id(instance)
    assert id(self5) != id(self1)
    assert id(self5) != id(self2)
    assert id(self5) != id(self3)
    assert id(self5) != id(self4)
    assert self5.value == 3

    # Remove the singleton
    SingletonClass.delete()

    # Initialise with get self with specific value
    self6 = SingletonClass.get_self(value=-3)
    assert self6 is not instance
    assert self6 is not self1
    assert self6 is not self2
    assert self6 is not self3
    assert self6 is not self4
    assert self6 is not self5
    assert id(self6) != id(instance)
    assert id(self6) != id(self1)
    assert id(self6) != id(self2)
    assert id(self6) != id(self3)
    assert id(self6) != id(self4)
    assert id(self6) != id(self5)
    assert self6.value == -3

