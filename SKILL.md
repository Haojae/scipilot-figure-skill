---
name: scipilot-figure-skill
description: >-
 SciPilot Skills 家族成员，负责科研数据可视化——但定位不是"画图工具"，
 而是"可视化顾问"。先做数据剖析（列类型/样本量/分布/异常值/分组结构/相关性），
 再结合用户的论证目标推荐图型，主动拦截科研画图的经典错误（小样本画均值柱掩盖
 分布、双 Y 轴、饼图、Y 轴不当截断、rainbow 色图、把分类点连成折线等），最后
 产出 Nature / Science / IEEE / Elsevier / PNAS / 中文核心期刊级别的成图。
 覆盖纯数据图：折线、柱状、散点、箱线 / 小提琴、热力图、误差棒、分布图（直方
 图 / KDE）、相关性矩阵 / 散点矩阵、多面板组合。技术栈 matplotlib + seaborn +
 SciencePlots（静态）+ plotly（交互）。中英文双语，中文模式自动配置 Noto Sans
 CJK / Source Han Sans / SimHei 并修复负号方框，支持中文期刊"宋体正文 +
 Times New Roman 数字"混排。默认色盲安全配色 + 冗余编码 + 灰度预览。出图后做
 "视觉自检闭环"：渲染 PNG 预览→程序自检缺字/文字裁切/刻度重叠→AI 读图复核遮盖
 与子图对齐→回改重渲，直到通过。
 当用户的任务涉及以下任何情况时主动触发：论文配图、科研画图、数据可视化、
 不知道用什么图、怎么展示数据、用什么图好、期刊投稿图、figure、出版级图表、
 matplotlib、seaborn、plotly、误差棒、显著性标注、色盲安全配色、矢量图导出、
 中文论文图表、多面板。**即使用户只是给一批数据问"这个怎么画"或"用什么图
 好"，也应使用本技能——本技能首要能力是"判断该用什么图"，其次才是绘制。**
 不做示意图、流程图、架构图。
---

# scipilot-figure-skill — 科研数据可视化顾问

> SciPilot Skills 家族成员 | 从数据剖析到出版级成图

## 概述

科研工作者最大的画图痛点往往不是"不会用 matplotlib"，而是"手上一堆数据，不知道该用什么图把结论讲清楚"。本技能的**首要能力是【思考与判断】**，其次才是【绘制】。

具体地——**永远先思考再画**：
1. 先理解数据再选图——拿到数据先做 EDA，用事实驱动图型选择
2. 先想清楚"这张图要论证什么"——同样数据，不同论点 = 不同图
3. 主动拦截科研画图的经典错误，而不是顺从
4. 维度太多就建议拆图，不硬塞

**只覆盖纯数据图**：折线、柱状、散点、箱线/小提琴、热力图、误差棒、分布图、相关性矩阵、多面板组合。**不做**示意图、流程图、架构图。

## 何时使用

- 用户给了一个 CSV / Excel / DataFrame 说"帮我画一下"或"用什么图好"
- 用户在写论文要插数据图
- 用户已有草图但说"达不到投稿要求"
- 用户提到 Nature / Science / IEEE 等具体期刊
- 用户问"中文论文 matplotlib 出方框怎么办"
- 用户提到误差棒、显著性、色盲、矢量导出、多面板

## 核心工作流（8 步）

**这是本技能与普通画图工具的根本区别——不能上来就画**。每一步缺位前一步的成果都不该执行。

### 第 0 步：理解任务

开画前**先搞清楚两件事**：

1. **这张图要论证什么观点 / 回答什么问题？** 同样数据，论点不同图就不同（详见 `references/chart_selection.md` 的"同一批数据、不同论点 → 不同图"小节）
2. **数据在哪里？长什么样？** 文件路径 / 字段含义 / 多少行 / 是否已经清洗

**如果用户没说清论证目标**，主动问一句："你这张图主要想说服读者相信什么？" 或从论文上下文推断并明确告诉用户你的假设。**不要默认"用户知道自己要什么"**。

### 第 1 步：剖析数据

调用 `scripts/profile_data.py`：

```bash
python scripts/profile_data.py data.csv --group group --group condition
```

输出包含：每列类型、样本量、缺失率、连续列的描述统计 + 偏度 + 异常值、分组样本量分布、相关性矩阵、初步图型建议。

不会读这份报告？查 `references/data_profiling.md`。

**重点核对**：
- 列类型识别对不对？（数字 ID 被认成 ordinal 是常见误判）
- 每组 n 是多少？小样本警告？
- 是否高度偏态？是否需要对数轴？

### 第 2 步：选图

**这是顾问职责的核心**。基于第 0、1 步的事实，查 `references/chart_selection.md` 的决策框架决定图型。要点：

- **给出推荐 + 简短理由 + 1-2 个备选**（不要只丢一个选择给用户）
- 如果数据维度过多（如分组组合 > 12）→ **明确建议拆图**，而不是硬塞
- 如果用户指定的图型**不适合数据**（如 n=5 要画均值柱）→ **善意指出问题并说明更好的选择**，让用户决定。详见下方"主动拦截"小节
- 如果数据特征意味着特殊处理（双峰分布、严重异常值、跨量级）→ 在选图建议里明确提及

### 第 3 步：查期刊规范

确定目标期刊后查 `references/journal_specs.md` 拿到：单/双栏宽（mm 与 inch）、字号、推荐字体、DPI、矢量格式偏好。

不知道目标期刊就问一句。"毕业论文 / 中文核心 / 英文 SCI / NeurIPS" 都对应不同规范。

### 第 4 步：配环境

```python
from setup_style import setup_style
setup_style(journal='nature', lang='en')             # 英文 Nature
setup_style(journal='general', lang='zh', serif_for_zh=True)   # 中文宋体混排
```

`SciencePlots` 装了自动用，没装回退到内置预设——不会因为缺它崩溃。

### 第 5 步：绘制

按 `references/plot_recipes.md` 对应章节的配方画。每节都有可直接复制的 Python 代码 + 常见坑。

画图时强制做到：
- `figsize=(目标宽, 目标高)` 单位英寸——直接定最终尺寸
- 用 `seaborn.color_palette('colorblind')` 或 Okabe-Ito + 冗余编码（不同线型/marker）
- 误差棒 / 阴影要在图注交代是 SD / SEM / 95% CI + n

### 第 6 步：自检闭环（机器 + AI 读图）

**三层都要过，缺一层都可能带病投稿**：

1. **语义层**：`references/viz_pitfalls.md` 18 条科研画图禁忌——图型/配色/误差是否踩坑
2. **形式层**：`references/publication_checklist.md` 形式合规（尺寸、DPI、字号、误差交代）
3. **视觉层（v2.1 新增）**：出图后**渲染 PNG → 程序自检 → AI 读图复核 → 回改**的闭环：
   - `visual_qa.render_preview(fig, 'figs/_preview.png')` 渲一张预览
   - `visual_qa.audit_layout(fig)` 程序抓**缺字乱码 / 文字裁切 / 刻度重叠**（确定性问题）
   - **用 `Read` 工具读这张 PNG**，对照 `references/visual_review.md` 的 8 项清单核对
     **图例压数据 / 子图标签对齐 / 配色灰度可分**（程序难判的感知问题）
   - 发现问题 → 按 `visual_review.md` 回改表改 → 重渲 → 再读，直到通过

任何一层不通过就回去改图。**矢量图的导出放在闭环通过之后**，把问题挡在投稿之前。

### 第 7 步：导出

```python
from export_figure import export_figure
export_figure(
    fig, basename='figs/fig1',
    formats=['pdf', 'svg', 'png'],
    size_inches=(3.5, 2.625),
    dpi=300,
    grayscale_preview=True,    # 自动出灰度版供色盲检查
)
```

最后跑一遍 `scripts/check_figure.py --strict` 机器审计。

## 选图速查（详细决策在 chart_selection.md）

| 数据形态 | 推荐首选 | **不该用** |
|---|---|---|
| 1 个连续 看分布 | 直方图 + KDE / 箱线 | 饼图 |
| 1 个分类 看占比 | 横向柱状（按值排序） | 饼图、3D 饼 |
| 1 分类 + 1 连续，n<10/组 | **stripplot / dot plot**（直接列点） | 均值柱（**严禁**） |
| 1 分类 + 1 连续，n≥10/组 | **箱线/小提琴 + stripplot 叠加** | 仅均值柱 |
| 2 连续 看关系 | 散点 + 回归 + r 值 | 折线（除非 x 有序连续） |
| 时间 / 剂量 vs 连续 | 折线 + 误差带 | 柱状 |
| 多变量相关（>3 列）| 相关性热力图 / pairplot | 平行坐标 |
| 矩阵数据 | 热力图（viridis/RdBu_r）| 3D 表面、rainbow 色图 |
| 构成占比 | 堆叠柱 / treemap | **饼图** |

完整决策树和"同一数据不同论点 → 不同图"对照表见 `chart_selection.md`。

## 五条硬性原则

### 原则 1：按最终尺寸出图，不二次缩放

`figsize` 直接设论文里实际尺寸（Nature 单栏 3.5 in、双栏 7.2 in；IEEE 单栏 3.5 in、双栏 7.16 in）。导出后**绝不在 Word / LaTeX 里再缩放**。

**为什么**：matplotlib 字号是绝对单位（pt），Word 里缩 50% 9pt 就变 4.5pt——投稿前自检直接打回。

### 原则 2：矢量优先

折线 / 柱状 / 散点 / 热力（数据网格除外）/ 误差棒 → PDF / SVG / EPS。显微图、照片才用 TIFF / PNG（300-600 DPI）。**绝对不用 JPEG**。

**为什么**：矢量任意缩放不糊，文字仍可选；JPEG 数据图边缘有压缩 artifact，期刊 PDF 检查器直接打回。

### 原则 3：配色对色盲友好

默认 `seaborn.color_palette('colorblind')` 或 Okabe-Ito。**同一张图不同类别加冗余编码**（线型 / marker）。出图前 `export_figure(..., grayscale_preview=True)` 看灰度版能否区分。

**为什么**：约 8% 男性、0.5% 女性色觉异常。审稿人里有这群人，全靠红绿区分的图对他们传达力归零。

### 原则 4：字号在最终尺寸下可读

正文标签和刻度数字 7-9 pt，最小字 **≥ 6 pt**。

**为什么**：审稿编辑会按 mm 打印查字号；<6 pt 不可读直接退回。

### 原则 5：误差必有交代

只要有误差棒 / 阴影区间 / 箱线——**图注必须写清**：
- 误差类型（SD / SEM / 95% CI / IQR）
- 样本量 n
- 显著性检验方法 + 校正（如 Bonferroni）
- 显著性符号定义（`* p<0.05` 等）

**为什么**：SD 和 SEM 差一个 √n。混淆 = 结论反转 = 退稿。

## 主动拦截（顾问职责）

发现用户的需求会触发以下错误时，**先说明再给替代方案，不要默默照做**。完整 15 条详见 `references/viz_pitfalls.md`。

| 错误 | 后果 | 替代方案 |
|---|---|---|
| n<10/组 还想画均值柱 | 掩盖分布、掩盖 n、审稿人怀疑 | 箱线 + stripplot；或直接 stripplot |
| 双 Y 轴显示无关变量 | 视觉上的相关 / 分歧是作图者捏造的 | 拆成上下子图共享 x；或标准化共轴 |
| 用饼图展示占比 | 人眼判角度差长度 3 倍 | 横向柱状（按值排序） |
| 3D 柱 / 3D 饼 | 视角扭曲所有数值 | 2D 柱、热力图 |
| 比例图 Y 轴不从 0 起 | 误导小差异看起来很大 | 从 0 起或用 log；或加明显断裂标记 |
| 颜色映射连续值无 colorbar | 读者不知道深浅对应数值 | 必加 colorbar + 标 label/单位 |
| x 是分类却用折线连均值 | 暗示不存在的连续关系 | 散点 / 点图 / 柱状 |
| 一图塞 5 个论点 | 没论点 | 拆图，一张图一个核心结论 |
| rainbow / jet 色图 | 感知不均匀、造假峰 | viridis / magma / RdBu_r |

**拦截话术示例**：

> 你要的"3 组各 5 个样本的均值柱状图"会触发 P1（均值柱掩盖分布）：n=5 太小，柱状会让审稿人怀疑你藏了什么。我建议改成**箱线 + stripplot 叠加每个点**，5 个点直接可见、分布形态一目了然。要按原方案画吗？

尊重用户最终决定，但**留下明确的劝阻记录**。

## 中文支持

中文字体检查应核对实际解析的字体文件与字重。能显示汉字仍可能因 Thin/Light 字体而难读；应在最终展示宽度下检查标签，必要时换用可用的常规字重字体。字号按用途和画布调整，不设统一增大规则。

中文 matplotlib 出方框的根本原因：默认字体（DejaVu Sans 等）不含 CJK 字符表。`setup_style(lang='zh')` 自动做两件事：

1. 按优先级查中文字体：`Noto Sans CJK SC` > `Source Han Sans SC` > `SimHei` > `Microsoft YaHei`
2. 修负号方框：`plt.rcParams['axes.unicode_minus'] = False`

找不到任何 CJK 字体会抛清晰的安装提示（不会让你画完发现是方框）。

**中文期刊的"宋体 + 数字 Times New Roman"混排**：传 `serif_for_zh=True`，优先选 Noto Serif CJK / Source Han Serif / SimSun。

详见 `references/journal_specs.md` 末尾的字体安装小节。

## 脚本说明

| 脚本 | 干啥 | 主入口 |
|---|---|---|
| `profile_data.py` | EDA：列类型 / 样本量 / 分布 / 异常 / 相关 / 初步图型建议 | `profile_data(source, group_cols)` |
| `setup_style.py` | 期刊预设 + CJK 字体配置 + SciencePlots 包装 | `setup_style(journal, lang, use_sciplots, serif_for_zh)` |
| `export_figure.py` | 多格式 + 按最终尺寸 + 灰度预览 | `export_figure(fig, basename, formats, dpi, size_inches, grayscale_preview)` |
| `check_figure.py` | 文件合规自检（格式 / DPI / 字体嵌入） | `check_figure(path, min_dpi, target_inches)` |
| `layout_tools.py` | 子图标签对齐 + constrained/tight 兜底理版 | `add_panel_labels(fig, style)` / `finalize_figure(fig)` |
| `visual_qa.py` | 渲染 PNG 预览 + 程序自检（缺字 / 裁切 / 刻度重叠） | `render_preview(fig, out)` / `audit_layout(fig)` |

## 参考文档

`references/` 下七份文档——**按需 view，不要一次全读**：

| 文档 | 何时读 |
|---|---|
| `chart_selection.md` | **每次选图必读**——决策框架、不同论点→不同图 |
| `data_profiling.md` | 读不懂 `profile_data.py` 输出 |
| `viz_pitfalls.md` | 自检前必读——18 条避坑清单（含 P16-18 排版/渲染坑） |
| `journal_specs.md` | 不确定目标期刊的栏宽/字号/DPI/字体 |
| `plot_recipes.md` | 9 类图各自的完整配方 + 适用场景 |
| `publication_checklist.md` | 投稿前最后过形式合规清单 |
| `visual_review.md` | 出图后视觉自检——AI 读图 8 项清单 + 回改循环协议 |

每份开头都有目录——先查目录定位，再 view 对应小节。

## 常见任务示例

### 任务 A：用户只丢一个 CSV 说"帮我把这个画成论文图"

**思考-绘制工作流的范例**：

1. **第 0 步**：问用户"你这份数据主要想说服读者相信什么？"——是组间差异？时间趋势？变量关系？
2. **第 1 步**：跑 `python scripts/profile_data.py data.csv` 得到剖析报告
3. **第 2 步**：读报告里"列类型 + 样本量 + 分组结构"，结合用户的论证目标查 `chart_selection.md` 决策。**主动给出推荐 + 理由 + 1-2 备选**
4. **拿到用户确认后**进入第 3-7 步：查期刊规范、配环境、画、自检、导出

不要跳过任何一步。

### 任务 B：用户说"我想用柱状图展示三组各 5 个样本的均值"

**主动拦截的范例**：

```
你要的"三组各 5 个样本均值柱状图"会触发科研画图的经典 P1 错误
（参见 viz_pitfalls.md）——n=5 太小，柱状图的高度 + 一根误差棒无法
告诉读者数据真实分布。审稿人看到很可能要求"show individual data points"。

我建议改成 **箱线图 + stripplot 叠加每个点**：5 个点直接可见，
不掩盖任何信息，反而更可信。代码也只多一行。

要按原方案画，还是改成箱线+stripplot？
```

如果用户坚持要柱状，那也照做——但**至少**强制叠加 stripplot 显示每个点。

### 任务 C：多面板组合图

用户："给我画一个 Figure 1：4 个 panel，分别是 PCA、loss 曲线、混淆矩阵、生存曲线。"

流程：
1. 确认目标期刊（决定整张图 7.2 in 还是 7.16 in；Nature `a/b/c` vs IEEE `(a)(b)(c)`）
2. 各 panel 独立画，**保证字号、配色、坐标尺度统一**（同一变量在 4 个 panel 里同色）
3. 用 `plt.subplots(2, 2, figsize=(7.2, 5.4))` 组合（`setup_style` 已默认开 constrained_layout）
4. `layout_tools.finalize_figure(fig)` 理顺版面，再 `add_panel_labels(fig, style='nature')` 打 a/b/c/d——**统一 figure 坐标自动横竖对齐**，不要手摆 `ax.text`（易错位，见 viz_pitfalls P18；IEEE 用 `style='ieee'` → (a)(b)(c)）
5. **视觉自检闭环**：`render_preview` 渲 PNG → `audit_layout` 程序自检 → `Read` 读图核对子图对齐/遮盖 → 回改 → 通过后再导出 + 灰度检查

详细配方见 `plot_recipes.md` 第 9 节。

### 任务 D：带显著性标注的统计图

用户："3 组数据，箱线图加显著性标注。"

流程：
1. profile 确认 n（n<10 → 必须叠 stripplot）
2. 跑统计检验（**用户必须告知**用了什么检验，是否多重比较校正）
3. 画箱线 + stripplot
4. 用 `matplotlib.lines.Line2D` 或 `statannotations` 在组之间画显著性桥
5. **图注必须写**：误差类型 / n / 检验方法 / 校正 / 符号含义

配方见 `plot_recipes.md` 第 4 节。

## 依赖

```
matplotlib>=3.7
seaborn>=0.13
plotly>=5.18
pandas>=2.0
numpy>=1.24
scipy>=1.10            # profile_data 的偏度计算用到
Pillow>=10.0           # check_figure / grayscale preview
SciencePlots>=2.1      # 可选；装了样式更接近期刊
pypdf>=4.0             # 可选；check_figure 字体嵌入检查
kaleido>=0.2.1         # 可选；plotly 导出 PDF/PNG
```

可选依赖缺失时本技能仍能跑——会优雅降级并提示。
