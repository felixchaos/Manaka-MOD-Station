# Manaka MOD Station

Manaka MOD Station 是一个面向 SecretFlasherManaka 的桌面 Mod 管理与任务编辑工具。当前版本已经从旧版 PyQt/Python 桌面壳重构为 Tauri v2 + React + TypeScript + Rust 实现，目标是把 Mod 管理、任务编辑、目录同步和应用更新收敛到一个真正可用的桌面工作台里。

## 本次大规模重构

这次重构不是换皮，而是把旧版 README 里提到的“占位页”和“后续逐步实现”真正落地为可运行的桌面应用。

| 维度 | 旧版 README | 当前版本 |
| --- | --- | --- |
| 桌面框架 | PyQt6 / Python | Tauri v2 / Rust + React 19 |
| 功能状态 | 以标签页框架和占位控件为主 | Mod 管理、编辑器、设置、更新已串通 |
| 任务创建 | 独立的新建页 | 集成到编辑器弹窗，可选空白或模板创建 |
| 页面切换 | 容易重载和丢状态 | 页面保持挂载，切换时保留缓存状态 |
| 编辑器能力 | 旧版单页编辑 | Monaco 编辑器 + 资源管理器 + 校验 + 内置帮助 |
| 默认数据目录 | 文档曾指向仓库内 database | 运行时统一解析到当前用户的 AppData |

## 当前功能

- 浏览本地 Mod 列表，支持按关卡分组、搜索、启用、禁用、删除和在编辑器中打开。
- 任务编辑器内置资源管理器、标签页、JSON 格式化、校验结果面板和开发帮助侧栏。
- 新建任务时可直接在编辑器中选择创建空白文件或带基础字段的模板文件。
- 设置页支持语言、主题、目录配置、分组记忆、删除确认和启动更新检查。
- 支持把游戏目录中的 CustomMissions 同步回本地任务库，并保持旧版冲突重命名行为。
- 支持 Windows 自定义标题栏拖动、最小化、最大化、关闭和应用内更新提示。
- About 页收拢版本、仓库、许可和法律说明。

## 默认路径与恢复默认

当前版本不再把开发机仓库路径当成默认目录。运行时默认目录统一根据当前用户环境解析：

- 应用数据目录：%APPDATA%/ManakaModStation
- 默认 Mod 库目录：%APPDATA%/ManakaModStation/database/CustomMissions
- 设置文件：%APPDATA%/ManakaModStation/database/Settings/settings.json
- Mod 状态文件：%APPDATA%/ManakaModStation/database/Settings/mods_state.json

恢复默认设置时：

- gameDir 会清空，等待用户重新指定游戏安装目录。
- modLibraryDir 会清空，随后回退到上面的默认 Mod 库目录。
- 默认目录解析不依赖开发仓库绝对路径。

这套策略与旧版 Python 实现保持一致，也能避免 per-machine 安装时把数据写回程序安装目录导致权限问题。

## 开发与构建

```bash
npm install
npm run build
npm run tauri dev
```

如需单独验证后端：

```bash
cd src-tauri
cargo check
cargo test
```

## 目录结构

- src/：React 前端界面、页面、组件、国际化与编辑器逻辑。
- src-tauri/：Tauri v2 配置、Rust 后端命令、桌面能力声明与打包配置。
- _legacy/：旧版 Python / PyQt 实现，保留作行为对照与迁移参考。
- public/：Vite 静态资源。
- database/：仓库内历史样本与开发参考数据，不再作为默认运行时数据目录。

## 技术栈

- Tauri v2
- Rust
- React 19
- TypeScript
- Fluent UI v9
- Monaco Editor
- i18next

## 运行说明

- 游戏目录不会自动猜测，首次使用请在设置页手动指定。
- 应用或替换任务后，需要回到游戏按 Alt + F9 重新加载自定义任务。
- 如果手动修改了 Mod 库目录，编辑器与 Mod 管理页会同时跟随新的目录。

## 仓库说明

- 旧版 README 中提到的独立“新建任务”页已经移除，相关流程已并入编辑器。
- 许可证见 LICENSE.txt。
