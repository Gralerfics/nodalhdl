from ..core.signal import SignalType, UInt, SInt, Input, Output, Auto, Bundle
from ..core.structure import Structure, StructuralNodes, RuntimeId, StructureGenerationException, IOProxy
from ..core.hdl import HDLFileModel


def Addition(op1_type: SignalType, op2_type: SignalType, fixed_id: str = None) -> Structure:
    # 参数合法性检查 (结构性检查, 即不影响结构生成即可, 因为这里可能涉及到 Auto 等未推导的父类型, 导就完了. 行为性检查在 HDL 生成或仿真中进行)
    
    # 创建结构
    res = Structure("addition", fixed_id = fixed_id)
    """
        此处命名 addition.
        若生成时 originally determined, 则得名称 addition_{id}, 这个 id 是独一无二的 structure_id (传入不同参数到 Diagram 生成的结构是不同 id 的), 不会冲突;
        若生成时 originally undetermined, 则名称前还会有前缀信息, 包含 inst_name, 不会冲突.
    """
    
    # 声明 IO Ports
    res.add_port("op1", Input[op1_type])
    res.add_port("op2", Input[op2_type])
    res.add_port("res", Output[Auto])
    
    def deduction(io: IOProxy):
        """
            TODO 除了从确定输入推得确定输出, 还可以:
                (1.) 从某个确定类型但不确定长度的信号, 推得其他信号类型. # 反之, 确定参数不确定类型的情况就还是不要存在了
                (2.) 输出长度大于某个输入信号的长度, 则另一个输入信号的长度必等于输出信号的长度.
            TODO 传个 IOProxy 之类的玩意, 以省去 runtime_id 的传递.
        """
        op1_type, op2_type = io.op1.type, io.op2.type
        
        if not op1_type.determined or not op2_type.determined:
            io.res.update(Auto)
        else:
            if op1_type.belongs(SInt):
                io.res.update(SInt[max(op1_type.W, op2_type.W)])
            else:
                io.res.update(UInt[max(op1_type.W, op2_type.W)])
    
    def generation(h: HDLFileModel, io: IOProxy):
        op1_type, op2_type, res_type = io.op1.type, io.op2.type, io.res.type
        
        if not (op1_type.belongs(UInt) and op2_type.belongs(UInt) or op1_type.belongs(SInt) and op2_type.belongs(SInt)):
            raise StructureGenerationException(f"Only accept UInt + UInt or SInt + SInt")
        if not res_type.W == max(op1_type.W, op2_type.W):
            raise StructureGenerationException(f"Result width should be the maximum of the two operands")
        
        h.set_raw(f".vhd", \
f"""\
library IEEE;
use IEEE.std_logic_1164.all;
use IEEE.numeric_std.all;

entity {h.entity_name} is
    port (
        op1: in std_logic_vector({op1_type.W - 1} downto 0);
        op2: in std_logic_vector({op2_type.W - 1} downto 0);
        res: out std_logic_vector({res_type.W - 1} downto 0)
    );
end entity;

architecture Behavioral of {h.entity_name} is
begin
    res <= std_logic_vector(signed(op1) + signed(op2));
end architecture;
"""
        )
    
    res.custom_deduction = deduction
    res.custom_generation = generation
    
    rid = RuntimeId()
    res.deduction(rid)
    res.apply_runtime(rid)
    
    return res

