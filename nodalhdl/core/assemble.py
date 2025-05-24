# This file is part of nodalhdl (https://github.com/Gralerfics/nodalhdl), distributed under the GPLv3. See LICENSE.

"""
    TODO 组装层.
    Idea:
        将单个状态机 / 流水线视为一个组件 (模块), 其间进行 ready-valid 握手.
        如此可以对功能模块进行建模、与状态机协同、拼装流水线（大型电路重定时效率低; 可以通过这种方式引入 IP 核等自带时序的模块, 虽然感觉从这个层面上解决有点难受）等.
    
    Memo:
        1. 握手的反压、打断问题.
        2. 关于通用流水线模型, 如暂停、冲刷等操作的模式化.
        3. ...
"""




