from .signal import *

import os
import shutil
import textwrap

from typing import List, Dict, Set, Tuple, Union


class HDLUtils:
    @staticmethod
    def type_decl(t: SignalType, hdl_type: str = "vhdl"):
        if hdl_type == "vhdl":
            return t.__name__ if t.bases(Bundle) else f"std_logic_vector({t.W - 1} downto 0)"
        elif hdl_type == "verilog":
            return t.__name__ if t.bases(Bundle) else f"[{t.W - 1}:0]"
        else:
            raise NotImplementedError
    
    @staticmethod
    def get_suffix(hdl_type: str):
        if hdl_type == "vhdl":
            return ".vhd"
        elif hdl_type == "verilog":
            return ".v"
        else:
            raise NotImplementedError
    
    @staticmethod
    def vhdl_ports(model: 'HDLFileModel', clock_wire_name = "clock", reset_wire_name = "reset"):
        port_lines = []
        
        if model.is_sequential:
            port_lines.append(f"{clock_wire_name}: in std_logic")
            port_lines.append(f"{reset_wire_name}: in std_logic")
        
        for name, (direction, t) in model.ports.items():
            port_lines.append(f"{name}: {direction} {HDLUtils.type_decl(t)}")
        
        return "port (\n" + textwrap.indent(";\n".join(port_lines), "    ") + "\n);"
    
    @staticmethod
    def vhdl_single_file(model: 'HDLFileModel'):
        """
            global_elements {
                <library references>
                <entity declaration>
                <architecture> [
                    "architecture arch of ... is"
                        declaration_elements {
                            <component declaration>_i
                            <signal declarations> (no empty lines)
                            <raw declarations> (no empty lines)
                        } or "-- no declarations"
                    "begin"
                        body_elements {
                            <sequential process> [
                                "process (clock, reset) is"
                                "begin"
                                    "if reset = '1' then"
                                        <register initialization>_i
                                    "elsif rising_edge(clock) [and ... = "1" ]then"
                                        <register next assignment>_i
                                    "end if;"
                                "end process;"
                            ]
                            <component instantiation>_i [
                                "{inst_name} {comp_name}"
                                    "port map ("
                                        <mapping>_i or "-- no mapping"
                                    ");"
                            ]
                            <concurrent assignments>_i
                            <raw bodies>_i
                        } or " -- no body"
                    "end architecture;"
                ]
            }
            all elements are separated by a empty line.
        """
        global_elements = []
        
        # library references
        global_elements.append("\n".join(model.libs.get("vhdl", [])))
        
        # entity declaration
        global_elements.append(
            f"entity {model.entity_name} is\n" +
            textwrap.indent(HDLUtils.vhdl_ports(model), "    ") + "\n" +
            "end entity;"
        )
        
        # architecture
        declaration_elements = []
        body_elements = []
        
        # - component declarations
        for comp in model.components.values():
            declaration_elements.append(
                f"component {comp.entity_name} is\n" +
                textwrap.indent(HDLUtils.vhdl_ports(comp), "    ") + "\n" +
                "end component;"
            )

        # - signal declarations
        if len(model.signals) > 0:
            declaration_elements.append(
                "\n".join([f"signal {name}: {HDLUtils.type_decl(t)};" for name, t in model.signals.items()])
            )
        
        # - raw declarations
        raw_declarations = model.raw_arch_declarations.get("vhdl", [])
        if len(raw_declarations) > 0:
            declaration_elements.append("\n".join(raw_declarations))
        
        # - sequential process
        if len(model.registers) > 0:
            def _generate_initialization(sub_reg_name: str, t: SignalType):
                res = []
                if t.bases(Bundle):
                    for k, v in t._bundle_types.items():
                        res.extend(_generate_initialization(sub_reg_name + "." + k, v))
                else:
                    res.append(f"{sub_reg_name} <= (others => '0');")
                return res
            
            initialization_elements = []
            for _, reg_name, signal_type in model.registers:
                initialization_elements.extend(_generate_initialization(reg_name, signal_type))
            
            next_assignment_elements = []
            for reg_next_name, reg_name, _ in model.registers:
                next_assignment_elements.append(f"{reg_name} <= {reg_next_name};")
            
            body_elements.append(
                "process (clock, reset) is\n" +
                "begin\n" +
                "    if reset = '1' then\n" +
                textwrap.indent("\n".join(initialization_elements), "        ") + "\n" +
                f"    elsif rising_edge(clock) {f"and {model.reg_enable_signal_name} = \"1\" " if model.reg_enable_signal_name is not None else ""}then\n" +
                textwrap.indent("\n".join(next_assignment_elements), "        ") + "\n" +
                "    end if;\n" +
                "end process;"
            )
        
        # - component instantiations
        for inst_name, (comp_name, mapping) in model.inst_comps.items():
            port_map_elements = [f"{comp_port} => {inst_port}" for comp_port, inst_port in mapping.items()]
            body_elements.append(
                f"{inst_name}: {comp_name}\n" +
                "    port map(\n" +
                (textwrap.indent(",\n".join(port_map_elements), "        ") if len(port_map_elements) > 0 else "-- no mapping") + "\n" +
                "    );"
            )
        
        # - concurrent assignments
        if len(model.assignments) > 0:
            body_elements.append(
                "\n".join([f"{target} <= {value};" for target, value in model.assignments])
            )
        
        # - raw bodies
        raw_bodies = model.raw_arch_bodies.get("vhdl", [])
        if len(raw_bodies) > 0:
            body_elements.append("\n".join(raw_bodies))
        
        # concatenate architecture
        global_elements.append(
            f"architecture structural of {model.entity_name} is\n" +
            textwrap.indent("\n\n".join(declaration_elements) if len(declaration_elements) > 0 else "-- no declarations", "    ") + "\n" +
            "begin\n" +
            textwrap.indent("\n\n".join(body_elements) if len(body_elements) > 0 else "-- no body", "    ") + "\n" +
            "end architecture;"
        )
        
        # concatenate the content
        return "\n\n".join(global_elements)


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
        
        for t in self.type_pool_ordered:
            t: BundleType
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
            add types into the global info.
            only accepts Bundle type (record type in VHDL), and it will be recursively added.
        """
        t = t.clear_io()
        
        if t in self.type_pool: # added, so the subtypes must have been added too
            return
        
        def _add_type(t: BundleType):
            if t.bases(Bundle): # only Bundles need to be added
                for _, v in t._bundle_types.items(): # sub-Bundles
                    _add_type(v)
                self.type_pool.add(t)
                self.type_pool_ordered.append(t) # add after all sub-Bundles are added
        
        _add_type(t)


class HDLFileModelException(Exception): pass

class HDLFileModel:
    """
        HDL file model.
        primitive HDL file content, including no judgement or validation.
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
        
        self.raw_arch_bodies: Dict[str, List[str]] = {} # Dict[语言类型, List[原始代码 (模块内部)]]
        self.raw_arch_declarations: Dict[str, List[str]] = {} # Dict[语言类型, List[原始声明]]
        
        self.reg_enable_signal_name: str = None # 寄存器时钟使能信号名, 为 None 时无时钟使能信号
        
        self.add_lib("vhdl", "library IEEE;")
        self.add_lib("vhdl", "use IEEE.std_logic_1164.all;")
        self.add_lib("vhdl", "use IEEE.numeric_std.all;")
        self.add_lib("vhdl", "use work.types.all;")
    
    @property
    def is_sequential(self): # self or submodules have sequential logic
        return len(self.registers) > 0 or any([comp.is_sequential for comp in self.components.values()])
    
    def emit_vhdl(self):
        res = {**self.global_info.emit_vhdl()} # global info
        
        def _collect(model: 'HDLFileModel'):
            models = set({model}) # add self
            for comp in model.components.values(): # recursively add submodules
                sub_models = _collect(comp)
                models.update(sub_models)
            return models
        
        models = _collect(self) # recursively collect all HDLFileModels
        
        for model in models:
            file_name = model.file_name + HDLUtils.get_suffix("vhdl")
            if file_name in res.keys():
                raise HDLFileModelException(f"File model names conflicting: \'{file_name}\'")
            res[file_name] = HDLUtils.vhdl_single_file(model) # emit each file
        
        return res
    
    def add_lib(self, hdl_type: str, line: str):
        if not self.libs.get(hdl_type):
            self.libs[hdl_type] = []
        self.libs[hdl_type].append(line)
    
    def add_port(self, name: str, direction: str, t: SignalType):
        """
            will be automatically called in generation().
            `direction`: "in" or "out".
        """
        if t.bases(Bundle):
            self.global_info.add_type(t) # add type into global info
        
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
            "clock": "clock", # TODO 关于 HDL_Utils.vhdl_ports 中的 clock_wire_name 等
            "reset": "reset",
            **mapping
        })
    
    def add_signal(self, name: str, t: SignalType):
        if t.bases(Bundle):
            self.global_info.add_type(t) # add type into global info
        
        self.signals[name] = t
    
    def add_register(self, name: str, t: SignalType, latency: int = 1) -> Tuple[str, str]: # , initial_values: Union[str, List[str]] = None)
        """
            return next_signal_name and reg_signal_name.
            notice that the naming rules here influence STA.
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
    
    def add_arch_body(self, hdl_type: str, content: str):
        if not hdl_type in self.raw_arch_bodies.keys():
            self.raw_arch_bodies[hdl_type] = []
        self.raw_arch_bodies[hdl_type].append(textwrap.dedent(content).strip())
    
    def add_arch_declaration(self, hdl_type: str, content: str):
        if not hdl_type in self.raw_arch_declarations.keys():
            self.raw_arch_declarations[hdl_type] = []
        self.raw_arch_declarations[hdl_type].append(textwrap.dedent(content).strip())
    
    def set_register_enable_signal_name(self, name: str = None):
        if self.reg_enable_signal_name is not None and self.reg_enable_signal_name in self.signals.keys():
            del self.signals[self.reg_enable_signal_name]
        
        if name is not None:
            self.add_signal(name, Bit)
        
        self.reg_enable_signal_name = name


def emit_to_files(emitted: Dict[str, str], target_folder_path: str):
    if os.path.exists(target_folder_path):
        shutil.rmtree(target_folder_path)
    os.makedirs(target_folder_path, exist_ok = True)
    
    for filename, content in emitted.items():
        with open(os.path.join(target_folder_path, filename), "w") as f:
            f.write(content)


import sys
_current_module = sys.modules[__name__]
__all__ = [name for name in dir() if not name.startswith('_') and getattr(getattr(_current_module, name, None), "__module__", None) == __name__]

