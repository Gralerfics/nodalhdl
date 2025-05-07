#


class ComputeElement:
    """
        对其的运算会记录轨迹（计算图）
        Variable / Element
    """
    def __init__(self):
        self.


# Int(Variable) 的话位宽怎么表示? 再来一遍 signal?


class Engine:
    def __init__(self):
        self._add = self._add
    
    """
        default operations
        TODO
        大概，转换过程是传入 Variable 跑一遍目标 func 得到计算图（没跑通说明不是 comb）
            例如 (a + b) * c 得到 MUL(ADD(a, b), c), abc 是传入的 Variable
            这样的树形表达式形式合适吗? 能满足所有情况吗, 还是说需要图结构?
                树形的话复用结构怎么复用? 好像可以, 记录一下就行
        然后根据计算图转为 structure
            计算图这边的运算对应 py 代码, 转换的方式则应该允许重载
            计算图中的函数对应的转换方式就是了
            不过用户的重载也用 py 写呢? 和转 structure 的重载需要思考区分一下
        TODO
    """
    def _add(v1, v2):
        pass
    
    """
        actions
    """
    def combinational_to_structure(f: callable):
        pass

