# OpenShot 视频编辑器

OpenShot Video Editor 是一款屡获殊荣的免费开源视频编辑器，支持 Linux、Mac 和 Windows，致力于为全球用户提供高质量的视频编辑和动画制作解决方案。

## 构建状态

[![openshot-qt CI Build](https://github.com/OpenShot/openshot-qt/actions/workflows/ci.yml/badge.svg)](https://github.com/OpenShot/openshot-qt/actions/workflows/ci.yml)
[![TeachCut Windows CI](https://github.com/geh293368-dotcom/teachcut/actions/workflows/windows-ci.yml/badge.svg)](https://github.com/geh293368-dotcom/teachcut/actions/workflows/windows-ci.yml)
[![libopenshot CI Build](https://github.com/OpenShot/libopenshot/actions/workflows/ci.yml/badge.svg)](https://github.com/OpenShot/libopenshot/actions/workflows/ci.yml)
[![libopenshot-audio CI Build](https://github.com/OpenShot/libopenshot-audio/actions/workflows/ci.yml/badge.svg)](https://github.com/OpenShot/libopenshot-audio/actions/workflows/ci.yml)
![Discord](https://img.shields.io/discord/1143390791507644496?style=flat)

## 功能特性

* 跨平台支持（Linux、Mac 和 Windows）
* 支持多种视频、音频和图像格式（基于 FFmpeg）
* 强大的基于曲线的关键帧动画
* 桌面集成（支持拖放）
* 不限数量的轨道和图层
* 支持剪辑尺寸调整、缩放、修剪、吸附、旋转和切割
* 带实时预览的视频转场
* 合成、图像叠加和水印
* 标题模板、标题制作和字幕
* 支持 2D 动画（图像序列）
* 3D 动画标题和特效
* 良好支持 SVG，可用于创建和添加矢量标题与演职员表
* 滚动式影片演职员表
* 高级时间线（支持拖放、滚动、平移、缩放和吸附）
* 精确到帧（可逐帧浏览视频）
* 剪辑时间映射和速度调整（慢放、快放、正放、倒放等）
* 音频混合与编辑
* 数字视频特效，包括亮度、伽马、色相、灰度、色度键等多种效果
* 实验性硬件编码与解码支持（VA-API、NVDEC、D3D9、D3D11、VTB）
* 导入和导出广泛支持的格式（EDL、XML）
* 使用多种编解码器和格式渲染视频（基于 FFmpeg）

## 快速开始

开始使用 OpenShot 最快捷的方式是下载预构建安装程序。在[下载页面](https://www.openshot.org/download/)中，点击 **Daily Builds** 按钮即可查看最新的实验性构建版本。仓库每次产生新提交时，都会创建相应的每日构建版本。

## 教程

你可以观看官方[分步视频教程](https://www.youtube.com/watch?list=PLymupH2aoNQNezYzv2lhSwvoyZgLp1Q0T&v=1k-ISfd-YBE)，或阅读官方[用户指南](https://www.openshot.org/user-guide/)。

## 开发者

你是否有兴趣更深入地参与 OpenShot 的开发？你可以构建令人兴奋的新功能、修复缺陷、结识朋友，并成为社区英雄！请阅读[分步说明](https://github.com/OpenShot/openshot-qt/wiki/Become-a-Developer)，了解如何获取源代码、配置依赖项并构建 OpenShot。

### Windows 开发构建

TeachCut 分支提供 Win11 x64 一键构建入口，统一完成原生库编译、Python 测试、cx_Freeze 打包和程序启动检查：

```powershell
.\scripts\build-windows.ps1
```

`libopenshot` 与 `libopenshot-audio` 已纳入 `native` 目录，应用与底层引擎可以在同一次提交中修改和回滚。需要保留按日期与提交号命名的成品时，运行：

```powershell
.\scripts\package-windows.ps1
```

首次配置、版本打包和 RTX 显卡验证方法见 [Windows 构建与验证](scripts/README-windows.md)。

Win11 + RTX 4090 的 4K 解码/导出实测结果见 [4K 性能基线](docs/performance/rtx4090-4k-baseline.md)，D3D11 共享设备、GPU Frame 和按需回读的阶段结果见 [D3D11 零拷贝基础层验证](docs/performance/d3d11-zero-copy-foundation.md)。导出窗口另外提供 `YouTube (4K NVIDIA)`、`MP4 (HEVC NVIDIA)` 和实验性的 `MP4 (AV1 NVIDIA)` 预设。

## 文档

可以使用 Sphinx 生成精美的 HTML 文档。

```sh
cd doc
make html
```

你可以在 [openshot.org/user-guide](https://www.openshot.org/user-guide/) 在线查看最新发布版本的文档。

## 报告缺陷

请使用我们网站上的官方[缺陷报告](https://www.openshot.org/issues/new/)功能提交问题。该功能会引导你完成缺陷报告流程，并帮助你为 OpenShot 社区创建高质量的问题报告。

你也可以直接在 GitHub 上提交新问题：

https://github.com/OpenShot/openshot-qt/issues

## 翻译

将 OpenShot 翻译成其他语言非常简单！请阅读[分步说明](https://github.com/OpenShot/openshot-qt/wiki/Become-a-Translator)，或者登录 Launchpad 开始翻译。你只需要一个网页浏览器。

* 应用程序翻译：https://translations.launchpad.net/openshot/2.0/+translations
* 网站翻译：https://translations.launchpad.net/openshot/website/+pots/django

## 依赖项

虽然安装程序更易于使用，但如果你必须从源代码构建，以下提示可以提供帮助。

OpenShot 使用 Python（3.0 及以上版本）编写，因此无需编译即可运行。不过，为确保 OpenShot 正常运行，请安装以下依赖项：

* Python 3.0+（http://www.python.org）
* 用于 Qt5 或 Qt6 的 PyQt / PySide 绑定（https://www.riverbankcomputing.com/software/pyqt/ 和 https://pyside.org/）
* libopenshot：OpenShot 视频库（https://github.com/OpenShot/libopenshot）
* libopenshot-audio：OpenShot 音频库（https://github.com/OpenShot/libopenshot-audio）
* FFmpeg 或 Libav（http://www.ffmpeg.org/ 或 http://libav.org/）
* GCC 构建工具（Windows 上也可使用 MinGW）

软件包维护者和开发者可以使用 `OPENSHOT_QT_API=auto|pyqt6|pyside6|pyqt5` 选择 Python Qt 绑定。构建 `libopenshot` 时，其 Qt 主版本需通过 `-DUSE_QT6=AUTO|ON|OFF` 单独选择。

## 启动

如果系统中已安装 `libopenshot`，可以使用以下命令从命令行运行 OpenShot。请根据安装位置或 openshot-qt 仓库位置调整路径：

```sh
cd [openshot-qt folder]
python3 src/launch.py
```

如果使用从源代码构建但尚未安装的 `libopenshot`，请将 `PYTHONPATH` 设置为已编译 Python 绑定所在的位置。例如：

```sh
cd [libopenshot folder]
cmake -B build -S . [options]
cmake --build build

cd [openshot-qt folder]
PYTHONPATH=[libopenshot folder]/build/bindings/python \
python3 src/launch.py
```

## 相关网站

- https://www.openshot.org/（官方网站和博客）
- https://github.com/OpenShot/openshot-qt（源代码和问题跟踪）
- https://github.com/OpenShot/libopenshot-audio（音频库源代码）
- https://github.com/OpenShot/libopenshot（视频库源代码）
- https://launchpad.net/openshot/

### 版权与许可证

版权所有 © 2008–2022 OpenShot Studios, LLC。本文件是 OpenShot Video Editor（https://www.openshot.org）的一部分。OpenShot 是一个开源项目，致力于为全球用户提供高质量的视频编辑和动画制作解决方案。

OpenShot Video Editor 是自由软件：你可以根据自由软件基金会发布的 GNU 通用公共许可证条款重新发布和修改本软件，可选择该许可证第 3 版或任何后续版本。

发布 OpenShot Video Editor 的目的是希望它能发挥作用，但不提供任何担保；甚至不提供适销性或特定用途适用性的默示担保。详情请参阅 GNU 通用公共许可证。

你应当已经随 OpenShot Library 收到一份 GNU 通用公共许可证；如果没有，请访问 <http://www.gnu.org/licenses/>。

<!-- 已于 2026-07-11 验证仓库同步。 -->
