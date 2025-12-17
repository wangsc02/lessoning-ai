#!/usr/bin/env python3
"""
Knowledge Publisher - 知识发布工具

这是一个 Tool，被 Cursor Skills 调用，用于发布知识库到 GitHub。

架构设计：
  Skill (轻量级入口) → Tool (所有业务逻辑) → Knowledge Base

功能模式：
  1. --publish  : 完整发布流程（Git 检查 → 图片生成 → 提交 → 推送 → 验证）
  2. --all      : 仅生成图片（不提交推送）
  3. <files>    : 处理指定文档

核心能力：
  - 提取 Markdown 中的 Mermaid 流程图
  - 生成高质量 PNG 图片（2000px，3x scale）
  - 按文档分子目录管理图片
  - 直接在原文档中替换 Mermaid 为图片链接（保留源码在折叠块）
  - 智能生成 commit message
  - Git 操作（检查、提交、推送、验证）

依赖：
  npm install -g @mermaid-js/mermaid-cli

使用示例：
  # 完整发布流程（推荐，由 Skill 调用）
  python tools/knowledge_publisher.py --publish

  # 仅生成图片（适合调试）
  python tools/knowledge_publisher.py --all
  python tools/knowledge_publisher.py knowledge/xxx.md

注意：
  - --publish 会直接修改原文档、提交并推送
  - 图片通过 GitHub Raw URL 引用
  - 飞书导入后可直接显示图片
"""

import re
import subprocess
import sys
import argparse
from pathlib import Path
import hashlib
import tempfile
from typing import List, Tuple, Optional
import time

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


def replace_mermaid_with_images(
    blocks: List[dict], original_content: str, doc_name: str
) -> str:
    """
    将 Mermaid 代码块替换为图片链接 + 折叠的源码
    直接修改原文档，不生成副本
    """
    new_content = original_content

    for block in blocks:
        i = block["index"]
        img_rel_path, _ = get_image_path(doc_name, i, block["hash"])
        github_url = f"https://raw.githubusercontent.com/{GITHUB_REPO}/{GITHUB_BRANCH}/knowledge/images/{img_rel_path}"

        # 替换为：图片 + 折叠的源码
        replacement = f"""![流程图 {i}]({github_url})

<details>
<summary>📝 查看/编辑 Mermaid 源码</summary>

```mermaid
{block['code']}```

</details>"""

        new_content = new_content.replace(block["full_match"], replacement, 1)

    return new_content


# ==================== Git 操作函数 ====================


def run_git_command(cmd: List[str], check: bool = True) -> Tuple[bool, str, str]:
    """运行 Git 命令并返回结果"""
    try:
        result = subprocess.run(
            cmd, capture_output=True, text=True, timeout=30, check=check
        )
        return result.returncode == 0, result.stdout, result.stderr
    except subprocess.TimeoutExpired:
        return False, "", "命令超时"
    except Exception as e:
        return False, "", str(e)


def check_git_status() -> bool:
    """检查 Git 状态，返回是否有修改"""
    print("📋 步骤 1/5: 检查 Git 状态\n")

    # 检查是否有修改（包括 staged 和 unstaged）
    success, stdout, _ = run_git_command(["git", "diff", "--quiet"], check=False)
    has_unstaged = not success

    success, stdout, _ = run_git_command(
        ["git", "diff", "--cached", "--quiet"], check=False
    )
    has_staged = not success

    if has_unstaged or has_staged:
        print("✅ 检测到文件修改\n")
        success, stdout, _ = run_git_command(["git", "status", "--short"])
        print(stdout)
        return True
    else:
        print("ℹ️  没有检测到修改\n")
        return False


def detect_mermaid_in_knowledge() -> List[Path]:
    """检测 Knowledge Base 中包含 Mermaid 的文档"""
    print("📋 步骤 2/5: 检测 Mermaid 代码块\n")

    mermaid_docs = []
    for doc_path in Path("knowledge").glob("*.md"):
        try:
            content = doc_path.read_text(encoding="utf-8")
            if "```mermaid" in content:
                print(f"✅ 发现 Mermaid: {doc_path.name}")
                mermaid_docs.append(doc_path)
        except Exception:
            continue

    print()
    return mermaid_docs


def generate_commit_message() -> str:
    """根据 Git 状态生成智能 commit message"""
    success, stdout, _ = run_git_command(["git", "status", "--short"])
    if not success:
        return "docs: 更新知识库"

    lines = stdout.strip().split("\n")

    # 分析修改类型
    doc_modified = sum(
        1
        for line in lines
        if line.strip().startswith("M") and "knowledge/" in line and ".md" in line
    )
    doc_added = sum(
        1
        for line in lines
        if line.strip().startswith("A") and "knowledge/" in line and ".md" in line
    )
    img_modified = sum(1 for line in lines if "knowledge/images/" in line)

    # 生成消息
    if doc_added > 0:
        # 获取新增文档名
        for line in lines:
            if line.strip().startswith("A") and "knowledge/" in line and ".md" in line:
                doc_name = Path(line.split()[-1]).stem
                return f"docs: 添加知识 {doc_name}"

    if doc_modified > 0 and img_modified > 0:
        return "docs: 更新知识及流程图"
    elif doc_modified > 0:
        return "docs: 更新知识内容"
    elif img_modified > 0:
        return "docs: 更新流程图"

    return "docs: 更新知识库"


def commit_and_push(commit_msg: str) -> Tuple[bool, str]:
    """提交并推送到 GitHub"""
    print("📋 步骤 4/5: 提交并推送\n")

    # 暂存所有修改
    print("📝 暂存修改...")
    success, _, stderr = run_git_command(["git", "add", "-A"])
    if not success:
        return False, f"暂存失败: {stderr}"

    # 提交
    print(f"📝 Commit Message: {commit_msg}")
    success, _, stderr = run_git_command(["git", "commit", "-m", commit_msg])
    if not success:
        return False, f"提交失败: {stderr}"

    print("✅ 提交成功\n")

    # 获取本地 commit hash
    success, local_hash, _ = run_git_command(["git", "rev-parse", "HEAD"])
    if not success:
        return False, "无法获取 commit hash"

    local_hash = local_hash.strip()
    print(f"本地 Commit: {local_hash[:7]}")

    # 推送
    print("正在推送...")
    success, _, stderr = run_git_command(["git", "push"])
    if not success:
        return False, f"推送失败: {stderr}"

    print("✅ 推送命令执行成功\n")

    return True, local_hash


def verify_push(local_hash: str) -> bool:
    """验证推送是否成功"""
    print("📋 步骤 5/5: 验证推送\n")

    # 等待远程更新
    time.sleep(1)

    # 拉取最新信息
    print("正在验证...")
    success, _, _ = run_git_command(["git", "fetch", "origin", "main", "--quiet"])
    if not success:
        print("⚠️  无法验证推送状态\n")
        return False

    # 获取远程 hash
    success, remote_hash, _ = run_git_command(["git", "rev-parse", "origin/main"])
    if not success:
        print("⚠️  无法获取远程 commit\n")
        return False

    remote_hash = remote_hash.strip()

    if local_hash == remote_hash:
        print(f"✅ 验证成功！本地和远程一致\n")
        return True
    else:
        print(f"⚠️  推送可能未完全同步")
        print(f"   本地: {local_hash[:7]}")
        print(f"   远程: {remote_hash[:7]}\n")
        return False


# ==================== 文档处理函数 ====================


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

    # 替换原文档中的 Mermaid 代码块
    if success_count > 0:
        print(f"\n📝 更新原文档: {doc_path}")

        new_content = replace_mermaid_with_images(blocks, original_content, doc_name)
        doc_path.write_text(new_content, encoding="utf-8")
        print(f"   ✅ 已将 Mermaid 代码块替换为图片链接\n")

    # 总结
    print(f"✅ 成功生成 {success_count}/{len(blocks)} 个图表")

    return success_count == len(blocks)


def publish() -> int:
    """
    完整的发布流程：检查 → 生成图片 → 提交 → 推送 → 验证
    返回退出码：0=成功，1=失败
    """
    print("=" * 60)
    print("📦 自动化知识发布流程")
    print("=" * 60)
    print()

    # 步骤 1: 检查 Git 状态
    if not check_git_status():
        print("ℹ️  没有修改需要发布，退出")
        return 0

    # 步骤 2: 检测 Mermaid
    mermaid_docs = detect_mermaid_in_knowledge()

    # 步骤 3: 生成图片（如果需要）
    if mermaid_docs:
        print("📋 步骤 3/5: 生成高质量流程图\n")

        if not check_mmdc():
            return 1

        success_count = 0
        for doc_path in mermaid_docs:
            if process_document(doc_path):
                success_count += 1

        if success_count == 0:
            print("\n❌ 图片生成失败")
            return 1

        print(f"\n✅ 成功生成 {success_count}/{len(mermaid_docs)} 个文档的流程图\n")
    else:
        print("ℹ️  无需生成图片\n")
        print("📋 步骤 3/5: 跳过图片生成\n")

    # 步骤 4: 生成 commit message 并提交推送
    commit_msg = generate_commit_message()
    success, result = commit_and_push(commit_msg)

    if not success:
        print(f"❌ {result}")
        return 1

    local_hash = result

    # 步骤 5: 验证推送
    verify_push(local_hash)

    # 最终总结
    print("=" * 60)
    print("🎉 发布成功！")
    print("=" * 60)
    print()
    print("📊 本次提交信息：")
    print(f"   Commit: {local_hash[:7]}")
    print(f"   Message: {commit_msg}")
    print()
    print("🔗 GitHub 链接：")
    print(f"   https://github.com/{GITHUB_REPO}/commit/{local_hash}")
    print()
    print("📁 查看 Knowledge Base：")
    print(f"   https://github.com/{GITHUB_REPO}/tree/{GITHUB_BRANCH}/knowledge")
    print()

    return 0


def build_only(doc_files: List[Path]) -> int:
    """
    仅生成图片（不提交推送）
    返回退出码：0=成功，1=失败
    """
    # 检查工具
    if not check_mmdc():
        return 1

    if not doc_files:
        print("❌ 没有找到要处理的文件\n")
        return 1

    print(f"\n🚀 准备处理 {len(doc_files)} 个文档\n")

    # 处理所有文档
    success_count = 0
    for doc_file in doc_files:
        if process_document(doc_file):
            success_count += 1

    # 总结
    print(f"\n{'='*60}")
    print(f"🎉 完成！成功处理 {success_count}/{len(doc_files)} 个文档")
    print(f"📁 图片根目录: {IMAGES_ROOT.absolute()}")
    print(f"\n✅ 已更新原文档：")
    print(f"  - Mermaid 代码块 → 图片链接 + 折叠源码")
    print(f"  - 可直接复制到飞书，图片自动加载")
    print(f"\n后续步骤：")
    print(f"  1. git add knowledge/")
    print(f"  2. git commit -m 'docs: 更新流程图'")
    print(f"  3. git push")
    print(f"{'='*60}\n")

    return 0 if success_count == len(doc_files) else 1


def main():
    parser = argparse.ArgumentParser(
        description="Knowledge Publisher - 知识发布工具",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
示例:
  # 完整发布流程（检测 → 生成图片 → 提交 → 推送 → 验证）
  python tools/knowledge_publisher.py --publish
  
  # 仅生成图片（不提交推送）
  python tools/knowledge_publisher.py --all
  python tools/knowledge_publisher.py knowledge/xxx.md
        """,
    )

    parser.add_argument("files", nargs="*", help="要处理的 Markdown 文件")
    parser.add_argument(
        "--all", action="store_true", help="处理 knowledge/ 目录下所有 .md 文件"
    )
    parser.add_argument(
        "--publish",
        action="store_true",
        help="完整发布流程（检测 → 生成 → 提交 → 推送）",
    )

    args = parser.parse_args()

    # 模式 1: 完整发布流程
    if args.publish:
        sys.exit(publish())

    # 模式 2: 仅生成图片
    if args.all:
        doc_files = list(Path("knowledge").glob("*.md"))
    elif args.files:
        doc_files = [Path(f) for f in args.files]
    else:
        print("❌ 请指定模式：\n")
        print("  --publish        完整发布流程")
        print("  --all            处理所有文档")
        print("  <files>          处理指定文档\n")
        parser.print_help()
        sys.exit(1)

    sys.exit(build_only(doc_files))


if __name__ == "__main__":
    main()
