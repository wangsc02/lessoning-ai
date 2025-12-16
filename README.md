# Lessoning AI - 技术学习文档库

> AI Agent 开发的深度学习资料集

## 📚 文档列表

| 文档 | 主题 | 流程图 | 状态 |
|------|------|--------|------|
| [LangChain 1.0 深度学习指南](doc/LangChain1.0深度学习指南.md) | LangChain 架构与实践 | 9 张 | ✅ |
| [Agent 开发深度学习指南](doc/Agent开发深度学习指南.md) | Agent 设计与落地 | 12 张 | ✅ |
| [Claude Skills 深度学习指南](doc/Claude%20Skills深度学习指南.md) | Claude Skills 机制 | 1 张 | ✅ |
| [Skill 与 Subagent 深度对比](doc/Skill与Subagent深度对比.md) | 架构对比分析 | - | ✅ |
| [多媒体流数据结构详解](doc/多媒体流数据结构详解.md) | WebRTC/WebSocket | - | ✅ |

## 🎯 飞书版本

每个文档都有对应的飞书版本（`*_feishu.md`），区别：
- ✅ Mermaid 代码块替换为高清图片链接
- ✅ 保留源码在折叠块中（可查看/编辑）
- ✅ 直接导入飞书即可显示图片

**导入方法**：
1. 打开 `doc/xxx_feishu.md`
2. 复制全部内容
3. 粘贴到飞书文档
4. 图片自动显示

## 🛠️ 维护流程

### 编辑现有文档

```bash
# 1. 编辑源文档（Markdown）
vim doc/LangChain1.0深度学习指南.md

# 2. 如果修改了 Mermaid 流程图，重新生成
python scripts/build.py doc/LangChain1.0深度学习指南.md

# 3. 提交
git add doc/images/ doc/*_feishu.md
git commit -m "docs: 更新 LangChain 文档"
git push

# 4. 重新导入飞书
```

### 添加新文档

```bash
# 1. 创建新文档
vim doc/新文档.md

# 2. 生成图片和飞书版本
python scripts/build.py doc/新文档.md

# 3. 提交
git add doc/ doc/images/
git commit -m "docs: 添加新文档"
git push
```

### 批量更新所有文档

```bash
# 重新生成所有流程图
python scripts/build.py --all

git add doc/images/ doc/*_feishu.md
git commit -m "docs: 批量更新流程图"
git push
```

## 📦 依赖安装

```bash
# Mermaid CLI（生成流程图）
npm install -g @mermaid-js/mermaid-cli

# Python（无额外依赖，使用标准库）
python --version  # >= 3.7
```

## 📊 流程图质量

| 指标 | 数值 |
|------|------|
| 宽度 | 2000px |
| 缩放 | 3x |
| 格式 | PNG（无损） |
| 背景 | 透明 |
| 平均大小 | 80-150 KB |

## 🔗 快速链接

- **GitHub 仓库**：https://github.com/wangsc02/lessoning-ai
- **构建脚本文档**：[scripts/README.md](scripts/README.md)
- **Mermaid 语法**：https://mermaid.js.org

## 📂 项目结构

```
lessoning-ai/
├── doc/                    # 源文档目录
│   ├── *.md               # 源文档（编辑这些）
│   ├── *_feishu.md        # 飞书版本（自动生成）
│   └── images/            # 统一图片目录
│       ├── langchain1_*.png
│       ├── agent_*.png
│       └── claude_*.png
├── scripts/
│   ├── build.py           # 统一构建脚本
│   └── README.md          # 脚本文档
└── README.md              # 本文档
```

## 🎯 设计原则

1. **统一**：所有文档使用同一套工具链
2. **简洁**：一个脚本解决所有问题
3. **可控**：本地生成，质量稳定
4. **通用**：支持任意 Markdown 文档
5. **可追溯**：图片命名包含文档名和哈希

## 📝 贡献指南

欢迎添加新的学习文档！只需：
1. 在 `doc/` 下创建 Markdown 文件
2. 运行 `python scripts/build.py doc/你的文档.md`
3. 提交 PR

## 📄 License

MIT

