#!/usr/bin/env python3
"""
编译器测试脚本
支持单个文件和批量测试，包含运行、调试和性能对比功能
"""

import os
import sys
import subprocess
import argparse
import time
import tempfile
import shutil
from pathlib import Path
from typing import List, Optional, Tuple
import difflib

class Colors:
    """ANSI颜色代码"""
    # 基础颜色
    RED = '\033[91m'
    GREEN = '\033[92m'
    YELLOW = '\033[93m'
    BLUE = '\033[94m'
    MAGENTA = '\033[95m'
    CYAN = '\033[96m'
    WHITE = '\033[97m'
    GRAY = '\033[90m'
    
    # 样式
    BOLD = '\033[1m'
    DIM = '\033[2m'
    UNDERLINE = '\033[4m'
    RESET = '\033[0m'
    
    # 背景色
    BG_RED = '\033[101m'
    BG_GREEN = '\033[102m'
    BG_YELLOW = '\033[103m'
    BG_BLUE = '\033[104m'

def colored_print(text: str, color: str = Colors.RESET, bold: bool = False, end='\n'):
    """打印彩色文本"""
    prefix = Colors.BOLD if bold else ""
    print(f"{prefix}{color}{text}{Colors.RESET}", end=end)

def clear_line():
    """清除当前行"""
    print('\r' + ' ' * 80 + '\r', end='', flush=True)

def get_progress_bar(current: int, total: int, width: int = 20) -> str:
    """生成进度条"""
    if total == 0:
        return '[' + '=' * width + ']'
    percent = current / total
    filled = int(width * percent)
    bar = '█' * filled + '░' * (width - filled)
    return f'[{bar}]'

def get_status_icon(status: str) -> str:
    """获取状态图标"""
    icons = {
        'running': '⚡',
        'compiling': '🔨',
        'linking': '🔗',
        'testing': '🧪',
        'passed': '✅',
        'failed': '❌',
        'warning': '⚠️',
        'info': 'ℹ️'
    }
    return icons.get(status, '•')

def run_command(cmd: List[str], input_text: str = "", timeout: int = 60) -> Tuple[int, str, str]:
    """运行命令并返回退出码、标准输出和标准错误"""
    try:
        result = subprocess.run(
            cmd,
            input=input_text,
            capture_output=True,
            text=True,
            timeout=timeout
        )
        return result.returncode, result.stdout, result.stderr
    except subprocess.TimeoutExpired:
        return -1, "", f"Command timed out after {timeout} seconds"
    except Exception as e:
        return -1, "", str(e)

def compile_program(compiler_cmd: List[str], source_file: str, asm_file: str, verbose: bool = True, timeout: int = 60) -> bool:
    """编译程序生成汇编代码"""
    if verbose:
        print(f"\n{get_status_icon('compiling')} {Colors.CYAN}{Colors.BOLD}编译源文件{Colors.RESET}")
        print(f"   {Colors.DIM}命令: {' '.join(compiler_cmd + [source_file, '-o', asm_file])}{Colors.RESET}")
    
    # 生成汇编代码
    cmd = compiler_cmd + [source_file, '-o', asm_file]
    
    returncode, stdout, stderr = run_command(cmd, timeout=timeout)
    
    if returncode != 0:
        if verbose:
            print(f"   {get_status_icon('failed')} {Colors.RED}{Colors.BOLD}编译失败{Colors.RESET}")
            if stderr:
                print(f"   {Colors.RED}错误信息:{Colors.RESET}")
                for line in stderr.strip().split('\n'):
                    print(f"   {Colors.DIM}{line}{Colors.RESET}")
        return False
    
    # 检查汇编文件是否生成
    if not os.path.exists(asm_file):
        if verbose:
            print(f"   {get_status_icon('failed')} {Colors.RED}{Colors.BOLD}编译失败: 汇编文件未生成{Colors.RESET}")
        return False
    
    if verbose:
        print(f"   {get_status_icon('passed')} {Colors.GREEN}编译成功{Colors.RESET} → {Colors.DIM}{os.path.basename(asm_file)}{Colors.RESET}")
    return True

def assemble_and_link(asm_file: str, lib_path: str, output_file: str, debug: bool = False, verbose: bool = True) -> bool:
    """汇编并链接程序"""
    cmd = [
        'riscv64-linux-gnu-gcc',
        '-static',
        '-march=rv64gc'
    ]
    
    # 如果是调试模式，添加调试选项
    if debug:
        cmd.extend(['-g', '-O0'])  # 调试模式通常不优化
        if verbose:
            print(f"   {get_status_icon('info')} {Colors.YELLOW}调试模式: 添加 -g -O0 选项{Colors.RESET}")
    
    cmd.extend([asm_file, lib_path, '-o', output_file])
    
    if verbose:
        print(f"\n{get_status_icon('linking')} {Colors.BLUE}{Colors.BOLD}汇编链接{Colors.RESET}")
        print(f"   {Colors.DIM}命令: {' '.join(cmd)}{Colors.RESET}")
    
    returncode, stdout, stderr = run_command(cmd)
    
    if returncode != 0:
        if verbose:
            print(f"   {get_status_icon('failed')} {Colors.RED}{Colors.BOLD}链接失败{Colors.RESET}")
            if stderr:
                print(f"   {Colors.RED}错误信息:{Colors.RESET}")
                for line in stderr.strip().split('\n'):
                    print(f"   {Colors.DIM}{line}{Colors.RESET}")
        return False
    
    if verbose:
        print(f"   {get_status_icon('passed')} {Colors.GREEN}链接成功{Colors.RESET} → {Colors.DIM}{os.path.basename(output_file)}{Colors.RESET}")
    return True

def run_program(program_path: str, input_text: str = "", simulator: str = "qemu-riscv64", interactive: bool = False) -> Tuple[int, str, str]:
    """运行程序"""
    # 首先检查模拟器是否存在
    if not shutil.which(simulator):
        colored_print(f"错误: 模拟器 '{simulator}' 不存在或不在PATH中", Colors.RED, bold=True)
        return -1, "", f"Simulator '{simulator}' not found"
    
    cmd = [simulator, program_path]
    
    if interactive:
        # 交互式模式
        colored_print("进入交互模式 (输入完成后按Ctrl+D结束):", Colors.CYAN)
        try:
            # 直接使用subprocess.run与用户交互
            result = subprocess.run(cmd, text=True)
            return result.returncode, "", ""
        except Exception as e:
            return -1, "", str(e)
    else:
        # 非交互式模式，使用之前的方法
        return run_command(cmd, input_text)

def compare_output(expected: str, actual: str, show_diff: bool = True) -> bool:
    """比较输出结果"""
    if expected == actual:
        return True
    
    if show_diff:
        print(f"\n   {Colors.YELLOW}{Colors.BOLD}输出差异对比:{Colors.RESET}")
        
        # 使用系统diff命令
        with tempfile.NamedTemporaryFile(mode='w', suffix='.expected', delete=False) as expected_file:
            expected_file.write(expected)
            expected_file.flush()
            expected_path = expected_file.name
        
        with tempfile.NamedTemporaryFile(mode='w', suffix='.actual', delete=False) as actual_file:
            actual_file.write(actual)
            actual_file.flush()
            actual_path = actual_file.name
        
        try:
            # 使用diff -u命令生成unified diff
            diff_cmd = ['diff', '-u', '--label=期望输出', '--label=实际输出', expected_path, actual_path]
            returncode, stdout, stderr = run_command(diff_cmd, timeout=10)
            
            if stdout:
                for line in stdout.split('\n'):
                    if line.startswith('---'):
                        print(f"   {Colors.CYAN}{line}{Colors.RESET}")
                    elif line.startswith('+++'):
                        print(f"   {Colors.CYAN}{line}{Colors.RESET}")
                    elif line.startswith('@@'):
                        print(f"   {Colors.MAGENTA}{line}{Colors.RESET}")
                    elif line.startswith('-'):
                        print(f"   {Colors.RED}{line}{Colors.RESET}")
                    elif line.startswith('+'):
                        print(f"   {Colors.GREEN}{line}{Colors.RESET}")
                    elif line.startswith(' '):
                        print(f"   {line}")
                    elif line.strip():  # 非空行但不匹配上面的模式
                        print(f"   {line}")
        finally:
            # 清理临时文件
            try:
                os.unlink(expected_path)
                os.unlink(actual_path)
            except:
                pass
    
    return False

def generate_reference_output(source_file: str, input_text: str, verbose: bool = True) -> Tuple[str, int]:
    """使用clang/gcc生成参考输出
    
    Args:
        source_file: 源文件路径
        input_text: 输入内容
        verbose: 是否显示详细信息
    
    Returns:
        (stdout, returncode): 标准输出和返回值，失败时返回(None, None)
    """
    script_dir = get_script_dir()
    sylib_c = script_dir / 'lib' / 'sylib.c'
    sylib_h = script_dir / 'lib' / 'sylib.h'
    
    # 检查运行时库文件是否存在
    if not sylib_c.exists() or not sylib_h.exists():
        if verbose:
            print(f"   {get_status_icon('failed')} {Colors.RED}运行时库文件不存在{Colors.RESET}")
        return None, None
    
    # 优先使用clang，如果不存在则使用gcc
    compiler = None
    for cmd in ['clang', 'gcc']:
        if shutil.which(cmd):
            compiler = cmd
            break
    
    if not compiler:
        if verbose:
            print(f"   {get_status_icon('failed')} {Colors.RED}未找到clang或gcc编译器{Colors.RESET}")
        return None, None
    
    with tempfile.TemporaryDirectory() as temp_dir:
        # 读取源文件内容
        try:
            with open(source_file, 'r', encoding='utf-8') as f:
                source_content = f.read()
        except Exception as e:
            if verbose:
                print(f"   {get_status_icon('failed')} {Colors.RED}读取源文件失败: {e}{Colors.RESET}")
            return None, None
        
        # 创建临时C文件，添加sylib.h的include并复制源文件内容
        temp_c_file = os.path.join(temp_dir, 'temp_program.c')
        try:
            with open(temp_c_file, 'w', encoding='utf-8') as f:
                f.write('#include "sylib.h"\n')
                f.write(source_content)
        except Exception as e:
            if verbose:
                print(f"   {get_status_icon('failed')} {Colors.RED}创建临时C文件失败: {e}{Colors.RESET}")
            return None, None
        
        # 创建修改后的sylib.h，将变量定义改为extern声明
        temp_sylib_h = os.path.join(temp_dir, 'sylib.h')
        try:
            with open(sylib_h, 'r', encoding='utf-8') as f:
                sylib_h_content = f.read()
            
            # 修改sylib.h内容，将变量定义改为extern声明
            modified_sylib_h = sylib_h_content.replace(
                'struct timeval _sysy_start, _sysy_end;',
                'extern struct timeval _sysy_start, _sysy_end;'
            ).replace(
                'int _sysy_l1[_SYSY_N], _sysy_l2[_SYSY_N];',
                'extern int _sysy_l1[_SYSY_N], _sysy_l2[_SYSY_N];'
            ).replace(
                'int _sysy_h[_SYSY_N], _sysy_m[_SYSY_N], _sysy_s[_SYSY_N], _sysy_us[_SYSY_N];',
                'extern int _sysy_h[_SYSY_N], _sysy_m[_SYSY_N], _sysy_s[_SYSY_N], _sysy_us[_SYSY_N];'
            ).replace(
                'int _sysy_idx;',
                'extern int _sysy_idx;'
            )
            
            with open(temp_sylib_h, 'w', encoding='utf-8') as f:
                f.write(modified_sylib_h)
        except Exception as e:
            if verbose:
                print(f"   {get_status_icon('failed')} {Colors.RED}创建修改后的sylib.h失败: {e}{Colors.RESET}")
            return None, None
        
        # 一次编译链接所有文件
        temp_program = os.path.join(temp_dir, 'temp_program')
        compile_cmd = [compiler, temp_c_file, str(sylib_c), '-o', temp_program, '-lm']
        
        if verbose:
            print(f"   {get_status_icon('compiling')} {Colors.CYAN}使用{compiler}编译参考程序{Colors.RESET}")
            print(f"   {Colors.DIM}命令: {' '.join(compile_cmd)}{Colors.RESET}")
        
        returncode, stdout, stderr = run_command(compile_cmd, timeout=30)
        
        if returncode != 0:
            if verbose:
                print(f"   {get_status_icon('failed')} {Colors.RED}参考程序编译失败{Colors.RESET}")
                if stderr:
                    print(f"   {Colors.RED}错误信息:{Colors.RESET}")
                    for line in stderr.strip().split('\n')[:3]:  # 只显示前3行错误
                        print(f"   {Colors.DIM}{line}{Colors.RESET}")
            return None, None
        
        # 运行程序获取参考输出
        if verbose:
            print(f"   {get_status_icon('running')} {Colors.MAGENTA}运行参考程序{Colors.RESET}")
        
        ref_returncode, ref_stdout, ref_stderr = run_command([temp_program], input_text, timeout=30)
        
        if verbose:
            print(f"   {get_status_icon('info')} 参考程序退出码: {Colors.BOLD}{ref_returncode}{Colors.RESET}")
            if ref_stdout:
                print(f"   {Colors.BLUE}{Colors.BOLD}参考输出:{Colors.RESET}")
                for line in ref_stdout.rstrip().split('\n'):
                    print(f"   {line}")
        
        return ref_stdout.rstrip('\n') if ref_stdout else "", ref_returncode

def single_test(source_file: str, compiler_cmd: List[str], lib_path: str, 
                input_file: str = None, output_file: str = None, 
                simulator: str = "qemu-riscv64", mode: str = "run",
                verbose: bool = True, batch_mode: bool = False) -> Tuple[bool, str]:
    """单个文件测试
    Args:
        verbose: 是否显示详细输出，批量测试时可设为False
        batch_mode: 是否为批量测试模式，影响进度显示
    Returns:
        (bool, str): (测试是否通过, 失败原因)
    """
    # 如果没有指定输入输出文件，自动查找同目录下的.in和.out文件
    if input_file is None or output_file is None:
        source_path = Path(source_file)
        base_name = source_path.stem
        dir_path = source_path.parent
        
        if input_file is None:
            auto_in_file = dir_path / f"{base_name}.in"
            if auto_in_file.exists():
                input_file = str(auto_in_file)
                if verbose:
                    print(f"   {get_status_icon('info')} {Colors.CYAN}自动检测到输入文件{Colors.RESET}: {Colors.DIM}{input_file}{Colors.RESET}")
        
        if output_file is None:
            auto_out_file = dir_path / f"{base_name}.out"
            if auto_out_file.exists():
                output_file = str(auto_out_file)
                if verbose:
                    print(f"   {get_status_icon('info')} {Colors.CYAN}自动检测到输出文件{Colors.RESET}: {Colors.DIM}{output_file}{Colors.RESET}")
    # 创建临时目录
    with tempfile.TemporaryDirectory() as temp_dir:
        base_name = Path(source_file).stem
        asm_file = os.path.join(temp_dir, f"{base_name}.s")
        program_file = os.path.join(temp_dir, f"{base_name}")
        
        # 如果是批量测试模式，更新状态显示
        if batch_mode and not verbose:
            clear_line()
            status_msg = f"{get_status_icon('compiling')} {Colors.YELLOW}编译中{Colors.RESET}: {Colors.DIM}{base_name}{Colors.RESET}"
            print(status_msg, end='', flush=True)
        
        # 为调试模式添加 -g 选项
        actual_compiler_cmd = compiler_cmd.copy()
        if mode == "debug" and "-g" not in actual_compiler_cmd:
            actual_compiler_cmd.append("-g")
            if verbose:
                colored_print("调试模式: 添加 -g 选项生成调试信息", Colors.YELLOW)
        
        # 编译生成汇编文件
        if not compile_program(actual_compiler_cmd, source_file, asm_file, verbose=verbose):
            if verbose:
                colored_print(f"{base_name}: 失败 (编译错误)", Colors.RED)
            # 获取错误信息
            returncode, stdout, stderr = run_command(actual_compiler_cmd + [source_file, '-o', asm_file], timeout=60)
            if stderr:
                # 提取错误信息的前5行
                error_lines = stderr.strip().split('\n')
                error_msg = '\n'.join(error_lines[:5])
            else:
                error_msg = '编译失败'
            return False, error_msg
        
        # 汇编链接
        if batch_mode and not verbose:
            clear_line()
            status_msg = f"{get_status_icon('linking')} {Colors.BLUE}链接中{Colors.RESET}: {Colors.DIM}{base_name}{Colors.RESET}"
            print(status_msg, end='', flush=True)
        
        if not assemble_and_link(asm_file, lib_path, program_file, debug=(mode == "debug"), verbose=verbose):
            if verbose:
                colored_print(f"{base_name}: 失败 (链接错误)", Colors.RED)
            # 获取链接错误信息
            cmd = ['riscv64-linux-gnu-gcc', '-static', '-march=rv64gc']
            if mode == "debug":
                cmd.extend(['-g', '-O0'])
            cmd.extend([asm_file, lib_path, '-o', program_file])
            returncode, stdout, stderr = run_command(cmd)
            if stderr:
                # 提取错误信息的前5行
                error_lines = stderr.strip().split('\n')
                error_msg = '\n'.join(error_lines[:5])
            else:
                error_msg = '链接失败'
            return False, error_msg
        
        if mode == "debug":
            # 调试模式 - 复制可执行文件到当前目录以便调试
            debug_program = f"{base_name}_debug"
            shutil.copy2(program_file, debug_program)
            colored_print(f"调试程序已复制到: {debug_program}", Colors.MAGENTA)
            colored_print(f"启动调试器: riscv64-linux-gnu-gdb {debug_program}", Colors.MAGENTA, bold=True)
            colored_print("调试提示:", Colors.YELLOW)
            colored_print("  (gdb) target remote | qemu-riscv64 -g 1234 ./程序名", Colors.YELLOW)
            colored_print("  或者直接: (gdb) run", Colors.YELLOW)
            os.system(f"riscv64-linux-gnu-gdb {debug_program}")
            return True, ""
        
        # 准备输入
        input_text = ""
        interactive = False
        if input_file and os.path.exists(input_file):
            with open(input_file, 'r') as f:
                input_text = f.read()
        elif input_file is None and verbose and output_file is None:
            # 只有在没有指定输入文件和输出文件时，才使用交互式输入
            # 如果有输出文件，说明需要进行输出比较，不应该是交互式的
            interactive = True
        
        # 运行程序
        if batch_mode and not verbose:
            clear_line()
            status_msg = f"{get_status_icon('running')} {Colors.MAGENTA}运行中{Colors.RESET}: {Colors.DIM}{base_name}{Colors.RESET}"
            print(status_msg, end='', flush=True)
        
        if verbose:
            print(f"\n{get_status_icon('running')} {Colors.MAGENTA}{Colors.BOLD}运行程序{Colors.RESET}")
            print(f"   {Colors.DIM}命令: {simulator} {os.path.basename(program_file)}{Colors.RESET}")
        
        start_time = time.time()
        returncode, stdout, stderr = run_program(program_file, input_text, simulator, interactive)
        end_time = time.time()
        
        if verbose:
            print(f"   {get_status_icon('info')} 运行时间: {Colors.BOLD}{end_time - start_time:.3f}s{Colors.RESET}, 退出码: {Colors.BOLD}{returncode}{Colors.RESET}")
        
        if stderr and verbose:
            print(f"\n   {Colors.YELLOW}{Colors.BOLD}标准错误:{Colors.RESET}")
            for line in stderr.strip().split('\n'):
                print(f"   {Colors.DIM}{line}{Colors.RESET}")
        
        # 如果模拟器不存在，直接返回失败
        if returncode == -1 and f"not found" in stderr:
            if verbose:
                print(f"\n{get_status_icon('failed')} {Colors.RED}{Colors.BOLD}测试失败: 模拟器不存在{Colors.RESET}")
            return False, f"模拟器 {simulator} 不存在"
        
        if stdout and verbose:
            print(f"\n   {Colors.BLUE}{Colors.BOLD}标准输出:{Colors.RESET}")
            for line in stdout.rstrip().split('\n'):
                print(f"   {line}")
        
        # 检查输出 - 如果没有期望输出文件，使用clang/gcc生成参考输出
        expected_stdout = ""
        expected_returncode = None
        
        if output_file and os.path.exists(output_file):
            with open(output_file, 'r') as f:
                expected_content = f.read().splitlines()
            
            # 解析期望输出：最后一行是返回值，前面的是stdout
            if len(expected_content) > 0:
                expected_returncode = expected_content[-1].strip()
                if len(expected_content) > 1:
                    expected_stdout = "\n".join(expected_content[:-1])
                elif len(expected_content) == 1:
                    # 只有一行，说明没有stdout，只有返回值
                    expected_stdout = ""
        elif not interactive:
            # 如果没有期望输出文件，使用clang/gcc生成参考输出
            if verbose:
                print(f"\n   {get_status_icon('info')}  {Colors.YELLOW}未找到期望输出文件，使用 clang/gcc 生成参考输出{Colors.RESET}")
            
            expected_stdout, expected_returncode = generate_reference_output(source_file, input_text, verbose)
            if expected_stdout is None and expected_returncode is None:
                if verbose:
                    print(f"   {get_status_icon('warning')} {Colors.YELLOW}无法生成参考输出，跳过输出比较{Colors.RESET}")
                # 无法生成参考输出时，只检查程序是否成功运行
                if returncode != 0:
                    return False, f"程序运行失败 (退出码: {returncode})"
                else:
                    if verbose:
                        print(f"\n{get_status_icon('passed')} {Colors.GREEN}{Colors.BOLD}测试通过{Colors.RESET} ✓")
                    return True, ""
        
        # 如果有期望输出（来自文件或clang/gcc），进行比较
        if expected_stdout is not None or expected_returncode is not None:
            # 比较stdout - 注意处理空字符串情况
            stdout_matched = True
            if expected_stdout is not None:
                # 保持原始格式进行比较，但移除末尾的换行符以匹配期望格式
                actual_stdout = stdout.rstrip('\n') if stdout else ""
                stdout_matched = compare_output(expected_stdout, actual_stdout, show_diff=verbose)
            
            # 比较返回值
            returncode_matched = True
            if expected_returncode is not None:
                try:
                    expected_returncode_int = int(expected_returncode)
                    returncode_matched = returncode == expected_returncode_int
                except (ValueError, TypeError):
                    returncode_matched = str(returncode) == str(expected_returncode)
            
            if not stdout_matched or not returncode_matched:
                if verbose:
                    print(f"\n{get_status_icon('failed')} {Colors.RED}{Colors.BOLD}测试失败{Colors.RESET}")
                    if not stdout_matched:
                        print(f"   {Colors.RED}✗ 标准输出不匹配{Colors.RESET}")
                    if not returncode_matched:
                        print(f"   {Colors.RED}✗ 返回值不匹配{Colors.RESET}")
                        print(f"     期望: {Colors.CYAN}{expected_returncode}{Colors.RESET}")
                        print(f"     实际: {Colors.CYAN}{returncode}{Colors.RESET}")
                
                # 生成简洁的错误消息用于批量测试显示
                error_msg = ""
                if not stdout_matched:
                    error_msg = "输出不匹配"
                    # 如果输出较短，可以显示部分差异
                    actual_stdout = stdout.rstrip('\n') if stdout else ""
                    if expected_stdout and len(expected_stdout) < 50 and len(actual_stdout) < 50:
                        error_msg += f" (期望: {repr(expected_stdout[:30])}, 实际: {repr(actual_stdout[:30])})"
                if not returncode_matched:
                    if error_msg:
                        error_msg += "; "
                    error_msg += f"返回值不匹配 (期望: {expected_returncode}, 实际: {returncode})"
                return False, error_msg
        
        if verbose:
            print(f"\n{get_status_icon('passed')} {Colors.GREEN}{Colors.BOLD}测试通过{Colors.RESET} ✓")
        return True, ""

def batch_test(test_dir: str, compiler_cmd: List[str], lib_path: str, 
               simulator: str = "qemu-riscv64") -> Tuple[int, int]:
    """批量测试"""
    test_path = Path(test_dir)
    if not test_path.exists() or not test_path.is_dir():
        colored_print(f"测试目录不存在: {test_dir}", Colors.RED, bold=True)
        return 0, 0
    
    sy_files = sorted(list(test_path.glob("*.sy")))  # 按文件名排序
    if not sy_files:
        colored_print(f"目录中没有找到.sy文件: {test_dir}", Colors.RED, bold=True)
        return 0, 0
    
    # 显示测试开始信息
    print(f"\n{Colors.BLUE}{'━' * 60}{Colors.RESET}")
    print(f"{get_status_icon('testing')} {Colors.BLUE}{Colors.BOLD}开始批量测试{Colors.RESET}")
    print(f"   📁 测试目录: {Colors.DIM}{test_dir}{Colors.RESET}")
    print(f"   📄 测试文件: {Colors.BOLD}{len(sy_files)}{Colors.RESET} 个")
    print(f"{Colors.BLUE}{'━' * 60}{Colors.RESET}\n")
    
    passed = 0
    failed = 0
    
    for i, sy_file in enumerate(sy_files):
        base_name = sy_file.stem
        in_file = test_path / f"{base_name}.in"
        out_file = test_path / f"{base_name}.out"
        
        input_file = str(in_file) if in_file.exists() else None
        output_file = str(out_file) if out_file.exists() else None
        
        # 更新进度显示
        progress = i + 1
        progress_bar = get_progress_bar(i, len(sy_files))
        percent = (i / len(sy_files)) * 100
        
        # 测试前显示当前测试项
        clear_line()
        status_text = f"{get_status_icon('testing')} 测试中 {progress_bar} {percent:5.1f}% [{progress}/{len(sy_files)}] {Colors.CYAN}{base_name}{Colors.RESET}"
        print(status_text, end='', flush=True)
        
        # 执行测试
        test_result, error_msg = single_test(str(sy_file), compiler_cmd, lib_path, input_file, output_file, simulator, mode="run", verbose=False, batch_mode=True)
        
        # 显示测试结果
        clear_line()
        if test_result:
            result_icon = get_status_icon('passed')
            result_color = Colors.GREEN
            result_text = "PASS"
            passed += 1
            # 打印格式化的测试结果
            print(f"{result_icon} [{progress:3d}/{len(sy_files)}] {base_name:<40} {result_color}{Colors.BOLD}[{result_text}]{Colors.RESET}")
        else:
            result_icon = get_status_icon('failed')
            result_color = Colors.RED
            result_text = "FAIL"
            failed += 1
            # 打印格式化的测试结果
            print(f"{result_icon} [{progress:3d}/{len(sy_files)}] {base_name:<40} {result_color}{Colors.BOLD}[{result_text}]{Colors.RESET}")
            # 显示失败原因
            if error_msg:
                # 处理多行错误信息，每行都要正确缩进
                error_lines = error_msg.split('\n')
                for i, line in enumerate(error_lines[:5]):  # 最多显示5行
                    if i == 0:
                        print(f"    {Colors.GRAY}↳ {line}{Colors.RESET}")
                    else:
                        print(f"      {Colors.GRAY}{line}{Colors.RESET}")
    
    # 测试结果总结
    print()  # 空行
    total = passed + failed
    success_rate = passed / total * 100 if total > 0 else 0
    
    # 绘制分隔线
    print(f"\n{Colors.BLUE}{'━' * 60}{Colors.RESET}")
    
    # 标题
    title = "📊 测试结果总结"
    print(f"{Colors.BLUE}{Colors.BOLD}{title:^60}{Colors.RESET}")
    print(f"{Colors.BLUE}{'━' * 60}{Colors.RESET}")
    
    # 结果统计
    print(f"\n  {get_status_icon('passed')} 通过: {Colors.GREEN}{Colors.BOLD}{passed:>4}{Colors.RESET} 个测试")
    print(f"  {get_status_icon('failed')} 失败: {Colors.RED}{Colors.BOLD}{failed:>4}{Colors.RESET} 个测试")
    print(f"  📋 总计: {Colors.BLUE}{Colors.BOLD}{total:>4}{Colors.RESET} 个测试")
    
    # 成功率进度条
    print(f"\n  成功率: {Colors.BOLD}{success_rate:>5.1f}%{Colors.RESET}")
    progress_width = 40
    filled = int(progress_width * success_rate / 100)
    
    # 根据成功率选择颜色
    if success_rate >= 90:
        bar_color = Colors.GREEN
    elif success_rate >= 70:
        bar_color = Colors.YELLOW
    else:
        bar_color = Colors.RED
        
    bar = '█' * filled + '░' * (progress_width - filled)
    print(f"  {bar_color}[{bar}]{Colors.RESET}")
    
    print(f"\n{Colors.BLUE}{'━' * 60}{Colors.RESET}")
    
    return passed, failed

def benchmark_test(source_file: str, compiler_cmds: List[List[str]], lib_path: str, 
                   input_file: str = None, simulator: str = "qemu-riscv64", runs: int = 3):
    """性能对比测试"""
    colored_print(f"性能对比测试: {source_file}", Colors.MAGENTA, bold=True)
    colored_print(f"运行次数: {runs}", Colors.BLUE)
    colored_print(f"对比编译器数量: {len(compiler_cmds)}", Colors.BLUE)
    
    results = {}
    
    for i, compiler_cmd in enumerate(compiler_cmds):
        compiler_name = f"编译器{i+1}: {' '.join(compiler_cmd)}"
        colored_print(f"\n测试 {compiler_name}", Colors.CYAN, bold=True)
        
        times = []
        success_count = 0
        
        for run in range(runs):
            colored_print(f"第 {run+1} 次运行...", Colors.YELLOW)
            
            with tempfile.TemporaryDirectory() as temp_dir:
                base_name = Path(source_file).stem
                asm_file = os.path.join(temp_dir, f"{base_name}.s")
                program_file = os.path.join(temp_dir, f"{base_name}")
                
                if not compile_program(compiler_cmd, source_file, asm_file, verbose=False):
                    continue
                
                if not assemble_and_link(asm_file, lib_path, program_file, debug=False, verbose=False):
                    continue
                
                # 准备输入
                input_text = ""
                if input_file and os.path.exists(input_file):
                    with open(input_file, 'r') as f:
                        input_text = f.read()
                
                # 运行并计时
                start_time = time.time()
                returncode, stdout, stderr = run_program(program_file, input_text, simulator)
                end_time = time.time()
                
                if returncode == 0:
                    times.append(end_time - start_time)
                    success_count += 1
                    colored_print(f"  运行时间: {end_time - start_time:.3f}s", Colors.GREEN)
                else:
                    colored_print(f"  运行失败 (退出码: {returncode})", Colors.RED)
        
        if times:
            avg_time = sum(times) / len(times)
            min_time = min(times)
            max_time = max(times)
            
            results[compiler_name] = {
                'avg': avg_time,
                'min': min_time,
                'max': max_time,
                'success_rate': success_count / runs
            }
            
            colored_print(f"平均时间: {avg_time:.3f}s", Colors.GREEN)
            colored_print(f"最短时间: {min_time:.3f}s", Colors.GREEN)
            colored_print(f"最长时间: {max_time:.3f}s", Colors.GREEN)
            colored_print(f"成功率: {success_count}/{runs}", Colors.GREEN)
        else:
            colored_print("所有运行都失败了", Colors.RED, bold=True)
    
    # 显示对比结果
    if len(results) > 1:
        colored_print(f"\n{'='*60}", Colors.BLUE)
        colored_print("性能对比结果", Colors.BLUE, bold=True)
        colored_print(f"{'='*60}", Colors.BLUE)
        
        sorted_results = sorted(results.items(), key=lambda x: x[1]['avg'])
        
        for i, (name, result) in enumerate(sorted_results):
            rank_color = Colors.GREEN if i == 0 else Colors.YELLOW if i == 1 else Colors.RED
            colored_print(f"{i+1}. {name}", rank_color, bold=True)
            colored_print(f"   平均时间: {result['avg']:.3f}s", rank_color)
            colored_print(f"   成功率: {result['success_rate']:.1%}", rank_color)
            
            if i > 0:
                speedup = sorted_results[0][1]['avg'] / result['avg']
                colored_print(f"   相对最快: {speedup:.2f}x", rank_color)

def parse_compiler_args(args: List[str]) -> Tuple[List[str], Optional[str], Optional[str]]:
    """解析命令行参数，分离编译器参数和输入/输出文件参数"""
    input_file = None
    output_file = None
    compiler_args = []
    
    i = 0
    while i < len(args):
        arg = args[i]
        if arg == '--in' and i + 1 < len(args):
            input_file = args[i+1]
            i += 2
        elif arg == '--out' and i + 1 < len(args):
            output_file = args[i+1]
            i += 2
        elif arg == '--':
            # 剩余的都是编译器参数
            compiler_args.extend(args[i+1:])
            break
        else:
            compiler_args.append(arg)
            i += 1
    
    return compiler_args, input_file, output_file

def get_script_dir():
    """获取脚本所在的目录"""
    return Path(__file__).parent.absolute()

def main():
    script_dir = get_script_dir()
    default_lib = str(script_dir / 'lib' / 'libsysy_riscv.a')

    parser = argparse.ArgumentParser(description="编译器测试脚本", 
                                   add_help=False)  # 禁用默认的--help
    
    # 添加自定义帮助选项
    parser.add_argument('--help', action='help', help='显示帮助信息并退出')
    
    # 主参数
    parser.add_argument('command', choices=['run', 'debug', 'bench'], help='命令: run(运行), debug(调试), bench(性能测试)')
    parser.add_argument('source', help='源文件或目录')
    parser.add_argument('--lib', default=default_lib, help=f'静态库路径 (默认: {default_lib})')
    parser.add_argument('--simulator', default='qemu-riscv64', help='模拟器 (默认: qemu-riscv64)')
    parser.add_argument('--runs', type=int, default=3, help='benchmark运行次数 (默认: 3)')
    
    # 使用parse_known_args先解析已知参数
    args, remaining = parser.parse_known_args()
    
    # 解析剩余参数中的--in和--out
    compiler_args, input_file, output_file = parse_compiler_args(remaining)
    
    # 检查是否为目录（批量测试）
    if os.path.isdir(args.source):
        if args.command != 'run':
            colored_print(f"错误: {args.command}模式不支持批量运行", Colors.RED, bold=True)
            return 1
        
        passed, failed = batch_test(args.source, compiler_args, args.lib, args.simulator)
        return 0 if failed == 0 else 1
    
    # 单个文件测试
    if not os.path.exists(args.source):
        colored_print(f"错误: 源文件不存在: {args.source}", Colors.RED, bold=True)
        return 1
    
    if args.command == 'bench':
        # 对于bench模式，解析多个编译器命令
        # 使用 ";" 分隔不同的编译器命令
        compiler_cmds = []
        current_cmd = []
        
        for arg in compiler_args:
            if arg == ';':
                if current_cmd:
                    compiler_cmds.append(current_cmd)
                    current_cmd = []
            else:
                current_cmd.append(arg)
        
        if current_cmd:
            compiler_cmds.append(current_cmd)

        if len(compiler_cmds) < 2:
            colored_print("错误: bench模式需要至少两个编译器命令，用分号(;)分隔", Colors.RED, bold=True)
            colored_print("例如: python test.py bench program.sy --in input.txt -- clang -S -O0 ; clang -S -O2 ; gcc -S -O1", Colors.YELLOW)
            return 1
        
        benchmark_test(args.source, compiler_cmds, args.lib, 
                      input_file,
                      args.simulator,
                      args.runs)
    else:
        success, _ = single_test(args.source, compiler_args, args.lib, 
                            input_file,
                            output_file,
                            args.simulator,
                            args.command,
                            verbose=True)
        return 0 if success else 1

if __name__ == "__main__":
    sys.exit(main())