# 原生 t 检验、显著性与项目保存

这些步骤已在本机 Prism 10.3.1 中完成实测。界面位置和默认值可能随版本及用户设置变化，按实际控件文字操作，不沿用截图坐标。统计设置必须符合本次数据的设计，示例中的 Welch 双侧检验不是所有数据的固定选择。

## 已有模板时的脚本工作流

匹配项目内已有原生分析及关联显著性标注时，直接用处理器填入新数据，执行 `Open` → `RecalcAll` → `GoTo R N` → `ExportTable` → `GoTo G N` → 原生图形导出 → `Save`。无需界面操作。`--results-index` 与 `--graph-index` 分别选择结果表和图形，不保证二者序号相同；多表项目还需核对 `--table-index`。

检验设计由模板确定，脚本不改变配对关系、Welch/等方差选项或单双侧。更换检验类型需要对应模板，不能沿用不匹配的设置。图形汇总默认 Mean ± SEM，用户明确指定其他方式时遵从；沿用项目前必须确认图形实际为 Mean with SEM。此前工作区示例的 Mean with SD 模板不符合新的默认值，不能直接当作 SEM 模板或只改图注；应在 Prism 中配置并另存匹配模板，保留已有结果文件。用更换数据后原生结果表和图内星号一起更新作为重算证据，避免仅导出旧结果。

## 首次创建两组原始值模板

1. 在 Column 数据表中核对两组原始数值、样本数、列名及缺测。选择数据表，Analyze → Column analyses → t tests (and nonparametric tests)，勾选需要比较的两组。
2. 对明确的独立、参数检验示例，Experimental Design 选择 Unpaired、Yes. Use parametric test；需要 Welch 时选择 Unpaired t test with Welch's correction. Do not assume equal SDs。配对数据不能使用这个配置。
3. Options 核对 One-tailed / Two-tailed、置信水平、差值方向及 p 值显示方式。不要为了改变星号调整检验；不更改用户全局默认值。可选的 Estimation Plot 是 Prism 原生的均值差与置信区间图。
4. 运行后读取 Prism Results，记录检验名称、p 值或原生显示的界限、p value summary、单双侧、t、df、n。不要把 `<0.0001` 报成从 Prism 读到的精确 p 值，也不要把同页的 F 检验 p 值当成 t 检验结果。
5. 从原始数据表 Create New Graph，选择 Column → Individual values → Scatter plot，默认将 Plot 设置为 Mean with SEM；用户明确指定 SD、置信区间或其他汇总方式时按指定值设置。保留全部观测点，均值与 SEM 由 Prism 根据原始数据计算。模板可能默认 Median 或 Mean with SD，必须检查；不要将中位线称作均值线，或把 SD 称作 SEM。新图可避免演示模板的旧统计表和浮动备注进入最终导出。
6. 在该图 Insert → Pairwise Comparisons。双击比较标注打开 Format Pairwise Comparisons，在 Comparisons on Graph 核对选中的 Prism 分析及比较对象，在 Appearance 选择 Asterisks 或 Numeric values 和括号样式。显著性由所选分析自动产生，不手填星号。
7. 在 Prism 中完成标题、Y 单位、坐标范围、误差条及排版后保存完整项目。Save As 可选 `.prism` 或 older format `.pzfx`；保留所有原生配置，不能以独立的数据 XML 重建它们。对 `.pzfx`，现有处理器可完整保留配置、填数据并让 Prism 重算。
8. 使用 Prism 导出 PDF、PNG 等所需格式。处理器的 `--graph-index` 必须对应最终图：新建图或 Estimation Plot 会改变图序号，不默认 G1 就是待交付图。在本次交付文件夹中直接保存一份最终源项目，与未经修改的原生导出图并列；脚本和中间文件放入 `_work`，不要在外层再创建项目副本。

## 验收证据

首次配置模板时，在界面确认 Results 中存在指定检验及结果，最终 Graphs 图存在，并从 Format Pairwise Comparisons 确认标注关联的是该分析和组别。后续使用已验收的模板时，可通过脚本原生导出的结果表、PNG 预览、源项目数据核对和执行日志完成验收，无需每次重新打开界面。核对原始值，检查导出图全部样本、汇总定义、误差条、星号、标题和单位。执行日志与完成标记证明原生导出成功；仅复制已有 PDF、仅写出数据表或只保存图形都不能证明原生检验和完整保存。

清单记录原生检验名称及设置、实际图序号、Prism 结果摘要和原生导出路径。如果没有执行或不能核对某一步，保留证据并说明具体未完成部分，不以外部统计或图片后处理补齐。
