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
    RED = '\033[91m'
    GREEN = '\033[92m'
    YELLOW = '\033[93m'
    BLUE = '\033[94m'
    MAGENTA = '\033[95m'
    CYAN = '\033[96m'
    WHITE = '\033[97m'
    BOLD = '\033[1m'
    UNDERLINE = '\033[4m'
    RESET = '\033[0m'

def colored_print(text: str, color: str = Colors.RESET, bold: bool = False):
    """打印彩色文本"""
    prefix = Colors.BOLD if bold else ""
    print(f"{prefix}{color}{text}{Colors.RESET}")

def run_command(cmd: List[str], input_text: str = "", timeout: int = 30) -> Tuple[int, str, str]:
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
        return -1, "", "Command timed out"
    except Exception as e:
        return -1, "", str(e)

def compile_program(compiler_cmd: List[str], source_file: str, asm_file: str, verbose: bool = True) -> bool:
    """编译程序生成汇编代码"""
    if verbose:
        colored_print(f"编译: {' '.join(compiler_cmd + [source_file, '-o', asm_file])}", Colors.CYAN)
    
    # 生成汇编代码
    cmd = compiler_cmd + [source_file, '-o', asm_file]
    
    returncode, stdout, stderr = run_command(cmd)
    
    if returncode != 0:
        if verbose:
            colored_print(f"编译失败:", Colors.RED, bold=True)
            colored_print(stderr, Colors.RED)
        return False
    
    # 检查汇编文件是否生成
    if not os.path.exists(asm_file):
        if verbose:
            colored_print(f"编译失败: 汇编文件未生成 {asm_file}", Colors.RED, bold=True)
        return False
    
    if verbose:
        colored_print(f"编译成功，生成汇编文件: {asm_file}", Colors.GREEN)
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
            colored_print("汇编链接: 添加调试选项 -g -O0", Colors.YELLOW)
    
    cmd.extend([asm_file, lib_path, '-o', output_file])
    
    if verbose:
        colored_print(f"汇编链接: {' '.join(cmd)}", Colors.CYAN)
    
    returncode, stdout, stderr = run_command(cmd)
    
    if returncode != 0:
        if verbose:
            colored_print(f"汇编链接失败:", Colors.RED, bold=True)
            colored_print(stderr, Colors.RED)
        return False
    
    if verbose:
        colored_print(f"汇编链接成功: {output_file}", Colors.GREEN)
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
    expected = expected.strip()
    actual = actual.strip()
    
    if expected == actual:
        return True
    
    if show_diff:
        colored_print("输出不匹配:", Colors.RED, bold=True)
        colored_print("期望输出:", Colors.YELLOW)
        print(repr(expected))
        colored_print("实际输出:", Colors.YELLOW)
        print(repr(actual))
        
        # 显示详细差异
        colored_print("详细差异:", Colors.YELLOW)
        diff = difflib.unified_diff(
            expected.splitlines(keepends=True),
            actual.splitlines(keepends=True),
            fromfile='期望输出',
            tofile='实际输出'
        )
        for line in diff:
            if line.startswith('+'):
                colored_print(line.rstrip(), Colors.GREEN)
            elif line.startswith('-'):
                colored_print(line.rstrip(), Colors.RED)
            else:
                print(line.rstrip())
    
    return False

def single_test(source_file: str, compiler_cmd: List[str], lib_path: str, 
                input_file: str = None, output_file: str = None, 
                simulator: str = "qemu-riscv64", mode: str = "run",
                verbose: bool = True) -> bool:
    """单个文件测试
    Args:
        verbose: 是否显示详细输出，批量测试时可设为False
    """
    # 创建临时目录
    with tempfile.TemporaryDirectory() as temp_dir:
        base_name = Path(source_file).stem
        asm_file = os.path.join(temp_dir, f"{base_name}.s")
        program_file = os.path.join(temp_dir, f"{base_name}")
        
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
            return False
        
        # 汇编链接
        if not assemble_and_link(asm_file, lib_path, program_file, debug=(mode == "debug"), verbose=verbose):
            if verbose:
                colored_print(f"{base_name}: 失败 (链接错误)", Colors.RED)
            return False
        
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
            return True
        
        # 准备输入
        input_text = ""
        interactive = False
        if input_file and os.path.exists(input_file):
            with open(input_file, 'r') as f:
                input_text = f.read()
        elif input_file is None and verbose:
            # 没有指定输入文件，使用交互式输入
            interactive = True
        
        # 运行程序
        if verbose:
            colored_print(f"运行: {simulator} {program_file}", Colors.CYAN)
        start_time = time.time()
        returncode, stdout, stderr = run_program(program_file, input_text, simulator, interactive)
        end_time = time.time()
        
        if verbose:
            colored_print(f"运行时间: {end_time - start_time:.3f}s", Colors.BLUE)
            colored_print(f"退出码: {returncode}", Colors.BLUE)
        
        if stderr and verbose:
            colored_print("标准错误:", Colors.YELLOW)
            print(stderr)
        
        # 如果模拟器不存在，直接返回失败
        if returncode == -1 and f"not found" in stderr:
            if verbose:
                colored_print("测试失败: 模拟器不存在", Colors.RED, bold=True)
            return False
        
        if stdout and verbose:
            colored_print("标准输出:", Colors.YELLOW)
            print(stdout)
        
        # 检查输出
        if output_file and os.path.exists(output_file):
            with open(output_file, 'r') as f:
                expected_content = f.read().splitlines()
            
            # 解析期望输出：最后一行是返回值，前面的是stdout
            expected_stdout = ""
            expected_returncode = None
            
            if len(expected_content) > 0:
                expected_returncode = expected_content[-1]
                if len(expected_content) > 1:
                    expected_stdout = "\n".join(expected_content[:-1]) + "\n"
            
            # 比较stdout
            stdout_matched = True
            if expected_stdout:
                stdout_matched = compare_output(expected_stdout, stdout, show_diff=verbose)
            
            # 比较返回值
            returncode_matched = str(returncode) == str(expected_returncode)
            
            if not stdout_matched or not returncode_matched:
                if verbose:
                    colored_print("测试失败", Colors.RED, bold=True)
                    if not stdout_matched:
                        colored_print("标准输出不匹配", Colors.RED)
                    if not returncode_matched:
                        colored_print(f"返回值不匹配: 期望 {expected_returncode}, 实际 {returncode}", Colors.RED)
                return False
        
        if verbose:
            colored_print("测试通过", Colors.GREEN, bold=True)
        return True

def batch_test(test_dir: str, compiler_cmd: List[str], lib_path: str, 
               simulator: str = "qemu-riscv64") -> Tuple[int, int]:
    """批量测试"""
    test_path = Path(test_dir)
    if not test_path.exists() or not test_path.is_dir():
        colored_print(f"测试目录不存在: {test_dir}", Colors.RED, bold=True)
        return 0, 0
    
    sy_files = list(test_path.glob("*.sy"))
    if not sy_files:
        colored_print(f"目录中没有找到.sy文件: {test_dir}", Colors.RED, bold=True)
        return 0, 0
    
    colored_print(f"开始批量测试，共找到 {len(sy_files)} 个测试文件", Colors.BLUE, bold=True)
    
    passed = 0
    failed = 0
    
    for sy_file in sy_files:
        base_name = sy_file.stem
        in_file = test_path / f"{base_name}.in"
        out_file = test_path / f"{base_name}.out"
        
        input_file = str(in_file) if in_file.exists() else None
        output_file = str(out_file) if out_file.exists() else None
        
        if single_test(str(sy_file), compiler_cmd, lib_path, input_file, output_file, simulator, verbose=False):
            colored_print(f"{base_name}: 通过", Colors.GREEN)
            passed += 1
        else:
            colored_print(f"{base_name}: 失败", Colors.RED)
            failed += 1
    
    colored_print(f"\n{'='*60}", Colors.BLUE)
    colored_print(f"批量测试完成", Colors.BLUE, bold=True)
    colored_print(f"通过: {passed}", Colors.GREEN)
    colored_print(f"失败: {failed}", Colors.RED)
    colored_print(f"总计: {passed + failed}", Colors.BLUE)
    colored_print(f"{'='*60}", Colors.BLUE)
    
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
        success = single_test(args.source, compiler_args, args.lib, 
                            input_file,
                            output_file,
                            args.simulator,
                            args.command,
                            verbose=True)
        return 0 if success else 1

if __name__ == "__main__":
    sys.exit(main())