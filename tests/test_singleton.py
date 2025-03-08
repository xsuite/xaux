# copyright ############################### #
# This file is part of the Xaux package.    #
# Copyright (c) CERN, 2025.                 #
# ######################################### #

import re
import pytest
import numpy as np

from xaux import singleton


# We are overly verbose in these tests, comparing every time again all instances to each other.
# This is to make sure that the singletons are really singletons and that they do not interfere
# with each other. It's an important overhead to ensure we deeply test the global states, because
# if we would pytest.parametrize this, we might be copying state and not realising this.


def test_singleton():
    # Non-singleton example.
    class NonSingletonClass:
        def __init__(self, value1=3):
            self.value1 = value1

    instance1 = NonSingletonClass()
    assert instance1.value1 == 3
    instance2 = NonSingletonClass(value1=5)
    assert instance1 is not instance2
    assert id(instance1) != id(instance2)
    assert instance1.value1 == 3
    assert instance2.value1 == 5
    instance1.value1 = 7
    assert instance1.value1 == 7
    assert instance2.value1 == 5

    @singleton
    class SingletonClass1:
        def __init__(self, value1=3):
            self.value1 = value1

    _assert_is_singleton(SingletonClass1, [instance1,instance2], 3)


def test_nonsingleton_inheritance():
    class NonSingletonParent:
        def __init__(self, value1=3):
            print("(in NonSingletonParent __init__)   ", end='', flush=True)
            self.value1 = value1

    @singleton
    class SingletonChild1(NonSingletonParent):
        def __init__(self, *args, value2=17, **kwargs):
            print("(in SingletonChild1 __init__)   ", end='', flush=True)
            self.value2 = value2
            super().__init__(*args, **kwargs)

    @singleton
    class SingletonChild2(NonSingletonParent):
        def __init__(self, *args, value2=-13, **kwargs):
            print("(in SingletonChild2 __init__)   ", end='', flush=True)
            self.value2 = value2
            super().__init__(*args, **kwargs)

    # Test the non-singleton parent class
    ns_parent_instance1 = NonSingletonParent(value1=8)
    assert ns_parent_instance1.value1 == 8
    ns_parent_instance2 = NonSingletonParent(value1=9)
    assert ns_parent_instance1 is not ns_parent_instance2
    assert ns_parent_instance1.value1 == 8
    assert ns_parent_instance2.value1 == 9

    # Test the singleton child classes
    _assert_is_singleton(SingletonChild1, [ns_parent_instance1,ns_parent_instance2], 3, 17)
    child1_instance = SingletonChild1()
    _assert_is_singleton(SingletonChild2, [child1_instance,ns_parent_instance1,ns_parent_instance2], 3, -13)


def test_singleton_inheritance():
    @singleton
    class SingletonParent1:
        def __init__(self, value1=7):
            print("(in SingletonParent1 __init__)   ", end='', flush=True)
            self.value1 = value1

    class SingletonChild3(SingletonParent1):
        def __init__(self, *args, value2=81, **kwargs):
            print("(in SingletonChild3 __init__)   ", end='', flush=True)
            self.value2 = value2
            super().__init__(*args, **kwargs)

    class SingletonChild4(SingletonParent1):
        def __init__(self, *args, value2=0, **kwargs):
            print("(in SingletonChild4 __init__)   ", end='', flush=True)
            self.value2 = value2
            super().__init__(*args, **kwargs)

    _assert_is_singleton(SingletonParent1, [], 7)
    parent1_instance = SingletonParent1()
    parent1_instance.value1 = 989
    _assert_is_singleton(SingletonChild3, [parent1_instance], 7, 81)
    child3_instance1 = SingletonChild3()
    child3_instance1.value1 = 111
    child3_instance1.value2 = -333
    _assert_is_singleton(SingletonChild4, [child3_instance1,parent1_instance], 7, 0)

    # Now delete all and start fresh, to ensure children can instantiate without parent existing.
    SingletonParent1.delete()
    assert not hasattr(SingletonParent1, '_singleton_instance')
    SingletonChild3.delete()
    assert not hasattr(SingletonChild3, '_singleton_instance')
    SingletonChild4.delete()
    assert not hasattr(SingletonChild4, '_singleton_instance')

    _assert_is_singleton(SingletonChild3, [], 7, 81)
    child3_instance2 = SingletonChild3()
    child3_instance2.value1 = 111
    child3_instance2.value2 = -333
    _assert_is_singleton(SingletonChild4, [child3_instance2], 7, 0)


# This is the same test as above, but with the singleton decorator applied to parent and child
def test_double_singleton_inheritance():
    @singleton
    class SingletonParent2:
        def __init__(self, value1=6):
            print("(in SingletonParent2 __init__)   ", end='', flush=True)
            self.value1 = value1

    @singleton
    class SingletonChild5(SingletonParent2):
        def __init__(self, *args, value2=82, **kwargs):
            print("(in SingletonChild5 __init__)   ", end='', flush=True)
            self.value2 = value2
            super().__init__(*args, **kwargs)

    @singleton
    class SingletonChild6(SingletonParent2):
        def __init__(self, *args, value2=-2, **kwargs):
            print("(in SingletonChild6 __init__)   ", end='', flush=True)
            self.value2 = value2
            super().__init__(*args, **kwargs)

    _assert_is_singleton(SingletonParent2, [], 6)
    parent2_instance = SingletonParent2()
    parent2_instance.value1 = 989
    _assert_is_singleton(SingletonChild5, [parent2_instance], 6, 82)
    child5_instance1 = SingletonChild5()
    child5_instance1.value1 = 222
    child5_instance1.value2 = -666
    _assert_is_singleton(SingletonChild6, [child5_instance1,parent2_instance], 6, -2)

    # Now delete all and start fresh, to ensure children can instantiate without parent existing.
    SingletonParent2.delete()
    assert not hasattr(SingletonParent2, '_singleton_instance')
    SingletonChild5.delete()
    assert not hasattr(SingletonChild5, '_singleton_instance')
    SingletonChild6.delete()
    assert not hasattr(SingletonChild6, '_singleton_instance')

    _assert_is_singleton(SingletonChild5, [], 7, 81)
    child5_instance2 = SingletonChild5()
    child5_instance2.value1 = 111
    child5_instance2.value2 = -333
    _assert_is_singleton(SingletonChild6, [child5_instance2], 6, -2)


def test_singleton_grand_inheritance():
    @singleton
    class SingletonParent3:
        def __init__(self, value1=4):
            print("(in SingletonParent2 __init__)   ", end='', flush=True)
            self.value1 = value1

    class SingletonChild7(SingletonParent3):
        def __init__(self, *args, value2=137, **kwargs):
            print("(in SingletonChild7 __init__)   ", end='', flush=True)
            self.value2 = value2
            super().__init__(*args, **kwargs)

    class SingletonGrandChild(SingletonChild7):
        def __init__(self, *args, value3=19870, **kwargs):
            print("(in SingletonGrandChild __init__)   ", end='', flush=True)
            self.value3 = value3
            super().__init__(*args, **kwargs)

    _assert_is_singleton(SingletonParent3, [], 4)
    parent3_instance = SingletonParent3()
    parent3_instance.value1 = 444
    _assert_is_singleton(SingletonChild7, [parent3_instance], 4, 137)
    child7_instance1 = SingletonChild7()
    child7_instance1.value1 = 678
    child7_instance1.value2 = -987
    _assert_is_singleton(SingletonGrandChild, [child7_instance1,parent3_instance], 4, 137, 19870)

    # Now delete all and start fresh, to ensure children can instantiate without parent existing.
    SingletonParent3.delete()
    assert not hasattr(SingletonParent3, '_singleton_instance')
    SingletonChild7.delete()
    assert not hasattr(SingletonChild7, '_singleton_instance')
    SingletonGrandChild.delete()
    assert not hasattr(SingletonGrandChild, '_singleton_instance')

    _assert_is_singleton(SingletonChild7, [], 4, 137)
    child7_instance2 = SingletonChild7()
    child7_instance2.value1 = -678
    child7_instance2.value2 = 987
    _assert_is_singleton(SingletonGrandChild, [child7_instance2], 4, 137, 19870)


def _assert_is_singleton(cls, other_cls_instances, value1_init, value2_init=None, value3_init=None):
    rng = np.random.default_rng()
    value1_test_vals = [value1_init, *rng.integers(low=-587692, high=6284724, size=10_000)]
    value2_test_vals = [value2_init, *rng.integers(low=-587692, high=6284724, size=10_000)]
    value3_test_vals = [value3_init, *rng.integers(low=-587692, high=6284724, size=10_000)]

    # These tests are overly overly verbose and expanded, to try to catch all possible corner cases.
    # We are comparing every time again all instances to each other.

    # This is an instance of another (maybe related) class, which should never be influenced by what we do on cls
    ref_values1 = [inst.value1 for inst in other_cls_instances]
    ref_values2 = [inst.value2 if hasattr(inst, 'value2') else None
                   for inst in other_cls_instances]
    ref_values3 = [inst.value3 if hasattr(inst, 'value3') else None
                   for inst in other_cls_instances]

    def init_switch(init_type, instances, i):
        if init_type is None:
            print(f"Initialise with default values (value1={value1_init}, value2={value2_init}, value3={value3_init})... ", end='', flush=True)
            instances.insert(0, cls())
        elif init_type == '1':
            i['1'] += 1
            print(f"Initialise with value1={value1_test_vals[i['1']]}... ", end='', flush=True)
            instances.insert(0, cls(value1=value1_test_vals[i['1']]))
        elif init_type == '2' and value2_init is not None:
            i['2'] += 1
            print(f"Initialise with value2={value2_test_vals[i['2']]}... ", end='', flush=True)
            instances.insert(0, cls(value2=value2_test_vals[i['2']]))
        elif init_type == '3' and value3_init is not None:
            i['3'] += 1
            print(f"Initialise with value3={value3_test_vals[i['3']]}... ", end='', flush=True)
            instances.insert(0, cls(value3=value3_test_vals[i['3']]))
        elif init_type == '12' and value2_init is not None:
            i['1'] += 1
            i['2'] += 1
            print(f"Initialise with value1={value1_test_vals[i['1']]} and value2={value2_test_vals[i['2']]}... ", end='', flush=True)
            instances.insert(0, cls(value1=value1_test_vals[i['1']], value2=value2_test_vals[i['2']]))
        elif init_type == '13' and value3_init is not None:
            i['1'] += 1
            i['3'] += 1
            print(f"Initialise with value1={value1_test_vals[i['1']]} and value3={value3_test_vals[i['3']]}... ", end='', flush=True)
            instances.insert(0, cls(value1=value1_test_vals[i['1']], value3=value3_test_vals[i['3']]))
        elif init_type == '23' and value2_init is not None and value3_init is not None:
            i['2'] += 1
            i['3'] += 1
            print(f"Initialise with value2={value2_test_vals[i['2']]} and value3={value3_test_vals[i['3']]}... ", end='', flush=True)
            instances.insert(0, cls(value2=value2_test_vals[i['2']], value3=value3_test_vals[i['3']]))
        elif init_type == '123' and value2_init is not None and value3_init is not None:
            i['1'] += 1
            i['2'] += 1
            i['3'] += 1
            print(f"Initialise with value1={value1_test_vals[i['1']]}, value2={value2_test_vals[i['2']]} and value3={value3_test_vals[i['3']]}... ", end='', flush=True)
            instances.insert(0, cls(value1=value1_test_vals[i['1']], value2=value2_test_vals[i['2']], value3=value3_test_vals[i['3']]))

    def assert_singleton(this_instance, *args, value1, value2, value3):
        assert this_instance is cls._singleton_instance
        for other_instance in args:
            assert this_instance is other_instance
            assert id(this_instance) == id(other_instance)
        assert this_instance.value1 == value1
        if value2_init is not None:
            assert this_instance.value2 == value2
        if value3_init is not None:
            assert this_instance.value3 == value3
        # Assert the other instances are unaffected
        for inst, ref_value1, ref_value2, ref_value3 in zip(other_cls_instances, ref_values1, ref_values2, ref_values3):
            assert inst is not this_instance
            assert inst.value1 == ref_value1
            if ref_value2 is not None:
                assert inst.value2 == ref_value2
            if ref_value3 is not None:
                assert inst.value3 == ref_value3

    def assert_and_increase_vals(instances, i):
        assert_singleton(*instances, value1=value1_test_vals[i['1']], value2=value2_test_vals[i['2']], value3=value3_test_vals[i['3']])
        print("OK")
        i['1'] += 1
        j = 1 if len(instances) > 1 else 0
        print(f"Overwriting value1={value1_test_vals[i['1']]}... ", end='', flush=True)
        instances[j].value1 = value1_test_vals[i['1']]
        assert_singleton(*instances, value1=value1_test_vals[i['1']], value2=value2_test_vals[i['2']], value3=value3_test_vals[i['3']])
        print("OK")
        if value2_init is not None:
            i['2'] += 1
            print(f"Overwriting value2={value2_test_vals[i['2']]}... ", end='', flush=True)
            instances[j].value2 = value2_test_vals[i['2']]
            assert_singleton(*instances, value1=value1_test_vals[i['1']], value2=value2_test_vals[i['2']], value3=value3_test_vals[i['3']])
            print("OK")
        if value3_init is not None:
            i['3'] += 1
            print(f"Overwriting value3={value3_test_vals[i['3']]}... ", end='', flush=True)
            instances[j].value3 = value3_test_vals[i['3']]
            assert_singleton(*instances, value1=value1_test_vals[i['1']], value2=value2_test_vals[i['2']], value3=value3_test_vals[i['3']])
            print("OK")

    # Initialise with default values first, then initialise with value1, then value2, then both
    if value2_init is None and value3_init is None:
        first_init_switches = [None, '1']
    elif value3_init is None:
        first_init_switches = [None, '1', '2', '12']
    else:
        first_init_switches = [None, '1', '2', '3', '12', '13', '23', '123']
    for first_init_switch in first_init_switches:
        print("First initialisation!   ", end='', flush=True)
        instances = []
        i = {'1': 0, '2': 0, '3': 0}
        assert not hasattr(cls, '_singleton_instance')
        init_switch(first_init_switch, instances, i)
        assert hasattr(cls, '_singleton_instance')
        assert hasattr(cls._singleton_instance, '_initialised')
        assert cls._singleton_instance._initialised
        assert_and_increase_vals(instances, i)

        init_switch('1', instances, i)
        assert_and_increase_vals(instances, i)
        init_switch('1', instances, i)
        assert_and_increase_vals(instances, i)
        init_switch(None, instances, i)
        assert_and_increase_vals(instances, i)
        if value2_init is not None:
            init_switch('2', instances, i)
            assert_and_increase_vals(instances, i)
            init_switch('1', instances, i)
            assert_and_increase_vals(instances, i)
            init_switch('2', instances, i)
            assert_and_increase_vals(instances, i)
            init_switch('2', instances, i)
            assert_and_increase_vals(instances, i)
            init_switch('12', instances, i)
            assert_and_increase_vals(instances, i)
        if value3_init is not None:
            init_switch('3', instances, i)
            assert_and_increase_vals(instances, i)
            init_switch('2', instances, i)
            assert_and_increase_vals(instances, i)
            init_switch('2', instances, i)
            assert_and_increase_vals(instances, i)
            init_switch('23', instances, i)
            assert_and_increase_vals(instances, i)
            init_switch('13', instances, i)
            assert_and_increase_vals(instances, i)
            init_switch('123', instances, i)
            assert_and_increase_vals(instances, i)

        cls.delete()
        assert not hasattr(cls, '_singleton_instance')
        for inst in instances:
            with pytest.raises(RuntimeError, match=f"This instance of the singleton {cls.__name__} "
                                                  + "has been invalidated!"):
                inst.value
        # Double deletion should not influence
        cls.delete()
        assert not hasattr(cls, '_singleton_instance')
        for inst in instances:
            with pytest.raises(RuntimeError, match=f"This instance of the singleton {cls.__name__} "
                                                  + "has been invalidated!"):
                inst.value
        print("")

def test_get_self():
    @singleton
    class SingletonClass2:
        def __init__(self, value1=19):
            self.value1 = value1

    # Initialise with default value
    instance = SingletonClass2()
    assert instance.value1 == 19

    # Get self with default value
    self1 = SingletonClass2.get_self()
    assert self1 is instance
    assert id(self1) == id(instance)
    assert self1.value1 == 19
    assert instance.value1 == 19

    # Get self with specific value
    self2 = SingletonClass2.get_self(value1=11)
    assert self2 is instance
    assert self2 is self1
    assert instance.value1 == 11

    # Get self with non-existing attribute
    self3 = SingletonClass2.get_self(non_existing_attribute=13)
    assert self3 is instance
    assert self3 is self1
    assert self3 is self2
    assert instance.value1 == 11
    assert not hasattr(SingletonClass2, 'non_existing_attribute')
    assert not hasattr(instance, 'non_existing_attribute')
    assert not hasattr(self1, 'non_existing_attribute')
    assert not hasattr(self2, 'non_existing_attribute')
    assert not hasattr(self3, 'non_existing_attribute')

    # Get self with specific value and non-existing attribute
    self4 = SingletonClass2.get_self(value1=12, non_existing_attribute=13)
    assert self4 is instance
    assert self4 is self1
    assert self4 is self2
    assert self4 is self3
    assert instance.value1 == 12
    assert not hasattr(SingletonClass2, 'non_existing_attribute')
    assert not hasattr(instance, 'non_existing_attribute')
    assert not hasattr(self1, 'non_existing_attribute')
    assert not hasattr(self2, 'non_existing_attribute')
    assert not hasattr(self3, 'non_existing_attribute')
    assert not hasattr(self4, 'non_existing_attribute')

    # Remove the singleton
    SingletonClass2.delete()
    assert not hasattr(SingletonClass2, '_singleton_instance')

    # Initialise with get self with default value
    self5 = SingletonClass2.get_self()
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
    assert self5.value1 == 19

    # Remove the singleton
    SingletonClass2.delete()
    assert not hasattr(SingletonClass2, '_singleton_instance')

    # Initialise with get self with specific value
    self6 = SingletonClass2.get_self(value1=-3)
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
    assert self6.value1 == -3

    class SingletonChild8(SingletonClass2):
        def __init__(self, *args, value2=100, **kwargs):
            print("In SingletonChild8 __init__")
            self.value2 = value2
            super().__init__(*args, **kwargs)

    # Initialise child with default value
    child = SingletonChild8()
    child.value = 19

    # Get self with default value
    self7 = SingletonChild8.get_self()
    assert self7 is child
    assert self7.value == 19
    assert child is not instance
    assert child is not self1

    # Remove both singletons
    SingletonClass2.delete()
    assert not hasattr(SingletonClass2, '_singleton_instance')
    SingletonChild8.delete()
    assert not hasattr(SingletonChild8, '_singleton_instance')

    # Initialise child with default value
    new_child = SingletonChild8()
    assert new_child.value1 == 19
    assert new_child is not child
    assert new_child is not instance
    assert new_child is not self1

    # Get self with default value
    self7 = SingletonChild8.get_self()
    assert self7 is new_child
    assert self7.value1 == 19
    assert self7 is not instance
    assert self7 is not self1
    assert self7 is not child

    # Get self with specific value
    self8 = SingletonChild8.get_self(value1=11)
    assert self8 is new_child
    assert self8 is self7
    assert new_child.value1 == 11
    assert self8 is not instance
    assert self8 is not self1
    assert self8 is not child

    # Get self with non-existing attribute
    self9 = SingletonChild8.get_self(non_existing_attribute=13)
    assert self9 is new_child
    assert self9 is self7
    assert self9 is self8
    assert new_child.value1 == 11
    assert self9 is not instance
    assert self9 is not self1
    assert self9 is not child
    assert not hasattr(SingletonChild8, 'non_existing_attribute')
    assert not hasattr(new_child, 'non_existing_attribute')
    assert not hasattr(self7, 'non_existing_attribute')
    assert not hasattr(self8, 'non_existing_attribute')
    assert not hasattr(self9, 'non_existing_attribute')

    # Get self with specific value and non-existing attribute
    self10 = SingletonChild8.get_self(value1=12, non_existing_attribute=13)
    assert self10 is new_child
    assert self10 is self7
    assert self10 is self8
    assert self10 is self9
    assert new_child.value1 == 12
    assert self10 is not instance
    assert self10 is not self1
    assert self10 is not child
    assert not hasattr(SingletonChild8, 'non_existing_attribute')
    assert not hasattr(new_child, 'non_existing_attribute')
    assert not hasattr(self7, 'non_existing_attribute')
    assert not hasattr(self8, 'non_existing_attribute')
    assert not hasattr(self9, 'non_existing_attribute')
    assert not hasattr(self10, 'non_existing_attribute')

    # Remove the singleton
    SingletonChild8.delete()
    assert not hasattr(SingletonChild8, '_singleton_instance')

    # Initialise with get self with default value
    self11 = SingletonChild8.get_self()
    assert self11 is not instance
    assert self11 is not self1
    assert self11 is not child
    assert self11 is not new_child
    assert self11 is not self7
    assert self11 is not self8
    assert self11 is not self9
    assert self11 is not self10
    assert id(self11) != id(new_child)
    assert id(self11) != id(self7)
    assert id(self11) != id(self8)
    assert id(self11) != id(self9)
    assert id(self11) != id(self10)
    assert self11.value1 == 19

    # Remove the singleton
    SingletonChild8.delete()
    assert not hasattr(SingletonChild8, '_singleton_instance')

    # Initialise with get self with specific value
    self12 = SingletonChild8.get_self(value1=-3)
    assert self12 is not instance
    assert self12 is not self1
    assert self12 is not child
    assert self12 is not new_child
    assert self12 is not self7
    assert self12 is not self8
    assert self12 is not self9
    assert self12 is not self10
    assert self12 is not self11
    assert id(self12) != id(new_child)
    assert id(self12) != id(self7)
    assert id(self12) != id(self2)
    assert id(self12) != id(self9)
    assert id(self12) != id(self10)
    assert id(self12) != id(self11)
    assert self12.value1 == -3

    # Clean up
    SingletonChild8.delete()
    assert not hasattr(SingletonChild8, '_singleton_instance')


def test_singleton_with_custom_dunder():
    @singleton
    class SingletonClass3:
        pass

    @singleton
    class SingletonClass4:
        def __new__(cls, *args, **kwargs):
            print("In SingletonClass4 __new__")
            instance = super().__new__(cls)
            instance.test_var_new = 1
            return instance

    @singleton
    class SingletonClass5:
        def __init__(self, value='YASSS'):
            print("In SingletonClass5 __init__")
            self.value = value
            self.test_var_init = 10

    @singleton
    class SingletonClass6:
        def __getattribute__(self, name):
            print("In SingletonClass6 __getattribute__")
            self.test_var_getattr = 100
            return super().__getattribute__(name)

    @singleton
    class SingletonClass7:
        def __new__(cls, *args, **kwargs):
            print("In SingletonClass7 __new__")
            instance = super().__new__(cls)
            instance.test_var_new = 2
            return instance

        def __init__(self, value='YASSS'):
            print("In SingletonClass7 __init__")
            self.value = value
            self.test_var_init = 20

        def __getattribute__(self, name):
            print("In SingletonClass7 __getattribute__")
            self.test_var_getattr = 200
            return super().__getattribute__(name)

    # Test SingletonClass3
    class3_instance1 = SingletonClass3()
    assert not hasattr(class3_instance1, 'test_var_new')
    assert not hasattr(class3_instance1, 'test_var_init')
    assert not hasattr(class3_instance1, 'test_var_getattr')
    class3_instance2 = SingletonClass3()
    assert class3_instance1 is class3_instance2
    assert not hasattr(class3_instance2, 'test_var_new')
    assert not hasattr(class3_instance2, 'test_var_init')
    assert not hasattr(class3_instance2, 'test_var_getattr')

    # Test SingletonClass4
    class4_instance1 = SingletonClass4()
    assert hasattr(class4_instance1, 'test_var_new')
    assert class4_instance1.test_var_new == 1
    assert not hasattr(class4_instance1, 'test_var_init')
    assert not hasattr(class4_instance1, 'test_var_getattr')
    class4_instance2 = SingletonClass4()
    assert class4_instance1 is class4_instance2
    assert hasattr(class4_instance2, 'test_var_new')
    assert class4_instance2.test_var_new == 1
    assert not hasattr(class4_instance2, 'test_var_init')
    assert not hasattr(class4_instance2, 'test_var_getattr')

    # Test SingletonClass5
    class5_instance1 = SingletonClass5()
    assert class5_instance1.value == 'YASSS'
    assert not hasattr(class5_instance1, 'test_var_new')
    assert hasattr(class5_instance1, 'test_var_init')
    assert class5_instance1.test_var_init == 10
    assert not hasattr(class5_instance1, 'test_var_getattr')
    class5_instance2 = SingletonClass5()
    assert class5_instance1 is class5_instance2
    assert not hasattr(class5_instance2, 'test_var_new')
    assert hasattr(class5_instance2, 'test_var_init')
    assert class5_instance2.test_var_init == 10
    assert not hasattr(class5_instance2, 'test_var_getattr')

    # Test SingletonClass6
    class6_instance1 = SingletonClass6()
    assert not hasattr(class6_instance1, 'test_var_new')
    assert not hasattr(class6_instance1, 'test_var_init')
    assert hasattr(class6_instance1, 'test_var_getattr')
    assert class6_instance1.test_var_getattr == 100
    class6_instance2 = SingletonClass6()
    assert class6_instance1 is class6_instance2
    assert not hasattr(class6_instance2, 'test_var_new')
    assert not hasattr(class6_instance2, 'test_var_init')
    assert hasattr(class6_instance2, 'test_var_getattr')
    assert class6_instance2.test_var_getattr == 100

    # Test SingletonClass7
    class7_instance1 = SingletonClass7()
    assert class7_instance1.value == 'YASSS'
    assert hasattr(class7_instance1, 'test_var_new')
    assert class7_instance1.test_var_new == 2
    assert hasattr(class7_instance1, 'test_var_init')
    assert class7_instance1.test_var_init == 20
    assert hasattr(class7_instance1, 'test_var_getattr')
    assert class7_instance1.test_var_getattr == 200
    class7_instance2 = SingletonClass7()
    assert class7_instance1 is class7_instance2
    assert class7_instance2.value == 'YASSS'
    assert hasattr(class7_instance2, 'test_var_new')
    assert class7_instance2.test_var_new == 2
    assert hasattr(class7_instance2, 'test_var_init')
    assert class7_instance2.test_var_init == 20
    assert hasattr(class7_instance2, 'test_var_getattr')
    assert class7_instance2.test_var_getattr == 200

    # Clean up
    SingletonClass3.delete()
    assert not hasattr(SingletonClass3, '_singleton_instance')
    SingletonClass4.delete()
    assert not hasattr(SingletonClass4, '_singleton_instance')
    SingletonClass5.delete()
    assert not hasattr(SingletonClass5, '_singleton_instance')
    SingletonClass6.delete()
    assert not hasattr(SingletonClass6, '_singleton_instance')
    SingletonClass7.delete()
    assert not hasattr(SingletonClass7, '_singleton_instance')


def test_singleton_with_custom_dunder_with_inheritance():
    @singleton
    class SingletonParent4:
        pass

    @singleton
    class SingletonParent5:
        def __new__(cls, *args, **kwargs):
            print("In SingletonParent5 __new__")
            instance = super().__new__(cls)
            print(f"In SingletonParent5 __new__ {cls=}  {type(instance)=}")
            instance.test_var_new = 3
            return instance

        def __init__(self, value='YASSS'):
            print("In SingletonParent5 __init__")
            self.value = value
            self.test_var_init = 30

        def __getattribute__(self, name):
            print("In SingletonParent5 __getattribute__")
            self.test_var_getattr = 300
            return super().__getattribute__(name)

    class SingletonChild9(SingletonParent4):
        def __new__(cls, *args, **kwargs):
            print("In SingletonChild9 __new__")
            instance = super().__new__(cls, *args, **kwargs)
            instance.test_var_new = 4
            return instance

        def __init__(self, value='YASSS'):
            print("In SingletonChild9 __init__")
            self.value = value
            self.test_var_init = 40

        def __getattribute__(self, name):
            print("In SingletonChild9 __getattribute__")
            self.test_var_getattr = 400
            return super().__getattribute__(name)

    class SingletonChild10(SingletonParent5):
        pass

    # Test SingletonChild9
    child9_instance1 = SingletonChild9()
    assert child9_instance1.value == 'YASSS'
    assert hasattr(child9_instance1, 'test_var_new')
    assert child9_instance1.test_var_new == 4
    assert hasattr(child9_instance1, 'test_var_init')
    assert child9_instance1.test_var_init == 40
    assert hasattr(child9_instance1, 'test_var_getattr')
    assert child9_instance1.test_var_getattr == 400
    child9_instance2 = SingletonChild9()
    assert child9_instance1 is child9_instance2
    assert child9_instance2.value == 'YASSS'
    assert hasattr(child9_instance2, 'test_var_new')
    assert child9_instance2.test_var_new == 4
    assert hasattr(child9_instance2, 'test_var_init')
    assert child9_instance2.test_var_init == 40
    assert hasattr(child9_instance2, 'test_var_getattr')
    assert child9_instance2.test_var_getattr == 400

    # Test SingletonChild10
    child10_instance1 = SingletonChild10()
    assert child10_instance1.value == 'YASSS'
    assert hasattr(child10_instance1, 'test_var_new')
    assert child10_instance1.test_var_new == 3
    assert hasattr(child10_instance1, 'test_var_init')
    assert child10_instance1.test_var_init == 30
    assert hasattr(child10_instance1, 'test_var_getattr')
    assert child10_instance1.test_var_getattr == 300
    child10_instance2 = SingletonChild10()
    assert child10_instance1 is child10_instance2
    assert child10_instance2.value == 'YASSS'
    assert hasattr(child10_instance2, 'test_var_new')
    assert child10_instance2.test_var_new == 3
    assert hasattr(child10_instance2, 'test_var_init')
    assert child10_instance2.test_var_init == 30
    assert hasattr(child10_instance2, 'test_var_getattr')
    assert child10_instance2.test_var_getattr == 300

    # Clean up
    SingletonParent4.delete()
    assert not hasattr(SingletonParent4, '_singleton_instance')
    SingletonParent5.delete()
    assert not hasattr(SingletonParent5, '_singleton_instance')
    SingletonChild9.delete()
    assert not hasattr(SingletonChild9, '_singleton_instance')
    SingletonChild10.delete()
    assert not hasattr(SingletonChild10, '_singleton_instance')


def test_singleton_docstring():
    @singleton
    class SingletonClass8:
        """SingletonClass8 docstring test"""

        def __new__(cls, *args, **kwargs):
            """SingletonClass8 __new__ docstring test"""
            instance = super().__new__(cls)
            return instance

        def __init__(self, value='YASSS'):
            """SingletonClass8 __init__ docstring test"""
            self.value = value

        def __getattribute__(self, name):
            """SingletonClass8 __getattribute__ docstring test"""
            return super().__getattribute__(name)

    assert singleton.__doc__.startswith("Singleton decorator.")
    assert SingletonClass8.__doc__ == "SingletonClass8 docstring test"
    assert SingletonClass8.__new__.__doc__ == "SingletonClass8 __new__ docstring test"
    assert SingletonClass8.__init__.__doc__ == "SingletonClass8 __init__ docstring test"
    assert SingletonClass8.__getattribute__.__doc__ == "SingletonClass8 __getattribute__ docstring test"
    assert SingletonClass8.delete.__doc__.startswith("The delete() method removes the singleton")
    assert SingletonClass8.get_self.__doc__.startswith("The get_self(**kwargs) method returns the")

    # Clean up
    assert not hasattr(SingletonClass8, '_singleton_instance')


def test_singleton_structure():
    with pytest.raises(TypeError, match=re.escape("Cannot create a singleton for class SingletonClass9 "
        + "with an __init__ method that has more than one required argument (only 'self' is allowed)!")):
        @singleton
        class SingletonClass9:
            def __init__(self, value):
                self.value = value

    with pytest.raises(TypeError, match=re.escape("Class SingletonClass10 provides a 'get_self' "
                              + "method. This is not compatible with the singleton decorator!")):
        @singleton
        class SingletonClass10:
            def get_self(self, *args, **kwargs):
                return 20

    with pytest.raises(TypeError, match=re.escape("Class SingletonClass11 provides a 'delete' "
                            + "method. This is not compatible with the singleton decorator!")):
        @singleton
        class SingletonClass11:
            def delete(self, *args, **kwargs):
                pass

    @singleton(allow_underscore_vars_in_init=False)
    class SingletonClass12:
        def __init__(self):
            self._value1 = 12

    @singleton
    class SingletonClass13:
        def __init__(self, _value1=7.3, value2='hello'):
            self._value1 = _value1
            self.value2 = value2

    with pytest.raises(AttributeError, match=re.escape("Cannot set private attribute _value1 for "
                + "SingletonClass12! Use the appropriate setter method instead. However, if you "
                + "really want to be able to set this attribute in the constructor, use "
                + "'allow_underscore_vars_in_init=True' in the singleton decorator.")):
        instance = SingletonClass12(_value1=10)
    instance2 = SingletonClass13(_value1=10)

    # Clean up
    SingletonClass12.delete()
    assert not hasattr(SingletonClass12, '_singleton_instance')
    SingletonClass13.delete()
    assert not hasattr(SingletonClass13, '_singleton_instance')
