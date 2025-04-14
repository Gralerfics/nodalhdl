import uuid
import weakref
from typing import Dict, List

import networkx as nx
import pulp


class MixedIntegerDifferenceConstraintSolver:
    """
        x_j - x_i <= a_ij (x_i ---a_ij--> x_j)
        TODO 链式前向星
    """
    def __init__(self):
        pass # TODO
    
    def solve(self):
        pass # TODO


# 扩展模型


# 求解，运行 WD 得到 D，在 D 上二分查找，使用 MIDCSolver 求解得到 r

