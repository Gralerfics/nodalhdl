以下两种综合出来一致，都是使用 FDCE（带使能功能的异步清除 D 触发器）。

```vhdl
library IEEE;
use IEEE.std_logic_1164.all;
use IEEE.numeric_std.all;

entity top is
    Port (
        clk, rst, en: in std_logic;
        z: out std_logic_vector(7 downto 0)
    );
end top;

architecture Behavioral of top is
    signal cnt_reg, cnt_next: std_logic_vector(7 downto 0);
begin
    process (clk, rst) is
    begin
        if rst = '1' then
            cnt_reg <= (others => '0');
        elsif rising_edge(clk) then
            cnt_reg <= cnt_next;
        end if;
    end process;

    cnt_next <= std_logic_vector(unsigned(cnt_reg) + 1) when en = '1' else cnt_reg;
    
    z <= cnt_reg;
end Behavioral;
```

```vhdl
library IEEE;
use IEEE.std_logic_1164.all;
use IEEE.numeric_std.all;

entity top is
    Port (
        clk, rst, en: in std_logic;
        z: out std_logic_vector(7 downto 0)
    );
end top;

architecture Behavioral of top is
    signal cnt_reg, cnt_next: std_logic_vector(7 downto 0);
begin
    process (clk, rst) is
    begin
        if rst = '1' then
            cnt_reg <= (others => '0');
        elsif rising_edge(clk) then
            if en = '1' then
                cnt_reg <= cnt_next;
            else
                cnt_reg <= cnt_reg;
            end if;
        end if;
    end process;

    cnt_next <= std_logic_vector(unsigned(cnt_reg) + 1);
    
    z <= cnt_reg;
end Behavioral;
```