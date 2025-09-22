# Practice 项目

本项目提供一个使用 PyQt6 构建的图形界面框架，包含以下标签页：
- Mod管理
- 任务Json编辑
- 新任务Json创建
- 设置
- 关于

目前功能为界面结构与占位控件，便于后续逐步实现。

## 运行方式
1. 确认已安装 Python 3.9+
2. 安装依赖（在 VS Code 任务或手动执行）
3. 运行 main.py

## 目录结构
- bin/ 可执行文件输出
- database/ 数据存储
  - CustomMissions/ 自定义任务Json
  - Settings/ 配置文件（settings.json）
- GUI/ 图形界面代码
- src/ 预留源代码目录
- tools/ 工具脚本
- update/ 更新脚本
- assets/ 资源文件
- docs/ 文档

## 说明
- 界面风格将尽量贴近 Win11 Microsoft Store 风格。
- 后续会补充日志、自动更新、安装包等功能。
