"""  __      __    __               ___
    /  \    /  \__|  | _ __        /   \
    \   \/\/   /  |  |/ /  |  __  |  |  |
     \        /|  |    <|  | |__| |  |  |
      \__/\__/ |__|__|__\__|       \___/

A web service for sharing opinions and avoiding arguments

@file       environment.py
@brief      The set of Django's private environment variables.
@copyright  GNU Public License, 2018
@authors    Frank Imeson
"""

import os

os.environ['SECRET_KEY'] = "'nxz-mdsd^^w*+(yzz0o7_rw6_@5^pu()#youf$s7t(m1_o!k*0'"
os.environ['DJANGO_PASSWORD'] = "django_password"

