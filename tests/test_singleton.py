# copyright ############################### #
# This file is part of the Xaux Package.    #
# Copyright (c) CERN, 2024.                 #
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


def test_singleton_structure():
    with pytest.raises(ValueError, match=re.escape("Cannot create a singleton with an __init__ "
                   + "method that has more than one required argument (only 'self' is allowed)!")):
        @singleton
        class SingletonClass2:
            def __init__(self, value):
                self.value = value


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

    # Assert the (non-singleton) ns_parent is not influenced by the children
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
    assert child3_instance1.value1 == 3
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
    assert child4_instance1.value1 == 3
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
    assert child3_instance5.value1 == 3
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
    assert child4_instance5.value1 == 3
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
    assert child5_instance1.value1 == 3
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
    assert child6_instance1.value1 == 3
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
    assert child5_instance5.value1 == 3
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
    assert child6_instance5.value1 == 3
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


def test_allow_underscore():
    @singleton(allow_underscore_vars_in_init=True)
    class SingletonClass3:
        def __init__(self, _value1=7.3, value2='hello'):
            self._value1 = _value1
            self.value2 = value2


def test_get_self():
    @singleton
    class SingletonClass4:
        def __init__(self, value=19):
            self.value = value

    # Initialise with default value
    instance = SingletonClass4()
    instance.value = 19

    # Get self with default value
    self1 = SingletonClass4.get_self()
    assert self1 is instance
    assert id(self1) == id(instance)
    assert self1.value == 19
    assert instance.value == 19

    # Get self with specific value
    self2 = SingletonClass4.get_self(value=11)
    assert self2 is instance
    assert self2 is self1
    assert id(self2) == id(instance)
    assert id(self2) == id(self1)
    assert instance.value == 11
    assert self1.value == 11
    assert self2.value == 11

    # Get self with non-existing attribute
    self3 = SingletonClass4.get_self(non_existing_attribute=13)
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
    assert not hasattr(SingletonClass4, 'non_existing_attribute')
    assert not hasattr(instance, 'non_existing_attribute')
    assert not hasattr(self1, 'non_existing_attribute')
    assert not hasattr(self2, 'non_existing_attribute')
    assert not hasattr(self3, 'non_existing_attribute')

    # Get self with specific value and non-existing attribute
    self4 = SingletonClass4.get_self(value=12, non_existing_attribute=13)
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
    assert not hasattr(SingletonClass4, 'non_existing_attribute')
    assert not hasattr(instance, 'non_existing_attribute')
    assert not hasattr(self1, 'non_existing_attribute')
    assert not hasattr(self2, 'non_existing_attribute')
    assert not hasattr(self3, 'non_existing_attribute')
    assert not hasattr(self4, 'non_existing_attribute')

    # Remove the singleton
    SingletonClass4.delete()

    # Initialise with get self with default value
    self5 = SingletonClass4.get_self()
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
    assert self5.value == 19

    # Remove the singleton
    SingletonClass4.delete()

    # Initialise with get self with specific value
    self6 = SingletonClass4.get_self(value=-3)
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


def test_get_self_with_inheritance():
    @singleton
    class SingletonClass5:
        def __init__(self, value=0.2):
            self.value = value


def test_singleton_with_custom_new_and_init():
    @singleton
    class SingletonClass6:
        def __init__(self, value='YASSS'):
            self.value = value


def test_singleton_with_custom_new_and_init_with_inheritance():
    pass

