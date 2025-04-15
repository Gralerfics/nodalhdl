from ..core.structure import Structure


class STAException(Exception): pass


class TimingPathInfo:
    pass


class TimingReportInfo:
    pass


class FlattenedStructureSTA: # Static Timing Analyser
    def __init__(self, s: Structure):
        if not s.is_flattened:
            raise STAException("Should be a flattened structure")
        self.s = s
    
    def a(self):
        pass


class VivadoSTA(FlattenedStructureSTA):
    pass


"""
    TODO
    
    要求 flatten.
    
    然后插寄存器, 生成 tcl, 跑时序分析, 从 path 里扣出某端口到某端口的延迟
    
    s_id: <TimingModel>
        d_ij, i for inputs, j for outputs.
    
    Configurations:
        哪些要细分, 哪些可以概括掉?
        未提及但还是有内部边的线路用什么数值概括?
        直接没有的内部边?
        
        理论上最细致是每一个输入 bit 到每一个输出 bit 都有 delay 的模型.
        进一步, 比较符合直观的是按端口划分, 这种情况端口到端口的 delay 应为 max{端口 bit 到端口 bit 的 delay}.
        
        或许可以在 structure 中定义一个所谓时序模型.
            对输入位、输出位进行分割分类, 互相对应建立内部边.
            每种 structure 还可以提供不同精度下的时序模型.
                所以时序模型应该是一个 "插件".
    
    Tip:
        s.id 一致的似乎不用多次分析;
        分析 flattened 结构第一级子模块是因为分析前需要综合, 一个一个拆出来生成、综合太慢了.
    
    ! 暂时先只设定两种模式, 一种每个子模块两两端口都 report_timing 建立内部边 (如果存在的话), 第二种全部用单条内部边概括.
        这件事影响两处: 1. sta 时; 2. 不在这个文件里的, pipelining 时转为 ExtendedCircuit 时的建边操作.
        嗯, 那这边 sta 后还需要妥善存储这个延迟信息. 矩阵?
    
    ? sta 结果中 net 延迟挺高, 也可能是为了分析, 加寄存器导致寄存器到组合逻辑的延迟高;
        所以注意 retiming 结果重要的是 r 而不是 Phi(G_r), Phi(G_r) 是理论的, 只能当建议, 实际的最大时钟周期得 PR 了才知道.
    
    流程:
        定义时序模型 TODO
        支持多工具, 现在考虑 Vivado TCL
        允许对一个 flattened 结构下第一级子模块进行 STA. 对 Vivado:
            flatten 了, 然后想办法, 或者就 duplicate 一下 (duplicate 没复制 runtime 信息, 注意要 deduction 一下),
            然后给每个 net 的 driver 和 load 都设置 1clk latency.
            然后 generation 一临时文件夹的 HDL (要不用 prefix, 不叫 root 了叫 tmp 之类),,
            生成 TCL, 前半段是创建工程和 synthesis (考虑一下要不要 implementation, 不用约束吗?);
            后半段 (或许可以拆开方便调试) 是时序分析,
            对每个一级模块 (同样的不用多次了), 每个 in 和 out IO 对添加 get_timing_paths, 通配符确保覆盖所有位, 取最差的 1 条, 这就是这组 in&out 的内部边延迟 d.
                方便生成和运行 TCL, 或许可以 get_timing_paths -through ........, 然后总的来一下 report_timing -of_objects $paths 导出到文件, 然后一起分析.
            然后分析报告存到 TimingReportInfo 对象, 里面关于路径存到 TimingPathInfo (考虑 net 要不要加进去).
            分别把它们分析后存到 structure 的 timing_info 里方便下次用 (注意拿来分析的是 duplicate 的, 要存得存进原来的里, 反正 flattened, 可以通过 inst_name 索引),
            不过马上是要用来生成 ExtendedCircuit 的, 似乎再单独存进一个对象比较好.
    
    下面是不在 .sta 里的部分.
        拿着分析好的 structure 和 timing 信息去生成 ExtendedCircuit, 然后就可以跑 retiming 了 (pipeline 则先插点寄存器, 见下).
            每个模块对应一个 node, 从 1 开始, 保留 0 作为 ports 等效 vertex.
            每一个 driver -> load 都是一个 external edge (每个对应一个 load), 这个不是手动添加而是直接写标号, 所以一开始要走一轮赋好编号.
                或许直接写到 load 节点的属性里, 虽然有点脏, 但方便, 要么就存一个 mapping.
                driver 上 (或者 net 里, 或者不存, 每次遍历) 则存一下所有 load 对应的 edge 号.
                跑之前把所有 driver 上的寄存器放到 load 去 (Net().transform_driver_latency_to_loads), w(e) 就是 load 的 latency.
            每个模块的每个 i&o 对都是一个 internal edge.
                在目前暂不实现细致的时序模型而是以 port 为最小单位的情况下, 每个 internal edge 只会有一个输入.
                    等下, 不分内部边的简化模式并不是如此. 而且加边时也可以省略很多东西. 看来这个得分开考虑了. 设置放哪里呢?
                每组 i&o i 的 port (注意要用 ports_outside, 不过因为 flattened, 也就一个? 不对, operators 可复用. 没事! 遍历的应该是所有模块的 ports_outside (注意还要去掉被其他模块引用的))
                    (如果前面 duplicate 的话好像 operators 也 deepcopy 了, 保险起见按上面的)
                这个 I port 就连 load 的 e, O port 连所在 net 所有 load 的 e in E_outs.
        然后 retiming 后会得到 r, 前面要存一下模块和 r 的对应关系, 我们 retime 直接在 structure 上做.
            不过如果是以 port 为最小单位的情况, e 就对应实际的连线, 可以 apply retiming 时直接对应修改 w(e) -> load latency.
                不过要考虑简化模式. 还是在 structure 上做.
            怎么做? 每个模块 I ports 和 O ports 按 r 改一下就好了, 如果 O ports 去改的是 driver, 那改完再 transform 一下.
                加个方法, transform 到 driver 以节约 reg, 可以最后的最后跑一下.
    
    pipelining 的话 structure 必须是 not is_sequential 的,
        也就是前面的单纯 retiming 可以允许 sequential, 所以运行 sta 前不能直接去原来的上面改 latency.
        话说论文里提到个什么来着, 忘了, 晚点看下.
    每个输入端口要插入相同数量的寄存器,
        这个数量除了用户设定, 怎么自动计算?
            比如时序报告中同时跑一个顶层模块输入到输出的最大路径 (要得到这个又不能插寄存器, 或者在跑下面那行的过程中通过模块的延迟累加起来), 除以预期时钟周期, 再去掉一些寄存器延迟;
            或者同时还要考虑上限, 即最多模块数的路径上有几个模块, 最多插 n - 1 个, 再多没意义.
        
"""