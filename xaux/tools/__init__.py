# copyright ############################### #
# This file is part of the Xaux Package.    #
# Copyright (c) CERN, 2025.                 #
# ######################################### #

from .general_tools import timestamp, ranID, system_lock, get_hash
from .function_tools import count_arguments, count_required_arguments, count_optional_arguments, \
                            has_variable_length_arguments, has_variable_length_positional_arguments, \
                            has_variable_length_keyword_arguments
from .singleton import singleton
from .class_property import ClassProperty, ClassPropertyMeta
from .protectfile import ProtectFile, ProtectFileError
