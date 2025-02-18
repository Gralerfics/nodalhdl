"""
+--------------------------------------------------------------------+
    Operators:
        TODO
    Examples:
        TODO
+--------------------------------------------------------------------+
    Comments:
        1.  `operator` 中的都应该是所谓的基础运算符，不可拆分的（所以例如多元 AND 运算应该不必要在这里定义）。
            基础运算符封装到 Node 中，Node 那里再去定义复杂的运算。
            TODO 所以建议这里定义 LUT？或者起码是与或非门，前者应该更好，更利于切分和插入寄存器（符合实际状况），
            TODO 基本的“算子”或可有 LUT，或可有二元布尔运算，或可有寄存器，或可有常数或信号端子等？
                 ... LUT 之类或许就算了，还有 CARRY 之类的原语太多，那样容易写成综合器，
                     不过或许可以添加一种高抽象层次的 LUT，即设计时就用给出真值表的方式设计的模块。
                 ... 不对！！！如果最后生成的 VHDL 使用运算符而非 LUT 原语，那么我们也没有办法在生成的 LUT 之间插入寄存器，
                     即无法做到一层 LUT 为最小单位的切分。
                     ... 但或许也是好的？以一层硬件原语结构为单位进行切分，在复杂逻辑电路中需要的寄存器等资源可能过于庞大。
                     ... 保留多种形式。
                 ... [!] 基本的算子应当是直接对应到 VHDL 的。
            TODO 需要一种方法快速确认一个组合逻辑转为 LUT 的组合后需要多少层（串联），以估测时延，
                 有这样的方法后可以依据这一点来切分流水线。
                 或可给组合逻辑计算一个复杂度因子，将其与预计层数相关联？
        TODO ！！！！！！！！！！！！！！！！！！！！！！！！！！！！！！！！！！！！！！！！！！！！考虑将 operator 并入 diagram
+--------------------------------------------------------------------+
"""

import hashlib

from .signal import *


""" Exceptions """
class OperatorException(Exception): pass


""" Metatypes """
class OperatorType(type):
    type_pool = {} # ensuring singularity. type_pool for OperatorType and its subclasses are all the same one

    def instantiate_type(cls, new_type_name, properties = {}): # type(cls) is OperatorType or its subclasses
        if not new_type_name in cls.type_pool.keys():
            cls.type_pool[new_type_name] = type(f"{new_type_name}", (cls, ), {})
        new_cls = cls.type_pool.get(new_type_name)
        for key, value in properties.items():
            setattr(new_cls, key, value)
        return new_cls

class UnaryOperatorType(OperatorType):
    def __getitem__(cls, item):
        if isinstance(item, SignalType) and item.width_determined: # Currently we only allow operator types with width-determined operands
            op_type = item
            return cls.instantiate_type(
                f"{cls.__name__}_{op_type.__name__}",
                {
                    "T_op": op_type
                }
            )
        else:
            raise SignalTypeException(f"Invalid parameter(s) \'{item}\' for type {cls.__name__}[<op_type (SignalType, width_determined)>]")

class BinaryOperatorType(OperatorType):
    def __getitem__(cls, item):
        if isinstance(item, tuple) and len(item) == 2 and isinstance(item[0], SignalType) and isinstance(item[1], SignalType) and item[0].width_determined and item[1].width_determined:
            op1_type, op2_type = item
            return cls.instantiate_type(
                f"{cls.__name__}_{op1_type.__name__}_{op2_type.__name__}",
                {
                    "T_op1": op1_type,
                    "T_op2": op2_type
                }
            )
        else:
            raise SignalTypeException(f"Invalid parameter(s) \'{item}\' for type {cls.__name__}[<op1_type (SignalType, width_determined)>, <op2_type (SignalType, width_determined)>]")

class SlicingOperatorType(OperatorType):
    def __getitem__(cls, item):
        indices = []
        if isinstance(item, int):
            indices = [item]
        elif isinstance(item, tuple) and len(item) == 2 and isinstance(item[0], int) and isinstance(item[1], int): # [from, to (inclusive)]
            from_index, to_index = item
            step = 1 if from_index <= to_index else -1
            indices = list(range(from_index, to_index + step, step))
        else:
            raise SignalTypeException(f"Invalid parameter(s) \'{item}\' for type {cls.__name__}[<index (int)>] or {cls.__name__}[<from (int)>, <to (int)>]") # TODO: or {cls.__name__}[<indices (List[int])>]")
        
        return cls.instantiate_type(
            f"{cls.__name__}_{'_'.join([str(x) for x in indices[:10]])}_{hashlib.md5(str(indices).encode('utf-8')).hexdigest()}",
            {
                "indices": indices
            }
        )


""" Types """
class Operator(metaclass = OperatorType):
    @classmethod
    def equals(cls, other: OperatorType):
        return cls == other
    
    @classmethod
    def belongs(cls, other: OperatorType):
        return issubclass(cls, other)

class UnaryOperator(Operator, metaclass = UnaryOperatorType): pass

class Not(UnaryOperator): pass

class BinaryOperator(Operator, metaclass = BinaryOperatorType): pass

class And(BinaryOperator): pass

class Or(BinaryOperator): pass

class Addition(BinaryOperator): pass

class Subtract(BinaryOperator): pass

class SlicingOperator(Operator, metaclass = SlicingOperatorType): pass

class Slice(SlicingOperator): pass

