from .signal import SignalType, Bundle, IOWrapper


class HDLFileModelException(Exception): pass

class HDLGlobalInfo:
    """
        HDL 文件模型中的全局信息.
        例如所用到的所有类型, 在 add_component 时会向上级传递, 最终顶层结构生成时会给出单独一个 types.vhd (以 VHDL 为例).
    """
    def __init__(self):
        self.type_pool = set() # 类型池, 可用于查重
        self.type_pool_ordered: list[SignalType] = [] # 有序的 type_pool, 以防 HDL 要求顺序声明类型
    
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

        return {"types.vhd":
f"""\
library IEEE;
use IEEE.std_logic_1164.all;
use IEEE.numeric_std.all;

package types is
{content}\
end package types;\
"""
        }
    
    def header_vhdl(self):
        return \
"""\
library IEEE;
use IEEE.std_logic_1164.all;
use IEEE.numeric_std.all;
use work.types.all;\
"""
    
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
        self.inline: bool = inline # TODO operator 无法在 box 层面 expand, 像切片这种操作单独文件又太繁琐, 或许可以在文件模型中标记, 在 HDL 层面展开.
        
        self.global_info: HDLGlobalInfo = HDLGlobalInfo()
        
        self.ports: dict[str, tuple[str, SignalType]] = {} # dict[端口名, (方向, 类型)]
        self.components: set[HDLFileModel] = set()
        self.inst_comps: dict[str, tuple[str, dict[str, str]]] = {} # dict[实例名, (组件名, dict[组件端口名, 实例端口名])]
        self.signals: dict[str, SignalType] = {}
        self.assignments: list[tuple[str, str]] = []
        
        self.raw: bool = False # 是否直接使用 HDL 定义 (即使使用 HDL 定义也应当声明 entity_name 和 ports [*], 以便上级结构生成) TODO
        self.raw_filename: str = None
        self.raw_content: str = None
    
    def emit_vhdl(self, prefix: str = None):
        """
            递归生成 VHDL.
            非 locked 结构对应的文件名需要带有 namespace 信息, 如为 None 则为最外层模块, 需要处理全局信息.
                    ... TODO 最外层或许并非顶层, 之后可能还要添加单独的 top, 并允许在其中实现三态门等结构.
            所有文件名前 (包括顶层模块) 添加标识 (例如 "vhdl_"), 以免和 types.vhd 等冲突.
            
            TODO 可复用模块不用前缀 namespace 还没实现.
        """
        if self.raw:
            if self.raw_filename is None or self.raw_content is None:
                raise HDLFileModelException(f"Raw HDL file model should be defined by .set_raw(filename, content)")
            return {self.raw_filename: self.raw_content}
        
        res = {}
        
        if prefix is None: # 最外层模块
            res.update(self.global_info.emit_vhdl()) # 全局信息
            prefix = "vhdl"
        
        next_prefix = prefix + "_" + self.entity_name
        for comp in self.components: # 子结构文件
            if not comp.inline: # inline 的结构不需要单独生成文件
                res.update(comp.emit_vhdl(next_prefix))
        
        # 实体声明
        def emit_ports(hdl: HDLFileModel, part: str = "entity", indent: str = ""):
            port_content = ""
            for name, (direction, t) in hdl.ports.items():
                if t.belongs(Bundle):
                    port_content += f"{indent}        {name}: {direction} {t.__name__};\n"
                else:
                    port_content += f"{indent}        {name}: {direction} std_logic_vector({t.W - 1} downto 0);\n"
            if port_content:
                port_content = port_content[:-2] # 去掉最后的分号和换行
            return \
f"""\
{indent}{part} {hdl.entity_name} is
{indent}    port (
{port_content}
{indent}    );
{indent}end {part};\
"""
        
        # 组件声明
        comp_declaration = ""
        for comp in self.components:
            comp_declaration += emit_ports(comp, "component", "    ") + "\n"
        if comp_declaration:
            comp_declaration = comp_declaration[:-1]
        
        # 信号声明
        signal_declaration = ""
        for name, t in self.signals.items():
            if t.belongs(Bundle):
                signal_declaration += f"    signal {name}: {t.__name__};\n"
            else:
                signal_declaration += f"    signal {name}: std_logic_vector({t.W - 1} downto 0);\n"
        if signal_declaration:
            signal_declaration = signal_declaration[:-1]
        
        # 模块例化
        comp_content = ""
        for inst_name, (comp_name, mapping) in self.inst_comps.items():
            mapping_content = ""
            for comp_port, inst_port in mapping.items():
                mapping_content += f"            {comp_port} => {inst_port},\n"
            if mapping_content:
                mapping_content = mapping_content[:-2]
            comp_content += \
f"""\
    {inst_name}: {comp_name}
        port map (
{mapping_content}
        );

"""
        if comp_content:
            comp_content = comp_content[:-1]
        
        # 并行赋值
        assignment_content = ""
        for target, value in self.assignments:
            assignment_content += f"    {target} <= {value};\n"
        if assignment_content:
            assignment_content = assignment_content[:-1]
        
        # 拼接文件内容
        res[prefix + "_" + self.entity_name + ".vhd"] = \
f"""\
{self.global_info.header_vhdl()}

{emit_ports(self, "entity")}

architecture Structural of {self.entity_name} is
{comp_declaration}
{signal_declaration}
begin
{comp_content}
{assignment_content}
end architecture;\
"""
        
        return res
    
    def add_port(self, name: str, direction: str, t: SignalType):
        if t.belongs(Bundle):
            self.global_info.add_type(t) # 添加类型到全局信息
        
        self.ports[name] = (direction, t)
    
    def add_component(self, comp: 'HDLFileModel'): # 添加组件到 components, 将 comp 的全局信息传递给自己的全局信息
        self.global_info.merge(comp.global_info)
        self.components.add(comp)
    
    def inst_component(self, inst_name: str, comp: 'HDLFileModel', mapping: dict[str, str]):
        if comp not in self.components: # 未添加到 components 中则添加
            self.add_component(comp)
        self.inst_comps[inst_name] = (comp.entity_name, mapping)
    
    def add_signal(self, name: str, t: SignalType):
        if t.belongs(Bundle):
            self.global_info.add_type(t) # 添加类型到全局信息
        
        self.signals[name] = t
    
    def add_assignment(self, target: str, value: str):
        self.assignments.append((target, value))
    
    def set_raw(self, filename: str, content: str):
        self.raw = True
        self.raw_filename = filename
        self.raw_content = content

def write_to_files(d: dict[str, str], path: str):
    for filename, content in d.items():
        with open(path + "/" + filename, "w") as f:
            f.write(content)

