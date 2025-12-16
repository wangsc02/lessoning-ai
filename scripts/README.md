# 通用 Mermaid 图表构建工具

## 📋 目的

为所有技术文档提供统一的 Mermaid 流程图生成方案：
- ✅ 支持任意 Markdown 文档
- ✅ 高质量输出（2000px 宽，3x scale）
- ✅ 本地可控（不依赖在线 API）
- ✅ 智能命名，避免冲突
- ✅ 一键批量处理

## 🚀 安装依赖

```bash
# 只需安装一次
npm install -g @mermaid-js/mermaid-cli
```

## 📝 使用方法

### 1. 处理单个文档

```bash
python scripts/build.py doc/LangChain1.0深度学习指南.md
```

### 2. 处理多个文档

```bash
python scripts/build.py doc/LangChain*.md doc/Agent*.md
```

### 3. 处理所有文档

```bash
python scripts/build.py --all
```

## 🎯 工作流程

### 新文档从零开始

```bash
# 1. 编写文档，包含 Mermaid 代码块
vim doc/新文档.md

# 2. 生成图片和飞书版本
python scripts/build.py doc/新文档.md

# 3. 提交
git add doc/images/ doc/新文档_feishu.md
git commit -m "docs: 添加新文档及流程图"
git push

# 4. 导入飞书
# 复制 doc/新文档_feishu.md 到飞书
```

### 修改现有文档的流程图

```bash
# 1. 编辑源文档
vim doc/LangChain1.0深度学习指南.md

# 2. 重新生成（只更新变化的图片）
python scripts/build.py doc/LangChain1.0深度学习指南.md

# 3. 提交
git add doc/images/ doc/*_feishu.md
git commit -m "docs: 更新流程图"
git push

# 4. 重新导入飞书
```

### 批量更新所有文档

```bash
# 如果修改了 Mermaid 配置，想重新生成所有图片
python scripts/build.py --all

git add doc/images/ doc/*_feishu.md
git commit -m "docs: 批量更新所有流程图"
git push
```

## 📁 文件组织

### 图片命名规则

```
doc/images/{文档名}_{序号}_{哈希}.png

示例：
  langchain_1_abc123.png      # LangChain 文档第 1 张图
  langchain_2_def456.png      # LangChain 文档第 2 张图
  agent_1_xyz789.png          # Agent 文档第 1 张图
```

**优势**：
- ✅ 按文档名分组，避免冲突
- ✅ 哈希保证唯一性
- ✅ 统一目录，便于管理

### 目录结构

```
doc/
├── images/                              # 统一图片目录
│   ├── langchain_1_abc123.png
│   ├── langchain_2_def456.png
│   ├── agent_1_xyz789.png
│   └── ...
├── LangChain1.0深度学习指南.md          # 源文档
├── LangChain1.0深度学习指南_feishu.md  # 飞书版本（自动生成）
├── Agent开发深度学习指南.md
├── Agent开发深度学习指南_feishu.md
└── ...
```

## 🔧 配置说明

编辑 `scripts/build.py` 中的配置：

### GitHub 仓库配置

```python
GITHUB_REPO = "wangsc02/lessoning-ai"
GITHUB_BRANCH = "main"
```

### 图片质量配置

```python
cmd = [
    'mmdc',
    '-i', temp_mmd,
    '-o', str(output_path),
    '-w', '2000',           # 宽度（px）
    '-s', '3',              # 缩放倍数（1-5）
    '-b', 'transparent'     # 背景（transparent/white/black）
]
```

### 自定义图片目录

```python
# 默认：doc/images/（统一目录）
IMAGES_DIR = Path("doc/images")

# 可选：每个文档一个目录
# IMAGES_DIR = doc_path.parent / "images"
```

## 📊 质量对比

| 指标 | 在线 API | 本地 CLI |
|------|----------|----------|
| 尺寸 | 784x95 | **5952x729** |
| 文件 | 9 KB | **95 KB** |
| 清晰度 | ❌ | ✅ |
| 稳定性 | ⚠️ 不稳定 | ✅ 100% |
| 可控性 | ❌ | ✅ |
| 通用性 | ⚠️ 需分别调用 | ✅ 批量处理 |

## 🐛 故障排除

### 1. mmdc 命令未找到

```bash
# 检查安装
which mmdc

# 如果没有，安装
npm install -g @mermaid-js/mermaid-cli

# Mac 用户可能需要
export PATH="/usr/local/bin:$PATH"
```

### 2. 图片生成失败

```bash
# 检查 Mermaid 语法
# 访问 https://mermaid.live 粘贴代码验证语法

# 查看详细错误
mmdc -i test.mmd -o test.png
```

### 3. 飞书图片不显示

```bash
# 确保已推送到 GitHub
git push

# 检查图片 URL 是否正确
curl -I https://raw.githubusercontent.com/wangsc02/lessoning-ai/main/doc/images/xxx.png

# 等待 1-2 分钟（GitHub CDN 缓存）
```

### 4. 文件名冲突

脚本使用"文档名 + 序号 + 哈希"确保唯一性，一般不会冲突。

如果出现冲突（极罕见），手动重命名即可。

## 💡 最佳实践

### 1. Git 忽略临时文件

```bash
# .gitignore
*.mmd
*.html
```

### 2. 定期清理旧图片

```bash
# 找出未被引用的图片
cd doc/images
for img in *.png; do
  grep -q "$img" ../*.md || echo "未使用: $img"
done
```

### 3. 备份重要文档

```bash
# 修改前备份
cp doc/重要文档.md doc/重要文档.backup.md
```

### 4. 验证生成质量

```bash
# Mac 用户
open doc/images/xxx.png

# Linux 用户
xdg-open doc/images/xxx.png
```

## 🚀 高级用法

### 自定义图片尺寸

```bash
# 修改 scripts/build.py 中的 cmd 参数
'-w', '3000',  # 更宽的图片
'-s', '4',     # 更高的缩放
```

### 生成 SVG（矢量图）

```bash
# 修改 mmdc 命令
'-o', str(output_path.with_suffix('.svg')),
```

### 批量转换旧图片

```bash
# 如果之前用在线 API 生成过，想批量替换
python scripts/build.py --all
```

## 📚 相关资源

- **Mermaid 官方文档**：https://mermaid.js.org
- **Mermaid Live Editor**：https://mermaid.live
- **mermaid-cli GitHub**：https://github.com/mermaid-js/mermaid-cli
- **项目仓库**：https://github.com/wangsc02/lessoning-ai

## 🎯 脚本设计原则

1. **通用性**：支持任意 Markdown 文档
2. **简洁性**：一个脚本解决所有问题
3. **可控性**：本地生成，完全可控
4. **可维护性**：清晰的命名和目录结构
5. **幂等性**：重复运行不会产生副作用
