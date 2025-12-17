---
description: 发布知识到 GitHub：检测 Mermaid → 生成图片 → 提交 → 推送 → 验证
globs: ["knowledge/**/*.md"]
---

# Skill: 发布知识 (Publish Knowledge)

**这是一个轻量级 Skill，所有业务逻辑都在 Tool 中实现。**

## 工作流程

1. 检查 Git 状态
2. 检测 Mermaid 代码块
3. 生成高清流程图（2000px，3x scale）
4. 智能生成 Commit Message
5. 提交并推送到 GitHub
6. 验证推送成功

## 实现

所有逻辑由 `tools/knowledge_publisher.py` 实现，Skill 只负责调用。

```bash
#!/bin/bash
set -e

# 切换到项目根目录
cd /Users/wangsc/Agent/lessoning-ai

# 调用 Tool 完成所有工作
python3 tools/knowledge_publisher.py --publish
```

