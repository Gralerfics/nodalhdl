from .signal import *

import hashlib


""" Exceptions """
class DiagramTypeException(Exception): pass
class DiagramInstantiationException(Exception): pass


""" Utils """
class DiagramStructure:
    def __init__(self):
        pass # TODO


""" Metatypes """
class DiagramType(type):
    INSTANTIATION_ARGUMENTS_ATTRNAME = "instantiation_arguments"
    STRUCTURE_ATTRNAME = "structure"
    DETERMINED_ATTRNAME = "determined"
    
    diagram_type_pool = {}
    
    def __new__(mcs, name: str, bases: tuple, attr: dict): # `mcs` here is the metaclass itself
        """
            创建新 Diagram 类型, 可能情况:
                (1.) 使用 class 继承 Diagram 创建子类.
                (2.) 使用中括号传递参数创建 Diagram 或其子类的衍生类.
                (3.) TODO 在衍生类基础上再加中括号传递参数.
                        ... 需要考虑该行为的物理意义, 无意义则应抛出异常, 可以在 __getitem__ 中判断是否已有参数 <INSTANTIATION_ARGUMENTS_ATTRNAME>.
            最终都进入 __new__, 情况 (2.) 会在 attr 中带有参数 <INSTANTIATION_ARGUMENTS_ATTRNAME>.
            创建类型须:
                (1.) 构建新类名, 查重, 并创建新类. (注意 hash() 是不稳定的, 与运行时环境有关, 建议使用稳定的映射)
                        ... TODO 构建方案需改进, 目前直接使用 str(inst_args), 与子结构的 str 结果高度相关, 可能限制参数传递的多样性以及破坏哈希的全局稳定性.
                        ... TODO 哈希重复是否要再检查一下参数是否严格相同, 以防止小概率的哈希冲突?
                (2.) 通过 setup(args) 构建框图结构, 更新类属性 structure.
                (3.) TODO 通过 deduction() 类型推导判断结构是否可例化 (例如类型宽度都已确定), 更新类属性 determined.
                (4.) 返回新类型.
        """
        inst_args = attr.get(DiagramType.INSTANTIATION_ARGUMENTS_ATTRNAME, ()) # 获取可能从 __getitem__ 传来的参数, 无则默认为空

        new_name = name
        if inst_args: # 若参数不为空则依据参数构建新名
            print(str(inst_args))
            new_name = f"{name}_{hashlib.md5(str(inst_args).encode('utf-8')).hexdigest()}"
        
        if not new_name in mcs.diagram_type_pool.keys(): # 若尚未创建过
            new_cls = super().__new__(mcs, new_name, bases, attr) # 先创建类, deduction() 和 setup() 可能未在子类中显式重写 (即未在 attr 中)
            deduction_func = new_cls.deduction
            setup_func = new_cls.setup
            
            new_structure, new_determined = None, False
            try:
                new_structure = setup_func(inst_args) # 生成结构
                new_determined = True # TODO 类型推导后确认是否 determined, 并给 new_cls.determined 赋值, 暂时给 True
            except DiagramTypeException as e:
                print(e)
                pass # 默认值如前, 可能是 setup() 未实现空参行为或类型推导出错, 结构留空并置 determined 为 False, 待后续带参构建
            
            setattr(new_cls, DiagramType.STRUCTURE_ATTRNAME, new_structure)
            setattr(new_cls, DiagramType.DETERMINED_ATTRNAME, new_determined)
            
            mcs.diagram_type_pool[new_name] = new_cls # 加入框图类型池

        return mcs.diagram_type_pool[new_name] # 从框图类型池中获取
    
    def __getitem__(cls: 'Diagram', args: tuple): # `cls` here is the generated class
        """
            在已有 Diagram 类基础上通过中括号传入参数以构建新的类并返回.
            行为上是将 args 通过 attr 传入 __new__, 在其中统一处理.
        """
        return DiagramType(
            cls.__name__, # 传入无参框图名, 在 __new__ 中构建新名
            (cls, ), # 继承无参框图的属性和方法, 主要是 setup 和 deduction 等
            {DiagramType.INSTANTIATION_ARGUMENTS_ATTRNAME: args} # 传递参数交给 __new__ 创建
        )


""" Types """
class Diagram(metaclass = DiagramType):
    is_operator = False # 是否是基本算子 (即无内部结构)
    
    structure = None
    determined = False # 是否定型 (即是否可例化), 理论上可以通过类型推导得出, 此处特殊空结构, 为 False
    
    def __init__(self):
        if not self.determined:
            raise DiagramInstantiationException(f"Undetermined diagram \'{type(self).__name__}\' cannot be instantiated.")
        pass # TODO 统一例化过程, 框图到实例, 继承者不可更改
    
    @classmethod
    def deduction(cls): # 类型推导
        print('deduction.')
        pass # TODO
    
    @staticmethod
    def setup(args: tuple = ()) -> DiagramStructure: # 框图结构生成, 可能含参, 此处为空结构无参, 继承者须覆写
        return DiagramStructure()


""" Derivatives """
class Addition(Diagram): # 带参 Diagram 示例, 整数加法
    @staticmethod
    def setup(args) -> DiagramStructure:
        # 类型检查
        # TODO
        return DiagramStructure()

