# 输入、模板和官方脚本

## 输入约定

CSV/TSV 的第一行为非空且唯一的表头，后续为数值或空值。JSON 采用 `{"columns": ["Control", "Treatment"], "rows": [[1, 2], [3, null]]}`；不接受对象数组以免列顺序不确定。文本文件自动尝试 UTF-8 BOM、UTF-16 BOM、UTF-8、GB18030。

XLSX 第一行为表头，通过 `--sheet` 指定工作表。不指定时仅在只有一张非空工作表时自动选中。公式单元格必须有缓存数值；没有缓存时明确报错，先用 Excel 重新计算并保存。日期、百分比文字和带单位字符串需要先明确转换，不自动猜测。

Column 表每个 YColumn 有一个 Subcolumn；XY 表同时有数值 XColumn。重复 Y 子列、均值/误差子列、Grouped、Survival 和 Multiple variables 不属于处理器支持的输入布局。用户需要这些类型时，扩展明确的转换规则或使用匹配模板和专用导入流程，不强行转换为 column。

## 模板使用

模板的每条曲线、每组的图形绑定、配色、点大小、字体、误差条方式和统计分析由 Prism 文件决定。修改 `.pzfx` 时保留所有其他节点，尤其 `<Template>` 中的不透明配置。处理器仅替换目标表中的数据值和标题，剩余 Y 列清空；模板可画的数据集上限不随输入扩展。

本机内置模板是候选起点，不保证任意安装版本的表格数量和结构一致。运行 `inspect-template` 或将 `.pzt` 由 Prism 保存为 `.pzfx` 后检查；演示模板可能有固定范围、注释或多个图，需要实际预览。项目原有统计设置也会重算，不把继承的统计结果当成用户请求的科学结论。

## 脚本机制

处理器以无 BOM 的 UTF-8 和 CRLF 写出 `.pzc`。Prism 10.3.1 会把 UTF-8 BOM 当作第一条命令的字符，导致 `Unknown Command`。命令行使用 `prism.exe @"full-path.pzc"`（Python 的参数列表由 Windows 自动引用）。模板转换和绘图导出分别使用唯一的完成文件；在读取输出前同时检查完成标记与预期文件。不能只等待 exe 进程退出：启动器可能把脚本转交给已有实例。

核心脚本示例：

```text
CreateLog
Open "D:\run\prepared.pzfx"
RecalcAll
GoTo G 1
SetGraphTitle "实验结果"
SetAxisTitle Y "响应值"
ExportPDF "D:\run\figure.pdf" RGB
ExportPNG "D:\run\figure.png" 300
Save "D:\run\project.pzfx"
Close
OpenOutput "D:\run\finished.txt"
WText "done"
CloseOutput
```

需要结果表时，在选择图形前插入 `GoTo R <结果表序号>` 和 `ExportTable "D:\run\results.txt"`。`.txt` 为制表符文本，`.csv` 为逗号分隔文本。`RecalcAll` 重算项目已有分析，不能创建新的统计设置。处理器先更新完整模板的 XML 数据，再启动 Prism 执行这些命令；Python 不计算统计检验或绘制导出图。

百分号用于 Prism 脚本变量，标题和路径中的字面 `%` 需写成 `%%`；引号及换行被拒绝，避免破坏脚本。部分旧版本可能不能读取中文 UTF-8 脚本；根据真实错误改用其支持的编码或手动运行，勿直接宣称兼容。导出 SVG 应核对已安装 Prism 的支持情况。

## 官方依据

- [Prism scripts overview](https://www.graphpad.com/guides/prism/latest/user-guide/overview.htm)：脚本自动化以现成项目和模板为基础。
- [Windows launching](https://www.graphpad.com/guides/prism/latest/user-guide/launching_a_prism_script_from_outside_prism_%28windows%29.htm)：命令行与 `Prism.command` OLE 入口。
- [Opening and saving Prism files](https://www.graphpad.com/guides/prism/latest/user-guide/opening_and_saving_prism_files.htm)：`Open`、`Save`、`Close`。
- [Changing graphs](https://www.graphpad.com/guides/prism/latest/user-guide/changing_graphs.htm)：标题、配色和轴范围命令；字面百分号转义。
- [Exporting a graph or layout](https://www.graphpad.com/guides/prism/latest/user-guide/exporting_a_graph_or_layout.htm)：格式、DPI 和颜色模式。
- [Exporting data, results or info tables](https://www.graphpad.com/guides/prism/latest/user-guide/exporting_data_results_or_info_tables.htm)：`ExportTable` 导出原生结果表。
- [Special purpose commands](https://www.graphpad.com/guides/prism/latest/user-guide/special_purpose_commands.htm)：`RecalcAll`、日志等命令。
- 安装目录中的 `PrismXMLSchema.xml`：以本机版本的数据表结构为准。
