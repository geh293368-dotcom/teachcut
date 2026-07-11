# 界面现代化与 Qt 迁移基线

TeachCut 的界面现代化遵循“保留功能、控件与 Dock 布局，只替换呈现层”的边界。Qt 6 是 Windows 默认目标，Qt 5 保留为可构建、可测试的回退路径。

## Qt 构建目标

- 默认：PyQt6 + Qt 6，输出到 `build/install-x64-qt6` 和 `build/exe.qt6`。
- 回退：PyQt5 + Qt 5，输出到 `build/install-x64` 和 `build/exe.qt5`。
- 两个目标使用独立的原生构建、安装和冻结目录，避免 DLL、插件和 Python 绑定互相污染。

```powershell
# Qt 6 完整构建、测试、冻结与启动检查
.\scripts\build-windows.ps1

# Qt 5 回退验证
.\scripts\build-windows.ps1 -QtMajor 5
```

## TeachCut Modern 主题

`TeachCut Modern` 复用现有菜单、工具栏、Dock、动作和时间线交互，仅调整以下呈现属性：

- Windows 中文字体使用 `Microsoft YaHei UI 9pt`；
- 中性石墨色表面与单一蓝色强调色；
- 统一菜单、标签、输入框、按钮、滚动条和焦点状态；
- 时间线使用对应的现代绘制主题；
- 不改变控件顺序、功能入口和项目数据。

原有 `Cosmic Dusk`、`Humanity: Dark` 和 `Retro` 主题继续保留，可在首选项中切换。

## SVG 与 PNG 资源策略

主题工具栏通过统一的 `BaseTheme.create_icon()` 加载资源：

- `.svg` 继续走显式高 DPI 矢量渲染；
- PNG 及 Qt 支持的其他栅格格式交给 `QIcon` 加载；
- PNG 可使用 `name.png`、`name@2x.png` 配套命名；
- 16–24 px 的功能性符号优先 SVG；复杂插画、AI 生成图和特效缩略图优先 PNG。

首版现代主题继续复用已有 SVG 功能图标，后续可以逐项替换为 PNG，而无需修改工具栏业务代码。

## 验证基线

- Qt 6 原生引擎构建成功；
- Qt 5 与 Qt 6 均运行同一套 Python 测试；
- cx_Freeze 为每个绑定生成独立插件路径；
- 冻结成品通过命令行版本检查和 GUI 启动冒烟检查；
- 视觉截图保存在 `artifacts/ui-teachcut-modern-workspace-v2.png`（构建产物，不提交 Git）。

### 截图缩放规则

界面截图验证必须使用固定窗口尺寸，并在启动截图进程前设置
`OPENSHOT_UI_SCALE=1.0`。该进程级覆盖项优先于用户首选项中的
`ui-scale`，因此不会改写用户日常使用的 120%、125% 等缩放设置。

```powershell
$env:OPENSHOT_UI_SCALE = "1.0"
.\build\exe.qt6\openshot-qt.exe
```

这里固定的是软件内部 UI 缩放，不是 Windows 显示设置。Windows 的物理显示
DPI 可以保持不变；若要做像素级图片差异比较，还应在同一台验证机器、同一
显示器缩放和同一窗口尺寸下生成基线图。
