# This file is part of nodalhdl (https://github.com/Gralerfics/nodalhdl), distributed under the GPLv3. See LICENSE.

import multiprocessing.pool
from ..core.structure import *
from ..core.hdl import *

import multiprocessing
import subprocess
import os
import shutil
import re
import hashlib
import textwrap

from typing import List, Dict


class STAException(Exception): pass


class StaticTimingAnalyser:
    """
        Static timing analyser, accept only flattened structures.
        Run analyse() to do timing analysis and save the timing info into all first-level substructures' timing_info.
    """
    def __init__(self):
        pass
    
    def analyse(s: Structure, root_runtime_id: RuntimeId) -> None:
        pass # to be override


class VivadoSTA(StaticTimingAnalyser):
    """
        Static timing analyser powered by Vivado TCL tools.
    """
    class TimingPath:
        def __init__(self):
            self.source: str = None
            self.destination: str = None
            self.path_group: str = None
            self.path_type: str = None
            self.data_path_delay: str = None
            self.logic_levels: str = None
            
            self.details: List[Dict] = [] # [{location, delay_type, incr_ns, path_ns, netlist_resources, ...}, ...]
        
        def __repr__(self):
            res = f"TimingPath<{self.source} -> {self.destination}, {self.data_path_delay} (ns), {self.path_type}, [\n"
            for row in self.details:
                res += "    " + str(row) + ",\n"
            return res[:-2] + "\n]>\n"
        
        @staticmethod
        def parse_lines(lines: List[str]):
            """
                Fuck Vivado.
                `-column_style variable_width` used.
                TODO 暂时默认是仅综合, 所以 Location 字段为空.
            """
            res = VivadoSTA.TimingPath()

            in_table = False
            for line in lines:
                line = line.rstrip()
                
                if line.startswith("Slack:"):
                    res.slack = line.split(":", 1)[1].strip()
                elif line.strip().startswith("Source:"):
                    res.source = line.split(":", 1)[1].strip()
                elif line.strip().startswith("Destination:"):
                    res.destination = line.split(":", 1)[1].strip()
                elif line.strip().startswith("Path Group:"):
                    res.path_group = line.split(":", 1)[1].strip()
                elif line.strip().startswith("Path Type:"):
                    res.path_type = line.split(":", 1)[1].strip()
                elif line.strip().startswith("Data Path Delay:"):
                    res.data_path_delay = line.split(":", 1)[1].strip()
                elif line.strip().startswith("Logic Levels:"):
                    res.logic_levels = line.split(":", 1)[1].strip()
                elif re.match(r"\s*Location\s+Delay type", line):
                    in_table = True
                elif in_table:
                    # empty lines or splitting line
                    if not line.strip() or re.match(r"^\s*-{10,}", line):
                        continue
                    
                    line_entry = {
                        "location": None,
                        "delay_type": None,
                        "incr_ns": None,
                        "path_ns": None,
                        "netlist_resources": []
                    }
                    
                    # extract raw info
                    rvs = re.split(r'\s{2,}', line.strip()) # raw_values
                    if len(rvs) == 4:
                        # e.g. "                         LUT4 (Prop_lut4_I0_O)        0.317     1.457 r  u1_z_add_123/res[3]_INST_0_i_1/O"
                        #      "                         LUT4 (Prop_lut4_I0_O)        0.317     1.457 f  u1_z_add_123/res[3]_INST_0_i_1/O"
                        strange_tag = None
                        if not rvs[2][-1].isdigit():
                            strange_tag = rvs[2][-1]
                            rvs[2] = rvs[2][:-2]
                        
                        line_entry["delay_type"] = rvs[0]
                        line_entry["incr_ns"] = float(rvs[1])
                        line_entry["path_ns"] = float(rvs[2])
                        line_entry["netlist_resources"].append((strange_tag, rvs[3]))
                    elif len(rvs) == 3:
                        # e.g. (1.) "                         FDCE                                         r  reg_0_d_u1_z_add_123_io_res_reg[3]/D"
                        # e.g. (2.) "                                                      0.000     0.000 r  b[0] (IN)"
                        if not rvs[0][0].isdigit(): # (1.)
                            line_entry["delay_type"] = rvs[0]
                            line_entry["netlist_resources"].append((rvs[1], rvs[2]))
                        else: # (2.)
                            line_entry["incr_ns"] = float(rvs[0])
                            line_entry["path_ns"] = float(rvs[1][:-2])
                            line_entry["netlist_resources"].append((rvs[1][-1], rvs[2]))
                    elif len(rvs) == 2:
                        # e.g. (1.) "                                                                      r  u1_z_add_123/res[3]_INST_0/I0"
                        #           "                                                                      f  u1_z_add_123/res[3]_INST_0/I0"
                        # e.g. (2.) "                         FDCE                                            reg_0_d_u1_z_add_123_io_res_reg[3]/D"
                        if len(rvs[0]) == 1: # (1.)
                            line_entry["netlist_resources"].append((rvs[0], rvs[1]))
                        else: # (2.)
                            line_entry["delay_type"] = rvs[0]
                            line_entry["netlist_resources"].append((None, rvs[1]))
                    elif len(rvs) == 1:
                        # e.g. "                                                                         u1_z_add_123/res[3]_INST_0/I0"
                        line_entry["netlist_resources"].append((None, rvs[0]))
                    else:
                        raise NotImplementedError
                    
                    # row info
                    if not line_entry["delay_type"] and len(res.details) > 0: # len(res.details) == 0 for (IN) row
                        # related to previous lines, extend previous row's information
                        row = res.details[-1]
                        
                        # merge values
                        for token in ["location", "delay_type", "incr_ns", "path_ns"]:
                            if row.get(token) is None:
                                row[token] = line_entry[token]
                        
                        # extend netlist_resources
                        last_nr = row.get("netlist_resources")
                        if isinstance(last_nr, list):
                            last_nr.extend(line_entry["netlist_resources"])
                    else:
                        # new independent row
                        res.details.append(line_entry)
            
            return res
    
    class TimingReport:
        def __init__(self):
            # [NOTICE] -no_header used currently
            self.tool_version: str = None
            self.date: str = None
            self.host: str = None
            self.command: str = None
            self.design: str = None
            self.device: str = None
            self.speed_file: str = None
            self.design_state: str = None
            
            self.paths: List[VivadoSTA.TimingPath] = []

        @staticmethod
        def parse_lines(lines: List[str]):
            res = VivadoSTA.TimingReport()

            path_lines = []
            for line in lines:
                if line.strip().startswith("Slack:"): # [NOTICE] slack?
                    if path_lines:
                        res.paths.append(VivadoSTA.TimingPath.parse_lines(path_lines))
                        path_lines.clear()
                path_lines.append(line)

            # the remained one
            if path_lines:
                path = VivadoSTA.TimingPath.parse_lines(path_lines)
                res.paths.append(path)
            
            return res
    
    def __init__(self, part_name: str = "xc7a200tfbg484-1", temporary_workspace_path: str = ".vivado_sta", vivado_executable_path: str = "vivado", pool_size = 12, syn_max_threads = 8):
        self.part_name = part_name
        self.temporary_workspace_path = os.path.abspath(temporary_workspace_path)
        self.vivado_executable_path = vivado_executable_path
        self.pool_size = pool_size
        self.syn_max_threads = syn_max_threads
        
        self.TMP_TOP_MODULE_NAME = "module"
        self.TMP_SRC_DIR = "src"
        self.TCL_SCRIPT_NAME = "build_and_timing.tcl"
        self.REPORT_FILENAME = "timing_report.txt"
        self.SUMMARY_FILENAME = "timing_summary.txt"
    
    def _create_temporary_workspace(self):
        if os.path.exists(self.temporary_workspace_path):
            return
            # shutil.rmtree(self.temporary_workspace_path)
        os.makedirs(self.temporary_workspace_path, exist_ok = True)
    
    def _analyse_single(self, vhdl: dict, key: str):
        # emitting files
        emit_to_files(vhdl, os.path.join(self.temporary_workspace_path, key, self.TMP_SRC_DIR)) # TODO 重复的 types.vhd 等
        
        # write script
        """
            references:
                https://docs.amd.com/r/en-US/ug835-vivado-tcl-commands/
                https://github.com/JulianKemmerer/PipelineC/blob/master/src/VIVADO.py
        """
        tcl_script_str = textwrap.dedent(f"""\
            ### auto generated by nodalhdl ###
            
            read_vhdl -library work {{ {" ".join([self.TMP_SRC_DIR + "/" + filename for filename in vhdl.keys()])} }}
            
            set_param general.maxThreads {self.syn_max_threads}
            
            synth_design \\
                -part {self.part_name} \\
                -mode out_of_context \\
                -top {self.TMP_TOP_MODULE_NAME} \\
                -flatten_hierarchy none
            
            report_timing \\
                -setup \\
                -no_header \\
                -column_style variable_width \\
                -file {self.REPORT_FILENAME}
        """)
        tcl_script_path = os.path.join(self.temporary_workspace_path, key, self.TCL_SCRIPT_NAME)
        with open(tcl_script_path, "w") as f:
            f.write(tcl_script_str)
        
        # run script
        if not os.path.exists(os.path.join(self.temporary_workspace_path, key, self.REPORT_FILENAME)):
            process = subprocess.Popen(
                [self.vivado_executable_path, "-mode", "batch", "-source", self.TCL_SCRIPT_NAME],
                cwd = os.path.join(self.temporary_workspace_path, key),
                stdout = subprocess.PIPE,
                stderr = subprocess.PIPE,
                text = True
            )
            # process.wait() # [NOTICE] 有点诡异, 用 .wait() 综合会到一半卡住; 用 .communicate() 也能等待到执行完
            outs, errs = process.communicate()
            
            if process.returncode != 0:
                print(f"[ERROR] failed in running the script")
        else:
            print(f"[INFO] module analysed, skipped (hash: {key})")
        
        # load and parse the report
        with open(os.path.join(self.temporary_workspace_path, key, self.REPORT_FILENAME), "r") as f:
            report_lines = f.readlines()
        report = VivadoSTA.TimingReport.parse_lines(report_lines)
        
        return report
    
    def analyse(self, s: Structure, root_runtime_id: RuntimeId):
        """
            refactorized with multiprocessing, inspired by PipelineC
        """
        assert s.is_flattened
        
        # create workspace
        self._create_temporary_workspace()
        
        # collect and analyse reusable structures
        structures_on_analysing: Dict[str, List[str]] = {} # {key: [subs_inst_name(s)]}
            # TODO 这里存 subs_inst_name 是因为理论上同结构的不同实例因为所处连接关系的不同 (例如有常数输入), 时序信息也可能不同; 下面暂时没有考虑这一点, 但数据结构在此保留.
        analyse_pool: multiprocessing.pool.ThreadPool = multiprocessing.pool.ThreadPool(self.pool_size)
        results_on_analysing: Dict[str, multiprocessing.pool.AsyncResult] = {}
        for idx, (subs_inst_name, subs) in enumerate(s.substructures.items()):
            # filtering
            if len(subs.ports_inside_flipped.nodes(filter = "in", flipped = True)) == 0: # no input
                continue
            if len(subs.ports_inside_flipped.nodes(filter = "out", flipped = True)) == 0: # no output
                continue
            
            # calculate hash
            model = subs.generation(root_runtime_id.next(subs_inst_name), top_module_name = self.TMP_TOP_MODULE_NAME)
            vhdl = model.emit_vhdl()
            file_hash = hashlib.sha256(vhdl[f"hdl_{self.TMP_TOP_MODULE_NAME}.vhd"].encode('utf-8')).hexdigest()
            
            # collect unique structures and analyse
            key = file_hash
            if structures_on_analysing.get(key, None) is None: # first time
                # save structure ref
                structures_on_analysing[key] = []
                
                # async analysis
                print(f"[INFO] analysing module {len(structures_on_analysing)} (hash: {key}, ref_inst_name: {subs_inst_name})")
                results_on_analysing[key] = analyse_pool.apply_async(self._analyse_single, (vhdl, key))
            
            structures_on_analysing[key].append(subs_inst_name)
        
        # fetch the results
        for idx, (key, subs_inst_names) in enumerate(structures_on_analysing.items()):
            print(f"[INFO] waiting on analysis results for module {idx + 1} / {len(structures_on_analysing.items())} (hash: {key})")
            report: VivadoSTA.TimingReport = results_on_analysing[key].get() # [NOTICE] add timeout and poll?
            
            # calculate delay(s) and assign timing_info(s) TODO 端口级完整延迟模型, 重构后这里暂只分析最大值
            max_delay = 0.0
            for path_report in report.paths:
                """
                    [NOTICE] e.g. (右侧的 "<-- x" 是 path_report.details 的索引)
                    
                        Location             Delay type                Incr(ns)  Path(ns)    Netlist Resource(s)
                    -------------------------------------------------------------------    -------------------
                                                                        0.000     0.000 r  b[0] (IN)                <-- 0
                                            net (fo=3, unset)            0.973     0.973    b[0]                    <-- 1
                                            LUT4 (Prop_lut4_I3_O)        0.124     1.097 r  r[3]_INST_0_i_1/O       <-- 2
                                            net (fo=1, unplaced)         1.111     2.208    r[3]_INST_0_i_1_n_0     <-- 3
                                            LUT5 (Prop_lut5_I0_O)        0.124     2.332 r  r[3]_INST_0/O           <-- 4
                                            net (fo=0)                   0.973     3.305    r[3]                    <-- 5
                                                                                        r  r[3] (OUT)
                    -------------------------------------------------------------------    -------------------
                        这里如果是纯 net, 条目不会超过三条;
                        如果有器件, 则有第一条 (IN), 第二条入口 net, 倒数第一条出口 net + (OUT).
                            后者延迟取倒数第二条 (4, i.e. -2) 的 path_ns (2.332) 减去第二条 (1) 的 path_ns (0.973), 为 1.359.
                    
                    TODO PnR 以获得更准确的 net 延迟, 加的话除了这里, TimingPath 解析也要修改 (Location)
                """
                if len(path_report.details) > 3:
                    delay = path_report.details[-2]["path_ns"] - path_report.details[1]["path_ns"]
                    max_delay = max(delay, max_delay)
            
            for subs_inst_name in subs_inst_names:
                runtime = s.substructures[subs_inst_name].get_runtime(root_runtime_id.next(subs_inst_name))
                runtime.timing_info[("_simple_in", "_simple_out")] = max_delay
        
        print(f"[INFO] static timing analysis finished")


import sys
_current_module = sys.modules[__name__]
__all__ = [name for name in dir() if not name.startswith('_') and getattr(getattr(_current_module, name, None), "__module__", None) == __name__]

