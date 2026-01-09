# Spring AI 核心设计深度解析

## TL;DR

Spring AI 的核心设计遵循 **"抽象不变，实现可换"** 的 Spring 哲学。它通过四层架构将 AI 能力融入 Spring 生态：**Model 抽象层**定义统一接口、**ChatClient 高级 API** 提供 Fluent 调用体验、**Models 模块**实现具体提供商适配、**Memory 模块**管理对话上下文。理解这四层的职责边界和协作方式，是掌握 Spring AI 的关键。

---

## 一、架构全景：为什么这样设计？

### 1.1 AI 集成的核心挑战

在设计 AI 框架时，架构师需要回答几个关键问题：

| 挑战 | 本质问题 | Spring AI 的回答 |
|------|----------|------------------|
| 提供商碎片化 | 如何屏蔽 OpenAI/Claude/Ollama 的差异？ | 抽象统一的 `ChatModel` 接口 |
| 上下文管理 | 多轮对话的状态如何维护？ | 分离 `ChatMemory` 和 `ChatMemoryRepository` |
| 横切关注点 | 日志、监控、安全如何统一处理？ | `Advisor` 拦截器链 |
| 开发体验 | 如何让调用足够简洁？ | `ChatClient` Fluent API |
| 可扩展性 | 如何支持自定义模型/存储/处理逻辑？ | 接口抽象 + 依赖注入 |

### 1.2 分层架构总览

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                         应用层 (Your Application)                           │
│                   业务逻辑、Controller、Service                             │
└─────────────────────────────────────────────────────────────────────────────┘
                                      │
                                      ▼
┌─────────────────────────────────────────────────────────────────────────────┐
│                      ChatClient 层 (Fluent API)                             │
│             面向开发者的高级抽象，屏蔽底层复杂度                              │
│     .prompt() → .system() → .user() → .tools() → .advisors() → .call()     │
└─────────────────────────────────────────────────────────────────────────────┘
                                      │
                    ┌─────────────────┴─────────────────┐
                    ▼                                   ▼
        ┌───────────────────────┐           ┌───────────────────────┐
        │    Advisor Chain      │           │    Tool Execution     │
        │  (横切关注点处理)      │           │   (Function Calling)  │
        │ Memory / Log / Guard  │           │  SQL / HTTP / RPC     │
        └───────────────────────┘           └───────────────────────┘
                    │
                    ▼
┌─────────────────────────────────────────────────────────────────────────────┐
│                       ChatModel 层 (Core Abstraction)                       │
│                   模型能力的统一抽象，定义输入输出契约                        │
│                call(Prompt) → ChatResponse                                  │
│                stream(Prompt) → Flux<ChatResponse>                          │
└─────────────────────────────────────────────────────────────────────────────┘
                                      │
        ┌─────────────┬───────────────┼───────────────┬─────────────┐
        ▼             ▼               ▼               ▼             ▼
  ┌──────────┐  ┌──────────┐   ┌──────────┐   ┌──────────┐   ┌──────────┐
  │  OpenAI  │  │ Anthropic│   │  Ollama  │   │  Azure   │   │  更多... │
  │   Impl   │  │   Impl   │   │   Impl   │   │   Impl   │   │          │
  └──────────┘  └──────────┘   └──────────┘   └──────────┘   └──────────┘
```

### 1.3 核心架构决策

**决策一：能力层与编排层分离（ChatModel vs ChatClient）**

Spring AI 做了一个关键分层：`ChatModel` 是能力层，`ChatClient` 是编排层。

```
┌─────────────────────────────────────────────────────────────────┐
│  ChatClient（编排层）                                           │
│  - 编排 Advisor 链、Tool 执行、Memory 注入的协作流程              │
│  - 提供 Fluent API，简化调用复杂度                               │
│  - 面向应用开发者                                               │
└─────────────────────────────────────────────────────────────────┘
                              │ 依赖
                              ▼
┌─────────────────────────────────────────────────────────────────┐
│  ChatModel（能力层）                                            │
│  - 最小化接口，只定义 call(Prompt) → ChatResponse               │
│  - 无状态、无副作用、易测试                                      │
│  - 面向模型提供商实现者                                          │
└─────────────────────────────────────────────────────────────────┘
```

**为什么不合并成一个？**

| 关注点 | ChatModel | ChatClient |
|--------|-----------|------------|
| 设计目标 | 最小化、稳定 | 编排协作、易用 |
| 变化频率 | 低（接口稳定） | 高（持续增强能力） |
| 扩展方向 | 新增提供商实现 | 新增 Advisor、工具、选项 |

如果合并，每次增强编排能力都会影响所有模型实现者；分离后，各自独立演进。

**决策二：状态外挂而非内置（Stateless ChatModel + Advisor 注入状态）**

`ChatModel` 被设计为 **完全无状态**，每次调用独立。多轮对话的上下文通过 `Advisor` 在调用前注入：

```
                    ┌─────────────────────────────────┐
                    │   MessageChatMemoryAdvisor      │
                    │   (在请求中注入历史消息)         │
                    └─────────────────┬───────────────┘
                                      │
用户消息 ──────────────────────────────▼
                              ┌───────────────────┐
    [历史消息1]               │                   │
    [历史消息2]     ─────────▶│    ChatModel      │──────▶ AI 响应
    [当前用户消息]            │   (无状态调用)     │
                              └───────────────────┘
```

**为什么不让 ChatModel 自己管理状态？**

- **简化模型实现**：提供商只需实现"一次请求-一次响应"，不用考虑会话管理
- **灵活的状态策略**：滑动窗口、Token 限制、摘要压缩等策略可以自由组合
- **可测试性**：无状态接口更容易单元测试
- **横向扩展**：无状态服务可以随意负载均衡

**决策三：Advisor 责任链处理横切关注点**

横切关注点通过 `Advisor` 机制处理，而非硬编码在核心流程中：

```
请求 → [MemoryAdvisor] → [LogAdvisor] → [SafeGuardAdvisor] → ChatModel → 响应
                                                                  │
响应 ← [MemoryAdvisor] ← [LogAdvisor] ← [SafeGuardAdvisor] ←──────┘
```

**为什么选择责任链而非装饰器？**

| 对比 | 责任链（Advisor） | 装饰器 |
|------|-------------------|--------|
| 配置方式 | 列表声明，顺序清晰 | 层层嵌套，难以追踪 |
| 动态调整 | 运行时可增删 | 需要重新构建对象 |
| 顺序控制 | `Ordered` 接口统一管理 | 依赖嵌套顺序 |
| 请求/响应 | 天然支持 before/after | 需要额外设计 |

Spring AI 的选择让横切关注点的组合更加灵活和可控。

---

## 二、spring-ai-model：核心抽象层

`spring-ai-model` 是 Spring AI 的基石，定义了所有核心抽象。

### 2.1 Model 接口：泛型设计的艺术

```java
public interface Model<TReq extends ModelRequest<?>, TRes extends ModelResponse<?>> {
    TRes call(TReq request);
}
```

**架构思考：为什么用泛型而不是具体类型？**

Spring AI 需要支持多种模型类型：
- **Chat 模型**：`Prompt` → `ChatResponse`
- **Embedding 模型**：`EmbeddingRequest` → `EmbeddingResponse`
- **Image 模型**：`ImagePrompt` → `ImageResponse`
- **Audio 模型**：`AudioTranscriptionPrompt` → `AudioTranscriptionResponse`

泛型让这些模型共享同一个顶层抽象，同时保持类型安全。

### 2.2 ChatModel 接口：接口的渐进式设计

```java
public interface ChatModel extends Model<Prompt, ChatResponse>, StreamingChatModel {
    
    // 最简调用方式（门槛低）
    default String call(String message) {
        Prompt prompt = new Prompt(new UserMessage(message));
        return call(prompt).getResult().getOutput().getText();
    }
    
    // 完整调用方式（能力全）
    ChatResponse call(Prompt prompt);
    
    // 流式调用（默认不支持，按需覆盖）
    default Flux<ChatResponse> stream(Prompt prompt) {
        throw new UnsupportedOperationException("streaming is not supported");
    }
}
```

**渐进式 API 设计原则：**

| 方法 | 复杂度 | 适用场景 |
|------|--------|----------|
| `call(String)` | 最简单 | 快速原型、简单问答 |
| `call(Prompt)` | 中等 | 需要控制参数、多轮对话 |
| `stream(Prompt)` | 完整 | 实时响应、长文本生成 |

这种设计让新手能快速上手，同时不限制高级用户的能力。

### 2.3 Message 体系：领域建模

```
Message (interface) ← 统一的消息抽象
    │
    ├── UserMessage         # 用户输入（可包含多媒体）
    ├── AssistantMessage    # AI 回复（可能包含 ToolCalls）
    ├── SystemMessage       # 系统提示词（影响 AI 行为）
    └── ToolResponseMessage # 工具调用结果（回传给模型）
```

**为什么需要这么多消息类型？**

这是对 AI 对话领域的精确建模。每种消息类型有不同的：
- **语义**：谁说的、什么目的
- **处理方式**：SystemMessage 通常放在最前面
- **生命周期**：SystemMessage 可能在整个会话中保持

### 2.4 Prompt 类：请求的聚合根

```java
public class Prompt implements ModelRequest<List<Message>> {
    private final List<Message> messages;
    private ChatOptions chatOptions;
}
```

`Prompt` 是 DDD 中的 **聚合根**（Aggregate Root）概念：
- 封装了一次请求的所有数据
- 对外提供统一的访问入口
- 内部状态的一致性由自身保证

### 2.5 ToolCallback 接口：Function Calling 抽象

```java
public interface ToolCallback {
    ToolDefinition getToolDefinition();  // 工具元数据（给 AI 看）
    String call(String toolInput);        // 工具执行（实际调用）
}
```

**元数据与执行分离的设计意图：**

- `ToolDefinition` 描述工具"是什么"，用于让 AI 决策
- `call()` 定义工具"怎么做"，是实际的执行逻辑

这种分离让同一个工具可以有不同的"描述方式"（比如多语言描述），而执行逻辑保持不变。

---

## 三、spring-ai-client-chat：高级 API 层

`spring-ai-client-chat` 在 `ChatModel` 之上构建了更友好的开发体验。

### 3.1 ChatClient：Fluent API 的价值

```java
// 传统方式（繁琐）
Prompt prompt = new Prompt(
    List.of(
        new SystemMessage("你是专业助手"),
        new UserMessage("分析这份数据")
    ),
    ChatOptions.builder().temperature(0.7).build()
);
ChatResponse response = chatModel.call(prompt);
String content = response.getResult().getOutput().getText();

// ChatClient 方式（简洁）
String content = chatClient.prompt()
    .system("你是专业助手")
    .user("分析这份数据")
    .options(o -> o.temperature(0.7))
    .call()
    .content();
```

**Fluent API 的架构优势：**

1. **声明式**：代码表达"做什么"而非"怎么做"
2. **可读性**：链式调用接近自然语言
3. **类型安全**：编译期检查，IDE 自动补全
4. **默认值友好**：Builder 模式天然支持可选参数

### 3.2 Advisor 机制：AOP 思想的应用

```java
public interface Advisor extends Ordered {
    String getName();
}

public interface BaseAdvisor extends Advisor {
    ChatClientRequest before(ChatClientRequest request, AdvisorChain chain);
    ChatClientResponse after(ChatClientResponse response, AdvisorChain chain);
}
```

**Advisor 的核心价值：关注点分离**

```
┌─────────────────────────────────────────────────────────────────┐
│                     传统实现（耦合）                             │
├─────────────────────────────────────────────────────────────────┤
│  public ChatResponse chat(String message) {                    │
│      // 1. 日志记录                                             │
│      log.info("Request: {}", message);                         │
│      // 2. 加载历史消息                                         │
│      List<Message> history = memory.get(sessionId);            │
│      // 3. 安全检查                                             │
│      if (containsSensitiveWords(message)) throw ...;           │
│      // 4. 调用模型                                             │
│      ChatResponse response = chatModel.call(...);              │
│      // 5. 保存历史                                             │
│      memory.add(sessionId, response);                          │
│      // 6. 记录指标                                             │
│      metrics.record(response.getUsage());                      │
│      return response;                                          │
│  }                                                             │
└─────────────────────────────────────────────────────────────────┘

┌─────────────────────────────────────────────────────────────────┐
│                     Advisor 实现（解耦）                         │
├─────────────────────────────────────────────────────────────────┤
│  ChatClient.builder(chatModel)                                 │
│      .defaultAdvisors(                                         │
│          new SimpleLoggerAdvisor(),        // 日志              │
│          MessageChatMemoryAdvisor.builder(memory).build(), // 记忆│
│          new SafeGuardAdvisor(),           // 安全              │
│          new MetricsAdvisor(registry)      // 监控              │
│      )                                                         │
│      .build();                                                 │
│                                                                │
│  // 业务代码只关注业务                                           │
│  chatClient.prompt().user(message).call().content();           │
└─────────────────────────────────────────────────────────────────┘
```

### 3.3 MessageChatMemoryAdvisor 源码解析

```java
public final class MessageChatMemoryAdvisor implements BaseChatMemoryAdvisor {
    
    private final ChatMemory chatMemory;
    
    @Override
    public ChatClientRequest before(ChatClientRequest request, AdvisorChain chain) {
        String conversationId = getConversationId(request.context());
        
        // 1. 从 Memory 获取历史消息
        List<Message> memoryMessages = this.chatMemory.get(conversationId);
        
        // 2. 将历史消息 + 当前消息合并
        List<Message> processedMessages = new ArrayList<>(memoryMessages);
        processedMessages.addAll(request.prompt().getInstructions());
        
        // 3. 保存当前用户消息到 Memory
        this.chatMemory.add(conversationId, request.prompt().getUserMessage());
        
        // 4. 返回修改后的请求
        return request.mutate()
            .prompt(request.prompt().mutate().messages(processedMessages).build())
            .build();
    }
    
    @Override
    public ChatClientResponse after(ChatClientResponse response, AdvisorChain chain) {
        // 保存 AI 回复到 Memory
        List<Message> assistantMessages = response.chatResponse()
            .getResults()
            .stream()
            .map(g -> (Message) g.getOutput())
            .toList();
        this.chatMemory.add(conversationId, assistantMessages);
        return response;
    }
}
```

**Advisor 链的执行顺序：**

```
请求进入 → Advisor1.before → Advisor2.before → Advisor3.before → ChatModel.call
                                                                       │
响应返回 ← Advisor1.after ← Advisor2.after ← Advisor3.after ←──────────┘
```

---

## 四、Models 模块：模型实现层

### 4.1 模块职责与边界

```
models/
├── spring-ai-openai/          # OpenAI (GPT-4, GPT-3.5)
├── spring-ai-anthropic/       # Anthropic (Claude)
├── spring-ai-azure-openai/    # Azure OpenAI Service
├── spring-ai-ollama/          # Ollama (本地模型)
├── spring-ai-bedrock/         # AWS Bedrock
├── spring-ai-vertex-ai-gemini/# Google Gemini
├── spring-ai-deepseek/        # DeepSeek
├── spring-ai-zhipuai/         # 智谱 AI
└── ...
```

**每个模块的职责：**

1. 实现 `ChatModel` 接口，提供标准化的调用入口
2. 封装提供商的 HTTP API 调用细节
3. 处理请求/响应格式转换
4. 集成 Spring 生态（RetryTemplate、ObservationRegistry）

### 4.2 模型实现的架构模式

以 `OpenAiChatModel` 为例，分析典型的模型实现结构：

```java
public class OpenAiChatModel implements ChatModel {
    
    // ===== 依赖注入 =====
    private final OpenAiApi openAiApi;           // 底层 API 客户端
    private final OpenAiChatOptions defaultOptions; // 默认配置
    
    // ===== Spring 生态整合 =====
    private final RetryTemplate retryTemplate;   // 重试机制
    private final ObservationRegistry observationRegistry; // 可观测性
    
    // ===== 扩展点 =====
    private final ToolCallingManager toolCallingManager; // 工具调用管理
    
    @Override
    public ChatResponse call(Prompt prompt) {
        // 1. 配置合并（请求级覆盖默认级）
        // 2. 格式转换（Spring AI → OpenAI API）
        // 3. API 调用（带重试和可观测性）
        // 4. Tool Calling 处理（如果有）
        // 5. 格式转换（OpenAI API → Spring AI）
    }
}
```

**架构要点：**

| 关注点 | 实现方式 | 可替换性 |
|--------|----------|----------|
| HTTP 调用 | 委托给 `OpenAiApi` | 可替换 HTTP 客户端 |
| 重试机制 | 使用 `RetryTemplate` | 可配置重试策略 |
| 可观测性 | 集成 `Micrometer` | 自动埋点 |
| 工具调用 | 委托给 `ToolCallingManager` | 可扩展执行策略 |

---

## 五、Memory 模块：对话记忆层

### 5.1 分层设计的价值

```
┌─────────────────────────────────────────┐
│           ChatMemory                    │  ← 业务策略层
│   • 消息窗口管理（滑动窗口）              │
│   • SystemMessage 替换策略              │
│   • Token 限制裁剪                      │
└─────────────────────────────────────────┘
                    │ 依赖倒置
                    ▼
┌─────────────────────────────────────────┐
│        ChatMemoryRepository             │  ← 存储抽象层
│   • findByConversationId               │
│   • saveAll                            │
│   • deleteByConversationId             │
└─────────────────────────────────────────┘
                    │ 具体实现
        ┌───────────┼───────────┐
        ▼           ▼           ▼
  ┌──────────┐ ┌──────────┐ ┌──────────┐
  │ InMemory │ │   JDBC   │ │ Cassandra│
  └──────────┘ └──────────┘ └──────────┘
```

**为什么要分两层？**

考虑这个场景：你需要把存储从 InMemory 切换到 Redis。

- **如果不分层**：需要修改消息窗口管理、Token 裁剪等所有逻辑
- **分层之后**：只需要实现一个 `RedisChatMemoryRepository`，业务逻辑完全不变

### 5.2 MessageWindowChatMemory 的策略设计

```java
public final class MessageWindowChatMemory implements ChatMemory {
    
    private final ChatMemoryRepository chatMemoryRepository;
    private final int maxMessages;  // 默认 20
    
    private List<Message> process(List<Message> memoryMessages, List<Message> newMessages) {
        List<Message> result = new ArrayList<>();
        
        // 策略1：SystemMessage 替换
        // 如果有新的 SystemMessage，移除旧的 SystemMessage
        boolean hasNewSystem = newMessages.stream()
            .anyMatch(m -> m instanceof SystemMessage);
        
        memoryMessages.stream()
            .filter(m -> !(hasNewSystem && m instanceof SystemMessage))
            .forEach(result::add);
        
        result.addAll(newMessages);
        
        // 策略2：窗口裁剪
        // 超过 maxMessages 时，优先移除旧的非系统消息
        if (result.size() > maxMessages) {
            return trimMessages(result);
        }
        
        return result;
    }
}
```

**内置策略的设计考量：**

| 策略 | 原因 |
|------|------|
| SystemMessage 替换 | 新的系统提示词通常代表新的意图，旧的应该失效 |
| 保留 SystemMessage 优先 | 系统提示词定义 AI 行为，不应该被裁剪掉 |
| 先进先出裁剪 | 旧消息的价值通常低于新消息 |

### 5.3 存储实现选型决策树

```
                        ┌──────────────────┐
                        │ 需要持久化吗？     │
                        └────────┬─────────┘
                           │           │
                         否 │           │ 是
                           ▼           ▼
                   ┌──────────┐  ┌────────────────┐
                   │ InMemory │  │ 是分布式部署吗？ │
                   └──────────┘  └───────┬────────┘
                                    │           │
                                  否 │           │ 是
                                    ▼           ▼
                            ┌──────────┐  ┌────────────────┐
                            │   JDBC   │  │ 需要高性能吗？   │
                            └──────────┘  └───────┬────────┘
                                             │           │
                                           否 │           │ 是
                                             ▼           ▼
                                     ┌──────────┐  ┌──────────┐
                                     │ Cassandra│  │   Redis  │
                                     └──────────┘  └──────────┘
```

---

## 六、设计模式总结

Spring AI 在设计中运用了多种经典设计模式，这些模式的组合使用是其架构灵活性的来源。

### 6.1 策略模式（Strategy）

**应用场景：ChatModel 接口与各提供商实现**

```
┌─────────────┐
│  ChatModel  │ ← 策略接口
└──────┬──────┘
       │
   ┌───┴───┐
   ▼       ▼
┌───────┐ ┌───────┐
│OpenAI │ │Claude │  ← 具体策略
└───────┘ └───────┘
```

**价值**：调用方依赖接口而非实现，可以在运行时切换模型提供商而不修改业务代码。

```java
// 切换模型只需要改配置，不改代码
@Bean
@Profile("openai")
public ChatModel openAiChatModel() { ... }

@Bean
@Profile("ollama")
public ChatModel ollamaChatModel() { ... }
```

### 6.2 责任链模式（Chain of Responsibility）

**应用场景：Advisor 链式处理**

```
Request → [MemoryAdvisor] → [LogAdvisor] → [GuardAdvisor] → ChatModel
              │                  │               │
              ▼                  ▼               ▼
          before()           before()        before()
```

**价值**：
- 每个 Advisor 只关注自己的职责
- 可以动态添加或移除处理节点
- 通过 `Ordered` 接口控制执行顺序

```java
public interface Advisor extends Ordered {
    int getOrder();  // 返回值越小，优先级越高
}
```

### 6.3 模板方法模式（Template Method）

**应用场景：BaseAdvisor 定义处理流程骨架**

```java
public interface BaseAdvisor extends Advisor {
    // 模板方法定义了处理流程
    default ChatClientResponse advise(ChatClientRequest request, AdvisorChain chain) {
        // 1. 前置处理（子类实现）
        ChatClientRequest processed = before(request, chain);
        
        // 2. 调用下一个 Advisor
        ChatClientResponse response = chain.next(processed);
        
        // 3. 后置处理（子类实现）
        return after(response, chain);
    }
    
    ChatClientRequest before(ChatClientRequest request, AdvisorChain chain);
    ChatClientResponse after(ChatClientResponse response, AdvisorChain chain);
}
```

**价值**：固定处理流程骨架，子类只需要关注具体的 before/after 逻辑。

### 6.4 建造者模式（Builder）

**应用场景：ChatClient、Prompt、MessageWindowChatMemory 等**

```java
// ChatClient Builder
ChatClient client = ChatClient.builder(chatModel)
    .defaultSystem("你是专业助手")
    .defaultTools(tool1, tool2)
    .defaultAdvisors(advisor1, advisor2)
    .build();

// MessageWindowChatMemory Builder
ChatMemory memory = MessageWindowChatMemory.builder()
    .chatMemoryRepository(repository)
    .maxMessages(30)
    .build();
```

**价值**：
- 解决多参数构造的可读性问题
- 支持可选参数和默认值
- 链式调用，代码更流畅

### 6.5 适配器模式（Adapter）

**应用场景：各 ChatModel 实现将提供商 API 适配到统一接口**

```
┌────────────────┐      ┌─────────────────────┐      ┌─────────────────┐
│   ChatModel    │      │   OpenAiChatModel   │      │    OpenAI API   │
│   (统一接口)    │ ───▶ │     (适配器)         │ ───▶ │   (外部接口)     │
└────────────────┘      └─────────────────────┘      └─────────────────┘
     Prompt                    转换                  ChatCompletionRequest
     ChatResponse              转换                  ChatCompletion
```

**价值**：将不兼容的接口转换为兼容的接口，使得不同提供商可以统一调用。

### 6.6 仓储模式（Repository）

**应用场景：ChatMemoryRepository 封装存储细节**

```java
public interface ChatMemoryRepository {
    List<Message> findByConversationId(String conversationId);
    void saveAll(String conversationId, List<Message> messages);
    void deleteByConversationId(String conversationId);
}
```

**价值**：
- 将存储逻辑与业务逻辑分离
- 业务层不关心数据存在哪里、怎么存
- 可以轻松切换存储实现（JDBC → Redis → Cassandra）

### 6.7 组合模式（Composite）

**应用场景：Prompt 聚合多个 Message**

```java
public class Prompt implements ModelRequest<List<Message>> {
    private final List<Message> messages;  // 聚合多个 Message
    
    public Prompt(Message... messages) {
        this.messages = Arrays.asList(messages);
    }
}
```

**价值**：将多个 Message 组合成一个 Prompt，调用方可以统一处理。

### 6.8 观察者模式（Observer）

**应用场景：通过 Micrometer 实现可观测性**

```java
public class OpenAiChatModel implements ChatModel {
    private final ObservationRegistry observationRegistry;
    
    @Override
    public ChatResponse call(Prompt prompt) {
        Observation observation = ChatModelObservationDocumentation.CHAT_MODEL_OPERATION
            .observation(observationRegistry, ...);
        
        return observation.observe(() -> {
            // 实际调用
        });
    }
}
```

**价值**：解耦核心逻辑和监控逻辑，监控系统变化不影响业务代码。

### 6.9 模式组合：整体协作

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                              设计模式协作图                                  │
├─────────────────────────────────────────────────────────────────────────────┤
│                                                                             │
│  ┌─────────────┐    Builder     ┌─────────────┐                            │
│  │ ChatClient  │ ◀────────────  │   Builder   │                            │
│  └──────┬──────┘                └─────────────┘                            │
│         │                                                                   │
│         │ 调用                                                              │
│         ▼                                                                   │
│  ┌─────────────────────────────────────────┐                               │
│  │          Advisor Chain                   │  ← 责任链模式                 │
│  │  ┌───────┐ ┌───────┐ ┌───────┐          │                               │
│  │  │Advisor│→│Advisor│→│Advisor│          │  ← 策略模式（每个Advisor）     │
│  │  └───────┘ └───────┘ └───────┘          │                               │
│  └───────────────────┬─────────────────────┘                               │
│                      │                                                      │
│                      ▼                                                      │
│  ┌─────────────────────────────────────────┐                               │
│  │            ChatModel                     │  ← 策略模式                   │
│  │      (OpenAI/Claude/Ollama)              │  ← 适配器模式                 │
│  └───────────────────┬─────────────────────┘                               │
│                      │                                                      │
│                      ▼                                                      │
│  ┌─────────────────────────────────────────┐                               │
│  │          ChatMemory                      │  ← 仓储模式                   │
│  │    ┌──────────────────────┐             │                               │
│  │    │ ChatMemoryRepository │             │  ← 策略模式（存储策略）        │
│  │    └──────────────────────┘             │                               │
│  └─────────────────────────────────────────┘                               │
│                                                                             │
└─────────────────────────────────────────────────────────────────────────────┘
```

---

## 七、总结

### 一句话理解 Spring AI

> Spring AI 通过 **能力层（ChatModel）+ 编排层（ChatClient）+ 拦截器（Advisor）+ 存储抽象（Repository）** 四层架构，将 AI 能力以 Spring 的方式融入 Java 生态——接口稳定、实现可换、关注点分离。

### 设计模式速查

| 模式 | 应用位置 | 一句话说明 |
|------|----------|------------|
| 策略模式 | ChatModel、Advisor | 切换模型/处理逻辑无需改业务代码 |
| 责任链模式 | AdvisorChain | Memory、日志、安全等关注点可插拔组合 |
| 建造者模式 | ChatClient、Prompt | 链式调用构建复杂对象 |
| 适配器模式 | OpenAI/Claude 等实现 | 统一不同提供商的 API 差异 |
| 仓储模式 | ChatMemoryRepository | 存储实现可从 InMemory 切到 JDBC/Redis |

### 什么时候用 Spring AI？

Spring AI 的能力边界取决于你的 **Agent 复杂度**：

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                          Agent 复杂度光谱                                   │
├─────────────────────────────────────────────────────────────────────────────┤
│                                                                             │
│   简单 Agent                              复杂 Agent                        │
│   ─────────────────────────────────────────────────────────────────────▶   │
│                                                                             │
│   • 单轮问答                              • ReAct 模式                      │
│   • 多轮对话 + Memory                     • 多步推理 + 自我反思              │
│   • 简单 Tool Calling                     • 动态任务分解                    │
│   • 固定流程编排                          • 条件分支 + 循环                  │
│                                                                             │
│   ◀──────── Spring AI 覆盖 ────────▶     ◀──── 需要自研编排 ────▶          │
│                                                                             │
└─────────────────────────────────────────────────────────────────────────────┘
```

| 场景 | 推荐方案 |
|------|----------|
| 问答机器人、客服助手、简单数据查询 | ✅ Spring AI 足够 |
| 多轮对话 + 调用 2-3 个工具 | ✅ Spring AI（ChatClient + Advisor + Tool） |
| 需要 ReAct、Plan-and-Execute 等复杂推理模式 | ⚠️ Spring AI 作为底层，自研编排层 |
| 多 Agent 协作、动态任务图 | ⚠️ 考虑 LangGraph 思路，自建流程引擎 |

**简单判断**：Spring AI 擅长的是 **模型调用 + 简单编排**，不是复杂的 Agent 流程控制。如果你需要 ReAct、多步推理、动态分支，Spring AI 可以作为底层调用层，但流程编排需要自己实现或引入其他框架。

### 关于 Spring AI Alibaba

如果你的技术栈是 **Java + 阿里云生态**，[Spring AI Alibaba](https://sca.aliyun.com/docs/ai/overview/) 值得关注：

- **模型对接**：通义系列（百炼平台）开箱即用，省去自己封装的成本
- **多模态支持**：文生图、语音转录、文生语音等能力
- **云原生集成**：与阿里云 ARMS 监控、日志服务深度整合
- **未来方向**：计划支持可视化工作流编排，一键导出 Spring AI 代码

对于深度使用阿里云基础设施的团队，Spring AI Alibaba 比自己封装 DashScope SDK 更省心。

---

更多示例参考：[Spring AI 官方文档](https://docs.spring.io/spring-ai/reference/)

---

*本文基于 Spring AI 1.0.0 版本源码分析。如有疏漏，欢迎指正。*
