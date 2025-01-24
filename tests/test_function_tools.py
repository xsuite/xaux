# copyright ############################### #
# This file is part of the Xaux Package.    #
# Copyright (c) CERN, 2024.                 #
# ######################################### #

from xaux.tools import count_arguments, count_required_arguments, count_optional_arguments, \
                       has_variable_length_arguments, has_variable_length_positional_arguments, \
                       has_variable_length_keyword_arguments


def _func_test_1():
    pass
def _func_test_2(b):
    pass
def _func_test_3(b, c):
    pass
def _func_test_4(c=3):
    pass
def _func_test_5(a, c=7):
    pass
def _func_test_6(*args):
    pass
def _func_test_7(a, b, c, *args):
    pass
def _func_test_8(*args, c=3, d=6):
    pass
def _func_test_9(a, b, *args, c=3, d=6):
    pass
def _func_test_10(**kwargs):
    pass
def _func_test_11(a, b, **kwargs):
    pass
def _func_test_12(*args, **kwargs):
    pass
def _func_test_13(a=43, **kwargs):
    pass
def _func_test_14(a, *args, **kwargs):
    pass
def _func_test_15(a, b, c=-93, **kwargs):
    pass
def _func_test_16(*args, a=23, b=-78, **kwargs):
    pass
def _func_test_17(a, b, c, *args, d=3, e=89, f=897, g=-0.8, **kwargs):
    pass
def _func_test_18(a, /):
    pass
def _func_test_19(a, /, b=4.31):
    pass
def _func_test_20(a, /, b, c, *args, d=3, e=89, f=897, g=-0.8, **kwargs):
    pass
def _func_test_21(a, /, b, c, *, d=3, e=89, f=897, g=-0.8, **kwargs):
    pass


def test_count_arguments():
    assert count_arguments(_func_test_1) == 0
    assert count_arguments(_func_test_2) == 1
    assert count_arguments(_func_test_3) == 2
    assert count_arguments(_func_test_4) == 1
    assert count_arguments(_func_test_5) == 2
    assert count_arguments(_func_test_6) == 0
    assert count_arguments(_func_test_7) == 3
    assert count_arguments(_func_test_8) == 2
    assert count_arguments(_func_test_9) == 4
    assert count_arguments(_func_test_10) == 0
    assert count_arguments(_func_test_11) == 2
    assert count_arguments(_func_test_12) == 0
    assert count_arguments(_func_test_13) == 1
    assert count_arguments(_func_test_14) == 1
    assert count_arguments(_func_test_15) == 3
    assert count_arguments(_func_test_16) == 2
    assert count_arguments(_func_test_17) == 7
    assert count_arguments(_func_test_18) == 1
    assert count_arguments(_func_test_19) == 2
    assert count_arguments(_func_test_20) == 7
    assert count_arguments(_func_test_21) == 7
    assert count_arguments(_func_test_1, count_variable_length_args=True) == 0
    assert count_arguments(_func_test_2, count_variable_length_args=True) == 1
    assert count_arguments(_func_test_3, count_variable_length_args=True) == 2
    assert count_arguments(_func_test_4, count_variable_length_args=True) == 1
    assert count_arguments(_func_test_5, count_variable_length_args=True) == 2
    assert count_arguments(_func_test_6, count_variable_length_args=True) == 1
    assert count_arguments(_func_test_7, count_variable_length_args=True) == 4
    assert count_arguments(_func_test_8, count_variable_length_args=True) == 3
    assert count_arguments(_func_test_9, count_variable_length_args=True) == 5
    assert count_arguments(_func_test_10, count_variable_length_args=True) == 1
    assert count_arguments(_func_test_11, count_variable_length_args=True) == 3
    assert count_arguments(_func_test_12, count_variable_length_args=True) == 2
    assert count_arguments(_func_test_13, count_variable_length_args=True) == 2
    assert count_arguments(_func_test_14, count_variable_length_args=True) == 3
    assert count_arguments(_func_test_15, count_variable_length_args=True) == 4
    assert count_arguments(_func_test_16, count_variable_length_args=True) == 4
    assert count_arguments(_func_test_17, count_variable_length_args=True) == 9
    assert count_arguments(_func_test_18, count_variable_length_args=True) == 1
    assert count_arguments(_func_test_19, count_variable_length_args=True) == 2
    assert count_arguments(_func_test_20, count_variable_length_args=True) == 9
    assert count_arguments(_func_test_21, count_variable_length_args=True) == 8


def test_count_required_arguments():
    assert count_required_arguments(_func_test_1) == 0
    assert count_required_arguments(_func_test_2) == 1
    assert count_required_arguments(_func_test_3) == 2
    assert count_required_arguments(_func_test_4) == 0
    assert count_required_arguments(_func_test_5) == 1
    assert count_required_arguments(_func_test_6) == 0
    assert count_required_arguments(_func_test_7) == 3
    assert count_required_arguments(_func_test_8) == 0
    assert count_required_arguments(_func_test_9) == 2
    assert count_required_arguments(_func_test_10) == 0
    assert count_required_arguments(_func_test_11) == 2
    assert count_required_arguments(_func_test_12) == 0
    assert count_required_arguments(_func_test_13) == 0
    assert count_required_arguments(_func_test_14) == 1
    assert count_required_arguments(_func_test_15) == 2
    assert count_required_arguments(_func_test_16) == 0
    assert count_required_arguments(_func_test_17) == 3
    assert count_required_arguments(_func_test_18) == 1
    assert count_required_arguments(_func_test_19) == 1
    assert count_required_arguments(_func_test_20) == 3
    assert count_required_arguments(_func_test_21) == 3


def test_count_optional_arguments():
    assert count_optional_arguments(_func_test_1) == 0
    assert count_optional_arguments(_func_test_2) == 0
    assert count_optional_arguments(_func_test_3) == 0
    assert count_optional_arguments(_func_test_4) == 1
    assert count_optional_arguments(_func_test_5) == 1
    assert count_optional_arguments(_func_test_6) == 0
    assert count_optional_arguments(_func_test_7) == 0
    assert count_optional_arguments(_func_test_8) == 2
    assert count_optional_arguments(_func_test_9) == 2
    assert count_optional_arguments(_func_test_10) == 0
    assert count_optional_arguments(_func_test_11) == 0
    assert count_optional_arguments(_func_test_12) == 0
    assert count_optional_arguments(_func_test_13) == 1
    assert count_optional_arguments(_func_test_14) == 0
    assert count_optional_arguments(_func_test_15) == 1
    assert count_optional_arguments(_func_test_16) == 2
    assert count_optional_arguments(_func_test_17) == 4
    assert count_optional_arguments(_func_test_18) == 0
    assert count_optional_arguments(_func_test_19) == 1
    assert count_optional_arguments(_func_test_20) == 4
    assert count_optional_arguments(_func_test_21) == 4

def test_has_variable_length_arguments():
    assert has_variable_length_arguments(_func_test_1) is False
    assert has_variable_length_arguments(_func_test_2) is False
    assert has_variable_length_arguments(_func_test_3) is False
    assert has_variable_length_arguments(_func_test_4) is False
    assert has_variable_length_arguments(_func_test_5) is False
    assert has_variable_length_arguments(_func_test_6) is True
    assert has_variable_length_arguments(_func_test_7) is True
    assert has_variable_length_arguments(_func_test_8) is True
    assert has_variable_length_arguments(_func_test_9) is True
    assert has_variable_length_arguments(_func_test_10) is True
    assert has_variable_length_arguments(_func_test_11) is True
    assert has_variable_length_arguments(_func_test_12) is True
    assert has_variable_length_arguments(_func_test_13) is True
    assert has_variable_length_arguments(_func_test_14) is True
    assert has_variable_length_arguments(_func_test_15) is True
    assert has_variable_length_arguments(_func_test_16) is True
    assert has_variable_length_arguments(_func_test_17) is True
    assert has_variable_length_arguments(_func_test_18) is False
    assert has_variable_length_arguments(_func_test_19) is False
    assert has_variable_length_arguments(_func_test_20) is True
    assert has_variable_length_arguments(_func_test_21) is True
    assert has_variable_length_positional_arguments(_func_test_1) is False
    assert has_variable_length_positional_arguments(_func_test_2) is False
    assert has_variable_length_positional_arguments(_func_test_3) is False
    assert has_variable_length_positional_arguments(_func_test_4) is False
    assert has_variable_length_positional_arguments(_func_test_5) is False
    assert has_variable_length_positional_arguments(_func_test_6) is True
    assert has_variable_length_positional_arguments(_func_test_7) is True
    assert has_variable_length_positional_arguments(_func_test_8) is True
    assert has_variable_length_positional_arguments(_func_test_9) is True
    assert has_variable_length_positional_arguments(_func_test_10) is False
    assert has_variable_length_positional_arguments(_func_test_11) is False
    assert has_variable_length_positional_arguments(_func_test_12) is True
    assert has_variable_length_positional_arguments(_func_test_13) is False
    assert has_variable_length_positional_arguments(_func_test_14) is True
    assert has_variable_length_positional_arguments(_func_test_15) is False
    assert has_variable_length_positional_arguments(_func_test_16) is True
    assert has_variable_length_positional_arguments(_func_test_17) is True
    assert has_variable_length_positional_arguments(_func_test_18) is False
    assert has_variable_length_positional_arguments(_func_test_19) is False
    assert has_variable_length_positional_arguments(_func_test_20) is True
    assert has_variable_length_positional_arguments(_func_test_21) is False
    assert has_variable_length_keyword_arguments(_func_test_1) is False
    assert has_variable_length_keyword_arguments(_func_test_2) is False
    assert has_variable_length_keyword_arguments(_func_test_3) is False
    assert has_variable_length_keyword_arguments(_func_test_4) is False
    assert has_variable_length_keyword_arguments(_func_test_5) is False
    assert has_variable_length_keyword_arguments(_func_test_6) is False
    assert has_variable_length_keyword_arguments(_func_test_7) is False
    assert has_variable_length_keyword_arguments(_func_test_8) is False
    assert has_variable_length_keyword_arguments(_func_test_9) is False
    assert has_variable_length_keyword_arguments(_func_test_10) is True
    assert has_variable_length_keyword_arguments(_func_test_11) is True
    assert has_variable_length_keyword_arguments(_func_test_12) is True
    assert has_variable_length_keyword_arguments(_func_test_13) is True
    assert has_variable_length_keyword_arguments(_func_test_14) is True
    assert has_variable_length_keyword_arguments(_func_test_15) is True
    assert has_variable_length_keyword_arguments(_func_test_16) is True
    assert has_variable_length_keyword_arguments(_func_test_17) is True
    assert has_variable_length_keyword_arguments(_func_test_18) is False
    assert has_variable_length_keyword_arguments(_func_test_19) is False
    assert has_variable_length_keyword_arguments(_func_test_20) is True
    assert has_variable_length_keyword_arguments(_func_test_21) is True
