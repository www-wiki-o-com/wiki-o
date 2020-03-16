"""  __      __    __               ___
    /  \    /  \__|  | _ __        /   \
    \   \/\/   /  |  |/ /  |  __  |  |  |
     \        /|  |    <|  | |__| |  |  |
      \__/\__/ |__|__|__\__|       \___/

Copyright (C) 2018 Wiki-O, Frank Imeson

This source code is licensed under the GPL license found in the
LICENSE.md file in the root directory of this source tree.
"""

# *******************************************************************************
# Imports
# *******************************************************************************
from core.converters import IntegerCypher

# *******************************************************************************
# Defines
# *******************************************************************************
try:
    from wiki_o.env_vars import CONTENT_KEYS
except ImportError:
    CONTENT_KEYS = None
CONTENT_PK_CYPHER = IntegerCypher(bit_length=72, keys=CONTENT_KEYS)
