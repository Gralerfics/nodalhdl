# nodalhdl

## Introduction

**(Ongoing)** Pipelined digital circuit design toolchain. Partially inspired by [PipelineC](https://github.com/JulianKemmerer/PipelineC).

Provide block diagram level circuit abstraction data structures, check `test.py` for details, others under development.

## TODO

## Usage

Dependencies please check `pyproject.toml`.

## TODO List

1. [***] core.signal 重构; 双位宽类型的定态定义问题等.
2. 定点数除法、CORDIC 等模块; 乘法的优化等.
3. retiming 效率问题. e.g. 转换时忽略基本无延迟的节点等.
4. [***] 参考 test_ph 构建 HLS 层.
5. operator 自带时钟延迟的问题 (retiming 可否解决), 解决则可引入 IP 核; 普通时序电路和流水线的区分.
6. [**] (整体 retiming 慢则拆分) 流水线拼接 (直接对接 / ready-valid); ready-valid 反压打断问题; 同功能的组合逻辑和状态机实现.
7. 外设.
8. pipelining 自动级数选取.
9.  时序分析临时目录缓存 (Structure 同构判断).
10. 运行时类型影响结构架构选取的功能 (应该可以套在外面实现, 不去改 deduction 过程和 Structure 结构).
11. .arith 的传参方式问题; Add/Subtract U/SInt 不等宽情况.
12. [**] CustomVHDLOperator 结构化端口.
13. 关于 Bundle 拆分、聚合、连接的问题. 还有如 StructuralNodes 同时分别返回 in 和 out 端口的功能等; 还有 IOProxy 实现对应 StructuralNodes 的功能 (一一对应外有没有更好的方法).
14. Verilog 完整支持.
15. 仿真支持; 定点数信号值对象运算行为的修正等.
16. 选择性 expand (substructures_expandable_flags: Dict[str, bool]).
17. is_flatly_timed 判断.
18. ExtendedCircuit CP algorithm.
19. STA 其他工具支持; Vivado 时序报告的解析功能完善.
20. [**]STA 有关同算子处于不同连接关系下时序不同的问题（例如存在常数输入导致各关键路径可能降低）; 尽量不重复分析，不然太多了, 虽然好像也能接受.
21. STA 中提取时序路径的双指针方法总感觉有隐患, 因为要求报告生成时严格按 TCL 中的添加顺序.
22. 结构快拆.
23. 持久化读写后如何保障 unique_name 等池子的一致性.
24. [*] 重构合理的异常处理体系.
25. 转英文注释.
26. ...

