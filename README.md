# Manaka MOD Station 项目

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
- Mod管理页：显示已安装的Mod列表，支持启用/禁用Mod。
- 任务Json编辑页：加载并编辑现有任务Json文件。
- 新任务Json创建页：提供模板和向导，帮助用户创建新的任务Json文件。
- 设置页：配置应用程序选项，如主题、语言等。
- 关于页：显示应用程序信息和开发者联系方式。

