中文 · [English](README.en.md)

# 🏗️ Kangmaojian Skills

#### 我在建筑施工图内审工作中反复使用并通过匿名回归测试的 Agent Skills

这里公开两套彼此分离的建筑工作流。一套负责从图纸事实和合法取得的本地规范中形成新的建筑专业审查结论；另一套只负责忠实整理审查人已经形成的意见、证据和 Word 成果。

仓库只包含 Skill 指令、脚本、匿名测试和已脱敏范本，不包含规范全文、项目图纸、客户资料、真实审查报告或私人知识索引。

## 📋 目录

| 名字 | 一句话 | 相关链接 |
|---|---|---|
| 🏢 [building-review（建筑施工图审查）](#-building-review建筑施工图审查) | 逐张盘点建筑图纸，以事实台账、规范证据和质量门禁形成新的建筑专业审查意见 | [SKILL.md](building-review/SKILL.md) · [工作流程图](media/building-review-workflow.svg) |
| 📝 [review-opinion-delivery（审查意见整理）](#-review-opinion-delivery审查意见整理) | 忠实整理审查人已有意见、图纸证据和 Word 交付，不新增技术结论 | [SKILL.md](review-opinion-delivery/SKILL.md) · [工作流程图](media/review-opinion-delivery-workflow.svg) |

## 📦 安装方式

在 Codex、Claude Code 或其他支持 Agent Skills 的工具中，直接说：

```text
帮我安装这个 skill：https://github.com/jack20040828/kangmaojian-skills/tree/main/building-review
```

或：

```text
帮我安装这个 skill：https://github.com/jack20040828/kangmaojian-skills/tree/main/review-opinion-delivery
```

如果使用 Codex 官方安装脚本，可分别指定一级子目录：

```powershell
python install-skill-from-github.py --repo jack20040828/kangmaojian-skills --path building-review
python install-skill-from-github.py --repo jack20040828/kangmaojian-skills --path review-opinion-delivery
```

安装后请新开一个会话，让 Agent 重新发现 Skill。

## ✨ Skills

### 🏢 building-review（建筑施工图审查）

> 先把每张图纸看见了什么说清楚，再谈它是否符合要求。

用于总图、建筑单体和建筑专项施工图技术审查。新建工作区使用 schema v1.7，由 AI 独立完成图纸清点、事实提取、专项路由、知识检索、规范核查、跨图检查、证据闭合和 Word 验收，不设置人工确认、人工复核或人工裁决门禁。只有达到 `ai_ready` 的意见才会进入 AI 初审 Word。v1.7 增加义务级数值比较、房间与窗的对象关联、反证检查及设计整改责任筛选；旧工作区不自动迁移。

适合：

- 建筑总图、建筑单体及建筑专业负责的消防、无障碍、防水、节能、绿建等专项审查。
- 需要逐张关闭图纸覆盖状态、保留规范依据和证据截图的内部技术审查。
- 需要直接生成并逐页核验正式范本格式的 AI 初审意见 Word。

不适合：

- 已经有审查意见，只需要整理和排版。请使用下面的 `review-opinion-delivery`。
- 结构、给排水、电气或暖通专业技术审查。
- 资质、签章、报建手续等行政性审查。
- 没有合法规范来源却要求 Agent 凭记忆给出正式条文结论。

怎么触发：

```text
用 building-review 审查这套建筑单体施工图
做一次建筑总图施工图技术审查
检查这套建筑图纸并形成有证据的 AI 初审意见
```

[![建筑施工图审查工作流程图](media/building-review-workflow.png)](media/building-review-workflow.svg)

审图测试分别运行既有68项匿名回归、6项 CAD 安全测试、规则扩充与高频映射测试，以及 v1.7 判断证据和整包出稿回归。运行目录包含162条规则。四层本地知识资料仍分别用于发现、正式依据、适用性解释和案例比较；脚本校验不能代替实际识图。仓库不附带中国标准、地方政策、真实项目或私有索引；用户必须提供自己合法取得并确认有效的本地资料。单体和总图报告仍继承正式范本，标题保留 `【AI初审】`。

→ [SKILL.md](building-review/SKILL.md) · [高清工作流程图](media/building-review-workflow.svg) · [运行要求](building-review/references/runtime-requirements.md)

### 📝 review-opinion-delivery（审查意见整理）

> 技术结论属于审查人，Skill 负责把它忠实、可追溯、可交付地整理出来。

用于把审查人已经写好的笔记、标记图纸、截图和最新版 Word 整理成正式成果。它会保留最新版 Word 的内容权威，记录确定性错字修正，核对意见类型和证据来源，并完成 Word 内容检查与逐页视觉验收。

适合：

- 把已有审查笔记、PDF 标记和截图整理进 Word。
- 以审查人确认的最新版 Word 为底稿补齐证据、统一类型和排版。
- 比较草稿与终稿，识别删除、收窄和多对一合并是否已有确认映射。

不适合：

- 从图纸里发现新的技术问题。
- 替审查人补写规范结论、改变强弱或推断责任。
- 在来源冲突时自行挑选一个“看起来合理”的版本。

怎么触发：

```text
用 review-opinion-delivery 整理这些施工图审查意见
把我的审查笔记、标记 PDF 和最新版 Word 合成正式成果
核对并排版这份已经确认的建筑内审意见
```

[![审查意见整理工作流程图](media/review-opinion-delivery-workflow.png)](media/review-opinion-delivery-workflow.svg)

新建整理工作区使用 schema v1.3，旧版不自动迁移。新增来源撤销保护、批准文字精确比对、文字与图片对象对应、独立裁切与问题框、稳定续图引用、用户授权的 PDF 页码定位例外，以及绑定当前文档哈希的全页 QA。保持纯整理权限，不加入技术审查矩阵。测试包含既有 v1.1/v1.2 回归及17项 v1.3 匿名正反例。

→ [SKILL.md](review-opinion-delivery/SKILL.md) · [高清工作流程图](media/review-opinion-delivery-workflow.svg) · [运行要求](review-opinion-delivery/references/runtime-requirements.md)

## 🧰 运行环境

| 能力 | 主要要求 |
|---|---|
| 两个 Skill 通用 | Python 3.11+、`python-docx`、可渲染 DOCX 的 Microsoft Word 或 LibreOffice |
| building-review | `pypdf`；需要 CAD 自动化时使用 Windows、AutoCAD/Core Console，并强制经过安全包装器 |
| review-opinion-delivery | `Pillow`、`pypdfium2`、`pypdf`；Windows 下可使用 Word COM 导出 PDF |

详细依赖和环境变量见各 Skill 的 `runtime-requirements.md`。脚本负责可追溯性、格式和一致性校验，不替代建筑专业人员的技术判断，也不替代法定施工图审查。

## 🔒 公开边界

- 不包含规范、政策、培训资料、案例截图或它们的私人索引。
- 不包含真实项目名称、图纸、客户信息、审查报告和证据截图。
- 两个 Word 范本已清除作者、最后修改者、自定义属性和修订会话标识。
- GitHub Actions 会复跑匿名回归，并阻止本机路径、私人索引和 Word 隐私元数据进入仓库。

## 🔄 维护者同步

仓库使用 `sync-manifest.json` 对两个开发源 Skill 做逐文件白名单同步。新出现的源文件会被默认阻止，必须先明确归类；本地规范索引、项目资料、成果目录、缓存和未选中的过程资产不会进入公开仓库。

先只读预检：

```powershell
powershell -ExecutionPolicy Bypass -File scripts/sync-public-skills.ps1 -SourceRoot "<同时包含 building-review 和 review-opinion-delivery 的开发源目录>" -Check
```

预检通过后应用到本地公开仓库：

```powershell
powershell -ExecutionPolicy Bypass -File scripts/sync-public-skills.ps1 -SourceRoot "<开发源目录>" -Apply
```

一条命令完成应用、提交、推送，并等待 GitHub Actions 验证：

```powershell
powershell -ExecutionPolicy Bypass -File scripts/sync-public-skills.ps1 -SourceRoot "<开发源目录>" -Apply -Publish -Message "Sync public Skills"
```

同步程序会先在临时目录生成脱敏快照，执行语法检查、公开边界校验和两套 Skill 的完整匿名回归，再写入仓库；结束时还会复核开发源目录的整树哈希没有变化。`-Publish` 只允许从 `main` 发布，且会拒绝无关工作区改动。

## 🌟 关于

这些 Skill 来自实际建筑施工图内审流程中的反复使用、复核和修订。公开它们，是希望把“证据链、专业边界、结论门禁和逐页验收”做成可复用的工作习惯。

有问题或改进建议，欢迎在 Issues 中提出。

[MIT License](LICENSE) · 自由使用、修改与再分发

Made by [@jack20040828](https://github.com/jack20040828)
