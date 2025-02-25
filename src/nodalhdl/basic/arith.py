from ..core.signal import SignalType, UInt, SInt, Input, Output, Auto, Bundle
from ..core.diagram import Diagram, DiagramTypeException, Structure, operator


@operator
class Addition(Diagram): # 带参基本算子示例, 整数加法
    @staticmethod
    def setup(args):
        # 未定义空参行为, 返回 None 以防后续异常
        if not args:
            return None
        
        # 参数合法性检查
        if len(args) != 2:
            raise DiagramTypeException(f"Invalid argument(s) \'{args}\' for diagram type Addition[<op1_type (SignalType)>, <op2_type (SignalType)>].")
        op1_type, op2_type = args
        if not (op1_type.belongs(UInt) and op2_type.belongs(UInt) or op1_type.belongs(SInt) and op2_type.belongs(SInt)):
            raise DiagramTypeException(f"Only UInt + UInt or SInt + SInt is acceptable")
        
        # 创建结构
        res = Structure()
        
        # 声明 IO Ports
        res.add_port("op1", Input[op1_type])
        res.add_port("op2", Input[op2_type])
        res.add_port("res", Output[Auto]) # Output[UInt[max(op1_type.W, op2_type.W) + 1]])
        
        # TODO deduction 如何给出? 现在它在 structure 里了, 应该给个函数接口什么的吧.
        
        return res

