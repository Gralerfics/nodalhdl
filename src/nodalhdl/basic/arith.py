from ..core.signal import SignalType, UInt, SInt, Input, Output, Auto, Bundle
from ..core.diagram import Diagram, DiagramTypeException, Structure, StructureGenerationException, operator
from ..core.hdl import HDLFileModel


@operator
class Addition(Diagram): # 带参基本算子示例, 整数加法
    @staticmethod
    def setup(args):
        # 未定义空参行为, 返回 None 以防后续异常
        if not args:
            return None
        
        # 参数合法性检查 (结构性检查, 即不影响结构生成即可, 因为这里可能涉及到 Auto 等未推导的父类型, 导就完了. 行为性检查在 HDL 生成或仿真中进行)
        if len(args) != 2:
            raise DiagramTypeException(f"Invalid argument(s) \'{args}\' for diagram type Addition[<op1_type (SignalType)>, <op2_type (SignalType)>].")
        op1_type, op2_type = args
        
        # 创建结构
        res = Structure()
        
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
        """
        io = s.EEB.IO
        op1_type, op2_type = io.op1.signal_type, io.op2.signal_type # 使用 .signal_type 获取无 IO, 含 runtime 信息的信号类型
        
        if not op1_type.determined or not op2_type.determined:
            io.res.merge_runtime_type(Auto) # 调用 StructureNode 的这些方法比调用其 .located_net 的同名方法多一层检查, 以防修改锁定结构
        else:
            if op1_type.belongs(SInt):
                io.res.merge_runtime_type(SInt[max(op1_type.W, op2_type.W)])
            else:
                io.res.merge_runtime_type(UInt[max(op1_type.W, op2_type.W)])
    
    def generation(s: Structure): # @operator 将自动将该函数注册进 structure_template 中
        """
            TODO 还应判断类型是否符合要求.
                    ... deduction 中呢? 例如一个加法器输入和输出都已经给定, 但并不合理, 例如 3 位加 4 位得到 5 位;
                    ... 在 generation 处理可以确保生成的 HDL 代码合法, 而在 deduction 处理则更符合直觉;
                    ... 问题在于已经 determined 的结构不会进入 deduction, 是否应该规定 operator 一定要执行 deduction?
        """
        # 端口合法性检查 (此时结构已经 determined, 可以进一步检查, 例如是否是 UInt + UInt 或 SInt + SInt)
        io = s.EEB.IO
        op1_type, op2_type, res_type = io.op1.signal_type, io.op2.signal_type, io.res.signal_type
        if not (op1_type.belongs(UInt) and op2_type.belongs(UInt) or op1_type.belongs(SInt) and op2_type.belongs(SInt)):
            raise StructureGenerationException(f"Only accept UInt + UInt or SInt + SInt")
        if not res_type.W == max(op1_type.W, op2_type.W):
            raise StructureGenerationException(f"Result width should be the maximum of the two operands")
        
        entity_name = f"Addition_{op1_type.__name__}_{op2_type.__name__}"
        
        res = HDLFileModel(entity_name, inline = False) # TODO inline
        
        res.set_raw(f".vhd", \
f"""\
library IEEE;
use IEEE.std_logic_1164.all;
use IEEE.numeric_std.all;

entity {entity_name} is
    port (
        op1: in std_logic_vector({op1_type.W - 1} downto 0);
        op2: in std_logic_vector({op2_type.W - 1} downto 0);
        res: out std_logic_vector({res_type.W - 1} downto 0)
    );
end entity;

architecture Behavioral of {entity_name} is
begin
    res <= std_logic_vector(signed(op1) + signed(op2));
end architecture;
""")
        
        return res

