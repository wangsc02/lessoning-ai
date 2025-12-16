#!/usr/bin/env python3
"""
统一的文档构建脚本 - 治本方案
功能：
  1. 提取 Markdown 中的 Mermaid 代码块
  2. 使用本地 mmdc 生成高质量 PNG（2000px 宽，3x scale）
  3. 自动更新飞书版本 Markdown
  4. 一键完成所有操作

依赖：
  - npm install -g @mermaid-js/mermaid-cli

使用：
  python scripts/build.py
"""

import re
import subprocess
from pathlib import Path
import hashlib
import tempfile

# 配置
GITHUB_REPO = "wangsc02/lessoning-ai"
GITHUB_BRANCH = "main"
SOURCE_FILE = "doc/LangChain1.0深度学习指南.md"
OUTPUT_FILE = "doc/LangChain1.0深度学习指南_feishu.md"
IMAGE_DIR = Path("doc/images")

# Mermaid CLI 配置（高质量输出）
MERMAID_CONFIG = {
    "theme": "default",
    "themeVariables": {
        "fontSize": "16px",
        "fontFamily": "Arial, sans-serif"
    },
    "flowchart": {
        "nodeSpacing": 50,
        "rankSpacing": 50,
        "curve": "basis"
    }
}

def check_mmdc():
    """检查 mmdc 是否已安装"""
    try:
        result = subprocess.run(['mmdc', '--version'], 
                              capture_output=True, text=True, timeout=5)
        print(f"✅ mmdc 已安装: {result.stdout.strip()}\n")
        return True
    except FileNotFoundError:
        print("❌ 错误：mmdc 未安装")
        print("请运行: npm install -g @mermaid-js/mermaid-cli")
        return False
    except Exception as e:
        print(f"❌ 检查 mmdc 失败: {e}")
        return False

def extract_mermaid_blocks(md_file):
    """提取所有 Mermaid 代码块"""
    content = Path(md_file).read_text(encoding='utf-8')
    pattern = r'```mermaid\n(.*?)```'
    
    blocks = []
    for i, match in enumerate(re.finditer(pattern, content, re.DOTALL), 1):
        code = match.group(1).strip()
        code_hash = hashlib.md5(code.encode()).hexdigest()[:8]
        blocks.append({
            'index': i,
            'code': code,
            'hash': code_hash,
            'full_match': match.group(0)
        })
    
    return blocks, content

def generate_diagram(mermaid_code, output_path):
    """使用 mmdc 生成高质量图片"""
    # 创建临时 .mmd 文件
    with tempfile.NamedTemporaryFile(mode='w', suffix='.mmd', 
                                     delete=False, encoding='utf-8') as f:
        f.write(mermaid_code)
        temp_mmd = f.name
    
    try:
        # 调用 mmdc 生成图片
        # -w 2000: 宽度 2000px
        # -s 3: 3倍缩放（高清）
        # -b transparent: 透明背景
        cmd = [
            'mmdc',
            '-i', temp_mmd,
            '-o', str(output_path),
            '-w', '2000',
            '-s', '3',
            '-b', 'transparent'
        ]
        
        result = subprocess.run(cmd, capture_output=True, text=True, timeout=30)
        
        if result.returncode == 0 and output_path.exists():
            size = output_path.stat().st_size
            print(f"  ✅ 成功 ({size:,} bytes)")
            return True
        else:
            print(f"  ❌ 失败: {result.stderr}")
            return False
            
    except subprocess.TimeoutExpired:
        print(f"  ❌ 超时")
        return False
    except Exception as e:
        print(f"  ❌ 错误: {e}")
        return False
    finally:
        # 清理临时文件
        Path(temp_mmd).unlink(missing_ok=True)

def build_feishu_version(blocks, original_content):
    """构建飞书版本的 Markdown"""
    new_content = original_content
    
    for block in blocks:
        i = block['index']
        img_name = f"diagram_{i}_{block['hash']}.png"
        github_url = f"https://raw.githubusercontent.com/{GITHUB_REPO}/{GITHUB_BRANCH}/doc/images/{img_name}"
        
        # 替换内容
        replacement = f"""![流程图 {i}]({github_url})

<details>
<summary>📝 查看/编辑 Mermaid 源码</summary>

```mermaid
{block['code']}```

</details>"""
        
        new_content = new_content.replace(block['full_match'], replacement, 1)
    
    return new_content

def main():
    print("=" * 60)
    print("统一构建脚本 - 生成高质量流程图")
    print("=" * 60)
    print()
    
    # 检查工具
    if not check_mmdc():
        return
    
    # 读取源文件
    print(f"📖 读取: {SOURCE_FILE}")
    blocks, original_content = extract_mermaid_blocks(SOURCE_FILE)
    print(f"   找到 {len(blocks)} 个 Mermaid 图表\n")
    
    if not blocks:
        print("❌ 没有找到 Mermaid 代码块")
        return
    
    # 创建图片目录
    IMAGE_DIR.mkdir(parents=True, exist_ok=True)
    
    # 生成图片
    print("🎨 生成高质量图片（2000px 宽，3x scale）\n")
    success_count = 0
    
    for block in blocks:
        i = block['index']
        img_name = f"diagram_{i}_{block['hash']}.png"
        img_path = IMAGE_DIR / img_name
        
        print(f"图表 {i}: {img_name}")
        if generate_diagram(block['code'], img_path):
            success_count += 1
        print()
    
    # 生成飞书版本
    if success_count > 0:
        print(f"📝 生成飞书版本: {OUTPUT_FILE}")
        feishu_content = build_feishu_version(blocks, original_content)
        Path(OUTPUT_FILE).write_text(feishu_content, encoding='utf-8')
        print(f"   ✅ 完成\n")
    
    # 总结
    print("=" * 60)
    print(f"✅ 成功生成 {success_count}/{len(blocks)} 个高质量图表")
    print(f"📁 图片目录: {IMAGE_DIR.absolute()}")
    print(f"📄 飞书版本: {OUTPUT_FILE}")
    print()
    print("后续步骤：")
    print("  1. git add doc/images/ doc/*_feishu.md")
    print("  2. git commit -m 'docs: 更新高质量流程图'")
    print("  3. git push")
    print("  4. 复制飞书版本到飞书文档")
    print("=" * 60)

if __name__ == '__main__':
    main()

