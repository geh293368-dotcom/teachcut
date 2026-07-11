# Windows 构建与验证

这套脚本为 Win11 x64 提供统一入口。本地开发和 GitHub Windows CI 使用相同的原生依赖版本、测试命令和 cx_Freeze 打包流程。

## 首次准备

1. 安装 64 位 MSYS2 到默认目录 `C:\msys64`。
2. 在普通 PowerShell 中运行：

```powershell
.\scripts\build-windows.ps1 -Bootstrap
```

`-Bootstrap` 会安装 `windows-msys2-packages.txt` 中的工具，并安装 `windows-requirements.txt` 中固定版本的 Python 依赖。原生 OpenShot 仓库固定在 `windows-build-lock.json` 记录的提交。

## 常用命令

完整增量构建、400 项 Python 测试、冻结打包和启动冒烟测试：

```powershell
.\scripts\build-windows.ps1
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

默认输出位置：

- 原生安装树：`build\install-x64`
- cx_Freeze 程序目录：`build\exe.*`
- 主程序：`build\exe.*\openshot-qt.exe`

## GitHub Windows CI

`.github/workflows/windows-ci.yml` 会在代码推送和拉取请求时启动 GitHub 托管的 Windows 机器。它不需要网页手工构建；网页只负责显示状态和日志。CI 机器没有 RTX 4090，因此会验证 NVENC 编码器是否存在，但实际 NVDEC/D3D11 解码测试只在本机使用 `-VerifyGpu` 执行。
