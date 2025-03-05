from .signal import SignalType, Bundle, IOWrapper


class HDLFileModelException(Exception): pass

class HDLGlobalInfo:
    """
        HDL 文件模型中的全局信息.
        例如所用到的所有类型, 在 add_component 时会向上级传递, 最终顶层结构生成时会给出单独一个 types.vhd (以 VHDL 为例).
    """
    def __init__(self):
        self.type_pool = set() # 类型池, 可用于查重
        self.type_pool_ordered = [] # 有序的 type_pool, 以防 HDL 要求顺序声明类型
    
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
                for _, v in t.items(): # 遍历子 Bundle
                    _add(v)
                self.type_pool.add(t) # 添加该 Bundle 类型
                self.type_pool_ordered.append(t) # 先添加子类型, 再添加父类型, 满足顺序声明要求
        
        _add(t)

class HDLFileModel:
    """
        HDL 文件模型.
        完全对应 HDL 文件内容, 不包含任何判断和校验等措施.
        TODO operator 无法在 box 层面 expand, 像切片这种操作单独文件又太繁琐, 或许可以在文件模型中标记, 在 HDL 层面展开.
    """
    def __init__(self):
        self.entity_name = None
        self.components = set() # Set[HDLFileModel], inst_comp 中
    
    def emit_vhdl(self):
        pass # TODO 返回 Dict[filename: str, content: str]
    
    def inst_comp(self, comp: 'HDLFileModel'): # HDLFileModel or Structure ???
        pass
    
    

