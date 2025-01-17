# copyright ############################### #
# This file is part of the Xaux package.    #
# Copyright (c) CERN, 2025.                 #
# ######################################### #

import pytest
import re

from xaux import singleton


# We are overly verbose in these tests, comparing every time again all instances to each other.
# This is to make sure that the singletons are really singletons and that they do not interfere
# with each other. It's an important overhead to ensure we deeply test the global states, because
# if we would pytest.parametrize this, we might be copying state and not realising this.


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
    class SingletonClass1:
        def __init__(self, value=3):
            self.value = value

    # Initialise with default value
    assert not hasattr(SingletonClass1, '_singleton_instance')
    instance1 = SingletonClass1()
    assert hasattr(SingletonClass1, '_singleton_instance')
    assert instance1.value == 3

    # Initialise with specific value
    instance2 = SingletonClass1(value=5)
    assert instance1 is instance2
    assert id(instance1) == id(instance2)
    assert instance1.value == 5
    assert instance2.value == 5

    # Initialise with default value again - this should not change the value
    instance3 = SingletonClass1()
    assert instance2 is instance3
    assert id(instance2) == id(instance3)
    assert instance1.value == 5
    assert instance2.value == 5
    assert instance3.value == 5

    # Change the value of the instance
    instance1.value = 7
    assert instance1.value == 7
    assert instance2.value == 7
    assert instance3.value == 7

    # Remove the singleton
    SingletonClass1.delete()
    assert not hasattr(SingletonClass1, '_singleton_instance')
    with pytest.raises(RuntimeError, match="This instance of the singleton SingletonClass1 "
                                         + "has been invalidated!"):
        instance1.value
    with pytest.raises(RuntimeError, match="This instance of the singleton SingletonClass1 "
                                         + "has been invalidated!"):
        instance2.value
    with pytest.raises(RuntimeError, match="This instance of the singleton SingletonClass1 "
                                         + "has been invalidated!"):
        instance3.value

    # First initialisation with specific value
    instance4 = SingletonClass1(value=8)
    assert hasattr(SingletonClass1, '_singleton_instance')
    assert instance4.value == 8
    assert instance1 is not instance4
    assert instance2 is not instance4
    assert instance3 is not instance4
    assert id(instance1) != id(instance4)
    assert id(instance2) != id(instance4)
    assert id(instance3) != id(instance4)

    # Clean up
    SingletonClass1.delete()
    assert not hasattr(SingletonClass1, '_singleton_instance')

    # Test double deletion
    SingletonClass1.delete()
    assert not hasattr(SingletonClass1, '_singleton_instance')


def test_nonsingleton_inheritance():
    class NonSingletonParent:
        def __init__(self, value1=3):
            print("In NonSingletonParent __init__")
            self.value1 = value1

    @singleton
    class SingletonChild1(NonSingletonParent):
        def __init__(self, *args, value2=17, **kwargs):
            print("In SingletonChild1 __init__")
            self.value2 = value2
            super().__init__(*args, **kwargs)

    @singleton
    class SingletonChild2(NonSingletonParent):
        def __init__(self, *args, value2=-13, **kwargs):
            print("In SingletonChild2 __init__")
            self.value2 = value2
            super().__init__(*args, **kwargs)

    # Test the non-singleton parent class
    ns_parent_instance1 = NonSingletonParent(value1=8)
    assert ns_parent_instance1.value1 == 8
    ns_parent_instance2 = NonSingletonParent(value1=9)
    assert ns_parent_instance1 is not ns_parent_instance2
    assert ns_parent_instance1.value1 == 8
    assert ns_parent_instance2.value1 == 9

    # Test the singleton child class
    child1_instance1 = SingletonChild1()
    assert child1_instance1 is not ns_parent_instance1
    assert child1_instance1.value1 == 3
    assert child1_instance1.value2 == 17
    child1_instance2 = SingletonChild1(value1=-2)
    assert child1_instance2 is child1_instance1
    assert child1_instance2 is not ns_parent_instance1
    assert child1_instance1.value1 == -2
    assert child1_instance1.value2 == 17
    child1_instance3 = SingletonChild1(value2=-9)
    assert child1_instance3 is child1_instance1
    assert child1_instance3 is not ns_parent_instance1
    assert child1_instance1.value1 == -2
    assert child1_instance1.value2 == -9
    child1_instance4 = SingletonChild1(value1=789, value2=-78)
    assert child1_instance4 is child1_instance1
    assert child1_instance4 is not ns_parent_instance1
    assert child1_instance1.value1 == 789
    assert child1_instance1.value2 == -78

    # Test the other singleton child class
    child2_instance1 = SingletonChild2()
    assert child2_instance1 is not ns_parent_instance1
    assert child2_instance1 is not ns_parent_instance2
    assert child2_instance1 is not child1_instance1
    assert child2_instance1 is not child1_instance2
    assert child2_instance1 is not child1_instance3
    assert child2_instance1 is not child1_instance4
    assert child2_instance1.value1 == 3
    assert child2_instance1.value2 == -13
    child2_instance2 = SingletonChild2(value1=-4)
    assert child2_instance2 is child2_instance1
    assert child2_instance2 is not ns_parent_instance1
    assert child2_instance2 is not ns_parent_instance2
    assert child2_instance2 is not child1_instance1
    assert child2_instance2 is not child1_instance2
    assert child2_instance2 is not child1_instance3
    assert child2_instance2 is not child1_instance4
    assert child2_instance1.value1 == -4
    assert child2_instance1.value2 == -13
    child2_instance3 = SingletonChild2(value2=-9)
    assert child2_instance3 is child2_instance1
    assert child2_instance3 is child2_instance2
    assert child2_instance3 is not ns_parent_instance1
    assert child2_instance3 is not ns_parent_instance2
    assert child2_instance3 is not child1_instance1
    assert child2_instance3 is not child1_instance2
    assert child2_instance3 is not child1_instance3
    assert child2_instance3 is not child1_instance4
    assert child2_instance1.value1 == -4
    assert child2_instance1.value2 == -9
    child2_instance4 = SingletonChild2(value1=127, value2=99)
    assert child2_instance4 is child2_instance1
    assert child2_instance4 is child2_instance2
    assert child2_instance4 is child2_instance3
    assert child2_instance4 is not ns_parent_instance1
    assert child2_instance4 is not ns_parent_instance2
    assert child2_instance4 is not child1_instance1
    assert child2_instance4 is not child1_instance2
    assert child2_instance4 is not child1_instance3
    assert child2_instance4 is not child1_instance4
    assert child2_instance1.value1 == 127
    assert child2_instance1.value2 == 99

    # Assert the (non-singleton) parent is not influenced by the children
    ns_parent_instance3 = NonSingletonParent(value1=23)
    assert ns_parent_instance1 is not ns_parent_instance2
    assert ns_parent_instance3 is not ns_parent_instance1
    assert child1_instance1 is not ns_parent_instance1
    assert child1_instance2 is not ns_parent_instance1
    assert child1_instance3 is not ns_parent_instance1
    assert child1_instance4 is not ns_parent_instance1
    assert child1_instance1 is not ns_parent_instance2
    assert child1_instance2 is not ns_parent_instance2
    assert child1_instance3 is not ns_parent_instance2
    assert child1_instance4 is not ns_parent_instance2
    assert child1_instance1 is not ns_parent_instance3
    assert child1_instance2 is not ns_parent_instance3
    assert child1_instance3 is not ns_parent_instance3
    assert child1_instance4 is not ns_parent_instance3
    assert child2_instance1 is not ns_parent_instance1
    assert child2_instance2 is not ns_parent_instance1
    assert child2_instance3 is not ns_parent_instance1
    assert child2_instance4 is not ns_parent_instance1
    assert child2_instance1 is not ns_parent_instance2
    assert child2_instance2 is not ns_parent_instance2
    assert child2_instance3 is not ns_parent_instance2
    assert child2_instance4 is not ns_parent_instance2
    assert child2_instance1 is not ns_parent_instance3
    assert child2_instance2 is not ns_parent_instance3
    assert child2_instance3 is not ns_parent_instance3
    assert child2_instance4 is not ns_parent_instance3
    assert ns_parent_instance1.value1 == 8
    assert ns_parent_instance2.value1 == 9
    assert ns_parent_instance3.value1 == 23
    assert child1_instance1.value1 == 789
    assert child1_instance1.value2 == -78
    assert child2_instance1.value1 == 127
    assert child2_instance1.value2 == 99

    # Clean up
    SingletonChild1.delete()
    assert not hasattr(SingletonChild1, '_singleton_instance')
    SingletonChild2.delete()
    assert not hasattr(SingletonChild2, '_singleton_instance')


def test_singleton_inheritance():
    @singleton
    class SingletonParent1:
        def __init__(self, value1=7):
            print("In SingletonParent1 __init__")
            self.value1 = value1

    class SingletonChild3(SingletonParent1):
        def __init__(self, *args, value2='lop', **kwargs):
            print("In SingletonChild3 __init__")
            self.value2 = value2
            super().__init__(*args, **kwargs)

    class SingletonChild4(SingletonParent1):
        def __init__(self, *args, value2=0, **kwargs):
            print("In SingletonChild4 __init__")
            self.value2 = value2
            super().__init__(*args, **kwargs)

    # Test the singleton parent class
    parent1_instance1 = SingletonParent1(value1=8)
    assert parent1_instance1.value1 == 8
    parent1_instance2 = SingletonParent1(value1=9)
    assert parent1_instance1 is parent1_instance2
    assert parent1_instance1.value1 == 9
    assert parent1_instance2.value1 == 9

    # Test the singleton child class
    child3_instance1 = SingletonChild3()
    assert child3_instance1 is not parent1_instance1
    assert child3_instance1 is not parent1_instance2
    # The parent values are INHERITED, but not SYNCED
    assert child3_instance1.value1 == 7
    assert child3_instance1.value2 == 'lop'
    child3_instance2 = SingletonChild3(value1=-2)
    assert child3_instance2 is child3_instance1
    assert child3_instance2 is not parent1_instance1
    assert child3_instance2 is not parent1_instance2
    assert child3_instance1.value1 == -2
    assert child3_instance1.value2 == 'lop'
    child3_instance3 = SingletonChild3(value2=4.345)
    assert child3_instance3 is child3_instance1
    assert child3_instance3 is child3_instance2
    assert child3_instance3 is not parent1_instance1
    assert child3_instance3 is not parent1_instance2
    assert child3_instance1.value1 == -2
    assert child3_instance1.value2 == 4.345
    child3_instance4 = SingletonChild3(value1='jej', value2='josepHArt')
    assert child3_instance4 is child3_instance1
    assert child3_instance4 is child3_instance2
    assert child3_instance4 is child3_instance3
    assert child3_instance4 is not parent1_instance1
    assert child3_instance1.value1 == 'jej'
    assert child3_instance1.value2 == 'josepHArt'

    # Test the other singleton child class
    child4_instance1 = SingletonChild4()
    assert child4_instance1 is not parent1_instance1
    assert child4_instance1 is not parent1_instance2
    assert child4_instance1 is not child3_instance1
    assert child4_instance1 is not child3_instance2
    assert child4_instance1 is not child3_instance3
    assert child4_instance1 is not child3_instance4
    # The parent values are INHERITED, but not SYNCED
    assert child4_instance1.value1 == 7
    assert child4_instance1.value2 == 0
    child4_instance2 = SingletonChild4(value1=0.11)
    assert child4_instance2 is child4_instance1
    assert child4_instance2 is not parent1_instance1
    assert child4_instance2 is not parent1_instance2
    assert child4_instance2 is not child3_instance1
    assert child4_instance2 is not child3_instance2
    assert child4_instance2 is not child3_instance3
    assert child4_instance2 is not child3_instance4
    assert child4_instance1.value1 == 0.11
    assert child4_instance1.value2 == 0
    child4_instance3 = SingletonChild4(value2=6)
    assert child4_instance3 is child4_instance1
    assert child4_instance3 is child4_instance2
    assert child4_instance3 is not parent1_instance1
    assert child4_instance3 is not parent1_instance2
    assert child4_instance3 is not child3_instance1
    assert child4_instance3 is not child3_instance2
    assert child4_instance3 is not child3_instance3
    assert child4_instance3 is not child3_instance4
    assert child4_instance1.value1 == 0.11
    assert child4_instance1.value2 == 6
    child4_instance4 = SingletonChild4(value1='hoho', value2=22)
    assert child4_instance4 is child4_instance1
    assert child4_instance4 is child4_instance2
    assert child4_instance4 is child4_instance3
    assert child4_instance4 is not parent1_instance1
    assert child4_instance4 is not parent1_instance2
    assert child4_instance4 is not child3_instance1
    assert child4_instance4 is not child3_instance2
    assert child4_instance4 is not child3_instance3
    assert child4_instance4 is not child3_instance4
    assert child4_instance1.value1 == 'hoho'
    assert child4_instance1.value2 == 22

    # Assert the (singleton) parent is not influenced by the children
    assert parent1_instance2 is parent1_instance1
    assert child3_instance1 is not parent1_instance1
    assert child3_instance2 is not parent1_instance1
    assert child3_instance3 is not parent1_instance1
    assert child3_instance4 is not parent1_instance1
    assert child3_instance1 is not parent1_instance2
    assert child3_instance2 is not parent1_instance2
    assert child3_instance3 is not parent1_instance2
    assert child3_instance4 is not parent1_instance2
    assert child4_instance1 is not parent1_instance1
    assert child4_instance2 is not parent1_instance1
    assert child4_instance3 is not parent1_instance1
    assert child4_instance4 is not parent1_instance1
    assert child4_instance1 is not parent1_instance2
    assert child4_instance2 is not parent1_instance2
    assert child4_instance3 is not parent1_instance2
    assert child4_instance4 is not parent1_instance2
    assert parent1_instance1.value1 == 9
    assert parent1_instance2.value1 == 9
    parent1_instance3 = SingletonParent1(value1=23)
    assert parent1_instance2 is parent1_instance1
    assert parent1_instance3 is parent1_instance2
    assert child3_instance1 is not parent1_instance1
    assert child3_instance2 is not parent1_instance1
    assert child3_instance3 is not parent1_instance1
    assert child3_instance4 is not parent1_instance1
    assert child3_instance1 is not parent1_instance2
    assert child3_instance2 is not parent1_instance2
    assert child3_instance3 is not parent1_instance2
    assert child3_instance4 is not parent1_instance2
    assert child4_instance1 is not parent1_instance1
    assert child4_instance2 is not parent1_instance1
    assert child4_instance3 is not parent1_instance1
    assert child4_instance4 is not parent1_instance1
    assert child4_instance1 is not parent1_instance2
    assert child4_instance2 is not parent1_instance2
    assert child4_instance3 is not parent1_instance2
    assert child4_instance4 is not parent1_instance2
    assert parent1_instance1.value1 == 23
    assert parent1_instance2.value1 == 23
    assert parent1_instance3.value1 == 23
    assert child3_instance1.value1 == 'jej'
    assert child3_instance1.value2 == 'josepHArt'
    assert child4_instance1.value1 == 'hoho'
    assert child4_instance1.value2 == 22

    # Now delete all and start fresh, to ensure children can instantiate without parent existing.
    SingletonParent1.delete()
    assert not hasattr(SingletonParent1, '_singleton_instance')
    SingletonChild3.delete()
    assert not hasattr(SingletonChild3, '_singleton_instance')
    SingletonChild4.delete()
    assert not hasattr(SingletonChild4, '_singleton_instance')

    # Test the singleton child class without parent
    child3_instance5 = SingletonChild3()
    # The parent values are INHERITED, but not SYNCED
    assert child3_instance5.value1 == 7
    assert child3_instance5.value2 == 'lop'
    child3_instance6 = SingletonChild3(value1=-2)
    assert child3_instance6 is child3_instance5
    assert child3_instance5.value1 == -2
    assert child3_instance5.value2 == 'lop'
    child3_instance7 = SingletonChild3(value2=4.345)
    assert child3_instance7 is child3_instance5
    assert child3_instance7 is child3_instance6
    assert child3_instance5.value1 == -2
    assert child3_instance5.value2 == 4.345
    child3_instance8 = SingletonChild3(value1='jej', value2='josepHArt')
    assert child3_instance8 is child3_instance5
    assert child3_instance8 is child3_instance6
    assert child3_instance8 is child3_instance7
    assert child3_instance5.value1 == 'jej'
    assert child3_instance5.value2 == 'josepHArt'

    # Test the other singleton child class without parent
    child4_instance5 = SingletonChild4()
    assert child4_instance5 is not child3_instance5
    assert child4_instance5 is not child3_instance6
    assert child4_instance5 is not child3_instance7
    assert child4_instance5 is not child3_instance8
    # The parent values are INHERITED, but not SYNCED
    assert child4_instance5.value1 == 7
    assert child4_instance5.value2 == 0
    child4_instance6 = SingletonChild4(value1=0.11)
    assert child4_instance6 is child4_instance5
    assert child4_instance6 is not child3_instance5
    assert child4_instance6 is not child3_instance6
    assert child4_instance6 is not child3_instance7
    assert child4_instance6 is not child3_instance8
    assert child4_instance5.value1 == 0.11
    assert child4_instance5.value2 == 0
    child4_instance7 = SingletonChild4(value2=6)
    assert child4_instance7 is child4_instance5
    assert child4_instance7 is child4_instance6
    assert child4_instance7 is not child3_instance5
    assert child4_instance7 is not child3_instance6
    assert child4_instance7 is not child3_instance7
    assert child4_instance7 is not child3_instance8
    assert child4_instance5.value1 == 0.11
    assert child4_instance5.value2 == 6
    child4_instance8 = SingletonChild4(value1='hoho', value2=22)
    assert child4_instance8 is child4_instance5
    assert child4_instance8 is child4_instance6
    assert child4_instance8 is child4_instance7
    assert child4_instance8 is not child3_instance5
    assert child4_instance8 is not child3_instance6
    assert child4_instance8 is not child3_instance7
    assert child4_instance8 is not child3_instance8
    assert child4_instance5.value1 == 'hoho'
    assert child4_instance5.value2 == 22

    # Clean up
    SingletonChild3.delete()
    assert not hasattr(SingletonChild3, '_singleton_instance')
    SingletonChild4.delete()
    assert not hasattr(SingletonChild4, '_singleton_instance')


# This is the same test as above, but with the singleton decorator applied to parent and child
def test_double_singleton_inheritance():
    @singleton
    class SingletonParent2:
        def __init__(self, value1=7):
            print("In SingletonParent2 __init__")
            self.value1 = value1

    @singleton
    class SingletonChild5(SingletonParent2):
        def __init__(self, *args, value2='lop', **kwargs):
            print("In SingletonChild5 __init__")
            self.value2 = value2
            super().__init__(*args, **kwargs)

    @singleton
    class SingletonChild6(SingletonParent2):
        def __init__(self, *args, value2=0, **kwargs):
            print("In SingletonChild6 __init__")
            self.value2 = value2
            super().__init__(*args, **kwargs)

    # Test the singleton parent class
    parent2_instance1 = SingletonParent2(value1=8)
    assert parent2_instance1.value1 == 8
    parent2_instance2 = SingletonParent2(value1=9)
    assert parent2_instance1 is parent2_instance2
    assert parent2_instance1.value1 == 9
    assert parent2_instance2.value1 == 9

    # Test the singleton child class
    child5_instance1 = SingletonChild5()
    assert child5_instance1 is not parent2_instance1
    assert child5_instance1 is not parent2_instance2
    # The parent values are INHERITED, but not SYNCED
    assert child5_instance1.value1 == 7
    assert child5_instance1.value2 == 'lop'
    child5_instance2 = SingletonChild5(value1=-2)
    assert child5_instance2 is child5_instance1
    assert child5_instance2 is not parent2_instance1
    assert child5_instance2 is not parent2_instance2
    assert child5_instance1.value1 == -2
    assert child5_instance1.value2 == 'lop'
    child5_instance3 = SingletonChild5(value2=4.345)
    assert child5_instance3 is child5_instance1
    assert child5_instance3 is child5_instance2
    assert child5_instance3 is not parent2_instance1
    assert child5_instance3 is not parent2_instance2
    assert child5_instance1.value1 == -2
    assert child5_instance1.value2 == 4.345
    child5_instance4 = SingletonChild5(value1='jej', value2='josepHArt')
    assert child5_instance4 is child5_instance1
    assert child5_instance4 is child5_instance2
    assert child5_instance4 is child5_instance3
    assert child5_instance4 is not parent2_instance1
    assert child5_instance1.value1 == 'jej'
    assert child5_instance1.value2 == 'josepHArt'

    # Test the other singleton child class
    child6_instance1 = SingletonChild6()
    assert child6_instance1 is not parent2_instance1
    assert child6_instance1 is not parent2_instance2
    assert child6_instance1 is not child5_instance1
    assert child6_instance1 is not child5_instance2
    assert child6_instance1 is not child5_instance3
    assert child6_instance1 is not child5_instance4
    # The parent values are INHERITED, but not SYNCED
    assert child6_instance1.value1 == 7
    assert child6_instance1.value2 == 0
    child6_instance2 = SingletonChild6(value1=0.11)
    assert child6_instance2 is child6_instance1
    assert child6_instance2 is not parent2_instance1
    assert child6_instance2 is not parent2_instance2
    assert child6_instance2 is not child5_instance1
    assert child6_instance2 is not child5_instance2
    assert child6_instance2 is not child5_instance3
    assert child6_instance2 is not child5_instance4
    assert child6_instance1.value1 == 0.11
    assert child6_instance1.value2 == 0
    child6_instance3 = SingletonChild6(value2=6)
    assert child6_instance3 is child6_instance1
    assert child6_instance3 is child6_instance2
    assert child6_instance3 is not parent2_instance1
    assert child6_instance3 is not parent2_instance2
    assert child6_instance3 is not child5_instance1
    assert child6_instance3 is not child5_instance2
    assert child6_instance3 is not child5_instance3
    assert child6_instance3 is not child5_instance4
    assert child6_instance1.value1 == 0.11
    assert child6_instance1.value2 == 6
    child6_instance4 = SingletonChild6(value1='hoho', value2=22)
    assert child6_instance4 is child6_instance1
    assert child6_instance4 is child6_instance2
    assert child6_instance4 is child6_instance3
    assert child6_instance4 is not parent2_instance1
    assert child6_instance4 is not parent2_instance2
    assert child6_instance4 is not child5_instance1
    assert child6_instance4 is not child5_instance2
    assert child6_instance4 is not child5_instance3
    assert child6_instance4 is not child5_instance4
    assert child6_instance1.value1 == 'hoho'
    assert child6_instance1.value2 == 22

    # Assert the (singleton) parent is not influenced by the children
    assert parent2_instance2 is parent2_instance1
    assert child5_instance1 is not parent2_instance1
    assert child5_instance2 is not parent2_instance1
    assert child5_instance3 is not parent2_instance1
    assert child5_instance4 is not parent2_instance1
    assert child5_instance1 is not parent2_instance2
    assert child5_instance2 is not parent2_instance2
    assert child5_instance3 is not parent2_instance2
    assert child5_instance4 is not parent2_instance2
    assert child6_instance1 is not parent2_instance1
    assert child6_instance2 is not parent2_instance1
    assert child6_instance3 is not parent2_instance1
    assert child6_instance4 is not parent2_instance1
    assert child6_instance1 is not parent2_instance2
    assert child6_instance2 is not parent2_instance2
    assert child6_instance3 is not parent2_instance2
    assert child6_instance4 is not parent2_instance2
    assert parent2_instance1.value1 == 9
    assert parent2_instance2.value1 == 9
    parent2_instance3 = SingletonParent2(value1=23)
    assert parent2_instance2 is parent2_instance1
    assert parent2_instance3 is parent2_instance2
    assert child5_instance1 is not parent2_instance1
    assert child5_instance2 is not parent2_instance1
    assert child5_instance3 is not parent2_instance1
    assert child5_instance4 is not parent2_instance1
    assert child5_instance1 is not parent2_instance2
    assert child5_instance2 is not parent2_instance2
    assert child5_instance3 is not parent2_instance2
    assert child5_instance4 is not parent2_instance2
    assert child6_instance1 is not parent2_instance1
    assert child6_instance2 is not parent2_instance1
    assert child6_instance3 is not parent2_instance1
    assert child6_instance4 is not parent2_instance1
    assert child6_instance1 is not parent2_instance2
    assert child6_instance2 is not parent2_instance2
    assert child6_instance3 is not parent2_instance2
    assert child6_instance4 is not parent2_instance2
    assert parent2_instance1.value1 == 23
    assert parent2_instance2.value1 == 23
    assert parent2_instance3.value1 == 23
    assert child5_instance1.value1 == 'jej'
    assert child5_instance1.value2 == 'josepHArt'
    assert child6_instance1.value1 == 'hoho'
    assert child6_instance1.value2 == 22

    # Now delete all and start fresh, to ensure children can instantiate without parent existing.
    SingletonParent2.delete()
    assert not hasattr(SingletonParent2, '_singleton_instance')
    SingletonChild5.delete()
    assert not hasattr(SingletonChild5, '_singleton_instance')
    SingletonChild6.delete()
    assert not hasattr(SingletonChild6, '_singleton_instance')

    # Test the singleton child class without parent
    child5_instance5 = SingletonChild5()
    # The parent values are INHERITED, but not SYNCED
    assert child5_instance5.value1 == 7
    assert child5_instance5.value2 == 'lop'
    child5_instance6 = SingletonChild5(value1=-2)
    assert child5_instance6 is child5_instance5
    assert child5_instance5.value1 == -2
    assert child5_instance5.value2 == 'lop'
    child5_instance7 = SingletonChild5(value2=4.345)
    assert child5_instance7 is child5_instance5
    assert child5_instance7 is child5_instance6
    assert child5_instance5.value1 == -2
    assert child5_instance5.value2 == 4.345
    child5_instance8 = SingletonChild5(value1='jej', value2='josepHArt')
    assert child5_instance8 is child5_instance5
    assert child5_instance8 is child5_instance6
    assert child5_instance8 is child5_instance7
    assert child5_instance5.value1 == 'jej'
    assert child5_instance5.value2 == 'josepHArt'

    # Test the other singleton child class without parent
    child6_instance5 = SingletonChild6()
    assert child6_instance5 is not child5_instance5
    assert child6_instance5 is not child5_instance6
    assert child6_instance5 is not child5_instance7
    assert child6_instance5 is not child5_instance8
    # The parent values are INHERITED, but not SYNCED
    assert child6_instance5.value1 == 7
    assert child6_instance5.value2 == 0
    child6_instance6 = SingletonChild6(value1=0.11)
    assert child6_instance6 is child6_instance5
    assert child6_instance6 is not child5_instance5
    assert child6_instance6 is not child5_instance6
    assert child6_instance6 is not child5_instance7
    assert child6_instance6 is not child5_instance8
    assert child6_instance5.value1 == 0.11
    assert child6_instance5.value2 == 0
    child6_instance7 = SingletonChild6(value2=6)
    assert child6_instance7 is child6_instance5
    assert child6_instance7 is child6_instance6
    assert child6_instance7 is not child5_instance5
    assert child6_instance7 is not child5_instance6
    assert child6_instance7 is not child5_instance7
    assert child6_instance7 is not child5_instance8
    assert child6_instance5.value1 == 0.11
    assert child6_instance5.value2 == 6
    child6_instance8 = SingletonChild6(value1='hoho', value2=22)
    assert child6_instance8 is child6_instance5
    assert child6_instance8 is child6_instance6
    assert child6_instance8 is child6_instance7
    assert child6_instance8 is not child5_instance5
    assert child6_instance8 is not child5_instance6
    assert child6_instance8 is not child5_instance7
    assert child6_instance8 is not child5_instance8
    assert child6_instance5.value1 == 'hoho'
    assert child6_instance5.value2 == 22

    # Clean up
    SingletonChild5.delete()
    assert not hasattr(SingletonChild5, '_singleton_instance')
    SingletonChild6.delete()
    assert not hasattr(SingletonChild6, '_singleton_instance')


def test_singleton_grand_inheritance():
    @singleton
    class SingletonParent3:
        def __init__(self, value1=4):
            print("In SingletonParent2 __init__")
            self.value1 = value1

    class SingletonChild7(SingletonParent3):
        def __init__(self, *args, value2='tsss', **kwargs):
            print("In SingletonChild7 __init__")
            self.value2 = value2
            super().__init__(*args, **kwargs)

    class SingletonGrandChild(SingletonChild7):
        def __init__(self, *args, value3='jeeej', **kwargs):
            print("In SingletonGrandChild __init__")
            self.value3 = value3
            super().__init__(*args, **kwargs)

    # Test the singleton parent class
    parent3_instance1 = SingletonParent3()
    assert parent3_instance1.value1 == 4
    parent3_instance2 = SingletonParent3(value1=5)
    assert parent3_instance1 is parent3_instance2
    assert parent3_instance1.value1 == 5
    assert parent3_instance2.value1 == 5

    # Test the singleton child class
    child7_instance1 = SingletonChild7()
    assert child7_instance1 is not parent3_instance1
    assert child7_instance1 is not parent3_instance2
    # The parent values are INHERITED, but not SYNCED
    assert child7_instance1.value1 == 4
    assert child7_instance1.value2 == 'tsss'
    child7_instance2 = SingletonChild7(value1=3, value2='pop')
    assert child7_instance2 is child7_instance1
    assert child7_instance2 is not parent3_instance1
    assert child7_instance2 is not parent3_instance2
    assert child7_instance1.value1 == 3
    assert child7_instance1.value2 == 'pop'

    # Test the singleton grandchild class
    grandchild_instance1 = SingletonGrandChild()
    assert grandchild_instance1 is not parent3_instance1
    assert grandchild_instance1 is not parent3_instance2
    assert grandchild_instance1 is not child7_instance1
    assert grandchild_instance1 is not child7_instance2
    # The parent and grandparent values are INHERITED, but not SYNCED
    assert grandchild_instance1.value1 == 4
    assert grandchild_instance1.value2 == 'tsss'
    assert grandchild_instance1.value3 == 'jeeej'
    assert child7_instance1.value1 == 3
    assert child7_instance1.value2 == 'pop'
    assert parent3_instance1.value1 == 5
    grandchild_instance2 = SingletonGrandChild(value1=1, value2='doll', value3='happy')
    assert grandchild_instance2 is grandchild_instance1
    assert grandchild_instance2 is not parent3_instance1
    assert grandchild_instance2 is not parent3_instance2
    assert grandchild_instance2 is not child7_instance1
    assert grandchild_instance2 is not child7_instance2
    assert grandchild_instance1.value1 == 1
    assert grandchild_instance1.value2 == 'doll'
    assert grandchild_instance1.value3 == 'happy'
    assert child7_instance1.value1 == 3
    assert child7_instance1.value2 == 'pop'
    assert parent3_instance1.value1 == 5

    # Now delete all and start fresh, to ensure grandchildren can instantiate without (grand)parents existing.
    SingletonParent3.delete()
    assert not hasattr(SingletonParent3, '_singleton_instance')
    SingletonChild7.delete()
    assert not hasattr(SingletonChild7, '_singleton_instance')
    SingletonGrandChild.delete()
    assert not hasattr(SingletonGrandChild, '_singleton_instance')
    with pytest.raises(RuntimeError, match="This instance of the singleton SingletonParent3 "
                                         + "has been invalidated!"):
        parent3_instance1.value1
    with pytest.raises(RuntimeError, match="This instance of the singleton SingletonParent3 "
                                         + "has been invalidated!"):
        parent3_instance2.value1
    with pytest.raises(RuntimeError, match="This instance of the singleton SingletonChild7 "
                                         + "has been invalidated!"):
        child7_instance1.value1
    with pytest.raises(RuntimeError, match="This instance of the singleton SingletonChild7 "
                                         + "has been invalidated!"):
        child7_instance1.value2
    with pytest.raises(RuntimeError, match="This instance of the singleton SingletonChild7 "
                                         + "has been invalidated!"):
        child7_instance2.value1
    with pytest.raises(RuntimeError, match="This instance of the singleton SingletonChild7 "
                                         + "has been invalidated!"):
        child7_instance2.value2
    with pytest.raises(RuntimeError, match="This instance of the singleton SingletonGrandChild "
                                         + "has been invalidated!"):
        grandchild_instance1.value1
    with pytest.raises(RuntimeError, match="This instance of the singleton SingletonGrandChild "
                                         + "has been invalidated!"):
        grandchild_instance1.value2
    with pytest.raises(RuntimeError, match="This instance of the singleton SingletonGrandChild "
                                         + "has been invalidated!"):
        grandchild_instance1.value3
    with pytest.raises(RuntimeError, match="This instance of the singleton SingletonGrandChild "
                                         + "has been invalidated!"):
        grandchild_instance2.value1
    with pytest.raises(RuntimeError, match="This instance of the singleton SingletonGrandChild "
                                         + "has been invalidated!"):
        grandchild_instance2.value2
    with pytest.raises(RuntimeError, match="This instance of the singleton SingletonGrandChild "
                                         + "has been invalidated!"):
        grandchild_instance2.value3

    grandchild_instance3 = SingletonGrandChild()
    assert grandchild_instance3 is not grandchild_instance1
    assert grandchild_instance3 is not grandchild_instance2
    assert grandchild_instance3 is not parent3_instance1
    assert grandchild_instance3 is not parent3_instance2
    assert grandchild_instance3 is not child7_instance1
    assert grandchild_instance3 is not child7_instance2
    assert grandchild_instance3.value1 == 4
    assert grandchild_instance3.value2 == 'tsss'
    assert grandchild_instance3.value3 == 'jeeej'
    grandchild_instance4 = SingletonGrandChild(value1=101, value2='poupee', value3='sad')
    assert grandchild_instance4 is grandchild_instance3
    assert grandchild_instance4 is not grandchild_instance1
    assert grandchild_instance4 is not grandchild_instance2
    assert grandchild_instance4 is not parent3_instance1
    assert grandchild_instance4 is not parent3_instance2
    assert grandchild_instance4 is not child7_instance1
    assert grandchild_instance4 is not child7_instance2
    assert grandchild_instance3.value1 == 101
    assert grandchild_instance3.value2 == 'poupee'
    assert grandchild_instance3.value3 == 'sad'

    # Clean up
    SingletonGrandChild.delete()
    assert not hasattr(SingletonGrandChild, '_singleton_instance')


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
            instance = super(cls, cls).__new__(cls)
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
            instance = super(cls, cls).__new__(cls)
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
            instance = super().__new__(cls, *args, **kwargs)
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
            instance = super(cls, cls).__new__(cls)
            return instance

        def __init__(self, value='YASSS'):
            """SingletonClass8 __init__ docstring test"""
            self.value = value

        def __getattribute__(self, name):
            """SingletonClass8 __getattribute__ docstring test"""
            return super().__getattribute__(name)

    assert singleton.__doc__.startswith("Singleton decorator.\n    This decorator will redefine")
    assert SingletonClass8.__doc__ == "SingletonClass8 docstring test"
    assert SingletonClass8.__new__.__doc__ == "SingletonClass8 __new__ docstring test"
    assert SingletonClass8.__init__.__doc__ == "SingletonClass8 __init__ docstring test"
    assert SingletonClass8.__getattribute__.__doc__ == "SingletonClass8 __getattribute__ docstring test"
    assert SingletonClass8.delete.__doc__.startswith("The delete() method removes the singleton")
    assert SingletonClass8.get_self.__doc__.startswith("The get_self(**kwargs) method returns the")

    # Clean up
    assert not hasattr(SingletonClass8, '_singleton_instance')


def test_singleton_structure():
    with pytest.raises(ValueError, match=re.escape("Cannot create a singleton with an __init__ "
                + "method that has more than one required argument (only 'self' is allowed)!")):
        @singleton
        class SingletonClass9:
            def __init__(self, value):
                self.value = value

    @singleton(allow_underscore_vars_in_init=False)
    class SingletonClass10:
        def __init__(self):
            self._value1 = 12

    @singleton
    class SingletonClass11:
        def __init__(self, _value1=7.3, value2='hello'):
            self._value1 = _value1
            self.value2 = value2

    with pytest.raises(ValueError, match=re.escape("Cannot set private attribute _value1 for "
                + "SingletonClass10! Use the appropriate setter method instead. However, if you "
                + "really want to be able to set this attribute in the constructor, use "
                + "'allow_underscore_vars_in_init=True' in the singleton decorator.")):
        instance = SingletonClass10(_value1=10)
    instance2 = SingletonClass11(_value1=10)

    # Clean up
    SingletonClass10.delete()
    assert not hasattr(SingletonClass10, '_singleton_instance')
    SingletonClass11.delete()
    assert not hasattr(SingletonClass11, '_singleton_instance')
