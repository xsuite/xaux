# copyright ############################### #
# This file is part of the Xaux package.    #
# Copyright (c) CERN, 2025.                 #
# ######################################### #

import inspect


def count_arguments(func, count_variable_length_args=False):
    i = 0
    sig = inspect.signature(func)
    for param in sig.parameters.values():
        if param.kind == inspect.Parameter.POSITIONAL_ONLY \
        or param.kind == inspect.Parameter.KEYWORD_ONLY \
        or param.kind == inspect.Parameter.POSITIONAL_OR_KEYWORD:
            i += 1
        if count_variable_length_args:
            if param.kind == inspect.Parameter.VAR_POSITIONAL \
            or param.kind == inspect.Parameter.VAR_KEYWORD:
                i += 1
    return i

def count_required_arguments(func):
    i = 0
    sig = inspect.signature(func)
    for param in sig.parameters.values():
        if (param.kind == inspect.Parameter.POSITIONAL_ONLY \
        or param.kind == inspect.Parameter.POSITIONAL_OR_KEYWORD) \
        and param.default == inspect.Parameter.empty:
            i += 1
    return i

def count_optional_arguments(func):
    i = 0
    sig = inspect.signature(func)
    for param in sig.parameters.values():
        if (param.kind == inspect.Parameter.KEYWORD_ONLY \
        or param.kind == inspect.Parameter.POSITIONAL_OR_KEYWORD) \
        and param.default != inspect.Parameter.empty:
            i += 1
    return i

def has_variable_length_arguments(func):
    return has_variable_length_positional_arguments(func) \
           or has_variable_length_keyword_arguments(func)

def has_variable_length_positional_arguments(func):
    sig = inspect.signature(func)
    for param in sig.parameters.values():
        if param.kind == inspect.Parameter.VAR_POSITIONAL:
            return True
    return False

def has_variable_length_keyword_arguments(func):
    sig = inspect.signature(func)
    for param in sig.parameters.values():
        if param.kind == inspect.Parameter.VAR_KEYWORD:
            return True
    return False
