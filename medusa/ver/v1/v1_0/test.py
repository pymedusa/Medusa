
from __future__ import absolute_import, print_function

from medusa.ver.v1.test import version, failed_list, better_list

version += '.0'

# here's where problems start... lists are mutable so mutable imported from other package also gets changed
failed_list.extend([4, 5, 6])

# typecasting it with list() is a better approach as it makes a copy
better_list = list(better_list)
better_list.extend(['d', 'e', 'f'])
