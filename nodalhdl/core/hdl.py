from .signal import SignalType, BundleType, Signal, Bundle, Bits

import os
import shutil
import hashlib

from typing import List, Dict, Set, Tuple, Union


class HDLFileModelException(Exception): pass

class HDLGlobalInfo:
    """
        HDL 文件模型中的全局信息.
        例如所用到的所有类型, 在 add_component 时会向上级传递, 最终顶层结构生成时会给出单独一个 types.vhd (以 VHDL 为例).
    """
    def __init__(self):
        self.type_pool: Set[BundleType] = set() # 类型池, 可用于查重
        self.type_pool_ordered: List[BundleType] = [] # 有序的 type_pool, 以防 HDL 要求顺序声明类型
    
    def merge(self, other: 'HDLGlobalInfo'):
        """
            将另一个 HDLGlobalInfo 合并到当前 HDLGlobalInfo.
            当前只有类型信息, 需要考虑顺序以及查重.
        """
        effective_new_list = []
        for t in other.type_pool_ordered:
            if t not in self.type_pool:
                self.type_pool.add(t)
                effective_new_list.append(t)
        self.type_pool_ordered = effective_new_list + self.type_pool_ordered
    
    def emit_vhdl(self):
        content = ""
        
        for t in self.type_pool_ordered: # t: BundleType
            content += f"    type {t.__name__} is record\n"
            for k, T in t._bundle_types.items():
                if T.bases(Bundle):
                    content += f"        {k}: {T.__name__};\n"
                else:
                    content += f"        {k}: std_logic_vector({T.W - 1} downto 0);\n"
            content += f"    end record;\n\n"

        return {"types.vhd": f"library IEEE;\nuse IEEE.std_logic_1164.all;\nuse IEEE.numeric_std.all;\n\npackage types is\n{content}end package types;"}
    
    def add_type(self, t: SignalType):
        """
            添加类型.
            非 Bundle 类型不接受 (全部视为 std_logic_vector, 应都有 .W 位宽属性), IO Wrapper 不接受.
            Bundle 类型会递归添加其内部的子 Bundle 类型.
        """
        if not t.bases(Bundle):
            raise HDLFileModelException(f"Type to be added should be a Bundle.")
        
        if t.io_wrapper_included:
            raise HDLFileModelException(f"Type to be added should not contain IO Wrappers.")
        
        if t in self.type_pool: # 已经添加过, 同时也说明子类型也添加过
            return
        
        def _add(t: BundleType):
            if t.bases(Bundle): # [NOTICE]
                for _, v in t._bundle_types.items(): # 遍历子 Bundle
                    _add(v)
                self.type_pool.add(t) # 添加该 Bundle 类型
                self.type_pool_ordered.append(t) # 先添加子类型, 再添加父类型, 满足顺序声明要求
        
        _add(t)

class HDLFileModel:
    """
        HDL 文件模型.
        完全对应 HDL 文件内容, 不包含任何判断和校验等措施.
    """
    def __init__(self, entity_name: str, file_name: str = None):
        self.entity_name: str = entity_name
        self.file_name: str = file_name if file_name is not None else entity_name
        
        self.global_info: HDLGlobalInfo = HDLGlobalInfo()
        
        self.libs: Dict[str, List[str]] = {} # Dict[语言类型, List[包引用行]]
        self.ports: Dict[str, Tuple[str, SignalType]] = {} # Dict[端口名, (方向, 类型)]
        self.components: Dict[str, HDLFileModel] = {} # Dict[组件名, 组件对应文件模型]
        self.inst_comps: Dict[str, Tuple[str, Dict[str, str]]] = {} # Dict[实例名, (组件名, Dict[组件端口名, 实例端口名])]
        self.signals: Dict[str, SignalType] = {} # Dict[信号名, 信号类型]
        self.assignments: List[Tuple[str, str]] = [] # List[Tuple[目标信号, 源信号]]
        self.registers: Set[Tuple[str, str, SignalType]] = set() # Set[<reg_next_name>, <reg_name>, <signal_type>], <signal_type> for initial value generation
        
        self.raw: bool = False # 是否直接使用 HDL 定义 (即使使用 HDL 定义也应当声明 entity_name; port 应与 substructure 相符)
        self.raw_suffix: str = None
        self.raw_content: str = None
        
        # TODO
        self.add_lib("vhdl", "library IEEE;")
        self.add_lib("vhdl", "use IEEE.std_logic_1164.all;")
        self.add_lib("vhdl", "use IEEE.numeric_std.all;")
        self.add_lib("vhdl", "use work.types.all;")
    
    @property
    def is_sequential(self): # 存在时序逻辑或任意子模块存在时序逻辑
        return len(self.registers) > 0 or any([comp.is_sequential for comp in self.components.values()])
    
    def emit_vhdl(self):
        res = {}
        
        res.update(self.global_info.emit_vhdl()) # 全局信息
        
        def _collect(model: 'HDLFileModel'):
            models = set({model}) # 加入自身
            for comp in model.components.values():
                sub_models = _collect(comp)
                models.update(sub_models)
            return models
        
        models = _collect(self) # 递归收集所有 HDLFileModel
        
        def _gen_vhdl(model: HDLFileModel):
            # 包引用声明
            libs_declaration = ""
            for line in self.libs["vhdl"]:
                libs_declaration += line + "\n"
            
            # 实体端口声明
            def _gen_ports(hdl: HDLFileModel, part: str = "entity", indent: str = ""):
                port_content = ""
                
                if hdl.is_sequential: # clock, reset
                    port_content += f"{indent}        clock: in std_logic;\n"
                    port_content += f"{indent}        reset: in std_logic;\n"
                
                for name, (direction, t) in hdl.ports.items():
                    if t.bases(Bundle):
                        port_content += f"{indent}        {name}: {direction} {t.__name__};\n"
                    else:
                        port_content += f"{indent}        {name}: {direction} std_logic_vector({t.W - 1} downto 0);\n"
                if port_content:
                    port_content = port_content[:-2] # 去掉最后的分号和换行
                
                return f"{indent}{part} {hdl.entity_name} is\n{indent}    port (\n{port_content}\n{indent}    );\n{indent}end {part};"
            
            # 组件声明
            comp_declaration = ""
            for comp in model.components.values():
                comp_declaration += _gen_ports(comp, "component", "    ") + "\n\n"

            # 信号声明
            signal_declaration = ""
            for name, t in model.signals.items():
                if t.bases(Bundle):
                    signal_declaration += f"    signal {name}: {t.__name__};\n"
                else:
                    signal_declaration += f"    signal {name}: std_logic_vector({t.W - 1} downto 0);\n"
            if signal_declaration:
                signal_declaration = signal_declaration[:-1]
            
            # 寄存器时序
            if len(model.registers) > 0:
                seq_process = "    process (clock, reset) is\n    begin\n        if (reset = '1') then\n"
                for _, reg_name, signal_type in model.registers:
                    def _generate(sub_reg_name: str, t: SignalType):
                        res = ""
                        if t.bases(Bundle):
                            for k, v in t._bundle_types.items():
                                res += _generate(sub_reg_name + "." + k, v)
                        else:
                            res += f"            {sub_reg_name} <= (others => '0');\n"
                        return res
                    
                    seq_process += _generate(reg_name, signal_type)
                seq_process += "        elsif rising_edge(clock) then\n"
                for reg_next_name, reg_name, _ in model.registers:
                    seq_process += f"            {reg_name} <= {reg_next_name};\n"
                seq_process += "        end if;\n    end process;\n"
            
            # 模块例化
            comp_content = ""
            for inst_name, (comp_name, mapping) in model.inst_comps.items():
                mapping_content = ""
                for comp_port, inst_port in mapping.items():
                    mapping_content += f"            {comp_port} => {inst_port},\n"
                if mapping_content:
                    mapping_content = mapping_content[:-2]
                comp_content += f"    {inst_name}: {comp_name}\n        port map (\n{mapping_content}\n        );\n\n"
            if comp_content:
                comp_content = comp_content[:-1]
            
            # 并行赋值
            assignment_content = ""
            for target, value in model.assignments:
                assignment_content += f"    {target} <= {value};\n"
            if assignment_content:
                assignment_content = assignment_content[:-1]
            
            # 拼接文件内容
            return f"{libs_declaration}\n{_gen_ports(model, "entity")}\n\narchitecture Structural of {model.entity_name} is\n{comp_declaration}{signal_declaration}\nbegin\n{seq_process + "\n" if len(model.registers) > 0 else ""}{comp_content}\n{assignment_content}\nend architecture;"
        
        for model in models:
            if model.raw:
                if model.raw_suffix is None or model.raw_content is None:
                    raise HDLFileModelException(f"Raw HDL file model should be defined by .set_raw(file_suffix, content)")
                
                file_name = model.file_name + model.raw_suffix
                if file_name in res.keys():
                    raise HDLFileModelException(f"File model names conflicting: \'{file_name}\'")
                
                res[file_name] = model.raw_content
            else:
                file_name = model.file_name + ".vhd"
                if file_name in res.keys():
                    raise HDLFileModelException(f"File model names conflicting: \'{file_name}\'")
                
                res[file_name] = _gen_vhdl(model)
        
        return res
    
    def add_lib(self, hdl_type: str, line: str):
        if not self.libs.get(hdl_type):
            self.libs[hdl_type] = []
        self.libs[hdl_type].append(line)
    
    def add_port(self, name: str, direction: str, t: SignalType):
        """
            不需要在 custom_generation 中使用, generation 时会根据结构自动调用.
        """
        if t.bases(Bundle):
            self.global_info.add_type(t) # 添加类型到全局信息
        
        self.ports[name] = (direction, t)
    
    def add_component(self, comp: 'HDLFileModel'): # 添加组件到 components, 将 comp 的全局信息传递给自己的全局信息
        self.global_info.merge(comp.global_info)
        self.components[comp.entity_name] = comp
    
    def inst_component(self, inst_name: str, comp: 'HDLFileModel', mapping: Dict[str, str]):
        if comp.entity_name not in self.components.keys(): # 未添加到 components 中则添加
            self.add_component(comp)
        elif comp is not self.components[comp.entity_name]: # 同名但不是同一个对象
            raise HDLFileModelException(f"Component \'{comp.entity_name}\' already exists in components but not the same model.")
        
        self.inst_comps[inst_name] = (comp.entity_name, mapping if not comp.is_sequential else {
            "clock": "clock",
            "reset": "reset",
            **mapping
        })
    
    def add_signal(self, name: str, t: SignalType):
        if t.__name__ == "Auto":
            print(" ========== ", name)
        
        if t.bases(Bundle):
            self.global_info.add_type(t) # 添加类型到全局信息
        
        self.signals[name] = t
    
    def add_register(self, name: str, t: SignalType, latency: int = 1) -> Tuple[str, str]: # , initial_values: Union[str, List[str]] = None)
        """
            Return next_signal_name and reg_signal_name.
            [NOTICE] notice that the naming method influences auto-pipelining.
        """
        for level in range(latency):
            reg_next_name, reg_name = f"reg_next_{level}_{name}", f"reg_{level}_{name}"
            self.registers.add((reg_next_name, reg_name, t))
            
            self.add_signal(reg_next_name, t)
            self.add_signal(reg_name, t)
            
            if level >= 1:
                self.add_assignment(f"reg_next_{level}_{name}", f"reg_{level - 1}_{name}")
        
        return (f"reg_next_0_{name}", f"reg_{latency - 1}_{name}")
    
    def add_assignment(self, target: str, value: str):
        self.assignments.append((target, value))
    
    def set_raw(self, file_suffix: str, content: str):
        self.raw = True
        self.raw_suffix = file_suffix
        self.raw_content = content


def emit_to_files(emitted: Dict[str, str], target_folder_path: str):
    if os.path.exists(target_folder_path):
        shutil.rmtree(target_folder_path)
    os.makedirs(target_folder_path, exist_ok = True)
    
    for filename, content in emitted.items():
        with open(os.path.join(target_folder_path, filename), "w") as f:
            f.write(content)

