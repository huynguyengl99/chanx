"""
Chanx framework constants.

This module defines constants used throughout the Chanx framework, providing a
centralized location for string literals, error messages, and other constant values.
Using these named constants rather than string literals helps maintain consistency
and makes updates easier across the codebase.
"""

MISSING_PYHUMPS_ERROR = (
    "Camelization is enabled but the 'pyhumps' package is not installed."
    " Please install it by running 'pip install pyhumps' or install the camel-case"
    " extra with 'pip install chanx[camel-case]'."
)
