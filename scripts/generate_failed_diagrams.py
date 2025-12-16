#!/usr/bin/env python3
"""
使用 Kroki API 生成失败的流程图
Kroki 支持更多 Mermaid 图表类型
"""

import requests
import base64
from pathlib import Path

# 失败的 Mermaid 代码（从原文档提取）
failed_diagrams = {
    "diagram_2": """stateDiagram-v2
  [*] --> init
  init --> plan
  plan --> act
  act --> observe
  observe --> decide
  decide --> done
  decide --> plan

  state act {
    [*] --> callTool
    callTool --> callModel
    callModel --> [*]
  }""",
    
    "diagram_4": """flowchart TD
  inNode[Input] --> seqA[Seq_A]
  seqA --> seqB[Seq_B]
  seqB --> out1[Output]

  inNode --> parA[Par_A]
  inNode --> parB[Par_B]
  parA --> joinP[Join]
  parB --> joinP
  joinP --> out2[Output]

  inNode --> router[Router]
  router --> path1[Path_1]
  router --> path2[Path_2]
  path1 --> out3[Output]
  path2 --> out3""",
    
    "diagram_5": """sequenceDiagram
  participant Human as Human
  participant Agent as Agent
  participant Model as Model
  participant Tool as Tool

  Human->>Agent: user_input
  Agent->>Model: messages(System+History+Human)
  Model-->>Agent: ai_message_with_tool_intent
  Agent->>Tool: tool_call(name,args)
  Tool-->>Agent: tool_result
  Agent->>Model: messages(+ToolMessage)
  Model-->>Agent: final_answer""",
    
    "diagram_6": """sequenceDiagram
  participant User as User
  participant App as App
  participant Retriever as Retriever
  participant Store as VectorStore
  participant Model as LLM

  User->>App: question
  App->>Retriever: build_query(question)
  Retriever->>Store: similarity_search(query)
  Store-->>Retriever: docs_with_scores
  Retriever-->>App: topk_docs
  App->>Model: prompt(question+contexts+citation_rules)
  Model-->>App: answer_with_citations
  App-->>User: answer + sources""",
    
    "diagram_8": """flowchart TD
  sup[Supervisor] --> a1[Agent_Research]
  sup --> a2[Agent_Dev]
  sup --> a3[Agent_Review]
  a1 --> sup
  a2 --> sup
  a3 --> sup
  sup --> out[Final]""",
    
    "diagram_9": """flowchart TD
  q1["Need_State_Resume?"] -->|Yes| g1["Use_GraphRuntime"]
  q1 -->|No| q2["Need_RAG_Verifiable?"]
  q2 -->|Yes| r1["Build_RAG_With_Citations"]
  q2 -->|No| q3["Need_Tools?"]
  q3 -->|Yes| a1["Agent_With_Governance"]
  q3 -->|No| s1["Direct_Model_Call"]"""
}

def generate_via_kroki(mermaid_code, output_path):
    """使用 Kroki API 生成图片"""
    # Kroki API endpoint
    url = "https://kroki.io/mermaid/png"
    
    # 发送 POST 请求
    headers = {'Content-Type': 'text/plain'}
    
    print(f"正在生成: {output_path.name}")
    
    try:
        response = requests.post(url, data=mermaid_code.encode('utf-8'), 
                               headers=headers, timeout=30)
        response.raise_for_status()
        
        # 保存图片
        output_path.parent.mkdir(parents=True, exist_ok=True)
        output_path.write_bytes(response.content)
        
        print(f"  ✅ 成功 ({len(response.content)} bytes)")
        return True
    except Exception as e:
        print(f"  ❌ 失败: {e}")
        return False

def main():
    image_dir = Path("doc/images")
    success_count = 0
    
    print("使用 Kroki API 生成失败的流程图\n")
    
    for name, code in failed_diagrams.items():
        output_path = image_dir / f"{name}.png"
        if generate_via_kroki(code, output_path):
            success_count += 1
        print()
    
    print(f"\n{'='*60}")
    print(f"✅ 成功生成 {success_count}/{len(failed_diagrams)} 个图表")
    print(f"📁 输出目录: {image_dir.absolute()}")
    print(f"\n后续步骤：")
    print(f"1. git add doc/images/")
    print(f"2. git commit -m 'docs: add remaining diagrams'")
    print(f"3. git push")
    print(f"4. 重新运行 python scripts/build_for_feishu.py")
    print(f"{'='*60}")

if __name__ == '__main__':
    main()

