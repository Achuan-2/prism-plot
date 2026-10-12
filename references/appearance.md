# 原生图形美化与源项目格式

## 脚本可以调整的部分

`--color-scheme` 对应 Prism 的 `ApplyColorScheme`，使用本机已有方案名称。`Floral` 的前两组使用蓝色和紫色，适合两组示例；`Colorblind Safe` 在本机前两组实际为黑色和洋红色，不能按名称猜成蓝橙。`Waves` 等其他方案应检查原生预览后再交付。不给用户的模板强制覆盖配色；用户要求美化且未指定风格时可选择合适方案并说明。

标题用 `--title`，轴标题用 `--x-title/--y-title`；范围用 `--x-min/--x-max/--y-min/--y-max`，主刻度间距用 `--x-interval/--y-interval`。本机 Prism 10.3.1 中 `SetGraphTitle ""` 会回退为数据表标题，不能声称已经隐藏图题；使用明确短标题并检查输出。空 X 轴标题可以用于移除冗余的“Group”。

散点图可根据数据及误差条选择较紧凑的范围，并保留比较标注空间；示例的 80–170 只适合该组模拟数据，不能固定应用到其他实验。柱形图通常需要零基线，不能为了美观截断柱高。检查所有原始点和误差条是否完整显示。

导出 600 dpi PNG 与矢量 PDF 适合后续排版；分辨率不会改变图形的字体和线宽。原始观测值的汇总默认 Mean ± SEM，用户指定其他方式时遵从；这是原生图形设置，不是配色或 DPI 设置，必须使用匹配模板并核对实际误差条定义。检验始终由 Prism 重算，比较标注继续关联原生分析；显示 SEM 不改变检验类型。

## 需要模板保存的部分

字体、字号、轴线宽、散点大小、误差线宽、组名角度、图形物理尺寸及横纵比例等依赖模板。论文用图可选择较细的线条、统一 Arial 字体、水平组名及适当留白，但必须使用已经保存这些设置的真实 Prism 项目。用户要求全程脚本时，复用匹配模板；不要自行转向电脑控制，也不要编造不透明图形配置。`.prism` 的图形配置在本机仍含 `data.bin`，不能因为其为 ZIP 格式就假设所有样式都有可写 JSON 属性。

## .prism 项目

Prism 10 起引入 `.prism` 原生格式。本机 10.3.1 已实测脚本 `Save "...project.prism"`，其产物包含 `document.json`、数据 CSV、分析参数及结果 JSON、原生图形配置；并已实测通过 `Open` 作为模板再次运行。脚本手册的 Save 页面仍只列旧格式，不应据此否定已实测的新格式能力。

处理器默认 `--project-format prism`；需要兼容 Prism 9 或更早版本时选 `--project-format pzfx`。输入 `.prism` 先由 Prism 转存 `.pzfx`，填入数据后重新计算和保存为最终所选格式。保留完整项目，不重建或改写分析参数与图形二进制。

官方依据：[Changing graphs](https://www.graphpad.com/guides/prism/latest/user-guide/changing_graphs.htm)、[Prism color schemes](https://www.graphpad.com/support/faq/prism-color-schemes/)、[The PRISM file format](https://www.graphpad.com/guides/prism/latest/user-guide/prism_file_format.htm)。
