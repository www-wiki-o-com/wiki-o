"""  __      __    __               ___
    /  \    /  \__|  | _ __        /   \
    \   \/\/   /  |  |/ /  |  __  |  |  |
     \        /|  |    <|  | |__| |  |  |
      \__/\__/ |__|__|__\__|       \___/

A web service for sharing opinions and avoiding arguments

@file       example_env_vars.py
@brief      The set of Django's private environment variables.
@copyright  GNU Public License, 2018
@authors    Frank Imeson
"""

import os

os.environ['PGUSER'] = "django"
os.environ['PGPASSWORD'] = "password"
os.environ['SECRET_KEY'] = "'nxz-mdsd^^w*+(yzz0o7_rw6_@5^pu()#youf$s7t(m1_o!k*0'"
