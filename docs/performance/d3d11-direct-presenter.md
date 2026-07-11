# D3D11 原生预览呈现器验证

验证日期：2026-07-11

机器：Windows 11、NVIDIA GeForce RTX 4090、Qt 6.11

素材：仓库基准脚本生成的 3840×2160 H.264 测试视频

## 本阶段结论

第二阶段 2.4 的最小直显链路已经跑通。`RendererBase` 收到 GPU-backed `Frame` 后，可以跳过 `GetImage()`，由 D3D11 VideoProcessor 直接完成 NV12 到 BGRA 的颜色转换、等比例缩放和黑边填充，随后输出到 Qt 原生窗口对应的 DXGI SwapChain。

实验路径由 `ENABLE_D3D11_ZERO_COPY` 和 `ENABLE_D3D11_DIRECT_PRESENT` 两个开关共同控制，两者都默认关闭。任意一步不满足或原生呈现失败时，会自动回到原来的 `QImage` 信号路径。

## 4K 直显验证

连续读取并呈现 60 帧的结果：

- 60/60 帧保持 GPU-only 存储。
- 60/60 帧通过 D3D11 SwapChain 呈现。
- 0 次 `QImage` 回退，0 次呈现失败。
- 解码阶段 0 次 GPU→CPU 下载、0 字节 CPU 图像复制、0 ms CPU 色彩转换。
- 不抓验证图时约 56 fps；完整解码、缩放和窗口呈现时间约 1.07 秒。
- 最后一帧额外执行一次“验证专用”的交换链后台缓冲回读，确认输出不是黑屏；生产直显路径不会执行这次回读。

验证抓图位于构建目录 `build/benchmarks/d3d11-presenter-last-frame.png`。抓图尺寸为 1920×1080，这是 1280×720 Qt 窗口在当前 150% Windows DPI 下的物理像素尺寸。

## 当前边界

这一步验证的是独立 `FFmpegReader → GPU Frame → D3D11 VideoProcessor → Qt HWND` 链路。正常 TeachCut 时间线仍会进行 CPU 合成，因此应用默认预览尚未进入零拷贝模式；Python 预览层的变换手柄、标注和 FPS 统计也还没有接入直接呈现信号。

下一步 2.5 应该把 GPU 路径接入最简单的单素材时间线，并为需要 CPU 特效、叠加或交互编辑的帧保留逐帧回退。

复现命令：

```powershell
.\scripts\verify-d3d11-presenter.ps1 -QtMajor 6 -Frames 60
```
