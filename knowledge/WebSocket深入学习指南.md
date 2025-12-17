# WebSocket深入学习指南 - 从原理到实践

## 目录
1. [WebSocket是什么](#websocket是什么)
2. [为什么需要WebSocket](#为什么需要websocket)
3. [WebSocket协议详解](#websocket协议详解)
4. [握手过程深度解析](#握手过程深度解析)
5. [数据帧结构](#数据帧结构)
6. [连接生命周期管理](#连接生命周期管理)
7. [心跳与重连机制](#心跳与重连机制)
8. [消息传输模式](#消息传输模式)
9. [安全性考虑](#安全性考虑)
10. [实战应用场景](#实战应用场景)
11. [性能优化](#性能优化)
12. [与其他技术对比](#与其他技术对比)

---

## WebSocket是什么

### 简单定义

**WebSocket** 是一种在单个TCP连接上进行**全双工通信**的协议，允许服务器主动向客户端推送数据。

### 生活化理解

想象一下打电话和发短信的区别：

```
传统HTTP（短信模式）：
客户端: "你好，请给我最新消息"
服务器: "好的，这是消息A"
    ↓
客户端: "还有新消息吗？"（再次询问）
服务器: "没有了"
    ↓
客户端: "现在有吗？"（又问一次）
服务器: "有，这是消息B"

每次都要主动询问，很麻烦！

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

WebSocket（电话模式）：
客户端: "你好，我们建立一个长期通话吧"
服务器: "好的，连接建立！"
    ↓
【保持连接】
    ↓
服务器: "有新消息A"（主动发送）
客户端: "收到"
    ↓
客户端: "我有个请求B"
服务器: "好的，这是回复B"
    ↓
服务器: "又有新消息C"（主动发送）

随时可以互相发送，就像打电话！
```

### 核心特点

```
┌────────────────────────────────────────────┐
│  WebSocket 五大特性                         │
├────────────────────────────────────────────┤
│  ✅ 全双工通信                              │
│     客户端和服务器可以同时发送数据           │
│                                            │
│  ✅ 持久连接                                │
│     一次握手，保持连接，不需要反复建立       │
│                                            │
│  ✅ 低延迟                                  │
│     没有HTTP的请求头开销                    │
│                                            │
│  ✅ 服务器推送                              │
│     服务器可以主动向客户端发送数据           │
│                                            │
│  ✅ 跨域支持                                │
│     支持跨域通信（需服务器允许）             │
└────────────────────────────────────────────┘
```

---

## 为什么需要WebSocket

### HTTP的局限性

```
HTTP/1.1的问题：

1. 半双工通信
   ┌────────┐                    ┌────────┐
   │ 客户端  │ ─── 请求 ────────→ │ 服务器  │
   │        │                    │        │
   │        │ ←── 响应 ───────── │        │
   └────────┘                    └────────┘
   
   必须先请求，再响应，不能同时进行

2. 请求头开销大
   GET /api/messages HTTP/1.1
   Host: example.com
   User-Agent: Mozilla/5.0...
   Accept: */*
   Accept-Encoding: gzip, deflate
   Connection: keep-alive
   Cookie: session_id=abc123...
   ...（可能几百字节）
   
   每次请求都要携带完整的头部

3. 服务器无法主动推送
   服务器有新消息，但客户端不知道
   只能客户端不断轮询

4. 资源浪费
   轮询会产生大量无效请求
```

### 轮询方案的演进

```
方案1：短轮询（Short Polling）

客户端                      服务器
  │                           │
  │ ──── 有新消息吗？────────→ │
  │ ←──── 没有 ──────────────  │
  │                           │
  │ [等待3秒]                 │
  │                           │
  │ ──── 有新消息吗？────────→ │
  │ ←──── 没有 ──────────────  │
  │                           │
  │ [等待3秒]                 │
  │                           │
  │ ──── 有新消息吗？────────→ │
  │ ←──── 有，消息A ──────────  │

缺点：
❌ 大量无效请求
❌ 延迟高（取决于轮询间隔）
❌ 服务器压力大

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

方案2：长轮询（Long Polling）

客户端                      服务器
  │                           │
  │ ──── 有新消息吗？────────→ │
  │                           │ [保持连接]
  │                           │ [等待新消息]
  │                           │ [30秒后仍无消息]
  │ ←──── 没有 ──────────────  │
  │                           │
  │ ──── 有新消息吗？────────→ │
  │                           │ [保持连接]
  │                           │ [5秒后有消息]
  │ ←──── 有，消息A ──────────  │
  │                           │
  │ ──── 有新消息吗？────────→ │ [立即重连]

优点：
✅ 减少无效请求
✅ 延迟较低

缺点：
❌ 服务器需要维持大量连接
❌ 仍然有HTTP开销
❌ 编程复杂

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

方案3：WebSocket（终极方案）

客户端                      服务器
  │                           │
  │ ──── 握手请求 ──────────→ │
  │ ←──── 握手成功 ──────────  │
  │                           │
  │ ═════ 建立连接 ══════════ │
  │                           │
  │ ←──── 消息A ────────────  │
  │ ──── 收到确认 ──────────→ │
  │ ←──── 消息B ────────────  │
  │ ──── 查询请求 ──────────→ │
  │ ←──── 查询结果 ──────────  │
  │                           │
  │ ═════ 持续连接 ══════════ │

优点：
✅ 一次握手，持久连接
✅ 双向通信，延迟极低
✅ 数据帧开销小（2-14字节）
✅ 服务器可主动推送
```

### 性能对比

```
传输1000条消息的开销对比：

┌──────────────┬──────────┬──────────┬──────────┐
│  方案        │ 请求次数  │ 总开销    │ 平均延迟  │
├──────────────┼──────────┼──────────┼──────────┤
│ 短轮询(3s)   │  1000次  │  ~800KB  │  1.5秒   │
│ 长轮询       │  1000次  │  ~750KB  │  50ms    │
│ WebSocket    │  1次握手 │  ~50KB   │  10ms    │
└──────────────┴──────────┴──────────┴──────────┘

WebSocket优势：
- 流量节省：94% ↓
- 延迟降低：99% ↓
- 服务器压力：80% ↓
```

---

## WebSocket协议详解

### 协议规范

```
WebSocket协议标准：
- RFC 6455（2011年）
- 基于TCP
- 默认端口：80（ws://）、443（wss://）
- URI格式：ws://example.com:8080/path?query=value

协议特点：
1. 基于HTTP升级机制
2. 使用TCP作为传输层
3. 支持文本和二进制数据
4. 内置Ping/Pong心跳
```

### 协议层次结构

```
┌─────────────────────────────────────────┐
│         应用层（业务逻辑）               │
│  - 聊天消息                             │
│  - 实时通知                             │
│  - 数据推送                             │
└──────────────────┬──────────────────────┘
                   │
┌──────────────────┴──────────────────────┐
│      WebSocket协议层                     │
│  ┌────────────────────────────────────┐ │
│  │  连接管理                          │ │
│  │  - 握手                            │ │
│  │  - 心跳                            │ │
│  │  - 关闭                            │ │
│  ├────────────────────────────────────┤ │
│  │  数据帧                            │ │
│  │  - 帧类型识别                      │ │
│  │  - 分片处理                        │ │
│  │  - 掩码处理                        │ │
│  ├────────────────────────────────────┤ │
│  │  消息传输                          │ │
│  │  - 文本消息                        │ │
│  │  - 二进制消息                      │ │
│  │  - 控制帧                          │ │
│  └────────────────────────────────────┘ │
└──────────────────┬──────────────────────┘
                   │
┌──────────────────┴──────────────────────┐
│         TCP传输层                        │
│  - 可靠传输                             │
│  - 流量控制                             │
│  - 拥塞控制                             │
└──────────────────┬──────────────────────┘
                   │
┌──────────────────┴──────────────────────┐
│         IP网络层                         │
└─────────────────────────────────────────┘
```

---

## 握手过程深度解析

### 握手流程

WebSocket使用HTTP协议完成握手，然后升级为WebSocket协议。

```
完整握手过程：

客户端                                    服务器
  │                                         │
  │ ① HTTP Upgrade请求                      │
  ├────────────────────────────────────────→│
  │  GET /chat HTTP/1.1                    │
  │  Host: example.com                     │
  │  Upgrade: websocket                    │
  │  Connection: Upgrade                   │
  │  Sec-WebSocket-Key: dGhlIHNhbXBsZQ==   │
  │  Sec-WebSocket-Version: 13             │
  │  Origin: http://example.com            │
  │                                         │
  │                              ② 服务器验证 │
  │                              - 检查Key   │
  │                              - 生成Accept │
  │                              - 验证Origin │
  │                                         │
  │ ③ HTTP 101 Switching Protocols         │
  │←────────────────────────────────────────┤
  │  HTTP/1.1 101 Switching Protocols      │
  │  Upgrade: websocket                    │
  │  Connection: Upgrade                   │
  │  Sec-WebSocket-Accept: s3pPLMBiTxaQ9...│
  │                                         │
  │ ④ 协议升级完成，切换到WebSocket          │
  │═════════════════════════════════════════│
  │         WebSocket连接建立               │
  │                                         │
```

### 握手请求详解

```
客户端请求（逐字段解释）：

GET /chat HTTP/1.1                         ← 必须是GET请求
Host: example.com:8080                     ← 服务器地址
Upgrade: websocket                         ← 要升级的协议
Connection: Upgrade                        ← 连接升级标识
Sec-WebSocket-Key: dGhlIHNhbXBsZQ==       ← 随机生成的Base64密钥
                                            （16字节随机数编码）
Sec-WebSocket-Version: 13                  ← WebSocket版本号
                                            （13是当前标准版本）
Origin: http://example.com                 ← 请求来源（跨域检查用）

可选字段：
Sec-WebSocket-Protocol: chat, superchat    ← 子协议（应用层协议）
Sec-WebSocket-Extensions: permessage-deflate ← 扩展（如压缩）
```

### 服务器响应详解

```
服务器响应（逐字段解释）：

HTTP/1.1 101 Switching Protocols           ← 101状态码表示协议切换
Upgrade: websocket                         ← 确认升级到WebSocket
Connection: Upgrade                        ← 确认连接升级
Sec-WebSocket-Accept: s3pPLMBiTxaQ9kYGzzhZRbK+xOo= 
                                           ↑ 验证密钥
                                           计算方式：
                                           Base64(SHA1(
                                               Sec-WebSocket-Key + 
                                               "258EAFA5-E914-47DA-95CA-C5AB0DC85B11"
                                           ))

可选响应：
Sec-WebSocket-Protocol: chat               ← 选择的子协议
Sec-WebSocket-Extensions: permessage-deflate ← 启用的扩展
```

### 密钥计算过程

```
验证密钥的计算（防止非WebSocket客户端连接）：

步骤详解：

1. 客户端生成随机Key
   randomBytes = [0x12, 0x34, 0x56, ...]  // 16字节随机数
   clientKey = Base64(randomBytes)
   // 结果: "dGhlIHNhbXBsZQ=="

2. 服务器接收Key后，进行计算
   magicString = "258EAFA5-E914-47DA-95CA-C5AB0DC85B11"  // RFC标准GUID
   
   concatenated = clientKey + magicString
   // "dGhlIHNhbXBsZQ==258EAFA5-E914-47DA-95CA-C5AB0DC85B11"
   
3. SHA-1哈希
   hash = SHA1(concatenated)
   // 结果: [0xb3, 0x7a, 0x4f, ...]  // 20字节
   
4. Base64编码
   serverAccept = Base64(hash)
   // "s3pPLMBiTxaQ9kYGzzhZRbK+xOo="

5. 客户端验证
   客户端收到Accept后，用同样方法计算并比对
   如果匹配，握手成功！

为什么这样设计？
✅ 防止非WebSocket客户端误连接
✅ 防止缓存服务器干扰
✅ 确保客户端理解WebSocket协议
```

### 握手失败的情况

```
常见握手失败原因：

1. 服务器不支持WebSocket
   HTTP/1.1 400 Bad Request
   原因：服务器不识别Upgrade头

2. 版本不匹配
   HTTP/1.1 426 Upgrade Required
   Sec-WebSocket-Version: 13
   原因：客户端版本过旧

3. Origin不被允许（跨域限制）
   HTTP/1.1 403 Forbidden
   原因：安全策略阻止

4. Key验证失败
   连接被关闭
   原因：Accept计算错误

5. 子协议不支持
   HTTP/1.1 400 Bad Request
   原因：服务器不支持请求的子协议
```

---

## 数据帧结构

### WebSocket帧格式

WebSocket的数据以**帧（Frame）**为单位传输，每一帧有统一的结构。

```
完整的帧结构（RFC 6455）：

 0                   1                   2                   3
 0 1 2 3 4 5 6 7 8 9 0 1 2 3 4 5 6 7 8 9 0 1 2 3 4 5 6 7 8 9 0 1
┌─┬─┬─┬─┬───────┬─┬───────┬───────────────────────────────────┐
│F│R│R│R│ Opcode│M│Payload│  Extended Payload Length          │
│I│S│S│S│(4bit) │A│ Len   │  (16bit or 64bit, 可选)          │
│N│V│V│V│       │S│(7bit) │                                   │
│ │1│2│3│       │K│       │                                   │
├─┴─┴─┴─┴───────┴─┴───────┴───────────────────────────────────┤
│  Extended Payload Length continued (if Payload Len == 127)  │
├─────────────────────────────────────────────────────────────┤
│  Masking-key (32bit) [客户端→服务器时必须]                   │
├─────────────────────────────────────────────────────────────┤
│  Payload Data (可变长度)                                     │
│  - Extension data                                           │
│  - Application data                                         │
└─────────────────────────────────────────────────────────────┘

字段详解：

┌────────────┬─────────────────────────────────────────┐
│ 字段名      │ 说明                                     │
├────────────┼─────────────────────────────────────────┤
│ FIN (1bit) │ 是否是消息的最后一帧                      │
│            │ 1=最后一帧, 0=还有后续帧                  │
├────────────┼─────────────────────────────────────────┤
│ RSV1-3     │ 保留位，用于扩展                          │
│ (3bit)     │ 默认为0，除非协商了扩展                   │
├────────────┼─────────────────────────────────────────┤
│ Opcode     │ 帧类型                                   │
│ (4bit)     │ 0x0=继续帧                               │
│            │ 0x1=文本帧                               │
│            │ 0x2=二进制帧                             │
│            │ 0x8=关闭帧                               │
│            │ 0x9=Ping帧                               │
│            │ 0xA=Pong帧                               │
├────────────┼─────────────────────────────────────────┤
│ MASK       │ 是否使用掩码                             │
│ (1bit)     │ 客户端→服务器: 必须为1                   │
│            │ 服务器→客户端: 必须为0                   │
├────────────┼─────────────────────────────────────────┤
│ Payload    │ 数据长度                                 │
│ Length     │ 0-125: 实际长度                          │
│ (7bit)     │ 126: 后续2字节表示长度（最大64KB）        │
│            │ 127: 后续8字节表示长度（最大2^63）        │
├────────────┼─────────────────────────────────────────┤
│ Masking    │ 掩码密钥（4字节）                        │
│ Key        │ 仅当MASK=1时存在                         │
│ (32bit)    │ 用于异或加密payload                      │
├────────────┼─────────────────────────────────────────┤
│ Payload    │ 实际传输的数据                           │
│ Data       │ 如果MASK=1，需要先解码                   │
└────────────┴─────────────────────────────────────────┘
```

### 帧类型详解

```
数据帧（Data Frames）：

1. 文本帧（0x1）
   ┌────────────────┐
   │ Opcode: 0x1    │
   │ Payload: UTF-8 │
   └────────────────┘
   
   示例：
   发送 "Hello"
   → 0x81 0x85 [mask] [masked "Hello"]

2. 二进制帧（0x2）
   ┌────────────────┐
   │ Opcode: 0x2    │
   │ Payload: bytes │
   └────────────────┘
   
   示例：
   发送图片、文件等二进制数据

3. 继续帧（0x0）
   ┌────────────────┐
   │ Opcode: 0x0    │
   │ FIN: 0         │
   └────────────────┘
   
   用于分片传输大消息

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

控制帧（Control Frames）：

1. 关闭帧（0x8）
   ┌───────────────────────────┐
   │ Opcode: 0x8               │
   │ Payload:                  │
   │  - 状态码（2字节）          │
   │  - 原因（UTF-8文本）        │
   └───────────────────────────┘
   
   常见状态码：
   1000: 正常关闭
   1001: 端点离开
   1002: 协议错误
   1003: 不可接受的数据类型
   1006: 异常关闭（无关闭帧）
   1009: 消息太大
   1011: 服务器错误

2. Ping帧（0x9）
   ┌───────────────────────────┐
   │ Opcode: 0x9               │
   │ Payload: 可选数据          │
   └───────────────────────────┘
   
   用于心跳检测，保持连接活跃

3. Pong帧（0xA）
   ┌───────────────────────────┐
   │ Opcode: 0xA               │
   │ Payload: 与Ping相同        │
   └───────────────────────────┘
   
   响应Ping帧

控制帧特点：
✅ 不能分片（FIN必须为1）
✅ 长度不能超过125字节
✅ 可以插入数据帧之间
```

### 掩码机制

```
为什么客户端必须使用掩码？

历史背景：
某些代理服务器会缓存WebSocket数据
如果数据看起来像HTTP响应，会造成安全问题

掩码算法：

1. 生成4字节随机掩码
   maskingKey = [0x12, 0x34, 0x56, 0x78]

2. 对每个字节进行异或
   originalData = [0x48, 0x65, 0x6C, 0x6C, 0x6F]  // "Hello"
   
   maskedData[0] = originalData[0] XOR maskingKey[0]
                 = 0x48 XOR 0x12 = 0x5A
   
   maskedData[1] = originalData[1] XOR maskingKey[1]
                 = 0x65 XOR 0x34 = 0x51
   
   maskedData[2] = originalData[2] XOR maskingKey[2]
                 = 0x6C XOR 0x56 = 0x3A
   
   ...以此类推，使用 maskingKey[i % 4]

3. 解码（相同的操作）
   originalData[i] = maskedData[i] XOR maskingKey[i % 4]
   
伪代码：

function maskData(data, maskingKey) {
    masked = new byte[data.length]
    
    for (i = 0; i < data.length; i++) {
        masked[i] = data[i] XOR maskingKey[i % 4]
    }
    
    return masked
}

特点：
✅ 异或运算可逆（加密解密用同一方法）
✅ 运算速度快
✅ 不是为了安全（仅防止缓存）
```

### 消息分片

```
大消息分片传输：

场景：发送1MB的文件

不分片（不推荐）：
┌─────────────────────────────┐
│ FIN=1, Opcode=0x2, Len=1MB  │ ← 单个巨大帧
│ Payload: [1MB data]         │
└─────────────────────────────┘

问题：
- 内存占用大
- 可能阻塞其他消息
- 传输失败需重传整个消息

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

分片传输（推荐）：

第一片：
┌─────────────────────────────┐
│ FIN=0, Opcode=0x2, Len=256K │ ← 开始，指定类型
│ Payload: [256K data]        │
└─────────────────────────────┘

中间片：
┌─────────────────────────────┐
│ FIN=0, Opcode=0x0, Len=256K │ ← 继续帧
│ Payload: [256K data]        │
└─────────────────────────────┘
┌─────────────────────────────┐
│ FIN=0, Opcode=0x0, Len=256K │
│ Payload: [256K data]        │
└─────────────────────────────┘

最后一片：
┌─────────────────────────────┐
│ FIN=1, Opcode=0x0, Len=256K │ ← 结束标记
│ Payload: [256K data]        │
└─────────────────────────────┘

优点：
✅ 内存友好
✅ 可以插入控制帧（Ping/Pong）
✅ 失败只需重传部分

重要规则：
- 第一帧指定消息类型（0x1或0x2）
- 后续帧都是继续帧（0x0）
- 最后一帧设置FIN=1
- 分片过程中不能插入其他数据帧
- 但可以插入控制帧
```

### 实际传输示例

```
示例1：发送短文本 "Hi"

二进制表示：
┌──────────┬──────────┬──────────┬──────────┬──────────┬──────────┬──────────┬──────────┐
│ 10000001 │ 10000010 │ 00010010 │ 00110100 │ 01011010 │ 01010001 │          │          │
├──────────┼──────────┼──────────┼──────────┼──────────┼──────────┤          │          │
│  0x81    │  0x82    │  0x12    │  0x34    │  0x5A    │  0x51    │          │          │
├──────────┼──────────┼──────────┼──────────┼──────────┼──────────┤          │          │
│ FIN=1    │ MASK=1   │          Masking Key           │  Masked Data        │          │
│ Opcode=1 │ Len=2    │                                │  "Hi"               │          │
│(文本帧)  │          │                                │                     │          │
└──────────┴──────────┴──────────┴──────────┴──────────┴──────────┴──────────┴──────────┘

解析过程：
1. 第1字节 0x81
   FIN=1 (最后一帧)
   Opcode=0x1 (文本帧)

2. 第2字节 0x82
   MASK=1 (有掩码)
   Len=2 (2字节数据)

3. 第3-6字节：掩码密钥
   [0x12, 0x34, 0x56, 0x78]

4. 第7-8字节：掩码数据
   解码:
   0x5A XOR 0x12 = 0x48 ('H')
   0x51 XOR 0x34 = 0x65 ('i')

最终消息："Hi"

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

示例2：发送中等长度数据（300字节）

┌──────────┬──────────┬──────────┬──────────┬──────────┬────────┐
│  0x81    │  0xFE    │  0x01    │  0x2C    │ [4 bytes│ [300   │
│          │          │          │          │  mask]  │ bytes] │
├──────────┼──────────┼──────────┼──────────┼─────────┼────────┤
│ FIN=1    │ MASK=1   │    Extended Len     │  掩码    │  数据   │
│ Opcode=1 │ Len=126  │    = 300 (0x012C)   │         │        │
└──────────┴──────────┴──────────┴──────────┴─────────┴────────┘

说明：
- Len=126 表示使用16位扩展长度
- 后续2字节表示实际长度（300）

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

示例3：服务器发送Ping

┌──────────┬──────────┬──────────┬──────────┐
│  0x89    │  0x04    │ 'p'  'i' │ 'n'  'g' │
├──────────┼──────────┼──────────┼──────────┤
│ FIN=1    │ MASK=0   │     Payload Data    │
│ Opcode=9 │ Len=4    │     "ping"          │
│(Ping帧)  │(服务器)  │                     │
└──────────┴──────────┴──────────┴──────────┘

客户端收到后回复Pong：
┌──────────┬──────────┬──────────┬──────────┬──────────┬──────────┬──────────┬──────────┐
│  0x8A    │  0x84    │ [4 bytes masking key]          │     Masked "ping"           │
├──────────┼──────────┼──────────┼──────────┼──────────┼──────────┼──────────┼──────────┤
│ FIN=1    │ MASK=1   │                                │                             │
│ Opcode=A │ Len=4    │                                │                             │
│(Pong帧)  │(客户端)  │                                │                             │
└──────────┴──────────┴──────────┴──────────┴──────────┴──────────┴──────────┴──────────┘
```

---

## 连接生命周期管理

### 完整生命周期

```
WebSocket连接的7个阶段：

1. CONNECTING (0) - 连接中
   ┌──────────────┐
   │ 发起握手请求  │
   └──────┬───────┘
          │
          ↓
2. OPEN (1) - 已连接
   ┌──────────────┐
   │ 握手成功     │
   │ 可以收发数据  │
   └──────┬───────┘
          │
          ↓
3. ESTABLISHED - 稳定连接
   ┌──────────────┐
   │ 正常通信     │
   │ 心跳维持     │
   └──────┬───────┘
          │
          ↓
4. CLOSING (2) - 关闭中
   ┌──────────────┐
   │ 发送关闭帧   │
   │ 等待对方确认  │
   └──────┬───────┘
          │
          ↓
5. CLOSED (3) - 已关闭
   ┌──────────────┐
   │ 连接结束     │
   └──────────────┘
```

### 连接建立

```javascript
// 伪代码：客户端建立连接

websocket = new WebSocket('ws://example.com/socket')

// 监听连接打开事件
websocket.onopen = (event) => {
    console.log('连接已建立')
    
    // 连接建立后的处理
    websocket.readyState === WebSocket.OPEN  // true
    
    // 可以开始发送消息
    websocket.send('Hello Server')
}

// 监听错误
websocket.onerror = (error) => {
    console.log('连接错误:', error)
    
    // 错误处理
    // - 记录日志
    // - 通知用户
    // - 准备重连
}
```

### 正常关闭流程

```
正常关闭（双向握手）：

客户端                                  服务器
  │                                       │
  │ ① 发起关闭                             │
  │    发送关闭帧                          │
  │    状态码: 1000                        │
  │    原因: "User logout"                │
  ├──────────────────────────────────────→│
  │                                       │
  │ readyState = CLOSING (2)              │ ② 接收关闭帧
  │                                       │    记录状态码
  │                                       │    清理资源
  │                                       │
  │ ③ 接收关闭确认                         │ ④ 发送关闭帧
  │←──────────────────────────────────────┤
  │    关闭帧                              │
  │    状态码: 1000                        │
  │                                       │
  │ ⑤ 关闭TCP连接                          │
  │                                       │
  │ readyState = CLOSED (3)               │
  │                                       │

正常关闭的特点：
✅ 双方都有机会清理资源
✅ 知道关闭原因
✅ 可以保存状态
```

### 异常关闭处理

```
异常情况：

1. 网络断开
   客户端                      服务器
     │                           │
     │ [网络中断]                 │
     ├─ ✗ ✗ ✗ ─                  │
     │                           │
     │                           │ 超时未收到心跳
     │                           │ 触发 onerror
     │                           │ readyState = CLOSED
     │                           │ 状态码: 1006 (异常关闭)
     
   处理：
   - 客户端：检测到 onerror，尝试重连
   - 服务器：心跳超时，清理连接

2. 服务器崩溃
   客户端                      服务器
     │                           │
     │    发送消息                 │
     ├──────────────────────────→ [崩溃]
     │                           ×
     │ ← TCP RST                 
     │                           
     │ 触发 onerror
     │ 触发 onclose
     │ 状态码: 1006
     
   处理：
   - 立即触发 onclose
   - 自动重连机制启动

3. 浏览器关闭/刷新
   客户端                      服务器
     │                           │
   [关闭浏览器]                  │
     │                           │
   TCP连接突然断开               │
     ×                           │
                                 │ 检测到连接断开
                                 │ 触发错误事件
                                 │ 清理资源
     
   注意：
   - beforeunload事件中可尝试发送关闭帧
   - 但不保证成功（浏览器可能立即关闭）

4. 超时未响应
   客户端                      服务器
     │                           │
     │ ──── Ping ─────────────→  │
     │                           │
     │ [等待30秒]                 │
     │                           │ [服务器无响应]
     │ 超时！                     │
     │                           │
     │ 主动关闭连接               │
     ├──── Close Frame ─────────→│
     │                           │
     
   处理：
   - 设置合理的超时时间
   - 超时后主动关闭
   - 触发重连逻辑
```

---

## 心跳与重连机制

### 为什么需要心跳？

```
问题场景：

1. 长时间空闲
   ┌────────────────────────────────────┐
   │ 客户端和服务器都没有数据发送         │
   │ 中间的代理、路由器可能认为连接已死   │
   │ → 关闭连接                          │
   └────────────────────────────────────┘

2. 网络静默故障
   ┌────────────────────────────────────┐
   │ 网络设备故障，但TCP连接未关闭        │
   │ 应用层不知道连接已不可用             │
   │ → 消息发送但无响应                  │
   └────────────────────────────────────┘

3. 僵尸连接
   ┌────────────────────────────────────┐
   │ 客户端异常退出，未发送关闭帧         │
   │ 服务器认为连接仍然存在              │
   │ → 浪费服务器资源                    │
   └────────────────────────────────────┘

心跳机制解决这些问题！
```

### 心跳实现方案

```
方案1：WebSocket原生Ping/Pong（推荐）

客户端                         服务器
  │                              │
  │                              │ [定时器：每30秒]
  │                              │
  │     ◄──── Ping Frame ────────┤
  │     (Opcode: 0x9)            │
  │                              │
  ├──── Pong Frame ─────────────→│
  │     (Opcode: 0xA)            │ 收到Pong，重置计时器
  │     (自动发送)               │
  │                              │
  │ [30秒后]                      │
  │                              │
  │     ◄──── Ping Frame ────────┤
  │                              │
  ├──── Pong Frame ─────────────→│
  │                              │

伪代码（服务器端）：

class WebSocketServer {
    connections = {}
    
    onConnection(client) {
        connections[client.id] = {
            socket: client,
            lastPong: Date.now()
        }
        
        // 启动心跳
        startHeartbeat(client)
    }
    
    startHeartbeat(client) {
        interval = setInterval(() => {
            if (client.readyState === OPEN) {
                // 发送Ping
                client.ping()
                
                // 检查上次Pong时间
                timeSinceLastPong = Date.now() - connections[client.id].lastPong
                
                if (timeSinceLastPong > 60000) {  // 60秒未响应
                    console.log('心跳超时，关闭连接')
                    client.close(1001, 'Heartbeat timeout')
                    clearInterval(interval)
                }
            }
        }, 30000)  // 每30秒
    }
    
    onPong(client) {
        connections[client.id].lastPong = Date.now()
    }
}

特点：
✅ 协议层面的支持
✅ 浏览器自动响应Pong
✅ 开销小（控制帧）

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

方案2：应用层心跳消息

客户端                         服务器
  │                              │
  │ [定时器：每30秒]              │
  │                              │
  ├──── {"type":"ping"} ────────→│
  │                              │
  │     {"type":"pong"}  ◄───────┤
  │                              │
  │ 收到pong，重置计时器          │
  │                              │

伪代码（客户端）：

class WebSocketClient {
    ws = null
    heartbeatInterval = null
    heartbeatTimeout = null
    
    connect() {
        ws = new WebSocket('ws://example.com')
        
        ws.onopen = () => {
            startHeartbeat()
        }
        
        ws.onmessage = (event) => {
            message = JSON.parse(event.data)
            
            if (message.type === 'pong') {
                // 收到心跳响应
                clearTimeout(heartbeatTimeout)
            } else {
                // 处理业务消息
                handleMessage(message)
            }
        }
    }
    
    startHeartbeat() {
        heartbeatInterval = setInterval(() => {
            sendPing()
        }, 30000)
    }
    
    sendPing() {
        ws.send(JSON.stringify({ type: 'ping' }))
        
        // 设置超时
        heartbeatTimeout = setTimeout(() => {
            console.log('心跳超时，连接可能已断开')
            ws.close()
            reconnect()  // 触发重连
        }, 5000)  // 5秒内必须收到pong
    }
}

特点：
✅ 更灵活（可携带额外信息）
✅ 跨平台统一
❌ 占用应用层带宽
```

### 智能心跳优化

```
优化策略：

1. 自适应心跳间隔

normal_interval = 30秒      // 正常情况
idle_interval = 60秒        // 长时间无业务消息
active_interval = 10秒      // 频繁通信时（可选）

if (最近1分钟无业务消息) {
    使用 idle_interval
} else if (最近10秒有多条消息) {
    使用 active_interval  // 或者不发心跳
} else {
    使用 normal_interval
}

2. 业务消息即心跳

lastActivity = Date.now()

onMessage(message) {
    lastActivity = Date.now()  // 更新活跃时间
    handleMessage(message)
}

onSend(message) {
    lastActivity = Date.now()
    ws.send(message)
}

shouldSendHeartbeat() {
    timeSinceLastActivity = Date.now() - lastActivity
    return timeSinceLastActivity > heartbeat_interval
}

// 只在真正空闲时发送心跳
if (shouldSendHeartbeat()) {
    sendPing()
}

优点：
✅ 减少不必要的心跳
✅ 节省带宽
✅ 降低服务器负载

3. 移动端优化

// 监听页面可见性
document.onvisibilitychange = () => {
    if (document.hidden) {
        // 页面隐藏，减少心跳频率
        heartbeat_interval = 120秒
    } else {
        // 页面显示，恢复正常频率
        heartbeat_interval = 30秒
        
        // 立即发送一次心跳，检测连接
        sendPing()
    }
}

// 网络状态监听
window.addEventListener('online', () => {
    console.log('网络恢复')
    reconnect()  // 立即重连
})

window.addEventListener('offline', () => {
    console.log('网络断开')
    stopHeartbeat()  // 停止心跳，节省资源
})
```

### 断线重连机制

```
完整的重连策略：

class ReconnectingWebSocket {
    url = ''
    ws = null
    
    // 重连配置
    config = {
        maxReconnectAttempts: 10,        // 最大重连次数
        reconnectInterval: 1000,         // 初始重连间隔（毫秒）
        maxReconnectInterval: 30000,     // 最大重连间隔
        reconnectDecay: 1.5,             // 退避系数
        timeoutInterval: 5000            // 连接超时
    }
    
    // 状态
    reconnectAttempts = 0
    shouldReconnect = true
    forcedClose = false
    
    connect() {
        ws = new WebSocket(url)
        
        // 连接超时检测
        connectTimeout = setTimeout(() => {
            console.log('连接超时')
            ws.close()
            reconnect()
        }, config.timeoutInterval)
        
        ws.onopen = () => {
            clearTimeout(connectTimeout)
            console.log('连接成功')
            
            // 重置重连计数
            reconnectAttempts = 0
            
            // 触发连接成功事件
            onConnected()
        }
        
        ws.onclose = (event) => {
            clearTimeout(connectTimeout)
            
            if (forcedClose) {
                console.log('主动关闭，不重连')
                return
            }
            
            if (shouldReconnect) {
                reconnect()
            }
        }
        
        ws.onerror = (error) => {
            console.log('连接错误:', error)
            // 错误会触发 onclose，在那里处理重连
        }
    }
    
    reconnect() {
        if (reconnectAttempts >= config.maxReconnectAttempts) {
            console.log('达到最大重连次数，停止重连')
            onReconnectFailed()
            return
        }
        
        reconnectAttempts++
        
        // 指数退避算法
        delay = min(
            config.reconnectInterval * pow(config.reconnectDecay, reconnectAttempts - 1),
            config.maxReconnectInterval
        )
        
        console.log(`第${reconnectAttempts}次重连，${delay}ms后尝试...`)
        
        setTimeout(() => {
            console.log('尝试重连...')
            connect()
        }, delay)
    }
    
    close() {
        forcedClose = true
        shouldReconnect = false
        
        if (ws) {
            ws.close(1000, 'Client closing')
        }
    }
}

重连时间示例：
第1次：1秒后
第2次：1.5秒后
第3次：2.25秒后
第4次：3.375秒后
第5次：5.06秒后
...
第10次：30秒后（达到上限）

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

重连时的状态管理：

状态机：
┌───────────┐
│  已断开    │
└─────┬─────┘
      │ 触发重连
      ↓
┌───────────┐
│  重连中    │ ← 显示"正在重连..."
└─────┬─────┘
      │
      ├─ 成功 ──→ ┌───────────┐
      │           │  已连接    │
      │           └───────────┘
      │
      └─ 失败 ──→ ┌───────────┐
                  │  重连失败  │ ← 提示用户
                  └───────────┘

重连过程中的处理：
1. 缓存未发送的消息
   messageQueue = []
   
   send(message) {
       if (ws.readyState === OPEN) {
           ws.send(message)
       } else {
           // 连接断开，缓存消息
           messageQueue.push(message)
       }
   }
   
   onConnected() {
       // 重连成功，发送缓存的消息
       while (messageQueue.length > 0) {
           message = messageQueue.shift()
           ws.send(message)
       }
   }

2. 状态同步
   onConnected() {
       // 重新获取最新状态
       ws.send({ type: 'sync', lastMessageId: lastId })
   }

3. 用户提示
   onReconnecting(attempt) {
       showNotification(`连接断开，正在重连(${attempt})...`)
   }
   
   onReconnected() {
       showNotification('连接已恢复')
   }
   
   onReconnectFailed() {
       showNotification('连接失败，请检查网络', { 
           action: '手动重连',
           onClick: () => forceReconnect()
       })
   }
```

---

## 消息传输模式

### 请求-响应模式

```
类HTTP的请求响应：

客户端                              服务器
  │                                   │
  │ 发送请求（带ID）                   │
  ├─────────────────────────────────→│
  │ {                                │
  │   "id": "req_001",               │ 处理请求
  │   "type": "getUserInfo",         │
  │   "userId": 123                  │
  │ }                                │
  │                                  │
  │ 接收响应（匹配ID）                 │
  │←─────────────────────────────────┤
  │ {                                │
  │   "id": "req_001",               │
  │   "type": "response",            │
  │   "data": { ... }                │
  │ }                                │
  │                                  │

实现：

class WebSocketRPC {
    ws = null
    pendingRequests = {}  // 等待响应的请求
    requestId = 0
    
    // 发送请求
    async request(type, params) {
        id = `req_${++requestId}`
        
        return new Promise((resolve, reject) => {
            // 保存回调
            pendingRequests[id] = {
                resolve,
                reject,
                timestamp: Date.now(),
                timeout: setTimeout(() => {
                    delete pendingRequests[id]
                    reject(new Error('Request timeout'))
                }, 30000)  // 30秒超时
            }
            
            // 发送请求
            ws.send(JSON.stringify({
                id,
                type,
                params
            }))
        })
    }
    
    // 接收响应
    onMessage(event) {
        message = JSON.parse(event.data)
        
        if (message.type === 'response' && message.id) {
            // 匹配请求
            request = pendingRequests[message.id]
            
            if (request) {
                clearTimeout(request.timeout)
                
                if (message.error) {
                    request.reject(message.error)
                } else {
                    request.resolve(message.data)
                }
                
                delete pendingRequests[message.id]
            }
        }
    }
}

使用：
try {
    userInfo = await ws.request('getUserInfo', { userId: 123 })
    console.log('用户信息:', userInfo)
} catch (error) {
    console.error('请求失败:', error)
}
```

### 发布-订阅模式

```
事件驱动的消息传递：

客户端A                服务器              客户端B
  │                     │                    │
  │ 订阅 "chat"         │                    │
  ├────────────────────→│                    │
  │ {                  │                    │
  │   "type": "subscribe",                  │
  │   "channel": "chat"│                    │
  │ }                  │                    │
  │                    │   订阅 "chat"       │
  │                    │←───────────────────┤
  │                    │                    │
  │ 发布消息到 "chat"   │                    │
  ├────────────────────→│                    │
  │ {                  │  广播到订阅者       │
  │   "type": "publish",├───────────────────→│
  │   "channel": "chat",│                    │
  │   "message": "Hi"  │                    │
  │ }                  │                    │
  │                    │                    │

实现：

class PubSubWebSocket {
    ws = null
    subscriptions = {}  // channel -> [callbacks]
    
    // 订阅频道
    subscribe(channel, callback) {
        if (!subscriptions[channel]) {
            subscriptions[channel] = []
            
            // 通知服务器
            ws.send(JSON.stringify({
                type: 'subscribe',
                channel
            }))
        }
        
        subscriptions[channel].push(callback)
        
        // 返回取消订阅函数
        return () => {
            unsubscribe(channel, callback)
        }
    }
    
    // 取消订阅
    unsubscribe(channel, callback) {
        if (subscriptions[channel]) {
            subscriptions[channel] = subscriptions[channel].filter(
                cb => cb !== callback
            )
            
            if (subscriptions[channel].length === 0) {
                delete subscriptions[channel]
                
                // 通知服务器
                ws.send(JSON.stringify({
                    type: 'unsubscribe',
                    channel
                }))
            }
        }
    }
    
    // 发布消息
    publish(channel, message) {
        ws.send(JSON.stringify({
            type: 'publish',
            channel,
            message
        }))
    }
    
    // 接收消息
    onMessage(event) {
        data = JSON.parse(event.data)
        
        if (data.type === 'message') {
            callbacks = subscriptions[data.channel]
            
            if (callbacks) {
                callbacks.forEach(callback => {
                    callback(data.message)
                })
            }
        }
    }
}

使用：
// 订阅聊天频道
unsubscribe = ws.subscribe('chat', (message) => {
    console.log('新消息:', message)
    displayMessage(message)
})

// 发送消息
ws.publish('chat', {
    user: 'Alice',
    text: 'Hello!'
})

// 取消订阅
unsubscribe()
```

### 流式传输

```
持续数据流传输：

场景：实时日志、股票行情、传感器数据

服务器                            客户端
  │                                 │
  │ ──── 数据1 ────────────────────→│
  │      { seq: 1, data: ... }     │
  │                                 │ 处理数据1
  │ ──── 数据2 ────────────────────→│
  │      { seq: 2, data: ... }     │
  │                                 │ 处理数据2
  │ ──── 数据3 ────────────────────→│
  │      { seq: 3, data: ... }     │
  │                                 │ 处理数据3
  │                                 │
  │ ──── 结束标记 ──────────────────→│
  │      { seq: -1, end: true }    │
  │                                 │ 流结束

实现：

class StreamWebSocket {
    ws = null
    streams = {}  // streamId -> handler
    
    // 开始接收流
    createStream(streamId, onData, onEnd) {
        streams[streamId] = {
            onData,
            onEnd,
            receivedSeq: 0,
            buffer: {}  // 乱序缓存
        }
        
        // 通知服务器开始流
        ws.send(JSON.stringify({
            type: 'stream_start',
            streamId
        }))
    }
    
    // 接收流数据
    onMessage(event) {
        data = JSON.parse(event.data)
        
        if (data.type === 'stream_data') {
            stream = streams[data.streamId]
            
            if (stream) {
                if (data.seq === -1) {
                    // 流结束
                    stream.onEnd()
                    delete streams[data.streamId]
                } else {
                    // 处理数据（保证顺序）
                    handleStreamData(stream, data)
                }
            }
        }
    }
    
    // 处理流数据（顺序保证）
    handleStreamData(stream, data) {
        if (data.seq === stream.receivedSeq + 1) {
            // 正好是下一个
            stream.onData(data.data)
            stream.receivedSeq++
            
            // 检查缓存中是否有后续数据
            while (stream.buffer[stream.receivedSeq + 1]) {
                nextData = stream.buffer[stream.receivedSeq + 1]
                stream.onData(nextData)
                delete stream.buffer[stream.receivedSeq + 1]
                stream.receivedSeq++
            }
        } else if (data.seq > stream.receivedSeq + 1) {
            // 乱序，缓存起来
            stream.buffer[data.seq] = data.data
        }
        // data.seq <= receivedSeq 的情况忽略（重复数据）
    }
    
    // 停止流
    stopStream(streamId) {
        delete streams[streamId]
        
        ws.send(JSON.stringify({
            type: 'stream_stop',
            streamId
        }))
    }
}

使用：
// 接收实时日志
ws.createStream('logs', 
    (data) => {
        console.log('日志:', data)
        appendLog(data)
    },
    () => {
        console.log('日志流结束')
    }
)
```

### 二进制数据传输

```
高效传输二进制数据：

应用场景：
- 文件传输
- 图片/视频
- 音频流
- 自定义协议

方式1：ArrayBuffer

// 发送二进制数据
buffer = new ArrayBuffer(1024)
view = new Uint8Array(buffer)

// 填充数据
view[0] = 0x01  // 消息类型
view[1] = 0x02  // 版本
// ...

ws.send(buffer)

// 接收二进制数据
ws.onmessage = (event) => {
    if (event.data instanceof ArrayBuffer) {
        buffer = event.data
        view = new Uint8Array(buffer)
        
        messageType = view[0]
        version = view[1]
        
        // 处理数据
    }
}

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

方式2：Blob（大文件）

// 发送文件
file = document.getElementById('fileInput').files[0]
ws.send(file)  // 直接发送Blob

// 接收文件
ws.binaryType = 'blob'  // 设置接收类型

ws.onmessage = (event) => {
    if (event.data instanceof Blob) {
        blob = event.data
        
        // 创建下载链接
        url = URL.createObjectURL(blob)
        link = document.createElement('a')
        link.href = url
        link.download = 'file.dat'
        link.click()
    }
}

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

混合协议（自定义二进制格式）：

消息格式设计：
┌────────┬────────┬────────┬────────┬─────────┐
│ 魔数    │ 版本   │ 类型   │ 长度   │ 数据     │
│ 2字节   │ 1字节  │ 1字节  │ 4字节  │ N字节    │
└────────┴────────┴────────┴────────┴─────────┘

MAGIC = 0xABCD

// 编码
function encodeMessage(type, data) {
    header = new ArrayBuffer(8)
    view = new DataView(header)
    
    view.setUint16(0, MAGIC)      // 魔数
    view.setUint8(2, 1)           // 版本
    view.setUint8(3, type)        // 类型
    view.setUint32(4, data.length) // 长度
    
    // 合并头部和数据
    message = new Uint8Array(8 + data.length)
    message.set(new Uint8Array(header), 0)
    message.set(data, 8)
    
    return message.buffer
}

// 解码
function decodeMessage(buffer) {
    view = new DataView(buffer)
    
    magic = view.getUint16(0)
    if (magic !== MAGIC) {
        throw Error('Invalid message')
    }
    
    version = view.getUint8(2)
    type = view.getUint8(3)
    length = view.getUint32(4)
    
    data = new Uint8Array(buffer, 8, length)
    
    return { type, data }
}
```

---

## 安全性考虑

### WSS加密连接

```
WebSocket安全传输（WSS）：

ws://  → 明文传输（类似HTTP）
wss:// → TLS加密（类似HTTPS）

┌─────────────────────────────────────┐
│       wss://example.com/socket      │
└──────────────┬──────────────────────┘
               │
┌──────────────┴──────────────────────┐
│         TLS/SSL层                   │
│  - 加密数据                         │
│  - 证书验证                         │
│  - 防止中间人攻击                    │
└──────────────┬──────────────────────┘
               │
┌──────────────┴──────────────────────┐
│       WebSocket协议                 │
└──────────────┬──────────────────────┘
               │
┌──────────────┴──────────────────────┐
│         TCP连接                     │
└─────────────────────────────────────┘

强烈建议：
✅ 生产环境必须使用WSS
✅ 使用有效的SSL证书
✅ 启用HTTPS后，WebSocket也必须用WSS
❌ 混合内容（HTTPS页面+WS连接）会被浏览器阻止
```

### 跨站WebSocket劫持（CSWSH）

```
攻击场景：

1. 受害者登录 bank.com
2. 访问攻击者网站 evil.com
3. evil.com的JavaScript尝试连接 ws://bank.com/socket
4. 浏览器自动携带 bank.com 的Cookie
5. 攻击成功！

攻击代码示例：
// 在 evil.com 的页面上
ws = new WebSocket('ws://bank.com/socket')

ws.onopen = () => {
    // 连接成功，浏览器自动带上bank.com的Cookie
    ws.send('{"action":"transfer","to":"attacker","amount":1000}')
}

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

防护措施：

1. 验证Origin头部（重要！）

// 服务器端
onConnection(request) {
    origin = request.headers['origin']
    
    allowedOrigins = [
        'https://bank.com',
        'https://www.bank.com'
    ]
    
    if (!allowedOrigins.includes(origin)) {
        console.log('拒绝来自', origin, '的连接')
        request.reject(403, 'Forbidden')
        return
    }
    
    // 接受连接
    connection = request.accept()
}

2. 使用Token验证

// 客户端：在URL中传递token
token = getAuthToken()
ws = new WebSocket(`wss://bank.com/socket?token=${token}`)

// 或在首次消息中传递
ws.onopen = () => {
    ws.send(JSON.stringify({
        type: 'auth',
        token: getAuthToken()
    }))
}

// 服务器端：验证token
onConnection(connection) {
    authenticated = false
    authTimeout = setTimeout(() => {
        if (!authenticated) {
            connection.close(4001, 'Authentication timeout')
        }
    }, 5000)  // 5秒内必须认证
}

onMessage(connection, message) {
    if (!authenticated) {
        if (message.type === 'auth') {
            if (validateToken(message.token)) {
                authenticated = true
                clearTimeout(authTimeout)
            } else {
                connection.close(4003, 'Invalid token')
            }
        } else {
            connection.close(4002, 'Not authenticated')
        }
    } else {
        // 处理业务消息
        handleMessage(message)
    }
}

3. CSRF Token

// 在页面中嵌入CSRF token
<meta name="csrf-token" content="random_token_here">

// 连接时发送
csrfToken = document.querySelector('meta[name="csrf-token"]').content
ws = new WebSocket(`wss://bank.com/socket?csrf=${csrfToken}`)
```

### 输入验证

```
防止注入攻击：

1. JSON注入

// 错误示例（危险！）
onMessage(data) {
    message = eval('(' + data + ')')  // ❌ 永远不要这样做！
    handleMessage(message)
}

// 正确示例
onMessage(data) {
    try {
        message = JSON.parse(data)  // ✅ 安全的解析
        
        // 验证消息结构
        if (!isValidMessage(message)) {
            throw Error('Invalid message format')
        }
        
        handleMessage(message)
    } catch (error) {
        console.error('Invalid JSON:', error)
        // 不要将错误详情发送给客户端
    }
}

2. XSS防护（显示用户消息时）

// 错误示例
displayMessage(message) {
    div = document.createElement('div')
    div.innerHTML = message.text  // ❌ 可能执行恶意脚本
    chatContainer.appendChild(div)
}

// 正确示例
displayMessage(message) {
    div = document.createElement('div')
    div.textContent = message.text  // ✅ 纯文本，不解析HTML
    // 或者使用DOMPurify库清理HTML
    chatContainer.appendChild(div)
}

3. 消息大小限制

onMessage(connection, message) {
    MAX_MESSAGE_SIZE = 1024 * 1024  // 1MB
    
    if (message.length > MAX_MESSAGE_SIZE) {
        console.log('消息过大，拒绝处理')
        connection.close(1009, 'Message too big')
        return
    }
    
    handleMessage(message)
}

4. 速率限制

class RateLimiter {
    limits = {}  // userId -> { count, resetTime }
    
    checkLimit(userId) {
        now = Date.now()
        limit = limits[userId]
        
        if (!limit || now > limit.resetTime) {
            // 重置计数
            limits[userId] = {
                count: 1,
                resetTime: now + 60000  // 1分钟后重置
            }
            return true
        }
        
        if (limit.count < 100) {  // 每分钟最多100条
            limit.count++
            return true
        }
        
        // 超过限制
        return false
    }
}

onMessage(connection, message) {
    if (!rateLimiter.checkLimit(connection.userId)) {
        connection.send(JSON.stringify({
            type: 'error',
            message: 'Rate limit exceeded'
        }))
        return
    }
    
    handleMessage(message)
}
```

### 拒绝服务（DoS）防护

```
防护策略：

1. 连接数限制

class ConnectionManager {
    connections = new Map()  // IP -> connections[]
    
    MAX_CONNECTIONS_PER_IP = 10
    
    canConnect(ip) {
        connections = connections.get(ip) || []
        
        if (connections.length >= MAX_CONNECTIONS_PER_IP) {
            console.log(`IP ${ip} 连接数已达上限`)
            return false
        }
        
        return true
    }
    
    addConnection(ip, connection) {
        if (!connections.has(ip)) {
            connections.set(ip, [])
        }
        connections.get(ip).push(connection)
    }
    
    removeConnection(ip, connection) {
        conns = connections.get(ip)
        if (conns) {
            conns = conns.filter(c => c !== connection)
            if (conns.length === 0) {
                connections.delete(ip)
            } else {
                connections.set(ip, conns)
            }
        }
    }
}

2. Slowloris攻击防护

// 连接建立后必须在指定时间内完成握手
onConnection(socket) {
    handshakeTimeout = setTimeout(() => {
        console.log('握手超时，关闭连接')
        socket.destroy()
    }, 10000)  // 10秒
    
    socket.on('handshake_complete', () => {
        clearTimeout(handshakeTimeout)
    })
}

3. 心跳超时

// 长时间不活跃的连接自动断开
onConnection(connection) {
    lastActivity = Date.now()
    
    checkActivity = setInterval(() => {
        idle = Date.now() - lastActivity
        
        if (idle > 300000) {  // 5分钟无活动
            connection.close(1000, 'Idle timeout')
            clearInterval(checkActivity)
        }
    }, 60000)
    
    connection.on('message', () => {
        lastActivity = Date.now()
    })
}

4. 资源清理

onClose(connection) {
    // 清理订阅
    unsubscribeAll(connection)
    
    // 清理定时器
    clearAllTimers(connection)
    
    // 清理缓存
    clearBuffer(connection)
    
    // 更新统计
    removeFromConnectionPool(connection)
}
```

---

## 实战应用场景

### 场景1：实时聊天

```
需求分析：
- 即时消息传递
- 在线状态显示
- 已读未读状态
- 消息历史
- 多端同步

技术实现：

// 客户端
class ChatClient {
    ws = null
    messageQueue = []
    
    connect() {
        ws = new ReconnectingWebSocket('wss://chat.example.com')
        
        ws.onopen = () => {
            // 认证
            ws.send(JSON.stringify({
                type: 'auth',
                token: getUserToken()
            }))
            
            // 加入聊天室
            ws.send(JSON.stringify({
                type: 'join',
                roomId: currentRoomId
            }))
        }
        
        ws.onmessage = (event) => {
            message = JSON.parse(event.data)
            
            switch(message.type) {
                case 'message':
                    displayMessage(message)
                    sendReadReceipt(message.id)
                    break
                    
                case 'user_online':
                    updateUserStatus(message.userId, 'online')
                    break
                    
                case 'user_offline':
                    updateUserStatus(message.userId, 'offline')
                    break
                    
                case 'typing':
                    showTypingIndicator(message.userId)
                    break
                    
                case 'read_receipt':
                    updateMessageStatus(message.messageId, 'read')
                    break
            }
        }
    }
    
    sendMessage(text) {
        message = {
            type: 'message',
            roomId: currentRoomId,
            text: text,
            clientId: generateClientId(),  // 客户端生成ID
            timestamp: Date.now()
        }
        
        // 立即显示（乐观更新）
        displayMessage(message, { pending: true })
        
        if (ws.readyState === WebSocket.OPEN) {
            ws.send(JSON.stringify(message))
        } else {
            // 离线，加入队列
            messageQueue.push(message)
        }
    }
    
    sendTypingIndicator() {
        // 节流：最多3秒发送一次
        if (!typingThrottled) {
            ws.send(JSON.stringify({
                type: 'typing',
                roomId: currentRoomId
            }))
            
            typingThrottled = true
            setTimeout(() => {
                typingThrottled = false
            }, 3000)
        }
    }
}

// 服务器端
class ChatServer {
    rooms = {}  // roomId -> { connections, messages }
    users = {}  // userId -> { connection, rooms }
    
    onMessage(connection, message) {
        switch(message.type) {
            case 'join':
                joinRoom(connection, message.roomId)
                
                // 发送历史消息
                history = getRecentMessages(message.roomId, 50)
                connection.send(JSON.stringify({
                    type: 'history',
                    messages: history
                }))
                
                // 通知其他人
                broadcastToRoom(message.roomId, {
                    type: 'user_online',
                    userId: connection.userId
                }, connection)
                break
                
            case 'message':
                // 保存消息
                savedMessage = saveMessage(message)
                
                // 广播给房间内的所有人
                broadcastToRoom(message.roomId, {
                    type: 'message',
                    ...savedMessage,
                    userId: connection.userId
                })
                
                // 发送确认
                connection.send(JSON.stringify({
                    type: 'ack',
                    clientId: message.clientId,
                    serverId: savedMessage.id
                }))
                break
                
            case 'typing':
                // 转发输入状态（不保存）
                broadcastToRoom(message.roomId, {
                    type: 'typing',
                    userId: connection.userId
                }, connection)
                break
        }
    }
    
    broadcastToRoom(roomId, message, excludeConnection) {
        room = rooms[roomId]
        
        if (room) {
            room.connections.forEach(conn => {
                if (conn !== excludeConnection && conn.readyState === OPEN) {
                    conn.send(JSON.stringify(message))
                }
            })
        }
    }
}
```

### 场景2：实时数据大屏

```
需求：
- 实时更新数据
- 多个图表同时更新
- 数据量大
- 低延迟

实现：

// 客户端
class Dashboard {
    ws = null
    charts = {}
    
    connect() {
        ws = new WebSocket('wss://dashboard.example.com')
        
        ws.onopen = () => {
            // 订阅所有需要的数据流
            subscribeData('sales')
            subscribeData('orders')
            subscribeData('traffic')
        }
        
        ws.onmessage = (event) => {
            // 可能是二进制数据（更高效）
            if (event.data instanceof ArrayBuffer) {
                data = decodeBinaryMessage(event.data)
            } else {
                data = JSON.parse(event.data)
            }
            
            // 更新对应的图表
            updateChart(data.metric, data.value)
        }
    }
    
    subscribeData(metric) {
        ws.send(JSON.stringify({
            type: 'subscribe',
            metric: metric,
            interval: 1000  // 每秒更新
        }))
    }
    
    updateChart(metric, value) {
        chart = charts[metric]
        
        if (chart) {
            // 添加新数据点
            chart.data.push(value)
            
            // 限制数据点数量（滑动窗口）
            if (chart.data.length > 60) {  // 只保留60秒
                chart.data.shift()
            }
            
            // 使用requestAnimationFrame优化渲染
            if (!chart.updatePending) {
                chart.updatePending = true
                
                requestAnimationFrame(() => {
                    chart.render()
                    chart.updatePending = false
                })
            }
        }
    }
}

// 服务器端（推送聚合数据）
class DashboardServer {
    subscriptions = {}  // metric -> [connections]
    dataCache = {}
    
    init() {
        // 定时聚合数据并推送
        setInterval(() => {
            pushMetrics()
        }, 1000)
    }
    
    pushMetrics() {
        // 从数据库或缓存获取最新数据
        metrics = {
            sales: getCurrentSales(),
            orders: getCurrentOrders(),
            traffic: getCurrentTraffic()
        }
        
        // 推送给订阅者
        for (metric in metrics) {
            connections = subscriptions[metric] || []
            value = metrics[metric]
            
            // 使用二进制格式减小数据量
            binaryData = encodeBinaryMessage(metric, value)
            
            connections.forEach(conn => {
                if (conn.readyState === OPEN) {
                    conn.send(binaryData)
                }
            })
        }
    }
    
    // 二进制编码（更高效）
    encodeBinaryMessage(metric, value) {
        metricId = getMetricId(metric)
        
        buffer = new ArrayBuffer(12)
        view = new DataView(buffer)
        
        view.setUint16(0, metricId)     // 2字节：指标ID
        view.setFloat64(2, value)       // 8字节：数值
        view.setUint16(10, Date.now())  // 2字节：时间戳(简化)
        
        return buffer
    }
}
```

### 场景3：协同编辑

```
需求：
- 多人同时编辑
- 实时同步
- 冲突解决
- 操作历史

实现（基于Operational Transformation）：

// 客户端
class CollaborativeEditor {
    ws = null
    document = ''
    localVersion = 0
    serverVersion = 0
    pendingOperations = []
    
    connect() {
        ws = new WebSocket('wss://editor.example.com')
        
        ws.onopen = () => {
            // 加入文档
            ws.send(JSON.stringify({
                type: 'join',
                documentId: currentDocId
            }))
        }
        
        ws.onmessage = (event) => {
            message = JSON.parse(event.data)
            
            switch(message.type) {
                case 'init':
                    // 初始化文档
                    document = message.content
                    serverVersion = message.version
                    localVersion = message.version
                    break
                    
                case 'operation':
                    // 应用远程操作
                    applyRemoteOperation(message.operation)
                    break
                    
                case 'ack':
                    // 服务器确认了操作
                    handleAck(message)
                    break
            }
        }
    }
    
    onLocalEdit(position, text, type) {
        // 创建操作
        operation = {
            type: type,  // 'insert' 或 'delete'
            position: position,
            text: text,
            version: localVersion
        }
        
        // 立即应用到本地
        applyLocalOperation(operation)
        localVersion++
        
        // 发送到服务器
        sendOperation(operation)
    }
    
    applyRemoteOperation(operation) {
        // 转换待发送的操作
        pendingOperations = pendingOperations.map(op => {
            return transform(op, operation)
        })
        
        // 应用到文档
        applyToDocument(operation)
        serverVersion++
    }
    
    // 操作转换（OT算法核心）
    transform(op1, op2) {
        if (op1.type === 'insert' && op2.type === 'insert') {
            if (op2.position <= op1.position) {
                op1.position += op2.text.length
            }
        } else if (op1.type === 'insert' && op2.type === 'delete') {
            if (op2.position < op1.position) {
                op1.position -= op2.text.length
            }
        }
        // ... 更多转换规则
        
        return op1
    }
}

// 服务器端
class CollaborationServer {
    documents = {}  // docId -> { content, version, operations }
    
    onMessage(connection, message) {
        if (message.type === 'operation') {
            doc = documents[connection.docId]
            
            // 检查版本
            if (message.version !== doc.version) {
                // 需要转换操作
                transformedOp = transformOperation(
                    message.operation,
                    doc.operations.slice(message.version)
                )
            } else {
                transformedOp = message.operation
            }
            
            // 应用操作
            applyOperation(doc, transformedOp)
            doc.version++
            
            // 广播给其他客户端
            broadcastOperation(connection.docId, transformedOp, connection)
            
            // 确认
            connection.send(JSON.stringify({
                type: 'ack',
                version: doc.version
            }))
        }
    }
}
```

### 场景4：物联网（IoT）

```
需求：
- 设备连接数量大
- 持续数据上报
- 远程控制
- 低功耗

实现：

// 设备端（简化）
class IoTDevice {
    ws = null
    deviceId = ''
    reconnectAttempts = 0
    
    connect() {
        ws = new WebSocket('wss://iot.example.com/device')
        
        ws.onopen = () => {
            // 设备认证
            ws.send(JSON.stringify({
                type: 'auth',
                deviceId: deviceId,
                secret: getDeviceSecret()
            }))
            
            // 开始上报数据
            startReporting()
        }
        
        ws.onmessage = (event) => {
            command = JSON.parse(event.data)
            
            if (command.type === 'control') {
                // 执行控制命令
                executeCommand(command)
                
                // 返回执行结果
                ws.send(JSON.stringify({
                    type: 'result',
                    commandId: command.id,
                    success: true,
                    data: getDeviceState()
                }))
            }
        }
        
        ws.onclose = () => {
            // 指数退避重连
            delay = min(1000 * pow(2, reconnectAttempts), 60000)
            setTimeout(() => connect(), delay)
            reconnectAttempts++
        }
    }
    
    startReporting() {
        // 定期上报数据
        setInterval(() => {
            if (ws.readyState === OPEN) {
                ws.send(JSON.stringify({
                    type: 'data',
                    deviceId: deviceId,
                    metrics: {
                        temperature: readTemperature(),
                        humidity: readHumidity(),
                        battery: getBatteryLevel()
                    },
                    timestamp: Date.now()
                }))
            }
        }, 60000)  // 每分钟上报
    }
}

// IoT平台服务器
class IoTPlatform {
    devices = {}  // deviceId -> connection
    
    onConnection(connection) {
        connection.authenticated = false
        
        // 认证超时
        setTimeout(() => {
            if (!connection.authenticated) {
                connection.close(4001, 'Auth timeout')
            }
        }, 10000)
    }
    
    onMessage(connection, message) {
        if (!connection.authenticated) {
            if (message.type === 'auth') {
                if (validateDevice(message.deviceId, message.secret)) {
                    connection.authenticated = true
                    connection.deviceId = message.deviceId
                    devices[message.deviceId] = connection
                    
                    // 记录设备上线
                    logDeviceOnline(message.deviceId)
                } else {
                    connection.close(4003, 'Invalid credentials')
                }
            }
        } else {
            if (message.type === 'data') {
                // 存储设备数据
                storeDeviceData(connection.deviceId, message.metrics)
                
                // 检查告警规则
                checkAlerts(connection.deviceId, message.metrics)
            }
        }
    }
    
    // 向设备发送控制命令
    sendCommand(deviceId, command) {
        connection = devices[deviceId]
        
        if (connection && connection.readyState === OPEN) {
            connection.send(JSON.stringify({
                type: 'control',
                id: generateCommandId(),
                command: command
            }))
        } else {
            return Error('Device offline')
        }
    }
}
```

---

## 性能优化

### 消息压缩

```
WebSocket扩展：permessage-deflate

握手时协商：
Client → Server:
    Sec-WebSocket-Extensions: permessage-deflate

Server → Client:
    Sec-WebSocket-Extensions: permessage-deflate; server_max_window_bits=15

效果：
未压缩：{"type":"message","content":"Hello World"...}  // 150 bytes
压缩后：[compressed binary data]                       // 80 bytes

节省：~47%

配置：

// 服务器端（Node.js ws库）
server = new WebSocketServer({
    perMessageDeflate: {
        zlibDeflateOptions: {
            chunkSize: 1024,
            memLevel: 7,
            level: 3  // 压缩级别（0-9）
        },
        zlibInflateOptions: {
            chunkSize: 10 * 1024
        },
        threshold: 1024  // 大于1KB才压缩
    }
})

注意事项：
- 小消息不要压缩（开销大于收益）
- CPU和带宽的权衡
- 移动设备考虑电量消耗
```

### 批量发送

```
减少帧数，提高效率：

// 不好的做法
for (i = 0; i < 100; i++) {
    ws.send(JSON.stringify({ id: i, data: data[i] }))
}
// 发送100个帧，每个帧有头部开销

// 优化方案
batch = []
for (i = 0; i < 100; i++) {
    batch.push({ id: i, data: data[i] })
}
ws.send(JSON.stringify({ type: 'batch', items: batch }))
// 只发送1个帧

进一步优化（定时批量）：

class BatchSender {
    ws = null
    queue = []
    timer = null
    
    send(message) {
        queue.push(message)
        
        if (!timer) {
            timer = setTimeout(() => {
                flush()
            }, 50)  // 50ms后批量发送
        }
        
        // 队列太大，立即发送
        if (queue.length >= 100) {
            flush()
        }
    }
    
    flush() {
        if (queue.length > 0) {
            ws.send(JSON.stringify({
                type: 'batch',
                items: queue
            }))
            
            queue = []
        }
        
        if (timer) {
            clearTimeout(timer)
            timer = null
        }
    }
}

效果：
- 减少帧数：100帧 → 1帧
- 减少头部开销：~95%
- 提高吞吐量
```

### 二进制vs文本

```
性能对比：

JSON文本：
{
    "type": 1,
    "userId": 12345,
    "timestamp": 1638360000000,
    "value": 98.765
}
大小：~80 bytes

二进制（自定义协议）：
[type:1byte][userId:4bytes][timestamp:8bytes][value:8bytes]
大小：21 bytes

节省：73%！

实现：

// 编码
function encodeBinary(message) {
    buffer = new ArrayBuffer(21)
    view = new DataView(buffer)
    
    view.setUint8(0, message.type)
    view.setUint32(1, message.userId, true)  // little-endian
    view.setFloat64(5, message.timestamp, true)
    view.setFloat64(13, message.value, true)
    
    return buffer
}

// 解码
function decodeBinary(buffer) {
    view = new DataView(buffer)
    
    return {
        type: view.getUint8(0),
        userId: view.getUint32(1, true),
        timestamp: view.getFloat64(5, true),
        value: view.getFloat64(13, true)
    }
}

// 发送
data = encodeBinary(message)
ws.send(data)

选择建议：
✅ 数据量大 → 二进制
✅ 需要调试 → JSON
✅ 结构复杂 → JSON
✅ 实时性要求高 → 二进制
```

### 连接池管理

```
服务器端优化：

class ConnectionPool {
    connections = new Map()
    stats = {
        total: 0,
        active: 0,
        idle: 0
    }
    
    addConnection(connection) {
        connectionId = generateId()
        
        connections.set(connectionId, {
            connection,
            lastActivity: Date.now(),
            messageCount: 0,
            bytesReceived: 0,
            bytesSent: 0
        })
        
        stats.total++
        stats.active++
        
        // 设置事件监听
        connection.on('message', () => {
            updateActivity(connectionId)
        })
        
        connection.on('close', () => {
            removeConnection(connectionId)
        })
    }
    
    removeConnection(connectionId) {
        connections.delete(connectionId)
        stats.total--
    }
    
    // 清理空闲连接
    cleanupIdle() {
        now = Date.now()
        
        connections.forEach((info, id) => {
            idle = now - info.lastActivity
            
            if (idle > 600000) {  // 10分钟无活动
                info.connection.close(1000, 'Idle timeout')
                removeConnection(id)
            }
        })
    }
    
    // 获取统计信息
    getStats() {
        return {
            total: stats.total,
            active: stats.active,
            idle: stats.idle,
            avgMessageCount: calculateAverage('messageCount'),
            totalBytesReceived: sum('bytesReceived'),
            totalBytesSent: sum('bytesSent')
        }
    }
}

// 定期清理
setInterval(() => {
    connectionPool.cleanupIdle()
}, 60000)  // 每分钟检查一次
```

---

## 与其他技术对比

### WebSocket vs HTTP长轮询

```
┌──────────────┬─────────────┬──────────────┐
│  特性        │  WebSocket  │  长轮询       │
├──────────────┼─────────────┼──────────────┤
│ 连接方式     │ 持久连接    │  反复建立     │
│ 延迟         │ <50ms       │  100-500ms   │
│ 服务器开销   │ 低          │  高          │
│ 客户端开销   │ 低          │  中          │
│ 浏览器兼容   │ 现代浏览器  │  全部        │
│ 穿透代理     │ 可能有问题  │  无问题      │
│ 双向通信     │ 原生支持    │  需要两条连接 │
│ 实现复杂度   │ 中          │  简单        │
└──────────────┴─────────────┴──────────────┘

选择建议：
✅ 实时性要求高 → WebSocket
✅ 兼容性要求高 → 长轮询（降级方案）
✅ 服务器资源有限 → WebSocket
```

### WebSocket vs Server-Sent Events (SSE)

```
┌──────────────┬─────────────┬──────────────┐
│  特性        │  WebSocket  │  SSE         │
├──────────────┼─────────────┼──────────────┤
│ 通信方向     │ 双向        │  单向(服务→客户)│
│ 协议         │ WebSocket   │  HTTP        │
│ 数据格式     │ 文本/二进制 │  文本        │
│ 自动重连     │ 需要自己实现│  原生支持    │
│ 浏览器支持   │ 好          │  好(IE不支持)│
│ 连接数限制   │ 无          │  6个/域名    │
│ 使用场景     │ 双向实时    │  服务器推送  │
└──────────────┴─────────────┴──────────────┘

SSE示例：
// 客户端
eventSource = new EventSource('/events')

eventSource.onmessage = (event) => {
    data = JSON.parse(event.data)
    handleData(data)
}

eventSource.onerror = () => {
    // 自动重连
}

// 服务器
response.writeHead(200, {
    'Content-Type': 'text/event-stream',
    'Cache-Control': 'no-cache',
    'Connection': 'keep-alive'
})

response.write('data: {"message": "Hello"}\n\n')

选择建议：
✅ 只需服务器推送 → SSE
✅ 需要客户端向服务器发送 → WebSocket
✅ 需要二进制传输 → WebSocket
```

### WebSocket vs WebRTC DataChannel

```
┌──────────────┬─────────────┬──────────────┐
│  特性        │  WebSocket  │  DataChannel │
├──────────────┼─────────────┼──────────────┤
│ 连接方式     │ 客户端-服务器│  P2P         │
│ 延迟         │ 中          │  极低        │
│ 建立复杂度   │ 简单        │  复杂        │
│ NAT穿透      │ 不需要      │  需要        │
│ 服务器压力   │ 高          │  低(只信令)  │
│ 适用场景     │ 通用        │  实时游戏/视频│
└──────────────┴─────────────┴──────────────┘

选择建议：
✅ 需要中心化控制 → WebSocket
✅ 追求极低延迟 → WebRTC
✅ 大规模用户 → WebSocket
✅ 小规模P2P → WebRTC
```

---

## 调试与监控

### 调试工具

```
1. Chrome DevTools

打开方式：
F12 → Network → WS

功能：
✅ 查看握手请求/响应
✅ 实时查看消息（绿色=发送，白色=接收）
✅ 查看帧详情
✅ 过滤消息
✅ 复制消息内容

2. websocat（命令行工具）

# 连接WebSocket服务器
websocat ws://echo.websocket.org

# 发送文件
websocat ws://example.com < data.json

# 保存接收的数据
websocat ws://example.com > output.txt

3. 自定义调试面板

class WebSocketDebugger {
    ws = null
    logs = []
    
    connect(url) {
        ws = new WebSocket(url)
        
        // 拦截send方法
        originalSend = ws.send.bind(ws)
        ws.send = (data) => {
            logMessage('SEND', data)
            originalSend(data)
        }
        
        ws.onmessage = (event) => {
            logMessage('RECV', event.data)
            // 调用原始处理器
        }
        
        ws.onerror = (error) => {
            logMessage('ERROR', error)
        }
    }
    
    logMessage(direction, data) {
        log = {
            timestamp: Date.now(),
            direction,
            size: data.length || data.byteLength,
            data: data
        }
        
        logs.push(log)
        displayInDebugPanel(log)
    }
    
    exportLogs() {
        return JSON.stringify(logs, null, 2)
    }
}
```

### 性能监控

```
监控指标：

class WebSocketMonitor {
    metrics = {
        // 连接指标
        connectionAttempts: 0,
        successfulConnections: 0,
        failedConnections: 0,
        currentConnections: 0,
        avgConnectionTime: 0,
        
        // 消息指标
        messagesSent: 0,
        messagesReceived: 0,
        bytesSent: 0,
        bytesReceived: 0,
        avgMessageSize: 0,
        avgLatency: 0,
        
        // 错误指标
        errors: 0,
        reconnects: 0,
        timeouts: 0
    }
    
    recordConnection(success, duration) {
        metrics.connectionAttempts++
        
        if (success) {
            metrics.successfulConnections++
            metrics.currentConnections++
            
            // 更新平均连接时间
            metrics.avgConnectionTime = calculateAverage(
                metrics.avgConnectionTime,
                duration,
                metrics.successfulConnections
            )
        } else {
            metrics.failedConnections++
        }
    }
    
    recordMessage(direction, size, latency) {
        if (direction === 'send') {
            metrics.messagesSent++
            metrics.bytesSent += size
        } else {
            metrics.messagesReceived++
            metrics.bytesReceived += size
            
            if (latency) {
                metrics.avgLatency = calculateAverage(
                    metrics.avgLatency,
                    latency,
                    metrics.messagesReceived
                )
            }
        }
        
        totalMessages = metrics.messagesSent + metrics.messagesReceived
        totalBytes = metrics.bytesSent + metrics.bytesReceived
        metrics.avgMessageSize = totalBytes / totalMessages
    }
    
    getReport() {
        return `
╔═══════════════════════════════════════╗
║      WebSocket性能报告                 ║
╠═══════════════════════════════════════╣
║ 连接统计:                             ║
║   尝试: ${metrics.connectionAttempts}  ║
║   成功: ${metrics.successfulConnections}║
║   失败: ${metrics.failedConnections}   ║
║   当前: ${metrics.currentConnections}  ║
║   平均连接时间: ${metrics.avgConnectionTime}ms ║
╠═══════════════════════════════════════╣
║ 消息统计:                             ║
║   发送: ${metrics.messagesSent}条     ║
║   接收: ${metrics.messagesReceived}条  ║
║   发送流量: ${formatBytes(metrics.bytesSent)} ║
║   接收流量: ${formatBytes(metrics.bytesReceived)} ║
║   平均消息大小: ${formatBytes(metrics.avgMessageSize)} ║
║   平均延迟: ${metrics.avgLatency}ms   ║
╠═══════════════════════════════════════╣
║ 错误统计:                             ║
║   错误: ${metrics.errors}次           ║
║   重连: ${metrics.reconnects}次       ║
║   超时: ${metrics.timeouts}次         ║
╚═══════════════════════════════════════╝
        `
    }
}
```

---

## 最佳实践

### 1. 连接管理

```
✅ 使用重连机制
✅ 实现心跳保活
✅ 正确处理关闭事件
✅ 设置合理的超时
✅ 缓存离线期间的消息

❌ 不要忘记清理资源
❌ 不要无限重连
❌ 不要忽略错误处理
```

### 2. 消息设计

```
✅ 使用统一的消息格式
✅ 包含消息类型标识
✅ 添加必要的元数据（ID、时间戳）
✅ 考虑版本兼容性
✅ 限制消息大小

消息格式示例：
{
    "version": "1.0",
    "type": "message_type",
    "id": "unique_id",
    "timestamp": 1638360000000,
    "data": {
        // 实际数据
    }
}
```

### 3. 安全实践

```
✅ 使用WSS加密
✅ 验证Origin
✅ 实现认证机制
✅ 输入验证
✅ 速率限制
✅ 防止XSS和注入

❌ 不要在URL中传敏感信息
❌ 不要信任客户端数据
❌ 不要暴露详细错误信息
```

### 4. 性能优化

```
✅ 批量发送消息
✅ 启用压缩
✅ 使用二进制格式（适当时）
✅ 限制连接数
✅ 监控性能指标

❌ 不要发送过大的消息
❌ 不要过度频繁发送
❌ 不要忽略资源清理
```

---

## 学习资源

### 官方规范
- RFC 6455: The WebSocket Protocol
- MDN Web Docs: WebSocket API

### 推荐库

**JavaScript/Node.js:**
- `ws` - 简单高效的WebSocket库
- `Socket.IO` - 功能丰富，自动降级
- `uWebSockets.js` - 高性能

**Python:**
- `websockets` - 异步WebSocket
- `Flask-SocketIO` - Flask集成

**Java:**
- `Java WebSocket API` - 标准实现
- `Spring WebSocket` - Spring集成

### 在线工具
- websocket.org - 测试服务器
- Postman - WebSocket客户端
- wscat - 命令行工具

---

## 总结

```
WebSocket技术要点：

核心特性：
├─ 全双工通信
├─ 持久连接
├─ 低延迟
├─ 服务器推送
└─ 轻量级协议

关键流程：
1. HTTP握手升级
2. 数据帧传输
3. 心跳保活
4. 正常关闭

最佳实践：
✅ 实现完善的重连机制
✅ 使用心跳检测
✅ 设计良好的消息格式
✅ 注重安全性
✅ 监控性能指标

应用场景：
- 实时聊天
- 实时通知
- 协同编辑
- 在线游戏
- 数据大屏
- 物联网

与其他技术：
- vs HTTP: 更低延迟，双向通信
- vs SSE: 双向 vs 单向
- vs WebRTC: 服务器中转 vs P2P
```

WebSocket为Web带来了真正的实时通信能力，掌握它将使你能够构建出色的实时应用！

继续探索，实践出真知！🚀

