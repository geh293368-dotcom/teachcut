# Windows 构建与验证

这套脚本为 Win11 x64 提供统一入口。本地开发和 GitHub Windows CI 使用相同的原生依赖版本、测试命令和 cx_Freeze 打包流程。

## 首次准备

1. 安装 64 位 MSYS2 到默认目录 `C:\msys64`。
2. 在普通 PowerShell 中运行：

```powershell
.\scripts\build-windows.ps1 -Bootstrap
```

`-Bootstrap` 会根据 `-QtMajor` 安装 `windows-msys2-packages-qt5.txt` 或 `windows-msys2-packages-qt6.txt` 中的工具，并安装 `windows-requirements.txt` 中固定版本的 Python 依赖。Qt 6 是默认目标，Qt 5 作为可验证的回退路径保留。原生引擎源码已纳入仓库的 `native` 目录；`windows-build-lock.json` 保留其上游来源、导入提交和已验证工具链。

## 常用命令

完整增量构建、Python 测试、冻结打包和启动冒烟测试：

```powershell
.\scripts\build-windows.ps1
```

显式构建 Qt 5 回退版本：

```powershell
.\scripts\build-windows.ps1 -QtMajor 5
```

干净重建：

```powershell
.\scripts\build-windows.ps1 -Clean
```

只运行测试：

```powershell
.\scripts\test-windows.ps1
```

在带 NVIDIA 显卡的本机额外验证 NVDEC 与 D3D11：

```powershell
.\scripts\smoke-test-windows.ps1 -VerifyGpu
```

运行 4K CPU/NVDEC/D3D11 与 H.264/HEVC/AV1 NVENC 基准：

```powershell
.\scripts\benchmark-windows-gpu.ps1
```

也可以传入实际 4K 素材。报告保存在 `build\benchmarks`，机器基线结论记录在 `docs\performance\rtx4090-4k-baseline.md`。

验证实验性 D3D11 共享设备、GPU Frame 保留和按需回读：

```powershell
.\scripts\verify-d3d11-foundation.ps1
```

该验证只对独立 `FFmpegReader` 开启零拷贝实验开关；时间线、多轨、特效和正常应用预览仍默认使用已经验证的 CPU/QImage 回退路径。当前实现与 RTX 4090 实测见 [D3D11 零拷贝基础层验证](../docs/performance/d3d11-zero-copy-foundation.md)。

默认输出位置：

- Qt 6 原生安装树：`build\install-x64-qt6`
- Qt 5 原生安装树：`build\install-x64`
- cx_Freeze 程序目录：`build\exe.qt6` 或 `build\exe.qt5`
- 主程序：对应目录下的 `openshot-qt.exe`

## 可追溯版本包

生成完整 Windows 构建并保存版本包：

```powershell
.\scripts\package-windows.ps1
```

已经完成构建时，可以只打包现有冻结目录：

```powershell
.\scripts\package-windows.ps1 -SkipBuild
```

成品保存在 `artifacts\windows`，名称格式为 `TeachCut-Windows-Qt主版本-yyyyMMdd-HHmmss-提交号.zip`。每个压缩包都包含 `build-manifest.json`，旁边还有 SHA-256 校验文件；存在未提交修改时文件名会带 `-dirty`。日期方便按天查找，提交号负责精确对应源码，同一天多次打包也不会互相覆盖。

## GitHub Windows CI

`.github/workflows/windows-ci.yml` 会在代码推送和拉取请求时分别验证 Qt 5 与 Qt 6。它不需要网页手工构建；网页只负责显示状态、日志和下载版本包。每次成功运行都会上传一个保留 90 天的可追溯 Windows 包。CI 机器没有 RTX 4090，因此会验证 NVENC 编码器是否存在，但实际 NVDEC/D3D11 解码测试只在本机使用 `-VerifyGpu` 执行。
