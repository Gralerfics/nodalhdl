from ..core.structure import Structure
from .retiming import ExtendedCircuit


pass # TODO



"""
    TODO
    要有个 retiming, 针对运行过 sta 的

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