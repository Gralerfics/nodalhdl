# TODO Notes

1. CORDIC 等模块; 乘法的优化等.
2. [***] 重构, HLS 计算图中间层.
3. [**] 内部 _unique_name 以及外面 naming 时不要直接 args_kwargs_all_values. 例如 Bits_8 和 UInt_8 都是八位, 在乘法器等结构中不影响内部结构, 但名字会导致它们被分为不同的可复用结构.
4. retiming 效率问题. e.g. 转换时忽略基本无延迟的节点等.
5. 结构展开为等价 LUT (组合逻辑根据输入位的个数应该就可判断, 然后通过仿真可以把表查出来?).
6. operator 自带时钟延迟的问题 (retiming 可否解决), 解决则可引入 IP 核; 普通时序电路和流水线的区分.
7. [*] 补充完整 signal, 比如 BundleValue.
8.  [**] (整体 retiming 慢则拆分) 流水线拼接 (直接对接 / ready-valid); ready-valid 反压打断问题; 同功能的组合逻辑和状态机实现.
9.  外设.
10. pipelining 自动级数选取.
11. 时序分析临时目录缓存 (Structure 同构判断).
12. .arith 的传参方式问题; Add/Subtract U/SInt 不等宽情况 (围绕 BitsAdd 重新建立); 前者也就是运行时类型影响结构架构选取的功能 (要不叫动态架构什么的, 应该可以套在外面实现, 例如类型推导先 custom_deduction 的模块跑 (基本算子以外的结构也加个类似 custom_deduction 的东西, 就是允许这种情况只跑推导不走内部), 跑完推完再填入合适的结构; 这种情况才会要求不能出现奇怪的冲突类型需要报错; 不实现该功能的时候冲突类型不用报出来, 因为不影响生成; 即 "指定" 而非 "允许" 的需求, 需要加到 signal 实现中).
13. [*] CustomVHDLOperator 结构化端口.
14. 关于 Bundle 拆分、聚合、连接的问题. 还有如 StructuralNodes 同时分别返回 in 和 out 端口的功能等; 还有 IOProxy 实现对应 StructuralNodes 的功能 (一一对应外有没有更好的方法).
15. Verilog 完整支持.
16. 仿真支持; 包括值对象的运算等.
17. 选择性 expand (substructures_expandable_flags: Dict[str, bool]).
18. STA 其他工具支持; Vivado 时序报告的解析功能完善.
19. [**]STA 有关同算子处于不同连接关系下时序不同的问题（例如存在常数输入导致各关键路径可能降低）; 尽量不重复分析，不然太多了, 虽然好像也能接受.
20. STA 中提取时序路径的双指针方法总感觉有隐患, 因为要求报告生成时严格按 TCL 中的添加顺序.
21. nodalhdl-editor; 支持编辑器需要添加一系列操作, 例如框选一组结构拖出去的操作等需要相应的 API.
22. 持久化读写后如何保障 unique_name 等池子的一致性.
23. [*] 重构合理的异常处理体系.
24. 异步、访存、并行与仲裁.
25. [***] extended 模型有问题, 似乎是否报错还和不同运行次数有关? 结果感觉也不太对.
26. ...
