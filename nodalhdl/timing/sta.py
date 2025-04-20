from ..core.structure import Structure, RuntimeId
from ..core.hdl import emit_to_files

import subprocess
import os
import shutil

import re

from typing import List, Dict, Tuple


class STAException(Exception): pass


class StaticTimingAnalyser:
    """
        Static timing analyser, accept only flattened structures.
        Run analyse() to do timing analysis and save the timing info into all first-level substructures' timing_info.
    """
    def __init__(self):
        pass
    
    def analyse(s: Structure) -> None:
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
                        r_tag = False
                        if rvs[2][-1] == "r":
                            r_tag = True
                            rvs[2] = rvs[2][:-2]
                        
                        line_entry["delay_type"] = rvs[0]
                        line_entry["incr_ns"] = float(rvs[1])
                        line_entry["path_ns"] = float(rvs[2])
                        line_entry["netlist_resources"].append((r_tag, rvs[3]))
                    elif len(rvs) == 3:
                        # e.g. "                         FDCE                                         r  reg_0_d_u1_z_add_123_io_res_reg[3]/D"
                        line_entry["delay_type"] = rvs[0]
                        line_entry["netlist_resources"].append((True, rvs[2]))
                    elif len(rvs) == 2:
                        # e.g. (1.) "                                                                      r  u1_z_add_123/res[3]_INST_0/I0"
                        # e.g. (2.) "                         FDCE                                            reg_0_d_u1_z_add_123_io_res_reg[3]/D"
                        if rvs[0] == "r": # (1.)
                            line_entry["netlist_resources"].append((True, rvs[1]))
                        else: # (2.)
                            line_entry["delay_type"] = rvs[0]
                            line_entry["netlist_resources"].append((False, rvs[1]))
                    elif len(rvs) == 1:
                        # e.g. "                                                                         u1_z_add_123/res[3]_INST_0/I0"
                        line_entry["netlist_resources"].append((False, rvs[0]))
                    else:
                        pass # ?
                    
                    # row info
                    if not line_entry["delay_type"]:
                        # related to previous lines, extend previous row's information
                        assert len(res.details) > 0
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
    
    def __init__(self, part_name: str = "xc7a200tfbg484-1", temporary_workspace_path: str = ".vivado_sta", vivado_executable_path: str = "vivado"):
        self.part_name = part_name
        self.temporary_workspace_path = os.path.abspath(temporary_workspace_path)
        self.vivado_executable_path = vivado_executable_path
        
        self.TMP_TOP_MODULE_NAME = "sta_root"
        self.TMP_PROJ_NAME = "vivado_sta_proj"
        self.TMP_SRC_DIR = "src"
        self.RUN_JOBS = 8
        self.REPORT_FILENAME = "timing_report.txt"
        self.TCL_SCRIPT_NAME = "build_and_timing.tcl"
    
    def _create_temporary_workspace(self):
        if os.path.exists(self.temporary_workspace_path):
            shutil.rmtree(self.temporary_workspace_path)
        os.makedirs(self.temporary_workspace_path, exist_ok = True)
    
    def _write_tcl_script_and_run(self, tcl_script_str: str):
        tcl_script_path = os.path.join(self.temporary_workspace_path, self.TCL_SCRIPT_NAME)
        with open(tcl_script_path, "w") as f:
            f.write(tcl_script_str)
        
        feedback = subprocess.run(
            [self.vivado_executable_path, "-mode", "batch", "-source", self.TCL_SCRIPT_NAME],
            cwd = self.temporary_workspace_path,
            # stdout = subprocess.PIPE,
            # stderr = subprocess.PIPE,
            text = True
        )
    
    def analyse(self, s: Structure, skip_emitting_and_script_running: bool = False): # skip_emitting_and_script_running only for debugging
        if not skip_emitting_and_script_running:
            self._create_temporary_workspace()
            
            # duplicate a temporary structure, set all latencies to 1, for generating
            s_dup = s.duplicate()
            for net in s_dup.get_nets():
                net.driver().set_latency(1)
            
            # deduction and generation
            s_dup_rid = RuntimeId.create()
            s_dup.deduction(s_dup_rid)
            s_dup_model = s_dup.generation(s_dup_rid, top_module_name = self.TMP_TOP_MODULE_NAME)
            emit_to_files(s_dup_model.emit_vhdl(), os.path.join(self.temporary_workspace_path, self.TMP_SRC_DIR))
        
        # create the script and record the paths ([NOTICE] report 中 path 信息应该是按 get_timing_paths 指令的顺序给出的)
        #  - header
        tcl = "### auto generated by nodalhdl ###\n"
        
        #  - create project
        tcl += f"create_project {self.TMP_PROJ_NAME} ./{self.TMP_PROJ_NAME} -part {self.part_name} -force\n"
        tcl += f"set_property top {self.TMP_TOP_MODULE_NAME} [current_fileset]\n"
        tcl += "\n"
        tcl += f"foreach file [glob -nocomplain ./{self.TMP_SRC_DIR}/*.vhd] {{\n"
        tcl += "    add_files $file\n"
        tcl += f"}}\n"
        tcl += "update_compile_order -fileset sources_1\n"
        tcl += "\n"
        
        #  - synthesis [NOTICE] add impl?
        tcl += "reset_run synth_1\n"
        tcl += f"set_property -name {{STEPS.SYNTH_DESIGN.ARGS.FLATTEN_HIERARCHY}} \\\n"
        tcl += f"             -value {{none}} \\\n"
        tcl += f"             -objects [get_runs synth_1]\n"
        tcl += "\n"
        tcl += f"launch_runs synth_1 -jobs {self.RUN_JOBS}\n"
        tcl += "wait_on_run synth_1\n"
        tcl += "\n"
        
        #  - open run
        tcl += "open_run synth_1\n"
        tcl += "\n"
        
        #  - add timing paths
        tcl += f"set paths {{}}\n"
        added_paths: List[Tuple] = [] # [(inst_name, pi_full_name, po_full_name, ), ]
        for inst_name, subs in s.substructures.items():
            if subs.timing_info is not None: # [NOTICE] 分析过的结构不用再分析
                continue
            subs.timing_info = {} # [NOTICE] 这次分析中已经计划分析的结构不用重复分析
            
            subs_ports_outside = s.get_subs_ports_outside(inst_name)
            in_ports = subs_ports_outside.nodes(filter = "in")
            out_ports = subs_ports_outside.nodes(filter = "out")
            
            for pi_full_name, pi in in_ports:
                if pi.located_net.driver is None or pi.located_net.driver() is None: # NC
                    continue
                
                from_po = pi.located_net.driver()
                if from_po.of_structure_inst_name: # [NOTICE] Pylance bug? if use `from_po.(...) is not None`, the else-branch will take from_po as None
                    desc_1 = f"{from_po.of_structure_inst_name}_io_{from_po.layered_name}"
                else:
                    desc_1 = from_po.layered_name
                through_1 = f"reg*d*{desc_1}*/C"
                
                for po_full_name, _ in out_ports:
                    desc_2 = f"{inst_name}_io_{po_full_name}"
                    through_2 = f"reg*d*{desc_2}*/D"
                    
                    tcl += f"set paths [concat $paths [get_timing_paths -through [get_pins -hier {through_1}] -through [get_pins -hier {through_2}] -delay_type max -max_paths 1 -nworst 1 -unique_pins]]\n"

                    # record keys for the instance, I-port and O-port for storing
                    added_paths.append((inst_name, pi_full_name, po_full_name, desc_1, desc_2)) # desc_x for checking if the timing path exists in the report, or it should be skipped
        tcl += "\n"
        
        #  - report timing
        if len(added_paths) == 0:
            tcl += "# " # no paths need to analysis, comment the report_timing command
        tcl += f"report_timing -file \"{self.REPORT_FILENAME}\" -of_objects $paths -no_header -column_style variable_width\n"
        tcl += "\n"
        
        #  - close project
        tcl += "close_project\n"
        tcl += "exit\n"
        
        if len(added_paths) > 0:
            # run the script
            if not skip_emitting_and_script_running:
                self._write_tcl_script_and_run(tcl)

            # load parse the results
            with open(os.path.join(self.temporary_workspace_path, self.REPORT_FILENAME), "r") as f:
                report_lines = f.readlines()
            report = VivadoSTA.TimingReport.parse_lines(report_lines)
            
            # process and store timing info (TODO 理论上没问题, 或者 added_paths 里面存为 Dict[(desc_1, desc_2): (inst_name, pi_full_name, po_full_name)]? 这样要求 desc_x 可以直接由 src/dest 还原.)
            added_paths_ptr = 0
            for idx, p in enumerate(report.paths):
                while p.source.find(added_paths[added_paths_ptr][3]) < 0 or p.destination.find(added_paths[added_paths_ptr][4]) < 0: # skip this added path
                    added_paths_ptr += 1
                
                # extract logic delays
                """
                    [NOTICE]
                    在这里, 时序路径报告的表格, 第一条一定是 FDCE/C, 第二条一定是 FDCE/Q, 第三条一定是这个寄存器连到组合逻辑入口的 net, 最后一条一定是下一个 FDCE/D.
                    舍去以上四条, 其余即所需要的延时.
                    这里可以遍历其余条目, 累加 incr_ns, 便于避开可能的 None; 或若能保证倒数第二条 (应该是组合逻辑出口连到下一个 FDCE 的 net, incr_ns = 0.0) 的 path_ns 不为 None, 可直接用其减去第三条的 path_ns.
                    这里暂采用后者.
                """
                if len(p.details) <= 4:
                    delay = 0.0
                else:
                    delay = p.details[-2]["path_ns"] - p.details[2]["path_ns"]
                
                # store into structure
                inst_name, pi_full_name, po_full_name = added_paths[added_paths_ptr][0:3]
                if s.substructures[inst_name].timing_info is None:
                    s.substructures[inst_name].timing_info = {}
                s.substructures[inst_name].timing_info[(pi_full_name, po_full_name)] = delay
                s.substructures[inst_name].timing_info[('_simple_in', '_simple_out')] = max(delay, s.substructures[inst_name].timing_info.get(('_simple_in', '_simple_out'), 0))
                
                # next added path
                added_paths_ptr += 1

