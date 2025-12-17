---
description: 发布知识到 GitHub：检测 Mermaid → 生成图片 → 提交 → 推送 → 验证
globs: ["knowledge/**/*.md"]
---

# Skill: 发布知识 (Publish Knowledge)

这个 Skill 会自动调用 Tool 完成知识发布流程：
1. 检查 Git 状态和 Knowledge Base 中的 Mermaid 代码
2. 调用 `knowledge_publisher.py` 生成高清流程图
3. 提交所有修改到 Git
4. 推送到 GitHub
5. 验证推送成功并显示 URL

```bash
#!/bin/bash
set -e

# 颜色定义
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

echo -e "${BLUE}============================================================${NC}"
echo -e "${BLUE}📦 自动化文档发布流程${NC}"
echo -e "${BLUE}============================================================${NC}"
echo ""

# 切换到项目根目录
cd /Users/wangsc/Agent/lessoning-ai

# 步骤 1: 检查 Git 状态
echo -e "${YELLOW}📋 步骤 1/5: 检查 Git 状态${NC}"
if ! git diff --quiet || ! git diff --cached --quiet; then
    echo -e "${GREEN}✅ 检测到文件修改${NC}"
    git status --short
    echo ""
else
    echo -e "${YELLOW}ℹ️  没有检测到修改，退出${NC}"
    exit 0
fi

# 步骤 2: 检测是否需要生成图片
echo -e "${YELLOW}📋 步骤 2/5: 检测 Mermaid 代码块${NC}"

# 检查 Knowledge Base 中是否有包含 mermaid 的文档
NEED_BUILD=false
for doc in knowledge/*.md; do
    if [ -f "$doc" ] && grep -q '\`\`\`mermaid' "$doc"; then
        echo -e "${GREEN}✅ 发现 Mermaid: $(basename $doc)${NC}"
        NEED_BUILD=true
    fi
done

# 步骤 3: 生成图片（如果需要）
if [ "$NEED_BUILD" = true ]; then
    echo ""
    echo -e "${YELLOW}📋 步骤 3/5: 调用 Tool 生成高质量流程图${NC}"
    if python3 tools/knowledge_publisher.py --all; then
        echo ""
        echo -e "${GREEN}✅ 图片生成成功${NC}"
    else
        echo ""
        echo -e "${RED}❌ 图片生成失败${NC}"
        exit 1
    fi
else
    echo -e "${BLUE}ℹ️  无需生成图片${NC}"
    echo ""
    echo -e "${YELLOW}📋 步骤 3/5: 跳过图片生成${NC}"
fi

# 步骤 4: 生成智能 Commit Message
echo ""
echo -e "${YELLOW}📋 步骤 4/5: 准备提交${NC}"

# 分析修改类型
DOC_MODIFIED=$(git status --short | grep -E '^\s*M\s+knowledge/.*\.md$' | wc -l | tr -d ' ')
DOC_ADDED=$(git status --short | grep -E '^\s*A\s+knowledge/.*\.md$' | wc -l | tr -d ' ')
IMG_MODIFIED=$(git status --short | grep 'knowledge/images/' | wc -l | tr -d ' ')

# 生成 commit message
if [ "$DOC_ADDED" -gt 0 ]; then
    # 获取新增文档名
    NEW_DOC=$(git status --short | grep -E '^\s*A\s+knowledge/.*\.md$' | head -1 | awk '{print $2}' | xargs basename | sed 's/.md$//')
    COMMIT_MSG="docs: 添加知识 ${NEW_DOC}"
elif [ "$DOC_MODIFIED" -gt 0 ] && [ "$IMG_MODIFIED" -gt 0 ]; then
    COMMIT_MSG="docs: 更新知识及流程图"
elif [ "$DOC_MODIFIED" -gt 0 ]; then
    COMMIT_MSG="docs: 更新知识内容"
elif [ "$IMG_MODIFIED" -gt 0 ]; then
    COMMIT_MSG="docs: 更新流程图"
else
    COMMIT_MSG="docs: 更新知识库"
fi

echo -e "${GREEN}📝 Commit Message: ${COMMIT_MSG}${NC}"

# 暂存所有修改
git add -A

# 提交
if git commit -m "$COMMIT_MSG"; then
    echo -e "${GREEN}✅ 提交成功${NC}"
else
    echo -e "${RED}❌ 提交失败${NC}"
    exit 1
fi

# 步骤 5: 推送并验证
echo ""
echo -e "${YELLOW}📋 步骤 5/5: 推送到 GitHub 并验证${NC}"

# 记录本地 commit hash
LOCAL_HASH=$(git rev-parse HEAD)
echo -e "${BLUE}本地 Commit: ${LOCAL_HASH:0:7}${NC}"

# 推送
echo -e "${BLUE}正在推送...${NC}"
if git push; then
    echo ""
    echo -e "${GREEN}✅ 推送命令执行成功${NC}"
    
    # 等待 1 秒，让远程更新
    sleep 1
    
    # 验证推送
    echo -e "${BLUE}正在验证...${NC}"
    git fetch origin main --quiet
    REMOTE_HASH=$(git rev-parse origin/main)
    
    if [ "$LOCAL_HASH" = "$REMOTE_HASH" ]; then
        echo ""
        echo -e "${GREEN}============================================================${NC}"
        echo -e "${GREEN}🎉 发布成功！${NC}"
        echo -e "${GREEN}============================================================${NC}"
        echo ""
        echo -e "${GREEN}📊 本次提交信息：${NC}"
        echo -e "   Commit: ${LOCAL_HASH:0:7}"
        echo -e "   Message: ${COMMIT_MSG}"
        echo ""
        echo -e "${GREEN}🔗 GitHub 链接：${NC}"
        echo -e "   https://github.com/wangsc02/lessoning-ai/commit/${LOCAL_HASH}"
        echo ""
        echo -e "${GREEN}📁 查看 Knowledge Base：${NC}"
        echo -e "   https://github.com/wangsc02/lessoning-ai/tree/main/knowledge"
        echo ""
    else
        echo ""
        echo -e "${YELLOW}⚠️  推送可能未完全同步${NC}"
        echo -e "${YELLOW}本地: ${LOCAL_HASH:0:7}${NC}"
        echo -e "${YELLOW}远程: ${REMOTE_HASH:0:7}${NC}"
        echo ""
        echo -e "${YELLOW}请稍后手动验证: git log origin/main${NC}"
    fi
else
    echo ""
    echo -e "${RED}============================================================${NC}"
    echo -e "${RED}❌ 推送失败${NC}"
    echo -e "${RED}============================================================${NC}"
    echo ""
    echo -e "${RED}可能的原因：${NC}"
    echo -e "  1. 网络连接问题"
    echo -e "  2. 权限不足"
    echo -e "  3. 远程分支有新提交（需要先 pull）"
    echo ""
    echo -e "${YELLOW}💡 建议操作：${NC}"
    echo -e "  git pull --rebase"
    echo -e "  git push"
    echo ""
    exit 1
fi
```

