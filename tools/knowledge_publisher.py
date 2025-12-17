#!/usr/bin/env python3
"""
Knowledge Publisher - 知识发布工具

这是一个 Tool，被 Cursor Skills 调用，用于发布知识库到 GitHub。

功能：
  - 提取 Markdown 中的 Mermaid 流程图
  - 生成高质量 PNG 图片（2000px，3x scale）
  - 按文档分子目录管理图片
  - 生成飞书兼容版本
  - 支持批量处理

架构：
  Skill (Command) → Tool (此文件) → Knowledge Base
  
依赖：
  npm install -g @mermaid-js/mermaid-cli

使用：
  # 处理单个文档
  python tools/knowledge_publisher.py knowledge/LangChain1.0深度学习指南.md

  # 批量处理
  python tools/knowledge_publisher.py knowledge/*.md

  # 处理所有文档
  python tools/knowledge_publisher.py --all
"""

import re
import subprocess
import sys
import argparse
from pathlib import Path
import hashlib
import tempfile
from typing import List, Tuple

# GitHub 配置（用于生成图片 URL）
GITHUB_REPO = "wangsc02/lessoning-ai"
GITHUB_BRANCH = "main"

# 图片根目录
IMAGES_ROOT = Path("knowledge/images")


def check_mmdc() -> bool:
    """检查 mmdc 是否已安装"""
    try:
        result = subprocess.run(
            ["mmdc", "--version"], capture_output=True, text=True, timeout=5
        )
        version = result.stdout.strip()
        print(f"✅ mmdc 已安装: {version}\n")
        return True
    except FileNotFoundError:
        print("❌ 错误：mmdc 未安装")
        print("安装方法: npm install -g @mermaid-js/mermaid-cli\n")
        return False
    except Exception as e:
        print(f"❌ 检查 mmdc 失败: {e}\n")
        return False


def extract_mermaid_blocks(md_file: Path) -> Tuple[List[dict], str]:
    """提取所有 Mermaid 代码块"""
    try:
        content = md_file.read_text(encoding="utf-8")
    except Exception as e:
        print(f"❌ 读取文件失败: {e}")
        return [], ""

    pattern = r"```mermaid\n(.*?)```"
    blocks = []

    for i, match in enumerate(re.finditer(pattern, content, re.DOTALL), 1):
        code = match.group(1).strip()
        code_hash = hashlib.md5(code.encode()).hexdigest()[:8]

        blocks.append(
            {"index": i, "code": code, "hash": code_hash, "full_match": match.group(0)}
        )

    return blocks, content


def get_image_path(doc_name: str, index: int, code_hash: str) -> tuple[str, Path]:
    """
    生成图片路径和相对路径
    目录结构: knowledge/images/{文档名}/{序号}_{哈希}.png
    例如: knowledge/images/langchain1/1_abc123.png
    
    返回: (相对路径, 绝对路径)
    """
    # 提取文档名（去掉路径和扩展名）
    doc_base = Path(doc_name).stem

    # 简化文档名（转小写，去掉特殊字符）
    doc_prefix = re.sub(r"[^a-z0-9]+", "_", doc_base.lower())

    # 限制长度
    if len(doc_prefix) > 20:
        doc_prefix = doc_prefix[:20]

    # 图片文件名（不含文档名前缀）
    img_filename = f"{index}_{code_hash}.png"

    # 文档专属目录
    doc_dir = IMAGES_ROOT / doc_prefix

    # 相对路径（用于 GitHub URL）
    rel_path = f"{doc_prefix}/{img_filename}"

    # 绝对路径（用于本地保存）
    abs_path = doc_dir / img_filename

    return rel_path, abs_path


def generate_diagram(mermaid_code: str, output_path: Path) -> bool:
    """使用 mmdc 生成高质量图片"""
    # 创建临时 .mmd 文件
    with tempfile.NamedTemporaryFile(
        mode="w", suffix=".mmd", delete=False, encoding="utf-8"
    ) as f:
        f.write(mermaid_code)
        temp_mmd = f.name

    try:
        # 调用 mmdc
        cmd = [
            "mmdc",
            "-i",
            temp_mmd,
            "-o",
            str(output_path),
            "-w",
            "2000",  # 宽度 2000px
            "-s",
            "3",  # 3倍缩放
            "-b",
            "transparent",  # 透明背景
        ]

        result = subprocess.run(cmd, capture_output=True, text=True, timeout=30)

        if result.returncode == 0 and output_path.exists():
            size = output_path.stat().st_size
            print(f"    ✅ 成功 ({size:,} bytes)")
            return True
        else:
            print(f"    ❌ 失败: {result.stderr}")
            return False

    except subprocess.TimeoutExpired:
        print(f"    ❌ 超时")
        return False
    except Exception as e:
        print(f"    ❌ 错误: {e}")
        return False
    finally:
        Path(temp_mmd).unlink(missing_ok=True)


def build_feishu_version(
    blocks: List[dict], original_content: str, doc_name: str
) -> str:
    """构建飞书版本的 Markdown"""
    new_content = original_content

    for block in blocks:
        i = block["index"]
        img_rel_path, _ = get_image_path(doc_name, i, block["hash"])
        github_url = f"https://raw.githubusercontent.com/{GITHUB_REPO}/{GITHUB_BRANCH}/knowledge/images/{img_rel_path}"

        # 替换内容
        replacement = f"""![流程图 {i}]({github_url})

<details>
<summary>📝 查看/编辑 Mermaid 源码</summary>

```mermaid
{block['code']}```

</details>"""

        new_content = new_content.replace(block["full_match"], replacement, 1)

    return new_content


def process_document(doc_path: Path) -> bool:
    """处理单个文档"""
    print(f"\n{'='*60}")
    print(f"📄 处理文档: {doc_path}")
    print(f"{'='*60}\n")

    # 检查文件是否存在
    if not doc_path.exists():
        print(f"❌ 文件不存在: {doc_path}\n")
        return False

    # 提取 Mermaid 代码块
    blocks, original_content = extract_mermaid_blocks(doc_path)

    if not blocks:
        print(f"ℹ️  未找到 Mermaid 代码块，跳过\n")
        return True

    print(f"📊 找到 {len(blocks)} 个 Mermaid 图表\n")

    # 生成图片
    print("🎨 生成高质量图片（2000px 宽，3x scale）\n")
    success_count = 0
    doc_name = doc_path.stem

    for block in blocks:
        i = block["index"]
        img_rel_path, img_abs_path = get_image_path(doc_name, i, block["hash"])

        # 创建文档专属目录
        img_abs_path.parent.mkdir(parents=True, exist_ok=True)

        print(f"  [{i}/{len(blocks)}] {img_rel_path}")

        if generate_diagram(block["code"], img_abs_path):
            success_count += 1

    # 生成飞书版本
    if success_count > 0:
        output_file = doc_path.parent / f"{doc_path.stem}_feishu.md"
        print(f"\n📝 生成飞书版本: {output_file}")

        feishu_content = build_feishu_version(blocks, original_content, doc_name)
        output_file.write_text(feishu_content, encoding="utf-8")
        print(f"   ✅ 完成\n")

    # 总结
    print(f"✅ 成功生成 {success_count}/{len(blocks)} 个图表")

    return success_count == len(blocks)


def main():
    parser = argparse.ArgumentParser(
        description="通用 Mermaid 图表构建工具",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
示例:
  # 处理单个文档
  python scripts/build.py doc/LangChain1.0深度学习指南.md
  
  # 处理多个文档
  python scripts/build.py doc/LangChain*.md doc/Agent*.md
  
  # 处理所有文档
  python scripts/build.py --all
        """,
    )

    parser.add_argument("files", nargs="*", help="要处理的 Markdown 文件")
    parser.add_argument(
        "--all", action="store_true", help="处理 doc/ 目录下所有 .md 文件"
    )

    args = parser.parse_args()

    # 检查工具
    if not check_mmdc():
        sys.exit(1)

    # 确定要处理的文件
    if args.all:
        doc_files = list(Path("knowledge").glob("*.md"))
    elif args.files:
        doc_files = [Path(f) for f in args.files]
    else:
        print("❌ 请指定要处理的文件或使用 --all\n")
        parser.print_help()
        sys.exit(1)

    # 过滤掉 _feishu.md 文件
    doc_files = [f for f in doc_files if not f.stem.endswith("_feishu")]

    if not doc_files:
        print("❌ 没有找到要处理的文件\n")
        sys.exit(1)

    print(f"\n🚀 准备处理 {len(doc_files)} 个文档\n")

    # 处理所有文档
    success_count = 0
    for doc_file in doc_files:
        if process_document(doc_file):
            success_count += 1

    # 最终总结
    print(f"\n{'='*60}")
    print(f"🎉 完成！成功处理 {success_count}/{len(doc_files)} 个文档")
    print(f"📁 图片根目录: {IMAGES_ROOT.absolute()}")
    print(f"\n后续步骤：")
    print(f"  1. git add knowledge/images/ knowledge/*_feishu.md")
    print(f"  2. git commit -m 'docs: 更新流程图'")
    print(f"  3. git push")
    print(f"  4. 导入飞书版本到飞书文档")
    print(f"{'='*60}\n")


if __name__ == "__main__":
    main()
