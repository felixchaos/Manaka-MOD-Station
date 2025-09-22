打包与发布说明
=================

本文件说明如何在本地构建带“检查更新”功能的可执行程序/安装程序，先在本机安装并验证，然后再将安装程序作为 GitHub Release 上传。

先决条件
-------
- Windows 10/11
- Python 3.9+
- 已安装依赖：在仓库根目录运行：

    python -m pip install -r requirements.txt

- PyInstaller（一般由现有脚本处理）
- 可选：WiX Toolset（如果要构建 MSI）

本地构建（EXE）
-----------------
1. 确保 `src/update_checker.py` 已存在并且 `GUI/tabs/about_tab.py` 已集成检查更新逻辑（已完成）。
2. 运行现有打包脚本（工作区内已有 `tools/build_exe.ps1`）：

    powershell -ExecutionPolicy Bypass -File tools/build_exe.ps1 -Version 1.0.0

3. 脚本将输出到 `bin/dist/PracticeApp`（或 `bin/dist/Manaka-MOD-Station`，取决于脚本内部设置）。

本地生成 MSI（可选）
-------------------
1. 如果需要 MSI 安装程序，请安装 WiX Toolset（v3 或 v6，根据项目脚本）。
2. 运行项目中现有的 WiX 打包脚本（如 `update/installer/build_installer.ps1` 或 `update/installer/build_installer_v6.ps1`）：

    powershell -ExecutionPolicy Bypass -File update/installer/build_installer_v6.ps1 -Version 1.0.0 -DistDir bin/dist/PracticeApp

3. 输出将位于 `update/installer/` 下（例如 `PracticeApp-1.0.0.msi`）。注意：大型 MSI 文件不应提交到 Git；请使用 Releases 上传。

本地安装并验证
----------------
1. 在本地运行生成的安装程序（EXE 或 MSI），完成安装到测试目录。请先卸载先前版本（如果存在）。
2. 启动已安装的程序，打开“关于”页，点击“检查更新”。程序会访问 GitHub Releases 的 latest 接口：

    https://api.github.com/repos/felixchaos/Manaka-MOD-Station/releases/latest

   - 如果检测到新版，会弹出对话框，允许打开 Releases 页面或直接下载资产。
   - 本地测试时你可以先在仓库手动创建一个 Release（Draft 也可），并上传一个示例资产（例如 MSI），以验证下载链接是否工作。

3. 测试完成并确认没有问题后，可以删除本地测试的 Release 或继续使用该 Release 发布正式版本。

发布到 GitHub Releases（上传安装程序）
----------------------------------
1. 在 GitHub 仓库页面打开 Releases -> Draft a new release。
2. 填写版本号（例如 `1.0.0`）和 Release 描述。
3. 将构建出的安装程序文件（EXE/MSI）作为资产（attachments）上传到该 Release。对于较大的文件（>50MB）请务必通过 Release 上传，而不要直接提交到 Git 仓库。
4. 发布 Release（Publish release）。

自动更新说明
------------
- 程序的检查更新逻辑会查询 `releases/latest` 接口并比较 tag_name（或 name）与当前版本号（从程序界面读取）。
- 若要让程序能自动下载并静默安装（更复杂），需要：
  - 为安装程序设计一个自解压/自更新方案或 helper 更新器（示例：单独的 updater.exe，拥有管理员权限安装能力）。
  - 注意：自动替换正在运行的可执行文件涉及权限与进程控制，建议先实现“下载并提示用户手动运行安装程序”的方案。

安全和合规
------------
- 不要将敏感凭据（如 GitHub Token）硬编码到程序或脚本中。
- 对于自动更新或安装，需要签名证书时请使用代码签名证书来避免 Windows SmartScreen 警告。

问题与支持
-----------
如需我帮助你实际生成安装程序并上传 Release，请先在本地按上面步骤构建并安装一次，然后把构建输出目录（例如 `bin/dist/PracticeApp` 或生成的 MSI）路径告诉我，并确认可以在你的机器上安装与运行；我将在确认后协助你把安装程序上传到 GitHub Release（需要你提供 GitHub 权限或授权 gh 命令行）。
