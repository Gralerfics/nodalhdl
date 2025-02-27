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
        res = Structure("addition")
        
        # 声明 IO Ports
        res.add_port("op1", Input[op1_type])
        res.add_port("op2", Input[op2_type])
        res.add_port("res", Output[Auto])
        
        return res
    
    def deduction(s: Structure): # @operator 将自动将该函数注册进 structure_template 中
        """
            TODO 除了从确定输入推得确定输出, 还可以:
                (1.) 从某个确定类型但不确定长度的信号, 推得其他信号类型. # 反之, 确定参数不确定类型的情况就还是不要存在了
                (2.) 输出长度大于某个输入信号的长度, 则另一个输入信号的长度必等于输出信号的长度.
            TODO TODO TODO EEB 的 IO 是反的等麻烦问题.
        """
        io = s.EEB.IO
        op1_type, op2_type = io.op1.origin_signal_type.T, io.op2.origin_signal_type.T

        if op1_type.belongs(Auto) or op2_type.belongs(Auto):
            io.res.origin_signal_type = Input[Auto]
        else:
            if op1_type.belongs(SInt):
                io.res.origin_signal_type = Input[SInt[max(op1_type.W, op2_type.W) + 1]]
            else:
                io.res.origin_signal_type = Input[UInt[max(op1_type.W, op2_type.W)]]
    
    def vhdl(s: Structure): # @operator 将自动将该函数注册进 structure_template 中
        print("vhdl")
        pass

