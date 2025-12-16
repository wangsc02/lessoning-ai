#!/usr/bin/env python3
"""
自动为飞书导入构建 Markdown 文档
功能：
1. 提取 Mermaid 代码块
2. 调用在线 API 生成图片
3. 替换 Mermaid 为 GitHub Raw URL 图片链接
4. 保留源码在 <details> 折叠块中

使用方法：
  python scripts/build_for_feishu.py
"""

import re
import base64
import requests
from pathlib import Path
import hashlib

# 配置
GITHUB_REPO = "wangsc02/lessoning-ai"
GITHUB_BRANCH = "main"
INPUT_FILE = "doc/LangChain1.0深度学习指南.md"
OUTPUT_FILE = "doc/LangChain1.0深度学习指南_feishu.md"
IMAGE_DIR = Path("doc/images")

def generate_image_from_mermaid(mermaid_code, output_path):
    """使用 Mermaid Ink API 生成图片"""
    # URL-safe base64 编码
    encoded = base64.urlsafe_b64encode(mermaid_code.encode('utf-8')).decode('ascii')
    url = f"https://mermaid.ink/img/{encoded}"
    
    print(f"正在生成: {output_path.name}")
    
    try:
        response = requests.get(url, timeout=30)
        response.raise_for_status()
        
        # 确保目录存在
        output_path.parent.mkdir(parents=True, exist_ok=True)
        
        # 保存图片
        output_path.write_bytes(response.content)
        print(f"  ✅ 成功 ({len(response.content)} bytes)")
        return True
    except Exception as e:
        print(f"  ❌ 失败: {e}")
        return False

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
    
    # 创建图片目录
    IMAGE_DIR.mkdir(parents=True, exist_ok=True)
    
    # 记录替换信息
    replacements = []
    
    for i, match in enumerate(matches, 1):
        mermaid_code = match.group(1).strip()
        
        # 生成唯一文件名（基于内容哈希）
        code_hash = hashlib.md5(mermaid_code.encode()).hexdigest()[:8]
        img_name = f"diagram_{i}_{code_hash}.png"
        img_path = IMAGE_DIR / img_name
        
        # 生成图片
        if generate_image_from_mermaid(mermaid_code, img_path):
            # GitHub Raw URL
            github_url = f"https://raw.githubusercontent.com/{GITHUB_REPO}/{GITHUB_BRANCH}/doc/images/{img_name}"
            
            # 准备替换内容
            replacement = f"""![流程图 {i}]({github_url})

<details>
<summary>📝 查看/编辑 Mermaid 源码</summary>

```mermaid
{mermaid_code}```

</details>"""
            
            replacements.append({
                'original': match.group(0),
                'replacement': replacement
            })
        
        print()  # 空行
    
    # 执行替换
    new_content = content
    for r in replacements:
        new_content = new_content.replace(r['original'], r['replacement'], 1)
    
    # 保存飞书版本
    Path(OUTPUT_FILE).write_text(new_content, encoding='utf-8')
    
    # 总结
    print(f"\n{'='*60}")
    print(f"✅ 成功生成 {len(replacements)}/{len(matches)} 个图表")
    print(f"📁 图片目录: {IMAGE_DIR.absolute()}")
    print(f"📄 飞书版本: {OUTPUT_FILE}")
    print(f"\n后续步骤：")
    print(f"1. git add doc/images/ {OUTPUT_FILE}")
    print(f"2. git commit -m 'docs: add diagrams and feishu version'")
    print(f"3. git push origin main")
    print(f"4. 等待推送完成后，导入 {OUTPUT_FILE} 到飞书")
    print(f"{'='*60}")

if __name__ == '__main__':
    process_markdown()

