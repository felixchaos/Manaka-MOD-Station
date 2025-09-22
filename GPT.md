这是一份GPT对话和生成内容的限制文档，在此工作区中，GPT的对话和生成内容必须遵守以下限制：

1. **工作区文件目录**：
   - 所有生成的代码内容必须保存在指定的工作区文件目录中。
   - 不得在工作区外部生成或存储任何内容。
   - 根目录所需创建的文件夹包含（若项目缺失相关文件夹，请帮我创建）：
     - `bin/`：存放编译后的可执行文件。
     - `database/CustomMissions/`：存放自定义任务的数据库json文件。
     - `database/Settings/`：存放配置和设置相关的数据库json文件。
     - `tools/`：存放各种GPT生成的工具脚本和实用程序。
     - `assets/`：存放图片、样式等资源文件。
     - `update/`：存放更新脚本和补丁文件。
     - `docs/`：存放文档和说明文件。
     - `src/`：存放源代码文件。
     - `GUI/`：存放图形用户界面相关的代码和资源。
     - 根目录存放的文件包含（若项目缺失相关文件，请帮我创建）：
        - `README.md`：项目说明文件。
        - `GPT.md`：GPT对话和生成内容的限制文档。
        - `main.py`：主程序入口文件。

2. **引擎规则**：
    - 底层使用C++编写，使用Python作为脚本语言。
    - 代码必须符合C++和Python的语法规范。
    - GUI应使用PYQT6框架进行开发，软件界面风格应接近win11的Microsoft Store。
    - 若需要添加新的功能模块或文件，请先确认工作区目录结构是否包含此功能类型的文件夹，若缺失相关文件夹或文件，请帮我创建。
    - 所有生成的代码必须经过严格测试，确保其功能正确且无错误。
    - 代码应具有良好的可读性和维护性，遵循最佳编程实践。
    - 生成的代码应包含GPT可读的注释，以便于理解和维护。
    - 代码应尽量简洁高效，避免冗余和重复。

3. **对话和生成内容的限制**：
    - 所有对话和生成内容必须与项目相关，避免偏离主题。
    - 不得生成任何与项目无关的内容。
    - 请不要反复询问我是否同意执行或是让我确认继续执行，只要我没有明确说不，你就可以继续执行。

4. **可执行程序和安装程序生成规则**：
    - 可执行程序请放在bin文件夹，msi安装程序请放在update/installer文件夹内。
    - 程序必须能够编译为可执行文件，并在Win10/11系统上运行。
    - 打包的程序必须是最小体积的，请只把调用的依赖打包进去，不要把整个Python环境打包进去。
    - 程序必须是独立的，不依赖于外部环境或配置。
    - 打包的程序不能弹出任何命令行窗口。
    - 程序应包含错误处理机制，确保在异常情况下能够正常运行或给出明确的错误提示。
    - 程序应包含日志记录功能，便于调试和问题排查。
    - 程序应包含自动更新功能，能够从指定的服务器下载并安装更新。
    - 需要包含卸载程序，便于用户卸载软件并清理注册表及其他相关文件。
    - 安装程序需要包含安装向导，指导用户完成安装过程。
    - 安装程序应支持自定义安装路径，允许用户选择安装目录。
    - 安装程序应包含必要的依赖项，确保软件能够正常运行。
    - 安装后的程序应具备跟工作区类似的文件目录结构。
    - 安装程序应包含许可证协议，用户必须同意后才能继续安装。
    - 安装程序应包含桌面快捷方式和开始菜单快捷方式的创建选项。
    - 需要安装时检查注册表，确保程序的唯一性，避免重复安装。
    - 打包结束后，请封存当前版本代码，并生成一个版本号，版本号格式为：主版本号.次版本号.修订号，例如1.0.0。只有在封存阶段结束后，才能在下一次生成中更新版本号。


5. **任务json规范**

以下规范基于工作区示例 `database/CustomMissions/park_stroll.json` 提炼，作为任务 JSON 的“建议版”标准，便于编辑器与引擎实现与校验。若引擎已有更严格的约束，以引擎实现为准。

- 文件位置与编码
    - 存放目录：`database/CustomMissions/`
    - 扩展名：`.json`
    - 编码：UTF-8（无 BOM）
    - 风格：2 或 4 空格缩进，键名使用小写蛇形或既有命名惯例保持一致

- 顶层结构（对象）
    - title: string（任务标题，必填）
    - listmission: boolean（是否在任务列表中展示，选填，默认 true）
    - addtitleinlist: boolean（是否在列表追加标题，选填）
    - addtitleinpanel: boolean（是否在信息面板显示标题，选填）
    - zones: Zone[]（任务地点集合，必填，至少 1 个）
    - subconditions: SubCondition[]（可复用的条件片段，选填）
    - checkpoints: Checkpoint[]（任务检查点/步骤流，必填，至少 1 个）

- Zone（地点）
    - id: string（唯一标识，必填）
    - areas: Area[]（区域集合，至少 1 个）

- Area（区域）
    - type: string（区域形状，当前示例为 "sphere"；建议枚举："sphere" 等）
    - stage: string（关卡/场景名，如 "Park"，必填）
    - x, y, z: number（世界坐标，必填）
    - r: number（半径，> 0，必填）
    - outlinehidden: boolean（是否隐藏轮廓，选填，默认 false）
    - compasshidden: boolean（是否隐藏指南针/导航，选填，默认 false）

- SubCondition（可复用条件）
    - id: string（唯一标识，必填）
    - condition: string（条件表达式，详见“表达式语法”，必填）

- Checkpoint（检查点/步骤）
    - id: string（可选标识。若存在，需在当前文件内唯一，便于跳转/随机选择）
    - zone: string（引用某个 Zone 的 id，必填）
    - travelcondition: ConditionBlock（行进条件，选填。用于进入该 checkpoint 前的移动/约束）
    - condition: ConditionBlock（在该区域内需要满足的条件/流程，选填）
    - nextcheckpoint: NextSelector（后续跳转选择，选填）

- ConditionBlock（条件块对象）
    - description: string（文本描述，用于 UI 提示，选填）
    - condition: string（条件表达式，详见“表达式语法”，选填）
    - duration: number（秒，>=0。满足条件需要持续的时间，选填）
    - reset: boolean（是否在失败/离开时重置计时和状态，选填，默认 false）
    - hideprogress: boolean（是否隐藏进度显示，选填，默认 false）
    - rp: number（积分/声望等，选填）
    - oncomplete: Action[]（完成后执行的动作列表，选填）
    - onviolatecondition: Action[]（违反 travelcondition 时执行的动作列表，选填，仅 travelcondition 可见）
    - faildescription: string（违反时 UI 提示，选填，仅 travelcondition 可见）

- NextSelector（后续跳转）
    - selectortype: string（跳转选择器类型，枚举：
        - "SpecificId"：跳转到指定 id（配合 id）
        - "RandomId"：在候选 id 集合中随机选择（配合 ids））
    - id: string（当 selectortype 为 SpecificId 时必填）
    - ids: string[]（当 selectortype 为 RandomId 时必填，数组非空）

- Action（动作对象，示例集）
    - 通用字段：
        - type: string（动作类型，必填）
    - 已见类型与附加字段（非穷尽，供实现参考）：
        - "unequipAllCosplay"
        - "equipCosplay"：parts: string[]
        - "unequipCosplay"：parts: string[]
        - "equipAdultToy"：parts: string[]
        - "unequipAdultToy"：parts: string[]
        - "setVibrator"：level: string（例如 "Off" / "High"）
        - "lockHandcuffs"：handcuffstype: string；attachtoobject: boolean；duration: number
        - "dropItem"：itemtype: string；stage: string；x,y,z: number；compasshidden?: boolean
        - "setCheckpoint"：selectortype: "SpecificId"；id: string

- 表达式语法（condition）
    - 基本形态：字符串，表达逻辑条件的组合。
    - AND 语义：使用方括号包裹的逗号分隔，如 "[A, B, !C]" 表示 A 且 B 且 非 C。
    - NOT：前缀 "!" 表示取反，例如 "!Naked"。
    - 分组：可使用括号进行分组，例如 "!(AdultToy_TimerHandcuff)"。
    - 复用：可通过 "SubCondition_<id>" 引用已定义的 SubCondition。
    - 令牌（Token）：引擎侧应定义并解析，如 Action_*、Owns*、Cosplay_*、AdultToy_*、NPCArea、Dashing 等。

- 规范性约束（建议校验）
    - 顶层：title 为非空；zones 与 checkpoints 至少各 1 个。
    - 唯一性：
        - zones[].id 全局唯一；
        - subconditions[].id 全局唯一；
        - checkpoints[].id 若存在需全局唯一。
    - 引用合法性：
        - checkpoint.zone 必须引用存在的 zone id；
        - nextcheckpoint（SpecificId/RandomId）引用的 id 必须存在于 checkpoints[].id 集合；
        - setCheckpoint 动作引用的 id 同上。
    - 数值范围：
        - areas[].r > 0；duration >= 0；坐标为有限数值。
    - 枚举与布尔：
        - areas[].type 建议受控枚举（至少包含 "sphere"）；
        - 布尔字段默认值：未提供时默认为 false（除非引擎另有约定）。
    - 结构互斥/必选：
        - nextcheckpoint 需提供与 selectortype 匹配的 id 或 ids。

- 最小示例骨架（非完整，仅示意）
    {
        "title": "Example Mission",
        "listmission": true,
        "addtitleinlist": true,
        "addtitleinpanel": true,
        "zones": [
            {
                "id": "start",
                "areas": [
                    { "type": "sphere", "stage": "Park", "x": 0, "y": 0, "z": 0, "r": 1, "outlinehidden": false, "compasshidden": false }
                ]
            }
        ],
        "subconditions": [
            { "id": "walkbasic", "condition": "[NPCArea,!Dashing]" }
        ],
        "checkpoints": [
            {
                "id": "step1",
                "zone": "start",
                "condition": {
                    "description": "在起点等待",
                    "condition": "SubCondition_walkbasic",
                    "duration": 5,
                    "oncomplete": [
                        { "type": "dropItem", "itemtype": "Note", "stage": "Park", "x": 0, "y": 0, "z": 1 }
                    ]
                },
                "nextcheckpoint": { "selectortype": "SpecificId", "id": "finish" }
            },
            {
                "id": "finish",
                "zone": "start",
                "condition": { "description": "任务完成", "duration": 1 }
            }
        ]
    }

6. **占位符**