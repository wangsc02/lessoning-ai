# Lessoning AI - AI Agent 学习知识库

> 打造成 Skill 的学习资料生成与发布系统

## 🎯 项目定位

这是一个基于 **Cursor Skills** 的知识管理系统，采用三层架构：

```
Skills (能力层)    → .cursor/commands/
  ↓ 调用
Tools (工具层)     → tools/
  ↓ 操作
Knowledge (知识层) → knowledge/
```

## 🏗️ 架构设计

### 三层架构

| 层级 | 目录 | 职责 | 类比 |
|------|------|------|------|
| **Skills** | `.cursor/commands/` | 定义能力、编排流程 | Claude Skills |
| **Tools** | `tools/` | 具体功能实现 | External Tools |
| **Knowledge** | `knowledge/` | 知识存储与索引 | Knowledge Base |

### 当前 Skills

| Skill | 功能 | 调用的 Tool |
|-------|------|------------|
| `publish-knowledge` | 发布知识到 GitHub | `knowledge_publisher.py` |
| `generate-learning-doc` | 生成 AI Agent 学习文档 | AI + Templates |

### 当前 Tools

| Tool | 功能 | 输入 | 输出 |
|------|------|------|------|
| `knowledge_publisher.py` | 知识发布器 | Markdown + Mermaid | 高清图片 + 飞书版本 |

## 📚 Knowledge Base

| 知识文档 | 主题 | 流程图 | 状态 |
|---------|------|--------|------|
| [LangChain 1.0 深度学习指南](knowledge/LangChain1.0深度学习指南.md) | LangChain 架构与实践 | 9 张 | ✅ |
| [Agent 开发深度学习指南](knowledge/Agent开发深度学习指南.md) | Agent 设计与落地 | 12 张 | ✅ |
| [Claude Skills 深度学习指南](knowledge/Claude%20Skills深度学习指南.md) | Claude Skills 机制 | 1 张 | ✅ |
| [Skill 与 Subagent 深度对比](knowledge/Skill与Subagent深度对比.md) | 架构对比分析 | - | ✅ |
| [多媒体流数据结构详解](knowledge/多媒体流数据结构详解.md) | WebRTC/WebSocket | - | ✅ |

## 🚀 快速开始

### 使用 Skill 发布知识

1. **编辑知识文档**：
   ```bash
   vim knowledge/LangChain1.0深度学习指南.md
   ```

2. **调用 Skill**：
   - 打开 Cursor Command Palette (`Cmd+Shift+P`)
   - 搜索 `publish-knowledge`
   - 回车执行

3. **自动完成**：
   - ✅ 检测 Mermaid 代码块
   - ✅ 调用 Tool 生成高清流程图
   - ✅ 智能生成 commit message
   - ✅ 提交并推送到 GitHub
   - ✅ 验证推送成功

### 手动使用 Tool

```bash
# 处理单个文档
python tools/knowledge_publisher.py knowledge/LangChain1.0深度学习指南.md

# 批量处理
python tools/knowledge_publisher.py --all
```

## 📂 项目结构

```
lessoning-ai/
├── .cursor/
│   ├── commands/                    # Skills 层（能力定义）
│   │   ├── publish-knowledge.md    # Skill: 发布知识
│   │   └── generate-learning-doc.md # Skill: 生成文档
│   └── rules/                       # 代码规范
├── tools/                           # Tools 层（工具实现）
│   └── knowledge_publisher.py      # Tool: 知识发布器
├── knowledge/                       # Knowledge 层（知识库）
│   ├── *.md                        # 源文档
│   ├── *_feishu.md                 # 飞书版本（自动生成）
│   └── images/                     # 流程图（按文档分组）
│       ├── langchain1/
│       ├── agent_/
│       └── claude_skills_/
└── README.md                        # 本文档
```

## 🔧 工作流程

### Skill 触发流程

```
用户 → Cursor Command Palette → Skill (publish-knowledge)
         ↓
       检查 Git 状态
         ↓
       检测 Mermaid
         ↓
       调用 Tool (knowledge_publisher.py)
         ↓
       生成高清图片 (2000px, 3x scale)
         ↓
       生成飞书版本
         ↓
       智能 commit & push
         ↓
       验证成功 & 显示 URL
```

### 手动发布流程

```bash
# 1. 编辑知识
vim knowledge/新知识.md

# 2. 调用 Tool
python tools/knowledge_publisher.py knowledge/新知识.md

# 3. 提交
git add knowledge/images/ knowledge/*_feishu.md
git commit -m "docs: 添加新知识"
git push
```

## 🎨 飞书版本

每个文档都有对应的飞书版本（`*_feishu.md`）：
- ✅ Mermaid 代码块替换为 GitHub Raw 图片链接
- ✅ 保留 Mermaid 源码在 `<details>` 折叠块中
- ✅ 直接导入飞书即可显示图片

**导入方法**：
1. 打开 `knowledge/xxx_feishu.md`
2. 复制全部内容
3. 粘贴到飞书文档
4. 图片自动从 GitHub 加载显示

## 📊 流程图质量

| 指标 | 数值 | 说明 |
|------|------|------|
| 宽度 | 2000px | 超高清 |
| 缩放 | 3x | 细节清晰 |
| 格式 | PNG | 无损压缩 |
| 背景 | 透明 | 适配各种主题 |
| 平均大小 | 80-150 KB | 快速加载 |
| 生成工具 | mermaid-cli | 本地可控 |

## 📦 依赖安装

```bash
# 安装 Mermaid CLI（Tool 依赖）
npm install -g @mermaid-js/mermaid-cli

# Python（无额外依赖，使用标准库）
python --version  # >= 3.7
```

## 🎯 设计原则

1. **Skill 化**：Cursor Commands 就是 Skills
2. **工具化**：复杂逻辑封装为 Tools
3. **知识化**：文档不是"doc"，是 Knowledge Base
4. **可组合**：Skills 可以调用多个 Tools
5. **可扩展**：新增 Skill/Tool 不影响现有功能

## 💡 为什么这样设计？

| 传统方案 | 本项目 | 优势 |
|---------|--------|------|
| `scripts/` | `tools/` | 明确是工具，不是临时脚本 |
| `doc/` | `knowledge/` | 明确是知识库，不是普通文档 |
| 手动脚本 | Cursor Skills | 集成到 IDE，一键调用 |
| 混乱的流程 | 三层架构 | 清晰、可维护、可扩展 |

## 🔗 快速链接

- **GitHub 仓库**：https://github.com/wangsc02/lessoning-ai
- **Knowledge Base**：https://github.com/wangsc02/lessoning-ai/tree/main/knowledge
- **Mermaid 语法**：https://mermaid.js.org

## 📝 贡献指南

欢迎添加新知识！只需：
1. 在 `knowledge/` 下创建 Markdown 文件
2. 运行 Skill: `publish-knowledge`
3. 提交 PR

## 📄 License

MIT
