# 编译器测试脚本

用于测试RISC-V编译器的Python脚本，支持单个文件和批量测试，包含运行、调试和性能对比功能。

## 使用说明

### 基本用法

```bash
python test.py <command> <source> [options] [compiler_cmds...]
```

### 命令

- `run`: 运行测试
- `debug`: 调试模式（生成带调试信息的可执行文件）
- `bench`: 性能对比测试（需要提供多个编译器命令）

### 参数说明

- `source`: 源文件(.sy)或包含多个测试文件的目录
- `compiler_cmds`: 编译指令
- `--lib`: 指定静态库路径（默认使用脚本目录下的lib/libsysy_riscv.a）
- `--simulator`: 指定模拟器（默认qemu-riscv64）
- `--runs`: benchmark运行次数（默认3）
- `--in`: 指定输入文件 (不指定时从标准输入读取)
- `--out`: 指定期望输出文件

### 示例

1. 单个文件测试：

```bash
test.py run test.sy --in test.in --out test.out -- compiler -S
```

2. 调试模式：

```bash
test.py debug test.sy -- compiler -S
```

3. 批量测试目录中的所有文件：

```bash
test.py run tests -- compiler -S
```

4. 性能对比测试：

```bash
test.py bench test.sy --in test.in -- compiler -O0 ";" compiler -O2 ";" compiler -O3
```

## 依赖要求

- Python 3.x
- RISC-V工具链（riscv64-linux-gnu-gcc）
- QEMU模拟器（qemu-riscv64, qemu-user）

## 注意事项

1. 批量测试时，测试文件需要与对应的.in/.out文件同名
1. 期望输出文件的最后一行应为期望的返回值
1. 性能对比测试需要至少两个不同的编译器命令, 用分号分隔
1. 用riscv64-linux-gnu-gcc/clang编译`.sy`文件需要指定参数`-x c -Wno-implicit-function-declaration`; `starttime`, `stoptime`在库文件中的实际名称是`_sysy_starttime`和`_sysy_starttime`
