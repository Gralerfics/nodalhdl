"""
+--------------------------------------------------------------------+
    Operators:
        TODO
    Examples:
        TODO
+--------------------------------------------------------------------+
    Comments:
        1.  TODO
+--------------------------------------------------------------------+
"""

from .signal import *


""" Exceptions """
class OperatorException(Exception): pass


""" Operators """
class Operator: pass

class UnaryOperator(Operator):
    def __init__(self, operand_type: SignalType):
        super().__init__()
        # ！！！！！！！！！！！！！！似乎不对！！！运算是否也应该做成 type？应该是！先去考虑结构表示 TODO

class Not(UnaryOperator): pass

class BinaryOperator(Operator): pass

class And(BinaryOperator): pass

class Or(BinaryOperator): pass

class Addition(BinaryOperator): pass

class Subtract(BinaryOperator): pass

class Multiply(BinaryOperator): pass

class Division(BinaryOperator): pass

class FloorDivision(BinaryOperator): pass

class Modulo(BinaryOperator): pass

