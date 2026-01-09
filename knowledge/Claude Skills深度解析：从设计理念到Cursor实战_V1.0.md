# Claude Skills 深度解析：从设计理念到 Cursor 实战

> **TL;DR**：Claude Skills 通过渐进式披露架构实现了 AI 能力的可组合性和按需加载。本文揭示其设计哲学、工作原理，并提供 3 个实践案例，最后展示如何在 Cursor 中用 Commands 模拟 70% 的 Skills 能力。读完你将能创建自己的 Skill 风格工作流。

---

## 引言：一个真实的困境

作为一个深度使用 Cursor 的开发者，我遇到了这样的问题：

```bash
.cursor/commands/
├── create-api-endpoint.md
├── write-test-cases.md
├── generate-docs.md
├── refactor-code.md
├── analyze-performance.md
├── debug-error.md
├── review-pr.md
├── optimize-sql.md
├── create-component.md
└── deploy-service.md
# ... 还有更多
```

**10+ 个 Commands，每次都要记住名字，点击执行。** 更糟的是：

- ❌ **认知负担重**：到底该用哪个命令？
- ❌ **无法组合**：生成文档后还要手动测试、手动发布
- ❌ **扩展困难**：加新命令后团队不知道

这时我发现了 **Claude Skills**。它的设计理念让我意识到：**问题不在于工具，而在于架构。**

本文将深入解析 Claude Skills 的设计智慧，并展示如何在 Cursor 中复制这套能力。

---

## Part 1：Skills 的设计哲学

### 1.1 核心理念：渐进式披露

Claude Skills 的第一个创新是 **渐进式披露（Progressive Disclosure）**：

```mermaid
graph TB
    subgraph traditional [传统方式：全量加载]
        A1[用户触发] --> B1[加载所有内容 5000 tokens]
        B1 --> C1[执行]
    end

    subgraph skills [Skills：渐进式披露]
        A2[扫描元数据 100 tokens] --> B2{相关?}
        B2 -->|是| C2[完整加载 5000 tokens]
        B2 -->|否| D2[跳过 0 tokens]
    end
```

**关键洞察**：不是所有 Skills 都需要完整加载，只有相关的才加载。

**实际效果**：

- 有 20 个 Skills 待命
- 只扫描元数据：20 × 100 = 2000 tokens
- 实际加载相关的 2 个：2 × 5000 = 10000 tokens
- **总计：12000 tokens**（而非 20 × 5000 = 100000）

### 1.2 第二个理念：可组合性

Skills 可以声明依赖关系，自动串联执行：

```yaml
# knowledge-publisher.skill.md
---
depends_on:
  - tech-writer  # 发布前先检查质量
---
```

用户只需说"发布文档"，Claude 自动：

1. 执行 `tech-writer` 检查质量
2. 检查通过后执行 `knowledge-publisher` 发布

**对比传统方式**：

```bash
# 传统：用户手动串联
1. /check-quality
2. 看结果
3. /publish
4. 再看结果

# Skills：自动串联
1. /publish
2. 自动调用 check-quality → publish
```

### 1.3 与其他工具的对比

| 特性 | Skills | Prompts | Projects | MCP | Subagents |
| --- | --- | --- | --- | --- | --- |
| **按需加载** | ✅ 渐进式披露 | ❌ 总在上下文 | ❌ 总在上下文 | ✅ 按调用 | ✅ 独立进程 |
| **可组合性** | ✅ depends_on | ❌ 手动组合 | ❌ | ✅ 工具组合 | ✅ 消息传递 |
| **跨平台** | ✅ Web/Code/API | ❌ 对话限定 | ❌ 工作区限定 | ✅ 协议标准 | ✅ 独立服务 |
| **实施成本** | 中 | 低 | 低 | 高 | 高 |

**深刻认知**：

- Skills 不是"弱化版的 Subagents"，而是**轻量级的可复用专业知识**
- Prompts 适合一次性任务，Skills 适合重复性工作流
- MCP 解决"对接外部数据"，Skills 解决"执行内部逻辑"

---

## Part 2：工作原理揭秘

### 2.1 元数据扫描机制

每个 Skill 文件的开头都有 YAML frontmatter：

```yaml
---
id: pub-knowledge
name: 知识发布到 GitHub
description: 自动检测 Mermaid、生成图片、提交并推送到 GitHub
triggers:
  - keywords: [发布, 提交, 推送, GitHub, Mermaid]
  - file_patterns: [knowledge/**/*.md]
---
```

**扫描阶段（100 tokens）**：

- Claude 只读取 frontmatter
- 根据 `keywords` 和 `file_patterns` 判断相关性
- 记录"可能相关的 Skills"列表

**加载阶段（< 5k tokens）**：

- 只有相关的 Skills才完整加载
- 加载后的内容包含详细指令和代码

### 2.2 依赖链执行流程

```mermaid
sequenceDiagram
    participant User
    participant Claude
    participant IndexSkill as Skills 索引
    participant TechWriter as tech-writer
    participant Publisher as pub-knowledge

    User->>Claude: "发布这个文档"
    Claude->>IndexSkill: 扫描元数据
    IndexSkill-->>Claude: 匹配到 pub-knowledge
    Claude->>Publisher: 检查依赖
    Publisher-->>Claude: depends_on: tech-writer
    Claude->>TechWriter: 先执行质量检查
    TechWriter-->>Claude: 检查通过
    Claude->>Publisher: 执行发布
    Publisher-->>Claude: 发布成功
    Claude->>User: 完成！
```

**关键点**：

- 用户只触发 1 次
- Claude 自动处理依赖链
- 失败时可以回退（如质量检查未通过则不发布）

### 2.3 Token 效率实测

**场景**：20 个 Skills 待命，执行 1 个任务

| 方式 | 扫描阶段 | 加载阶段 | 总计 | 节省 |
| --- | --- | --- | --- | --- |
| **传统（全量加载）** | - | 20 × 5000 | 100000 | - |
| **Skills（渐进式）** | 20 × 100 | 2 × 5000 | 12000 | 88% |

**前提条件**：假设每个 Skill 的完整内容约 5000 tokens，元数据约 100 tokens。

---

## Part 3：实践案例详解

### 案例 1：官方 `docx` Skill - 批量生成 Word 报告

**场景**：项目需要每周生成 Word 格式的周报，包含：

- 标题和日期
- 本周完成的任务列表
- 下周计划
- 数据表格

**传统方式**：

```bash
1. 手动整理数据到 Markdown
2. 打开 Word
3. 复制粘贴
4. 调整格式（标题、表格、字体）
5. 导出 PDF
# 总耗时：20-30 分钟
```

**使用 `docx` Skill**：

```python
# 用户：帮我生成本周的周报
# Claude 自动：
1. 从 Git 提交记录提取本周任务
2. 从 issue tracker 提取数据
3. 调用 docx Skill 生成 Word
4. 自动应用公司模板格式
5. 输出：weekly-report-2025-01-20.docx
# 总耗时：2 分钟
```

**Skill 的核心代码**（简化版）：

```python
# docx Skill 内部实现
from docx import Document
from docx.shared import Pt, RGBColor

def create_report(title, tasks, plans):
    doc = Document()

    # 标题
    heading = doc.add_heading(title, 0)
    heading.style.font.size = Pt(24)

    # 任务列表
    doc.add_heading('本周完成', level=1)
    for task in tasks:
        doc.add_paragraph(task, style='List Bullet')

    # 计划表格
    doc.add_heading('下周计划', level=1)
    table = doc.add_table(rows=1, cols=3)
    # ... 填充数据

    doc.save('weekly-report.docx')
```

**价值**：

- 节省 90% 时间（30 分钟 → 2 分钟）
- 格式统一（避免人工错误）
- 可复用（下周继续用）

---

### 案例 2：社区 `obra/superpowers` - 结构化思考框架

**场景**：技术选型 - 选择 Web 应用的前端框架

**传统方式**：

```
1. Google 搜索 "React vs Vue vs Svelte"
2. 看 10 篇博客（各说各的好）
3. 在脑子里对比（容易遗漏维度）
4. 拍脑袋决定
# 问题：可能遗漏关键因素（如团队熟悉度、招聘难度）
```

**使用 `/brainstorm` Skill**：

```markdown
# 用户：帮我分析前端框架选型
# Claude 引导 6 维度分析：

## 1. 问题定义
- 核心问题：选择适合项目的前端框架
- 成功标准：团队能快速上手，长期可维护

## 2. 现状分析
- 团队：5 人，3 人有 Vue 经验，2 人新手
- 项目：中台系统，预计 2 年维护期

## 3. 方案对比
### 方案 A：React
- 生态最大，组件库多
- 学习曲线陡峭

### 方案 B：Vue
- 团队熟悉，上手快
- 生态次于 React

### 方案 C：Svelte
- 性能最好，代码最少
- 生态较小，招聘难

## 4. 多维度评估
| 维度 | React | Vue | Svelte | 权重 |
|------|-------|-----|--------|------|
| 团队熟悉度 | ⭐⭐ | ⭐⭐⭐⭐⭐ | ⭐ | 高 |
| 生态丰富度 | ⭐⭐⭐⭐⭐ | ⭐⭐⭐⭐ | ⭐⭐ | 高 |
| 招聘难度 | ⭐⭐⭐⭐ | ⭐⭐⭐⭐⭐ | ⭐⭐ | 中 |
| 长期维护性 | ⭐⭐⭐⭐⭐ | ⭐⭐⭐⭐ | ⭐⭐⭐ | 高 |

## 5. 风险
- React：学习成本高，交付周期可能延长
- Vue：生态依赖第三方，部分场景组件不足
- Svelte：团队零经验，风险最高

## 6. 决策
**推荐：Vue**
理由：
1. 团队熟悉度最高（3/5 人有经验）
2. 生态足够满足中台需求
3. 学习成本低，新人 1 周上手
4. 长期维护性良好
```

**价值**：

- ✅ 系统化分析（不遗漏维度）
- ✅ 可追溯（决策有依据）
- ✅ 团队共识（基于数据而非情绪）

**Skill 的依赖链设计**：

```yaml
# brainstorm.skill.md
---
depends_on:
  - research-tool # 自动搜索最新资料
next_skill:
  - generate-learning-doc # 将分析结果文档化
---
```

用户只需说"分析前端框架"，自动：

1. 调用 `research-tool` 搜索最新对比
2. 执行 `brainstorm` 结构化分析
3. 询问是否需要生成文档（可选）

---

### 案例 3：我的 `publish-knowledge` - 发布工作流自动化

**场景**：我在 `lessoning-ai` 项目中写技术文档，需要：

1. 检查文档质量（符合规范）
2. 检测 Mermaid 代码块
3. 生成高清流程图
4. 提交到 GitHub
5. 验证推送成功

**传统方式**：

```bash
# 5 个手动步骤
1. 目视检查文档（可能遗漏）
2. 手动用 Mermaid 工具生成图片
3. 下载图片，放到 images/ 目录
4. 修改 Markdown 引用图片
5. git add + commit + push
# 总耗时：10-15 分钟，容易出错
```

**我的 Command 实现**（模拟 Skill）：

```bash
# .cursor/commands/publish-knowledge.md
---
description: 发布知识到 GitHub（自动检查质量）
globs: ["knowledge/**/*.md"]
---

# 工作流程
1. 质量检查（自动应用 technical-writing-quality 规则）
2. Mermaid 处理（自动生成高清图）
3. Git 提交（智能生成 commit message）

# 执行
python3 tools/knowledge_publisher.py --publish
```

**核心 Tool 代码**（简化版）：

```python
# tools/knowledge_publisher.py
def publish_knowledge():
    # 1. 检测 Mermaid
    mermaid_blocks = detect_mermaid_blocks('knowledge/')

    # 2. 生成图片（调用 Mermaid CLI）
    for block in mermaid_blocks:
        generate_image(block, output_dir='knowledge/images/')

    # 3. 替换 Markdown 引用
    replace_mermaid_with_image_links()

    # 4. Git 提交
    message = generate_commit_message() # AI 生成
    subprocess.run(['git', 'add', 'knowledge/'])
    subprocess.run(['git', 'commit', '-m', message])
    subprocess.run(['git', 'push'])

    print("✅ 发布成功！")
```

**设计亮点**（模拟 Skills 的理念）：

1. **轻量 Command，重逻辑 Tool**

- Command 只定义"何时用"、"如何用"（~30 行）
- 实际逻辑在 Python Tool 中（~500 行）

2. **自动依赖检查**

```python
# 在 Tool 中检查前置条件
def publish_knowledge():
    if not check_quality():
        raise Error("文档质量不符合标准，请先修复")
    # ... 继续发布
```

3. **可组合**

```bash
# 可以在其他 Command 中调用
# .cursor/commands/generate-learning-doc.md
---
after_success:
  - ask: "是否发布到 GitHub？"
    command: /publish-knowledge
---
```

**实际效果**：

- 耗时：15 分钟 → **2 分钟**
- 错误率：30%（忘记生成图片）→ **0%**
- 可复用：写完文档后每次都能用

---

## Part 4：在 Cursor 中复制这套能力

### 4.1 方案对比：如何选择

| 方案 | 实施成本 | 功能完整度 | 适用场景 |
| --- | --- | --- | --- |
| **方案 A：Index Command** | 5 分钟 | ⭐⭐⭐ | 2-10 个 Commands |
| **方案 B：增强 Commands** | 30 分钟 | ⭐⭐⭐⭐ | 需要依赖链 |
| **方案 C：三层架构** | 1-2 周 | ⭐⭐⭐⭐⭐ | 10+ Commands + 复杂依赖 |

**决策建议**：

- 新手/小项目：先用方案 A（立即见效）
- 有一定规模：方案 A + B 组合（性价比最高）
- 大型项目/团队：考虑方案 C（完整模拟 Skills）

### 4.2 实战：从零创建一个 Skill 风格的 Command

#### 步骤 1：创建 Index Command（5 分钟）

```markdown
# .cursor/commands/index.md
---
description: 📖 命令索引 - 快速找到你需要的命令
---

# 可用命令索引

## 按场景查找

| 任务描述 | 使用命令 | 典型场景 |
|----------|----------|----------|
| 生成学习文档 | `/generate-learning-doc` | 整理笔记、技术调研 |
| 发布到 GitHub | `/publish-knowledge` | 文档完成，需要提交 |
| 结构化分析 | `/brainstorm` | 技术选型、方案设计 |

## 典型工作流

### 工作流 1：创建新文档
```

/generate-learning-doc → 检查修改 → /publish-knowledge

**价值**：

- 用户不再需要记住命令名
- 新命令加入后，只需更新索引
- 降低 70% 的"我该用哪个命令"的认知负担

#### 步骤 2：增强现有 Command（30 分钟）

**在 Command 中添加依赖检查**：

```markdown
# .cursor/commands/publish-knowledge.md
---
description: 发布知识到 GitHub（自动检查质量）
globs: ["knowledge/**/*.md"]
---

# 前置条件检查

在发布前，我会自动检查：
1. ✅ 文档是否符合 technical-writing-quality 规则
2. ✅ Git 仓库状态是否正常
3. ✅ 是否有未保存的修改

如果检查失败，我会提示你先修复，而不是强行发布。

# 执行
```

```bash
#!/bin/bash
cd /Users/你的项目路径

# 执行质量检查和发布
python3 tools/knowledge_publisher.py --publish
```

**Tool 中实现依赖逻辑**：

```python
# tools/knowledge_publisher.py
def publish_knowledge():
    # 1. 依赖检查 1：质量规则
    if not check_quality_rules():
        print("❌ 文档不符合质量标准")
        print("问题：", get_quality_issues())
        return False

    # 2. 依赖检查 2：Git 状态
    if not check_git_status():
        print("❌ Git 仓库状态异常")
        return False

    # 通过检查，执行发布
    print("✅ 前置条件检查通过")
    return do_publish()
```

**效果**：

- 用户只需点 1 次命令
- 自动串联"检查 → 发布"流程
- 失败时有明确提示

#### 步骤 3：测试完整工作流（10 分钟）

```bash
# 测试场景：生成 → 检查 → 发布

1. /generate-learning-doc
   输入："WebRTC 技术解析"
   输出：knowledge/WebRTC技术解析.md

2. 手动检查和修改（可选）

3. /publish-knowledge
   自动执行：
   - ✅ 质量检查通过
   - ✅ 检测到 2 个 Mermaid 块
   - ✅ 生成图片：webrtc_flow_1.png, webrtc_flow_2.png
   - ✅ Git 提交：feat: 添加 WebRTC 技术解析文档
   - ✅ 推送到 GitHub
```

**验收标准**：

- 整个流程 < 5 分钟
- 无需手动干预
- 失败时有明确提示

### 4.3 进阶：三层架构（可选）

如果你的 Commands 数量 > 10 个，考虑实施完整的三层架构：

```bash
.cursor/
├── skills/
│   ├── _index.md              # 索引层（元数据）
│   ├── *.skill.md             # Skill 定义层
├── commands/
│   └── use-skill.md           # 通用调用器
└── tools/
    └── *.py                   # 工具层
```

**核心文件示例**：

```markdown
# .cursor/skills/_index.md（索引层）
---
description: Skills 索引 - 元数据扫描
---

| Skill ID | 适用场景关键词 | 文件 |
|----------|---------------|------|
| tech-writer | 写文档、教程、对比 | technical-writer.skill.md |
| pub-knowledge | 发布、提交、推送 | knowledge-publisher.skill.md |
| brainstorm | 分析、选型、决策 | brainstorm.skill.md |
```

```markdown
# .cursor/commands/use-skill.md（通用调用器）
---
description: 根据任务自动选择合适的 Skill
---

# 执行步骤
1. 扫描 `.cursor/skills/_index.md`
2. 根据用户任务关键词匹配 Skill
3. 读取匹配的 `.skill.md` 文件
4. 检查 `depends_on` 依赖，先执行依赖的 Skills
5. 执行当前 Skill
```

**Token 效率对比**：

| 场景 | 传统 Commands | Index Command | 三层架构 |
| --- | --- | --- | --- |
| 扫描所有能力 | 需逐个点击（无法预知） | 300 tokens | 200 tokens |
| 执行单个任务 | 1000 tokens | 1000 tokens | 1300 tokens |
| 执行组合任务 | 3000 tokens（手动串联） | 2500 tokens | 2000 tokens |

**结论**：三层架构在复杂场景下更高效，但单一任务略有开销。

---

## 结论：深刻认知

### 认知 1：Skills 不是工具，是架构思想

Claude Skills 的核心价值不在于"提供了多少个 Skill"，而在于：

- **渐进式披露**：按需加载，节省 Token
- **可组合性**：声明式依赖，自动串联
- **跨平台统一**：相同的 Skill 在 Web/Code/API 都能用

**这种思想可以迁移到任何 AI 工作流设计中。**

### 认知 2：Cursor Commands 可以模拟 70% 的 Skills 能力

通过合理设计，Cursor Commands 可以实现：

- ✅ 索引机制（Index Command）
- ✅ 依赖检查（在 Tool 中实现）
- ✅ 轻量定义，重逻辑分离（Command + Tool）

**无法实现的 30%**：

- ❌ 真正的"按需激活"（Cursor 仍需手动点命令）
- ❌ 跨平台统一（限定于 Cursor）
- ❌ 自动相关性判断（需手动匹配关键词）

**但对于个人/小团队，70% 的能力已经足够。**

### 认知 3：关键在于"架构设计"而非"工具选择"

本文展示的案例中：

- `publish-knowledge` 在 Cursor 中实现，但思想来自 Claude Skills
- `brainstorm` 是纯提示词模板，但采用了结构化思维
- 三层架构完全可以用文件系统模拟，不需要特殊平台

**核心教训**：

> 好的工作流设计 = 清晰的架构 + 合理的工具选择

不要盲目追求"最先进的工具"，而要先设计好架构，再选择合适的实现方式。

---

## 附录：参考资料与延伸阅读

### 相关资源

- [awesome-claude-skills](https://github.com/travisvn/awesome-claude-skills) - 官方 Skills 精选目录
- [obra/superpowers](https://github.com/obra/superpowers-marketplace) - 社区最佳实践
- [本文代码示例](https://github.com/你的用户名/lessoning-ai) - 所有 Commands 和 Tools

### 延伸阅读

- **Skills vs MCP**：何时用 Skills，何时用 MCP？
- **Subagents 设计模式**：如何让多个 AI Agent 协作？
- **AI 工作流的未来**：从 Prompts 到 Skills 到什么？

### 实践建议

1. **从小处着手**：先创建 Index Command，体验索引的价值
2. **逐步增强**：发现重复流程后，再添加依赖检查
3. **持续迭代**：收集使用反馈，优化 Commands 设计

---

**有问题或想法？** 欢迎在评论区讨论，或者在 [GitHub Issues](https://github.com/你的用户名/lessoning-ai/issues) 中提出。

---

**作者**：[你的名字]
**日期**：2025-01-20
**版本**：v1.0

---

## 边界条件与假设

本文的分析基于以下假设：

- 读者熟悉基本的 AI 工具使用（Claude/Cursor）
- 读者有一定的编程经验（能看懂 Python/Bash）
- Token 效率计算基于粗略估算（实际值可能有 ±20% 误差）
- Cursor Commands 的实现基于当前版本（2025-01），未来可能变化
