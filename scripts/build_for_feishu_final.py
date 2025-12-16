#!/usr/bin/env python3
"""
最终版本：使用已生成的图片构建飞书文档
不再调用 API，直接使用 doc/images/ 中的图片
"""

import re
from pathlib import Path

# 配置
GITHUB_REPO = "wangsc02/lessoning-ai"
GITHUB_BRANCH = "main"
INPUT_FILE = "doc/LangChain1.0深度学习指南.md"
OUTPUT_FILE = "doc/LangChain1.0深度学习指南_feishu.md"
IMAGE_DIR = Path("doc/images")

# 图片映射（按照文档中出现的顺序）
IMAGE_MAP = {
    1: "diagram_1_49c518d7.png",  # v0.x vs v1.0 对比
    2: "diagram_2.png",            # LangGraph 状态机
    3: "diagram_3_2cf8d1f8.png",  # 模块依赖关系
    4: "diagram_4.png",            # Runnable 组合模式
    5: "diagram_5.png",            # ReAct 消息流
    6: "diagram_6.png",            # RAG 数据流
    7: "diagram_7_da413455.png",  # Agent 状态机
    8: "diagram_8.png",            # Multi-Agent 拓扑
    9: "diagram_9.png",            # 决策树
}

def process_markdown():
    """处理 Markdown 文件"""
    print(f"📖 读取文件: {INPUT_FILE}\n")
    
    content = Path(INPUT_FILE).read_text(encoding='utf-8')
    
    # 匹配所有 Mermaid 代码块
    pattern = r'```mermaid\n(.*?)```'
    matches = list(re.finditer(pattern, content, re.DOTALL))
    
    print(f"找到 {len(matches)} 个 Mermaid 图表\n")
    
    if not matches:
        print("没有找到 Mermaid 代码块")
        return
    
    # 检查图片是否都存在
    missing = []
    for i, img_name in IMAGE_MAP.items():
        img_path = IMAGE_DIR / img_name
        if not img_path.exists():
            missing.append(img_name)
            print(f"  ⚠️  缺失: {img_name}")
        else:
            print(f"  ✅ 存在: {img_name}")
    
    if missing:
        print(f"\n❌ 缺少 {len(missing)} 张图片，请先运行生成脚本")
        return
    
    print("\n开始替换...\n")
    
    # 准备替换
    new_content = content
    for i, match in enumerate(matches, 1):
        mermaid_code = match.group(1).strip()
        img_name = IMAGE_MAP.get(i, f"diagram_{i}.png")
        
        # GitHub Raw URL
        github_url = f"https://raw.githubusercontent.com/{GITHUB_REPO}/{GITHUB_BRANCH}/doc/images/{img_name}"
        
        # 准备替换内容
        replacement = f"""![流程图 {i}]({github_url})

<details>
<summary>📝 查看/编辑 Mermaid 源码</summary>

```mermaid
{mermaid_code}```

</details>"""
        
        # 执行替换
        new_content = new_content.replace(match.group(0), replacement, 1)
        print(f"  ✅ 图表 {i}: {img_name}")
    
    # 保存飞书版本
    Path(OUTPUT_FILE).write_text(new_content, encoding='utf-8')
    
    # 总结
    print(f"\n{'='*60}")
    print(f"✅ 成功生成飞书版本")
    print(f"📄 文件: {OUTPUT_FILE}")
    print(f"\n📊 图片链接示例：")
    print(f"   {github_url}")
    print(f"\n后续步骤：")
    print(f"1. git add {OUTPUT_FILE}")
    print(f"2. git commit -m 'docs: update feishu version with all diagrams'")
    print(f"3. git push")
    print(f"4. 复制 {OUTPUT_FILE} 的内容到飞书")
    print(f"   → 所有 9 张图会自动显示！")
    print(f"{'='*60}")

if __name__ == '__main__':
    process_markdown()

