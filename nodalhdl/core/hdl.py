from .signal import SignalType, Bundle

from typing import List, Dict, Set, Tuple


class HDLFileModelException(Exception): pass

class HDLGlobalInfo:
    """
        HDL 文件模型中的全局信息.
        例如所用到的所有类型, 在 add_component 时会向上级传递, 最终顶层结构生成时会给出单独一个 types.vhd (以 VHDL 为例).
    """
    def __init__(self):
        self.type_pool: Set[SignalType] = set() # 类型池, 可用于查重
        self.type_pool_ordered: List[SignalType] = [] # 有序的 type_pool, 以防 HDL 要求顺序声明类型
    
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
                if T.belongs(Bundle):
                    content += f"        {k}: {T.__name__};\n"
                else:
                    content += f"        {k}: std_logic_vector({T.W - 1} downto 0);\n"
            content += f"    end record;\n\n"

        return {"types.vhd": f"library IEEE;\nuse IEEE.std_logic_1164.all;\nuse IEEE.numeric_std.all;\n\npackage types is\n{content}end package types;"}
    
    def header_vhdl(self):
        return "library IEEE;\nuse IEEE.std_logic_1164.all;\nuse IEEE.numeric_std.all;\nuse work.types.all;"
    
    def add_type(self, t: SignalType):
        """
            添加类型.
            非 Bundle 类型不接受 (全部视为 std_logic_vector, 应都有 .W 位宽属性), IO Wrapper 不接受.
            Bundle 类型会递归添加其内部的子 Bundle 类型.
        """
        if not t.belongs(Bundle):
            raise HDLFileModelException(f"Type to be added should be a Bundle.")
        
        if t.io_wrapper_included:
            raise HDLFileModelException(f"Type to be added should not contain IO Wrappers.")
        
        if t in self.type_pool: # 已经添加过, 同时也说明子类型也添加过
            return
        
        def _add(t: SignalType):
            if t.belongs(Bundle): # 只要处理 Bundle 类型
                for _, v in t._bundle_types.items(): # 遍历子 Bundle
                    _add(v)
                self.type_pool.add(t) # 添加该 Bundle 类型
                self.type_pool_ordered.append(t) # 先添加子类型, 再添加父类型, 满足顺序声明要求
        
        _add(t)


class HDLFileModel:
    """
        HDL 文件模型.
        完全对应 HDL 文件内容, 不包含任何判断和校验等措施.
        TODO 时序电路.
    """
    def __init__(self, entity_name: str, inline: bool = False):
        self.entity_name: str = entity_name
        self.inline: bool = inline # TODO operator 无法在 box 层面 expand, 像切片这种操作单独文件又太繁琐, 或许可以在文件模型中标记, 在 HDL 层面展开
        
        self.global_info: HDLGlobalInfo = HDLGlobalInfo()
        
        self.ports: Dict[str, Tuple[str, SignalType]] = {} # Dict[端口名, (方向, 类型)]
        self.components: Set[HDLFileModel] = set()
        self.inst_comps: Dict[str, Tuple[str, Dict[str, str]]] = {} # Dict[实例名, (组件名, Dict[组件端口名, 实例端口名])]
        self.signals: Dict[str, SignalType] = {}
        self.assignments: List[Tuple[str, str]] = []
        
        self.raw: bool = False # 是否直接使用 HDL 定义 (即使使用 HDL 定义也应当声明 entity_name; port 应与 box 相符) TODO
        self.raw_file_suffix: str = None
        self.raw_content: str = None
    
    def emit_vhdl(self):
        """
            递归生成 VHDL.
            非 locked 结构对应的文件名需要带有 namespace 信息, 如为 None 则为最外层模块, 需要处理全局信息.
                    ... TODO 最外层或许并非顶层, 之后可能还要添加单独的 top, 并允许在其中实现三态门等结构.
            所有文件名前 (包括顶层模块) 添加标识 (例如 "vhdl_"), 以免和 types.vhd 等冲突.
            
            文件名就应该是 entity_name.
            namespace 信息应该在 generation 时创建 HDLFileModel 时就写入, 也在那是控制是否 reusable.
        """
        res = {}
        
        res.update(self.global_info.emit_vhdl()) # 全局信息
        
        def _collect(model: 'HDLFileModel'):
            models = set({model}) # 加入自身
            for comp in model.components:
                if not comp.inline: # inline 的结构不需要单独生成文件
                    sub_models = _collect(comp)
                    models.update(sub_models)
            return models
        
        models = _collect(self) # 递归收集所有 HDLFileModel (去重)
        
        def _gen_vhdl(model: HDLFileModel):
            # 实体声明
            def _gen_ports(hdl: HDLFileModel, part: str = "entity", indent: str = ""):
                port_content = ""
                for name, (direction, t) in hdl.ports.items():
                    if t.belongs(Bundle):
                        port_content += f"{indent}        {name}: {direction} {t.__name__};\n"
                    else:
                        port_content += f"{indent}        {name}: {direction} std_logic_vector({t.W - 1} downto 0);\n"
                if port_content:
                    port_content = port_content[:-2] # 去掉最后的分号和换行
                return f"{indent}{part} {hdl.entity_name} is\n{indent}    port (\n{port_content}\n{indent}    );\n{indent}end {part};"
        
            # 组件声明
            comp_declaration = ""
            for comp in model.components:
                comp_declaration += _gen_ports(comp, "component", "    ") + "\n"
            if comp_declaration:
                comp_declaration = comp_declaration[:-1]
        
            # 信号声明
            signal_declaration = ""
            for name, t in model.signals.items():
                if t.belongs(Bundle):
                    signal_declaration += f"    signal {name}: {t.__name__};\n"
                else:
                    signal_declaration += f"    signal {name}: std_logic_vector({t.W - 1} downto 0);\n"
            if signal_declaration:
                signal_declaration = signal_declaration[:-1]
            
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
            return f"{model.global_info.header_vhdl()}\n\n{_gen_ports(model, "entity")}\n\narchitecture Structural of {model.entity_name} is\n{comp_declaration}\n{signal_declaration}\nbegin\n{comp_content}\n{assignment_content}\nend architecture;"
        
        for model in models:
            if model.raw:
                if model.raw_file_suffix is None or model.raw_content is None:
                    raise HDLFileModelException(f"Raw HDL file model should be defined by .set_raw(filename, content)")
                res[model.entity_name + model.raw_file_suffix] = model.raw_content
            else:
                res[model.entity_name + ".vhd"] = _gen_vhdl(model)
        
        return res
    
    def add_port(self, name: str, direction: str, t: SignalType):
        """
            不应该在 custom_generation 中使用, generation 时会根据结构自动调用.
        """
        if t.belongs(Bundle):
            self.global_info.add_type(t) # 添加类型到全局信息
        
        self.ports[name] = (direction, t)
    
    def add_component(self, comp: 'HDLFileModel'): # 添加组件到 components, 将 comp 的全局信息传递给自己的全局信息
        self.global_info.merge(comp.global_info)
        self.components.add(comp)
    
    def inst_component(self, inst_name: str, comp: 'HDLFileModel', mapping: Dict[str, str]):
        if comp not in self.components: # 未添加到 components 中则添加
            self.add_component(comp)
        self.inst_comps[inst_name] = (comp.entity_name, mapping)
    
    def add_signal(self, name: str, t: SignalType):
        if t.belongs(Bundle):
            self.global_info.add_type(t) # 添加类型到全局信息
        
        self.signals[name] = t
    
    def add_assignment(self, target: str, value: str):
        self.assignments.append((target, value))
    
    def set_raw(self, file_suffix: str, content: str):
        self.raw = True
        self.raw_file_suffix = file_suffix
        self.raw_content = content


def write_to_files(d: Dict[str, str], path: str): # TODO Temprary
    for filename, content in d.items():
        with open(path + "/" + filename, "w") as f:
            f.write(content)

