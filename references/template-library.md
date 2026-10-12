# 常用原生模板库

模板由本机 Prism 10.3.1 保存和验收。运行 `scripts/prism_plot.py profiles` 获取实际目录、SHA256、表序号和原生参数。登记文件是 `assets/analysis-profiles.json`、`assets/graph-profiles.json`；不要凭文件名猜测分析或误差条。

| 参数 | 数据结构 | 图形与统计 |
| --- | --- | --- |
| `--analysis welch-t` | 两列独立样本，允许不等样本数 | 双侧 Welch t，原始点 + Mean ± SEM，关联括号 |
| `--analysis welch-t --error-bars sd` | 同上 | 双侧 Welch t，Mean ± SD |
| `--analysis student-t` | 两列独立样本，等方差假设由用户明确 | 双侧普通 t，Mean ± SEM，关联括号 |
| `--analysis paired-t` | 两列，每行同一对象 | 双侧配对 t，Mean ± SEM，关联括号 |
| `--analysis mann-whitney` | 两列独立样本 | 双侧 Mann–Whitney，Mean ± SEM，关联括号 |
| `--analysis wilcoxon` | 两列，每行同一对象 | 双侧配对符号秩检验，Mean ± SEM，关联括号 |
| `--analysis anova-tukey` | 当前为三组独立样本模板 | 普通单因素 ANOVA + Tukey 全部组间比较，Mean ± SEM，关联括号 |
| `--graph scatter-sem` | 2–3 列原始观测值 | 原始散点 + Mean ± SEM，仅绘图 |
| `--graph bar-sem` | 2–3 列原始观测值 | 柱状 + 原始点 + Mean ± SEM，仅绘图 |
| `--graph box-minmax` | 2–3 列原始观测值 | 中位数、四分位箱体，须线 Min-to-Max，仅绘图 |
| `--graph paired-lines` | 两列完整配对 | 每行点与点连线，不含统计检验或误差条 |
| `--graph xy-line` | 第一列数值 X，随后 1–8 列 Y | 各 Y 列一条曲线；显示 X 标题和按列名关联的图例；单值曲线不生成 SEM，不拟合 |

非参数检验不意味着检验均值；其默认 Mean ± SEM 是用户要求的图形展示，检验含义仍按 Prism 原生方法说明。用户指定中位数等方式时需要相应图形配置，不把均值图改称中位数。箱线图属于明确选择的展示方式，不继承 SEM 默认值。

统计参数是独立选择：`--analysis` 不推断配对、正态性、等方差或研究设计。配对数据单边缺测会报错，不能通过各列分别去空值后重新拼接。仅绘图的 `--graph` 不自动进行检验；不与 `--analysis` 混用。需要“配对连线 + 检验”等组合时，选择/建立包含该组合的匹配模板。

全部库模板的交付目标均为 D1/G1，统计模板为 R1。普通 ANOVA 的 `statistics.txt` 导出 V1 总体检验，`comparisons.txt` 导出 V2 Tukey 调整后比较；两个文件均来自 Prism。`.prism` 源项目保留原生完整结果，不依赖文本导出。

## 文件格式和维护

当前库使用 `.pzfx` 作为可替换数据的运行模板。只编辑 XML 的 Table、YColumn/Subcolumn 和合法标题，保留 Template 原生配置。PZFX 的图形与分析配置不是普通 XML，不能用 XML 标签自行生成分析或改 SEM/SD。

全部库模板及旧版兼容 `.prism` 模板的数据表数值列统一显示 3 位小数；PZFX 的数值列 `Decimals` 设置为 `3`，XY 模板同时设置 XColumn、XAdvancedColumn 和 YColumn。仅改变显示精度，原始数值、原生分析参数、p 值格式及图形坐标格式保持原样。更新后由 Prism 打开、重算并保存核对副本，确认显示设置被保留，再更新目录中的 SHA256。

Prism 10+ 的 `.prism` 是容器格式：数据为 CSV，分析参数和结果为 JSON。因此“AI 编辑数据”适合 PZFX，“AI 检查或修改原生统计参数”往往更适合 PRISM。图形样式仍由本机实际结构及 Prism 能力决定，不直接篡改不透明 data.bin。

本次已在项目副本中更改 `experimentalDesign` 为 `UNPAIRED_T_TEST`、`PAIRED_T_TEST`、`MANN_WHITNEY_TEST`、`WILCOXON_TEST`，随后让 Prism `RecalcAll`、保存并核对实际结果，验证了本机版本中的这些路径。此能力不属于 `.pzc` 分析创建命令，也不代表任意 JSON 参数或其他版本都兼容。维护新组合时，保留其他参数，先验证 Prism 重算后的方法、样本数、结果和标注，再登记模板；不要修改缓存结果来代替重算。

PZFX 目录通过 SHA256 固定已验证的原生配置；原生参数快照记录在分析目录中。完成运行后读取真正由 Prism 保存的 `.prism`，再次检查实际 experimentalDesign、双侧选项或 ANOVA 的 Tukey/ALL_VS_ALL 设置。模板变化后先重新验收再更新 SHA，不绕过校验。保留旧 `.prism` 模板以兼容历史引用，新目录选择 PZFX。

## 运行与预览

```powershell
uv run --with openpyxl python "<skill>/scripts/prism_plot.py" plot --input "D:\data.xlsx" --analysis paired-t --output "D:\figures"
uv run python "<skill>/scripts/prism_plot.py" plot --input "D:\three-groups.csv" --analysis anova-tukey --output "D:\figures"
uv run python "<skill>/scripts/prism_plot.py" plot --input "D:\three-groups.csv" --graph bar-sem --output "D:\figures"
uv run python "<skill>/scripts/prism_plot.py" plot --input "D:\timecourse.csv" --graph xy-line --x-title "Time (s)" --y-title "Signal" --output "D:\figures"
```

坐标范围由真实模板控制，替换数据后必须核对。AI 可以依据原始值选择 `--y-min/--y-max/--y-interval` 等显示参数，统计与 SEM 仍由 Prism 计算。注意显著性括号位置、未用组位、过长标签、XY 曲线辨识和图例；不以运行成功代替预览。

Windows 默认使用可执行文件 `@script.pzc`。CLI 退出而无完成标记时先检查日志与实例状态，可显式选择官方 OLE 接口 `--backend ole`；注册组件对应本机安装版本，不能保证与 `--prism-exe` 路径一致。两种方式均是原生脚本执行，不是坐标点击。OLE 初始化失败或超时如实报告；不关闭用户窗口或在不明原因时连续创建实例。

官方参考：[PZFX 与 PRISM](https://www.graphpad.com/guides/prism/latest/user-guide/pzf_vs__pzfx_file_format.htm)、[PRISM 内部格式](https://www.graphpad.com/guides/prism/latest/user-guide/prism_file_format.htm)、[项目与结果子页导航](https://www.graphpad.com/guides/prism/latest/user-guide/general_commands.htm)。
