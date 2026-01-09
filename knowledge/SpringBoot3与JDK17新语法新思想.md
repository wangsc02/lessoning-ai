# Spring Boot 3 + JDK 17：新语法与新思想

> **TL;DR**：这不是一份迁移清单，而是一份"如何写出更现代Java代码"的指南。JDK 17和Spring Boot 3带来的不只是API变化，更是编码思想的升级——**更简洁、更安全、更函数式**。

---

## 一、JDK 17 新语法：让代码更简洁

### 1.1 var 局部变量类型推断

**旧写法**：
```java
Map<String, List<UserDTO>> usersByDepartment = new HashMap<String, List<UserDTO>>();
```

**新写法**：
```java
var usersByDepartment = new HashMap<String, List<UserDTO>>();
```

**什么时候用**：

| 场景 | 是否推荐 | 原因 |
|---|---|---|
| 右侧类型很明显 | ✅ 推荐 | `var list = new ArrayList<String>()` |
| 方法返回值类型复杂 | ✅ 推荐 | 减少重复 |
| 右侧类型不明显 | ❌ 不推荐 | `var result = service.process()` 看不出类型 |
| 基本类型 | ⚠️ 谨慎 | `var count = 1` 是int还是long？ |

**核心原则**：`var` 是为了减少冗余，不是为了隐藏类型。如果用了 `var` 反而让代码更难读，就不要用。

---

### 1.2 Record 类

**旧写法（传统POJO）**：
```java
public class UserDTO {
    private final String name;
    private final Integer age;
    private final String email;
    
    public UserDTO(String name, Integer age, String email) {
        this.name = name;
        this.age = age;
        this.email = email;
    }
    
    public String getName() { return name; }
    public Integer getAge() { return age; }
    public String getEmail() { return email; }
    
    @Override
    public boolean equals(Object o) { /* ... */ }
    
    @Override
    public int hashCode() { /* ... */ }
    
    @Override
    public String toString() { /* ... */ }
}
```

**新写法（Record）**：
```java
public record UserDTO(String name, Integer age, String email) {}
```

一行代码，自动生成：
- 构造器
- getter（`name()` 而非 `getName()`）
- `equals()`、`hashCode()`、`toString()`

**Record vs Lombok**：

| 维度 | Record | Lombok |
|---|---|---|
| 不可变性 | ✅ 强制不可变 | 需要手动加 `@Value` |
| 编译时检查 | ✅ 原生支持 | 依赖注解处理器 |
| 可读性 | ✅ 一眼看懂 | 需要了解注解含义 |
| 灵活性 | 较低 | 更高 |
| 继承 | ❌ 不支持 | 支持 |

**核心思想**：Record 不只是语法糖，它表达了一种设计意图——**这是一个纯粹的数据载体，不可变，没有行为**。

**适用场景**：
- DTO（数据传输对象）
- VO（值对象）
- 方法的多返回值
- 配置类的属性绑定

#### Record 的组织方式：还需要单独建 class 文件吗？

以前每个 DTO 都是单独一个文件，放在 `data` 包里。现在 Record 这么简洁，有几种新的组织方式可以考虑：

**方式一：嵌套 Record（推荐用于局部使用）**

如果一个 Record 只在某个 Service 或 Controller 中使用，可以定义为内部类：

```java
@Service
public class UserService {
    
    // 只在这个类中使用的 Record，直接定义在类内部
    public record UserCreateResult(Long userId, String token) {}
    
    public record UserQueryParam(String keyword, Integer status, int page, int size) {}
    
    public UserCreateResult createUser(UserCreateParam param) {
        // ...
        return new UserCreateResult(userId, token);
    }
}
```

**方式二：分组 Record（推荐用于相关数据）**

把相关的 Record 放在一个文件里：

```java
// UserData.java - 用户相关的所有 DTO
public final class UserData {
    private UserData() {}  // 工具类，不允许实例化
    
    public record CreateParam(String name, String email, String password) {}
    public record UpdateParam(Long id, String name, String email) {}
    public record DetailVO(Long id, String name, String email, LocalDateTime createdAt) {}
    public record ListItemVO(Long id, String name) {}
}

// 使用时
UserData.CreateParam param = new UserData.CreateParam("张三", "test@example.com", "123456");
```

**方式三：伴随定义（推荐用于接口层）**

Controller 的请求/响应 Record 和 Controller 放在同一个包里：

```
controller/
├── UserController.java
├── UserRequest.java      // 或直接定义在 Controller 内部
└── UserResponse.java
```

```java
// UserRequest.java
public final class UserRequest {
    public record Create(String name, String email) {}
    public record Update(String name, String email) {}
    public record Query(String keyword, Integer status) {}
}
```

**方式四：独立文件（用于广泛共享的 DTO）**

如果一个 DTO 被多个模块使用，还是单独建文件：

```java
// 放在 common 或 shared 包里
public record PageResult<T>(List<T> items, long total, int page, int size) {
    
    public static <T> PageResult<T> of(List<T> items, long total, int page, int size) {
        return new PageResult<>(items, total, page, size);
    }
    
    public boolean hasMore() {
        return (long) page * size < total;
    }
}
```

#### 选择建议

| 场景 | 推荐方式 | 原因 |
|---|---|---|
| 只在一个类中使用 | 嵌套 Record | 减少文件数量，就近定义 |
| 一组相关的请求/响应 | 分组到一个文件 | 好找，改起来方便 |
| Controller 的入参/出参 | 伴随 Controller | 符合就近原则 |
| 跨模块共享 | 独立文件 | 便于复用和管理 |
| 通用数据结构（如分页） | 独立文件 + 放 common 包 | 全局复用 |

#### 核心原则

> **就近原则**：Record 放在离使用它最近的地方。只有需要共享时，才往外提。

这和以前"所有 DTO 都放 data 包"的思路不同。以前那样做是因为 POJO 太冗长，分开放更好管理。现在 Record 很简洁，可以更灵活。

---

### 1.3 Pattern Matching

#### instanceof 模式匹配

**旧写法**：
```java
if (obj instanceof String) {
    String s = (String) obj;
    System.out.println(s.length());
}
```

**新写法**：
```java
if (obj instanceof String s) {
    System.out.println(s.length());
}
```

类型检查和类型转换一步完成。

#### switch 表达式增强

**旧写法**：
```java
String result;
switch (day) {
    case MONDAY:
    case TUESDAY:
        result = "工作日";
        break;
    case SATURDAY:
    case SUNDAY:
        result = "周末";
        break;
    default:
        result = "未知";
}
```

**新写法**：
```java
var result = switch (day) {
    case MONDAY, TUESDAY -> "工作日";
    case SATURDAY, SUNDAY -> "周末";
    default -> "未知";
};
```

**更强大的模式匹配（JDK 21预览，但思想先了解）**：
```java
// 根据类型分支处理
var message = switch (obj) {
    case Integer i -> "整数: " + i;
    case String s -> "字符串: " + s;
    case null -> "空值";
    default -> "其他类型";
};
```

**核心思想**：减少样板代码，让逻辑更清晰。

---

### 1.4 Text Blocks

**旧写法**：
```java
String json = "{\n" +
    "  \"name\": \"张三\",\n" +
    "  \"age\": 30,\n" +
    "  \"email\": \"zhangsan@example.com\"\n" +
    "}";
```

**新写法**：
```java
String json = """
    {
      "name": "张三",
      "age": 30,
      "email": "zhangsan@example.com"
    }
    """;
```

**常用场景**：
- SQL语句
- JSON/XML模板
- HTML片段
- 正则表达式

**格式化技巧**：
```java
// 使用 formatted() 方法
String sql = """
    SELECT * FROM users
    WHERE name = '%s'
    AND age > %d
    """.formatted(name, age);
```

---

### 1.5 Sealed（了解即可）

> **先说结论：大多数日常业务开发不需要 Sealed。**
> 
> 如果你没有明确的需求场景，可以跳过这一节。

#### 什么是 Sealed？

一句话：**限制谁可以实现/继承你的接口/类。**

```java
// 普通接口 - 任何人都可以实现
public interface PaymentResult {}

// sealed 接口 - 只有指定的类可以实现
public sealed interface PaymentResult 
    permits Success, Failure, Pending {}
// 除了 Success、Failure、Pending，别人写的实现会编译报错
```

#### 什么时候需要？

**当你同时满足以下两个条件时**：

1. ✅ 业务概念是"有限集合"（状态、类型、结果等）
2. ✅ 每种情况需要携带**不同的数据**

如果只满足条件1，用**枚举**就够了：

```java
// 状态只是标记，不带额外数据 → 用枚举
public enum OrderStatus { CREATED, PAID, SHIPPED, DELIVERED, CANCELLED }
```

如果两个条件都满足，才考虑 sealed：

```java
// 每种状态需要带不同的数据 → 用 sealed + record
public sealed interface OrderStatus 
    permits Created, Paid, Shipped, Cancelled {}

public record Created(LocalDateTime time) implements OrderStatus {}
public record Paid(String paymentId, BigDecimal amount) implements OrderStatus {}
public record Shipped(String trackingNo, String carrier) implements OrderStatus {}
public record Cancelled(String reason, String operator) implements OrderStatus {}
```

#### 实际例子：API 返回值

以前的常见写法：

```java
public class Result<T> {
    private int code;       // 0=成功，其他=失败
    private String message; // 失败时的错误信息
    private T data;         // 成功时的数据
}

// 问题：code=0 时 data 一定有值吗？类型系统不保证
```

用 sealed 重写：

```java
public sealed interface Result<T> permits Success, Failure {}

public record Success<T>(T data) implements Result<T> {}
public record Failure<T>(String code, String message) implements Result<T> {}

// 使用时
return switch (result) {
    case Success<User> s -> s.data();  // 编译器知道这里一定有 data
    case Failure<User> f -> throw new BizException(f.code());
}; // 如果以后加了 Pending 类型，这里会编译报错提醒你
```

#### 判断标准

| 你的情况 | 用什么 |
|---|---|
| 状态/类型是固定的几个值，不需要携带额外数据 | **枚举** |
| 状态/类型是固定的几个值，每种需要携带不同数据 | **Sealed** |
| 接口是开放的，允许任意实现 | **普通 interface** |

#### 建议

日常 CRUD 开发中，Sealed 的出镜率很低。

当你遇到以下情况时再考虑：
- 用枚举表示状态，但发现每个状态需要带不同的字段
- 写了很多 `if-else` 或 `switch` 判断类型，想让编译器帮你检查是否遗漏
- 设计 API 返回值，想让"成功"和"失败"携带不同的数据结构

如果没遇到这些场景，**先不用管 Sealed**。

---

## 二、Spring Boot 3 架构变化

### 2.1 Jakarta EE 命名空间

**变化**：
```java
// 旧
import javax.servlet.http.HttpServletRequest;
import javax.persistence.Entity;
import javax.validation.constraints.NotNull;

// 新
import jakarta.servlet.http.HttpServletRequest;
import jakarta.persistence.Entity;
import jakarta.validation.constraints.NotNull;
```

**为什么变**：
- Oracle 将 Java EE 捐给 Eclipse 基金会
- Eclipse 基金会不能使用 `javax` 商标
- 于是改名为 Jakarta EE，命名空间从 `javax` 改为 `jakarta`

**影响范围**：

| 包 | 旧命名空间 | 新命名空间 |
|---|---|---|
| Servlet | `javax.servlet` | `jakarta.servlet` |
| JPA | `javax.persistence` | `jakarta.persistence` |
| Validation | `javax.validation` | `jakarta.validation` |
| Transaction | `javax.transaction` | `jakarta.transaction` |
| WebSocket | `javax.websocket` | `jakarta.websocket` |

---

### 2.2 配置风格变化

#### 属性命名规范

Spring Boot 3 要求配置属性使用 **kebab-case**（小写+连字符）。

**旧写法**：
```yaml
spring:
  datasource:
    driverClassName: com.mysql.cj.jdbc.Driver
```

**新写法**：
```yaml
spring:
  datasource:
    driver-class-name: com.mysql.cj.jdbc.Driver
```

#### 配置类的新写法

**旧写法**：
```java
@Configuration
public class AppConfig {
    
    @Bean
    public DataSource dataSource() {
        // ...
    }
    
    @Bean
    public JdbcTemplate jdbcTemplate() {
        return new JdbcTemplate(dataSource());
    }
}
```

**新写法（推荐）**：
```java
@Configuration
public class AppConfig {
    
    @Bean
    DataSource dataSource() {  // 可以省略 public
        // ...
    }
    
    @Bean
    JdbcTemplate jdbcTemplate(DataSource dataSource) {  // 参数注入
        return new JdbcTemplate(dataSource);
    }
}
```

通过参数注入而非方法调用，更清晰地表达依赖关系。

---

### 2.3 依赖注入的新推荐

#### 构造器注入成为首选

**旧写法（字段注入）**：
```java
@Service
public class UserService {
    
    @Autowired
    private UserRepository userRepository;
    
    @Autowired
    private EmailService emailService;
}
```

**新写法（构造器注入）**：
```java
@Service
public class UserService {
    
    private final UserRepository userRepository;
    private final EmailService emailService;
    
    // 单构造器时，@Autowired 可省略
    public UserService(UserRepository userRepository, EmailService emailService) {
        this.userRepository = userRepository;
        this.emailService = emailService;
    }
}
```

**配合 Lombok 更简洁**：
```java
@Service
@RequiredArgsConstructor
public class UserService {
    
    private final UserRepository userRepository;
    private final EmailService emailService;
}
```

**为什么构造器注入更好**：

| 维度 | 字段注入 | 构造器注入 |
|---|---|---|
| 不可变性 | ❌ 字段可被修改 | ✅ 可以是 final |
| 测试友好 | ❌ 需要反射注入 | ✅ 直接 new |
| 依赖可见 | ❌ 隐藏在类内部 | ✅ 构造器明确列出 |
| 循环依赖 | ⚠️ 运行时才发现 | ✅ 编译时就报错 |

---

## 三、Spring Security 6 新范式

### 3.1 SecurityFilterChain 配置方式

**旧写法（继承式）**：
```java
@Configuration
@EnableWebSecurity
public class SecurityConfig extends WebSecurityConfigurerAdapter {
    
    @Override
    protected void configure(HttpSecurity http) throws Exception {
        http
            .authorizeRequests()
                .antMatchers("/public/**").permitAll()
                .antMatchers("/admin/**").hasRole("ADMIN")
                .anyRequest().authenticated()
            .and()
            .formLogin()
                .loginPage("/login")
                .permitAll();
    }
}
```

**新写法（函数式 + Lambda DSL）**：
```java
@Configuration
@EnableWebSecurity
public class SecurityConfig {
    
    @Bean
    public SecurityFilterChain filterChain(HttpSecurity http) throws Exception {
        http
            .authorizeHttpRequests(auth -> auth
                .requestMatchers("/public/**").permitAll()
                .requestMatchers("/admin/**").hasRole("ADMIN")
                .anyRequest().authenticated()
            )
            .formLogin(form -> form
                .loginPage("/login")
                .permitAll()
            );
        
        return http.build();
    }
}
```

**核心变化**：

| 旧 | 新 |
|---|---|
| 继承 `WebSecurityConfigurerAdapter` | 直接定义 `@Bean` |
| `authorizeRequests()` | `authorizeHttpRequests()` |
| `antMatchers()` | `requestMatchers()` |
| 链式 `.and()` | Lambda 表达式 |

### 3.2 权限控制的新写法

**方法级别的授权**：
```java
@Service
public class UserService {
    
    @PreAuthorize("hasRole('ADMIN')")
    public void deleteUser(Long userId) {
        // 只有 ADMIN 角色可以调用
    }
    
    @PreAuthorize("#userId == authentication.principal.id")
    public UserDTO getUser(Long userId) {
        // 只能查询自己的信息
    }
    
    @PostAuthorize("returnObject.ownerId == authentication.principal.id")
    public Order getOrder(Long orderId) {
        // 返回结果必须是自己的订单
    }
}
```

---

## 四、测试的新风格

### 4.1 JUnit 5 核心变化

#### 注解变化

| JUnit 4 | JUnit 5 |
|---|---|
| `@Before` | `@BeforeEach` |
| `@After` | `@AfterEach` |
| `@BeforeClass` | `@BeforeAll` |
| `@AfterClass` | `@AfterAll` |
| `@Ignore` | `@Disabled` |
| `@RunWith` | `@ExtendWith` |

#### 断言 API

**旧写法**：
```java
import static org.junit.Assert.*;

@Test
public void testAdd() {
    assertEquals(4, calculator.add(2, 2));
    assertTrue(result > 0);
}
```

**新写法**：
```java
import static org.junit.jupiter.api.Assertions.*;

@Test
void shouldAddNumbers() {  // 方法不需要 public
    assertEquals(4, calculator.add(2, 2));
    assertTrue(result > 0);
    
    // 分组断言 - 全部执行完再报告失败
    assertAll(
        () -> assertEquals(4, calculator.add(2, 2)),
        () -> assertEquals(0, calculator.add(-2, 2)),
        () -> assertEquals(-4, calculator.add(-2, -2))
    );
}
```

#### 参数化测试

```java
@ParameterizedTest
@ValueSource(strings = {"racecar", "radar", "level"})
void shouldDetectPalindrome(String candidate) {
    assertTrue(isPalindrome(candidate));
}

@ParameterizedTest
@CsvSource({
    "1, 2, 3",
    "5, 5, 10",
    "-1, 1, 0"
})
void shouldAdd(int a, int b, int expected) {
    assertEquals(expected, calculator.add(a, b));
}
```

### 4.2 Spring Boot 测试

**Controller 测试**：
```java
@WebMvcTest(UserController.class)
class UserControllerTest {
    
    @Autowired
    private MockMvc mockMvc;
    
    @MockBean
    private UserService userService;
    
    @Test
    void shouldReturnUser() throws Exception {
        // given
        var user = new UserDTO("张三", 30, "test@example.com");
        when(userService.getUser(1L)).thenReturn(user);
        
        // when & then
        mockMvc.perform(get("/users/1"))
            .andExpect(status().isOk())
            .andExpect(jsonPath("$.name").value("张三"));
    }
}
```

---

## 五、思维转变：从"能用"到"优雅"

### 5.1 不可变优先

**思想**：数据一旦创建就不应该被修改。

```java
// 使用 Record
public record UserDTO(String name, Integer age) {}

// 使用 final 字段
private final UserRepository userRepository;

// 使用不可变集合
var users = List.of(user1, user2, user3);  // 不可变
var mutableUsers = new ArrayList<>(users); // 需要修改时显式转换
```

**好处**：
- 线程安全
- 更容易推理
- 减少副作用

### 5.2 函数式风格

**旧写法**：
```java
List<String> names = new ArrayList<>();
for (User user : users) {
    if (user.isActive()) {
        names.add(user.getName());
    }
}
```

**新写法**：
```java
var names = users.stream()
    .filter(User::isActive)
    .map(User::getName)
    .toList();  // JDK 16+ 的新方法
```

### 5.3 声明式配置

**思想**：告诉框架"要什么"，而非"怎么做"。

```java
// 声明式安全配置
@PreAuthorize("hasRole('ADMIN')")
public void adminOperation() { }

// 声明式事务
@Transactional(readOnly = true)
public List<User> findAllUsers() { }

// 声明式缓存
@Cacheable("users")
public User findById(Long id) { }
```

### 5.4 防御性编程

**Optional 的正确使用**：
```java
// ❌ 不推荐
public User getUser(Long id) {
    User user = userRepository.findById(id);
    if (user == null) {
        throw new UserNotFoundException(id);
    }
    return user;
}

// ✅ 推荐
public User getUser(Long id) {
    return userRepository.findById(id)
        .orElseThrow(() -> new UserNotFoundException(id));
}
```

**Sealed Classes 防止非法状态**：
```java
// 编译时就能保证只有合法的状态
public sealed interface PaymentStatus 
    permits Pending, Completed, Failed {}
```

---

## 六、Java 17 vs TypeScript：架构思想对比

如果你有 TypeScript/前端开发经验，会发现 JDK 17 的很多特性和 TypeScript 的设计思想非常接近。这不是巧合——**现代语言都在向"类型安全 + 函数式 + 不可变"的方向演进**。

### 6.1 数据结构定义

| 场景 | TypeScript | Java 17 |
|---|---|---|
| 定义数据结构 | `interface` / `type` | `record` |
| 不可变性 | `readonly` | Record 天然不可变 |
| 可选字段 | `?` 修饰符 | `Optional<T>` |

**TypeScript**：
```typescript
interface User {
  readonly id: number;
  readonly name: string;
  readonly email?: string;  // 可选
}

const user: User = { id: 1, name: "张三" };
```

**Java 17**：
```java
public record User(
    Long id,
    String name,
    Optional<String> email  // 可选用 Optional 表达
) {}

var user = new User(1L, "张三", Optional.empty());
```

**核心思想**：用类型系统表达数据结构的约束，而非靠注释或运行时检查。

### 6.2 联合类型与模式匹配

TypeScript 的 **Discriminated Unions**（区分联合类型）是处理多种状态的利器。Java 17 的 **Sealed Classes + Pattern Matching** 实现了类似的效果。

**TypeScript**：
```typescript
type PaymentResult = 
  | { status: 'success'; transactionId: string }
  | { status: 'failed'; errorCode: string; errorMessage: string }
  | { status: 'pending'; estimatedTime: number };

function handleResult(result: PaymentResult) {
  switch (result.status) {
    case 'success':
      console.log(`成功: ${result.transactionId}`);
      break;
    case 'failed':
      console.log(`失败: ${result.errorMessage}`);
      break;
    case 'pending':
      console.log(`等待: ${result.estimatedTime}秒`);
      break;
  }
}
```

**Java 17**：
```java
public sealed interface PaymentResult 
    permits Success, Failure, Pending {}

public record Success(String transactionId) implements PaymentResult {}
public record Failure(String errorCode, String errorMessage) implements PaymentResult {}
public record Pending(Duration estimatedTime) implements PaymentResult {}

// 模式匹配（JDK 21 完全支持，JDK 17 预览）
public String handleResult(PaymentResult result) {
    return switch (result) {
        case Success s -> "成功: " + s.transactionId();
        case Failure f -> "失败: " + f.errorMessage();
        case Pending p -> "等待: " + p.estimatedTime().toSeconds() + "秒";
    };
}
```

**核心思想**：用类型系统穷尽所有可能的状态，编译器帮你检查是否遗漏。

### 6.3 空值处理

| 方式 | TypeScript | Java 17 |
|---|---|---|
| 可选链 | `user?.address?.city` | `Optional` + `map` |
| 空值合并 | `value ?? defaultValue` | `orElse()` |
| 非空断言 | `value!` | `orElseThrow()` |

**TypeScript**：
```typescript
const city = user?.address?.city ?? "未知";

// 或者
if (user?.address?.city) {
  console.log(user.address.city);
}
```

**Java 17**：
```java
var city = Optional.ofNullable(user)
    .map(User::getAddress)
    .map(Address::getCity)
    .orElse("未知");

// 或者使用 ifPresent
Optional.ofNullable(user)
    .map(User::getAddress)
    .map(Address::getCity)
    .ifPresent(System.out::println);
```

**核心思想**：用类型（Optional/可选类型）显式表达"可能为空"，而非到处判 null。

### 6.4 函数式编程

| 概念 | TypeScript | Java 17 |
|---|---|---|
| 箭头函数 | `(x) => x * 2` | `x -> x * 2` |
| 数组操作 | `map`, `filter`, `reduce` | `Stream` API |
| 方法引用 | 无（直接传函数） | `User::getName` |

**TypeScript**：
```typescript
const activeUserNames = users
  .filter(u => u.isActive)
  .map(u => u.name);
```

**Java 17**：
```java
var activeUserNames = users.stream()
    .filter(User::isActive)
    .map(User::getName)
    .toList();
```

几乎一样！

### 6.5 类型推断

| 场景 | TypeScript | Java 17 |
|---|---|---|
| 变量类型推断 | `const x = 1` | `var x = 1` |
| 泛型推断 | 自动推断 | 钻石操作符 `<>` |

**TypeScript**：
```typescript
const users = new Map<string, User>();  // 或省略类型
const list = [1, 2, 3];  // 推断为 number[]
```

**Java 17**：
```java
var users = new HashMap<String, User>();  // 右侧指定类型
var list = List.of(1, 2, 3);  // 推断为 List<Integer>
```

### 6.6 架构思想的共同演进

| 思想 | TypeScript 实践 | Java 17 实践 |
|---|---|---|
| **不可变优先** | `readonly`、`const`、Immutable.js | `Record`、`final`、不可变集合 |
| **类型安全** | 严格模式、类型守卫 | Sealed Classes、Pattern Matching |
| **空安全** | 严格空检查、可选链 | `Optional`、`@NonNull` |
| **函数式** | 高阶函数、纯函数 | Stream、Lambda、方法引用 |
| **声明式** | 装饰器、React Hooks | 注解驱动、DSL |

### 6.7 给有 TypeScript 经验的开发者的建议

如果你熟悉 TypeScript，学习 Java 17 时可以这样对应理解：

| TypeScript 概念 | 对应的 Java 17 概念 |
|---|---|
| `interface` 定义数据 | `record` |
| Discriminated Union | `sealed interface` + `record` |
| `?:` 可选属性 | `Optional<T>` |
| Type Guard | Pattern Matching |
| `?.` 可选链 | `Optional.map()` |
| `??` 空值合并 | `orElse()` |
| `readonly` | `final` + Record |
| 装饰器 | 注解 |

**核心启示**：

> **两种语言都在向同一个方向演进——用类型系统在编译时捕获更多错误，减少运行时的意外。**

掌握这个共同的思想，比记住具体语法更重要。

---

## 总结

### 语法层面

| 特性 | 核心价值 |
|---|---|
| var | 减少类型冗余 |
| Record | 不可变数据载体 |
| Pattern Matching | 简化类型判断 |
| Text Blocks | 多行字符串更清晰 |
| Sealed Classes | 精确控制继承 |

### 架构层面

| 变化 | 核心思想 |
|---|---|
| jakarta 命名空间 | 拥抱 Jakarta EE 生态 |
| 构造器注入 | 依赖显式化 + 不可变 |
| 函数式配置 | 声明式 > 命令式 |
| Lambda DSL | 配置更简洁 |

### 思想层面

| 原则 | 实践 |
|---|---|
| 不可变优先 | Record、final、不可变集合 |
| 函数式风格 | Stream、Lambda、方法引用 |
| 声明式编程 | 注解驱动、DSL配置 |
| 防御性编程 | Optional、Sealed Classes |

---

> **最后一句话**：新版本带来的不只是API变化，更是编程范式的升级。与其把它当成"不得不做的迁移"，不如把它当成"写出更好代码的机会"。

