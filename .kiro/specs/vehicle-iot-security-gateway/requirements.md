# 需求文档：车联网安全通信网关系统

## 引言

本文档定义了基于国密算法（SM2/SM4）的车联网安全通信网关系统的功能需求。该系统旨在保障车云通信的真实性、机密性与不可否认性，通过轻量级证书颁发机构（CA）建立信任根，实现车云双向身份认证，采用 SM4 对称加密保护业务数据，使用 SM2 数字签名确保数据完整性，并提供 Web 可视化管理平台实时监控安全通信过程。

系统符合国家商用密码标准，有效防御身份伪造、中间人攻击及数据篡改等安全威胁。

## 术语表

- **系统（System）**：车联网安全通信网关系统
- **证书管理模块（Certificate_Management_Module）**：负责国密证书颁发、存储、验证与撤销的组件
- **身份认证模块（Authentication_Module）**：实现车云双向身份认证的组件
- **加密签名模块（Crypto_Module）**：提供 SM2/SM4 加密解密和数字签名验签服务的组件
- **审计模块（Audit_Module）**：记录所有安全事件和业务操作的组件
- **Web管理平台（Web_Platform）**：提供可视化界面的管理平台
- **车端设备（Vehicle）**：接入系统的车辆终端设备
- **网关（Gateway）**：安全通信网关服务
- **CA（Certificate_Authority）**：证书颁发机构
- **会话（Session）**：车端与网关之间建立的安全通信会话
- **证书（Certificate）**：符合国密标准的 SM2 数字证书
- **安全报文（Secure_Message）**：经过加密和签名的数据报文
- **CRL（Certificate_Revocation_List）**：证书撤销列表
- **Nonce**：用于防重放攻击的唯一随机数

## 需求

### 需求 1：国密证书颁发

**用户故事**：作为系统管理员，我希望系统能够为车端和云端签发符合国密标准的 SM2 数字证书，以便建立系统信任根。

#### 验收标准

1. WHEN 收到有效的证书申请请求时，THE Certificate_Management_Module SHALL 生成唯一的证书序列号
2. WHEN 颁发证书时，THE Certificate_Management_Module SHALL 使用 SM2 算法对证书进行签名
3. WHEN 颁发证书时，THE Certificate_Management_Module SHALL 设置证书有效期为 1 年
4. WHEN 颁发证书时，THE Certificate_Management_Module SHALL 确保证书的 validFrom 早于 validTo
5. WHEN 证书颁发完成时，THE Certificate_Management_Module SHALL 将证书存储到数据库
6. WHEN 证书颁发完成时，THE Audit_Module SHALL 记录证书颁发操作到审计日志

### 需求 2：证书验证

**用户故事**：作为系统，我希望能够验证证书的有效性，以便确保只有持有有效证书的实体才能接入系统。

#### 验收标准

1. WHEN 验证证书时，THE Certificate_Management_Module SHALL 检查证书格式是否正确
2. IF 当前时间早于证书的 validFrom，THEN THE Certificate_Management_Module SHALL 拒绝该证书并返回"证书尚未生效"错误
3. IF 当前时间晚于证书的 validTo，THEN THE Certificate_Management_Module SHALL 拒绝该证书并返回"证书已过期"错误
4. WHEN 验证证书时，THE Certificate_Management_Module SHALL 检查证书序列号是否在 CRL 中
5. IF 证书序列号在 CRL 中，THEN THE Certificate_Management_Module SHALL 拒绝该证书并返回"证书已被撤销"错误
6. WHEN 验证证书时，THE Certificate_Management_Module SHALL 使用 CA 公钥验证证书签名
7. IF 证书签名验证失败，THEN THE Certificate_Management_Module SHALL 拒绝该证书并返回"证书签名验证失败"错误

### 需求 3：证书撤销管理

**用户故事**：作为系统管理员，我希望能够撤销已颁发的证书，以便应对证书泄露或其他安全事件。

#### 验收标准

1. WHEN 收到证书撤销请求时，THE Certificate_Management_Module SHALL 将证书序列号添加到 CRL
2. WHEN 证书被撤销时，THE Audit_Module SHALL 记录证书撤销操作到审计日志
3. THE Certificate_Management_Module SHALL 至少每天更新一次 CRL
4. WHEN 验证证书时，THE Certificate_Management_Module SHALL 使用最新的 CRL

### 需求 4：车云双向身份认证

**用户故事**：作为系统，我希望实现车云双向身份认证，以便防御身份伪造和中间人攻击。

#### 验收标准

1. WHEN 车端发起连接请求时，THE Authentication_Module SHALL 验证车端证书的有效性
2. WHEN 车端证书验证失败时，THE Authentication_Module SHALL 终止认证流程并返回相应错误码
3. WHEN 车端证书验证成功时，THE Gateway SHALL 向车端发送网关证书
4. WHEN 网关发送证书后，THE Authentication_Module SHALL 生成 32 字节的随机挑战值
5. WHEN 收到车端的签名响应时，THE Authentication_Module SHALL 使用车端证书公钥验证签名
6. IF 车端签名验证失败，THEN THE Authentication_Module SHALL 返回 SIGNATURE_VERIFICATION_FAILED 错误
7. WHEN 车端签名验证成功时，THE Authentication_Module SHALL 验证网关签名
8. WHEN 双向认证成功时，THE Authentication_Module SHALL 生成会话密钥
9. WHEN 双向认证成功时，THE Authentication_Module SHALL 生成认证令牌
10. WHEN 认证完成时，THE Audit_Module SHALL 记录认证事件（成功或失败）到审计日志

### 需求 5：会话管理

**用户故事**：作为系统，我希望管理车端与网关之间的安全会话，以便确保通信的持续安全性。

#### 验收标准

1. WHEN 认证成功时，THE Authentication_Module SHALL 创建唯一的会话标识符（32 字节）
2. WHEN 创建会话时，THE Authentication_Module SHALL 生成 SM4 会话密钥（16 或 32 字节）
3. WHEN 创建会话时，THE Authentication_Module SHALL 设置会话过期时间
4. WHEN 创建会话时，THE Authentication_Module SHALL 将会话信息存储到 Redis
5. WHEN 会话过期时，THE Authentication_Module SHALL 自动清理过期会话
6. THE Authentication_Module SHALL 每 5 分钟执行一次过期会话清理
7. IF 同一车辆尝试建立多个并发会话，THEN THE Authentication_Module SHALL 根据配置策略处理会话冲突

### 需求 6：数据加密

**用户故事**：作为系统，我希望使用 SM4 算法加密业务数据，以便保护数据传输的机密性。

#### 验收标准

1. WHEN 发送业务数据时，THE Crypto_Module SHALL 使用 SM4 算法加密明文数据
2. WHEN 加密数据时，THE Crypto_Module SHALL 使用会话密钥作为加密密钥
3. WHEN 加密数据时，THE Crypto_Module SHALL 确保密文长度为明文长度向上取整到 16 字节的倍数
4. WHEN 接收加密数据时，THE Crypto_Module SHALL 使用相同的会话密钥解密数据
5. IF 解密失败，THEN THE Crypto_Module SHALL 返回 DECRYPTION_FAILED 错误并丢弃数据

### 需求 7：数字签名

**用户故事**：作为系统，我希望使用 SM2 算法对数据进行签名和验签，以便确保数据完整性和不可否认性。

#### 验收标准

1. WHEN 发送数据时，THE Crypto_Module SHALL 使用发送方 SM2 私钥对数据进行签名
2. WHEN 生成签名时，THE Crypto_Module SHALL 确保签名长度为 64 字节
3. WHEN 接收数据时，THE Crypto_Module SHALL 使用发送方 SM2 公钥验证签名
4. IF 签名验证失败，THEN THE Crypto_Module SHALL 拒绝该数据并返回 SIGNATURE_VERIFICATION_FAILED 错误
5. WHEN 签名验证失败时，THE Audit_Module SHALL 记录安全警告到审计日志

### 需求 8：安全报文构造

**用户故事**：作为系统，我希望构造包含加密数据和签名的安全报文，以便实现端到端的安全通信。

#### 验收标准

1. WHEN 构造安全报文时，THE Crypto_Module SHALL 生成 16 字节的唯一 nonce
2. WHEN 构造安全报文时，THE Crypto_Module SHALL 添加当前时间戳
3. WHEN 构造安全报文时，THE Crypto_Module SHALL 创建包含发送方和接收方标识的消息头
4. WHEN 构造安全报文时，THE Crypto_Module SHALL 使用 SM4 加密业务数据
5. WHEN 构造安全报文时，THE Crypto_Module SHALL 对消息头、加密数据、时间戳和 nonce 进行 SM2 签名
6. THE Crypto_Module SHALL 确保安全报文包含 header、encryptedPayload、signature、timestamp 和 nonce 字段

### 需求 9：防重放攻击

**用户故事**：作为系统，我希望检测并拒绝重放的消息，以便防御重放攻击。

#### 验收标准

1. WHEN 验证安全报文时，THE Crypto_Module SHALL 检查时间戳与当前时间的差值
2. IF 时间戳差值超过 5 分钟，THEN THE Crypto_Module SHALL 拒绝该消息并返回"消息过期"错误
3. WHEN 验证安全报文时，THE Crypto_Module SHALL 检查 nonce 是否已被使用
4. IF nonce 已被使用，THEN THE Crypto_Module SHALL 拒绝该消息并返回"检测到重放攻击"错误
5. WHEN 消息验证成功时，THE Crypto_Module SHALL 将 nonce 标记为已使用
6. WHEN 检测到重放攻击时，THE Audit_Module SHALL 记录高优先级安全事件并触发告警

### 需求 10：密钥生成

**用户故事**：作为系统，我希望生成密码学安全的密钥，以便确保加密和签名的安全性。

#### 验收标准

1. WHEN 生成 SM4 密钥时，THE Crypto_Module SHALL 使用密码学安全随机数生成器（CSRNG）
2. WHEN 生成 SM4 密钥时，THE Crypto_Module SHALL 确保密钥长度为 16 字节或 32 字节
3. WHEN 生成 SM2 密钥对时，THE Crypto_Module SHALL 使用密码学安全随机数生成器
4. WHEN 生成 SM2 密钥对时，THE Crypto_Module SHALL 确保私钥长度为 32 字节
5. WHEN 生成 SM2 密钥对时，THE Crypto_Module SHALL 确保公钥为椭圆曲线上的有效点
6. THE Crypto_Module SHALL 确保每次生成的密钥都是唯一的

### 需求 11：审计日志记录

**用户故事**：作为系统管理员，我希望系统记录所有安全事件和业务操作，以便进行审计追溯。

#### 验收标准

1. WHEN 发生认证事件时，THE Audit_Module SHALL 记录车辆标识、事件类型、操作结果和时间戳
2. WHEN 发生数据传输时，THE Audit_Module SHALL 记录车辆标识、数据大小和加密状态
3. WHEN 发生证书操作时，THE Audit_Module SHALL 记录操作类型、证书序列号和时间戳
4. WHEN 发生安全异常时，THE Audit_Module SHALL 记录异常类型、相关实体和详细信息
5. THE Audit_Module SHALL 为每条日志生成唯一的日志标识符
6. THE Audit_Module SHALL 确保日志详细信息长度不超过 1024 字符
7. THE Audit_Module SHALL 将审计日志持久化存储到 PostgreSQL

### 需求 12：审计日志查询

**用户故事**：作为系统管理员，我希望能够查询和导出审计日志，以便进行安全分析和合规审计。

#### 验收标准

1. WHEN 管理员查询审计日志时，THE Audit_Module SHALL 支持按时间范围过滤
2. WHEN 管理员查询审计日志时，THE Audit_Module SHALL 支持按车辆标识过滤
3. WHEN 管理员查询审计日志时，THE Audit_Module SHALL 支持按事件类型过滤
4. WHEN 管理员查询审计日志时，THE Audit_Module SHALL 支持按操作结果过滤
5. WHEN 管理员导出审计报告时，THE Audit_Module SHALL 生成包含指定时间范围内所有日志的报告
6. THE Audit_Module SHALL 确保日志查询响应时间小于 1 秒

### 需求 13：实时车辆状态监控

**用户故事**：作为系统管理员，我希望通过 Web 管理平台实时查看车辆在线状态，以便监控系统运行情况。

#### 验收标准

1. WHEN 管理员访问 Web 管理平台时，THE Web_Platform SHALL 显示当前在线车辆列表
2. WHEN 显示车辆列表时，THE Web_Platform SHALL 包含车辆标识、连接时间和会话状态
3. WHEN 管理员查询特定车辆时，THE Web_Platform SHALL 显示该车辆的详细状态信息
4. WHEN 车辆状态变化时，THE Web_Platform SHALL 在 5 秒内更新显示
5. THE Web_Platform SHALL 支持按车辆标识搜索

### 需求 14：安全指标可视化

**用户故事**：作为系统管理员，我希望通过 Web 管理平台查看安全通信指标，以便评估系统安全性。

#### 验收标准

1. WHEN 管理员访问监控页面时，THE Web_Platform SHALL 显示认证成功率
2. WHEN 管理员访问监控页面时，THE Web_Platform SHALL 显示认证失败次数
3. WHEN 管理员访问监控页面时，THE Web_Platform SHALL 显示数据传输量统计
4. WHEN 管理员访问监控页面时，THE Web_Platform SHALL 显示签名验证失败次数
5. WHEN 管理员访问监控页面时，THE Web_Platform SHALL 显示检测到的安全异常次数
6. THE Web_Platform SHALL 支持按时间范围查看历史指标

### 需求 15：证书管理界面

**用户故事**：作为系统管理员，我希望通过 Web 管理平台管理证书，以便执行证书颁发和撤销操作。

#### 验收标准

1. WHEN 管理员访问证书管理页面时，THE Web_Platform SHALL 显示所有已颁发证书列表
2. WHEN 显示证书列表时，THE Web_Platform SHALL 包含证书序列号、主体信息、有效期和状态
3. WHEN 管理员颁发新证书时，THE Web_Platform SHALL 提供证书申请表单
4. WHEN 管理员提交证书申请时，THE Web_Platform SHALL 调用 Certificate_Management_Module 颁发证书
5. WHEN 管理员撤销证书时，THE Web_Platform SHALL 调用 Certificate_Management_Module 撤销证书
6. WHEN 管理员查看 CRL 时，THE Web_Platform SHALL 显示当前证书撤销列表

### 需求 16：安全策略配置

**用户故事**：作为系统管理员，我希望能够配置安全策略，以便根据实际需求调整系统安全参数。

#### 验收标准

1. WHEN 管理员配置安全策略时，THE Web_Platform SHALL 支持设置会话超时时间
2. WHEN 管理员配置安全策略时，THE Web_Platform SHALL 支持设置证书有效期
3. WHEN 管理员配置安全策略时，THE Web_Platform SHALL 支持设置时间戳容差范围
4. WHEN 管理员配置安全策略时，THE Web_Platform SHALL 支持设置并发会话处理策略
5. WHEN 管理员保存安全策略时，THE System SHALL 验证配置参数的有效性
6. WHEN 安全策略更新时，THE System SHALL 在下一个会话中应用新策略

### 需求 17：错误处理与恢复

**用户故事**：作为系统，我希望能够妥善处理各种错误情况，以便保持系统稳定性和安全性。

#### 验收标准

1. IF 证书验证失败，THEN THE System SHALL 终止认证流程并返回具体错误码
2. IF 签名验证失败，THEN THE System SHALL 拒绝数据并记录安全警告
3. IF 会话密钥过期，THEN THE System SHALL 拒绝操作并通知车端重新认证
4. IF 检测到重放攻击，THEN THE System SHALL 拒绝消息并触发安全告警
5. IF 解密失败，THEN THE System SHALL 丢弃数据并记录解密失败事件
6. IF CA 服务不可用，THEN THE System SHALL 使用缓存的证书和 CRL（如果在有效期内）
7. WHEN 错误发生时，THE Audit_Module SHALL 记录错误详情到审计日志

### 需求 18：性能要求

**用户故事**：作为系统，我希望满足性能指标要求，以便支持大规模车辆接入。

#### 验收标准

1. THE Authentication_Module SHALL 在 500 毫秒内完成单次双向认证
2. THE Authentication_Module SHALL 支持每秒至少 100 次并发认证请求
3. THE Crypto_Module SHALL 实现 SM4 加密吞吐量至少 100 MB/s
4. THE Crypto_Module SHALL 实现 SM4 解密吞吐量至少 100 MB/s
5. THE Crypto_Module SHALL 在 10 毫秒内完成 1KB 数据的加密操作
6. THE Crypto_Module SHALL 支持每秒至少 1000 次 SM2 签名操作
7. THE Crypto_Module SHALL 支持每秒至少 2000 次 SM2 验签操作
8. THE Authentication_Module SHALL 支持至少 10,000 个并发活跃会话
9. THE Authentication_Module SHALL 在 5 毫秒内完成会话查询
10. THE Authentication_Module SHALL 在 100 毫秒内完成会话建立

### 需求 19：密钥安全存储

**用户故事**：作为系统，我希望安全地存储密钥，以便防止密钥泄露。

#### 验收标准

1. THE Certificate_Management_Module SHALL 将 CA 私钥存储在硬件安全模块（HSM）或安全隔离区
2. WHERE 车端支持可信执行环境（TEE）或安全芯片，THE Vehicle SHALL 将私钥存储在 TEE 或安全芯片中
3. THE Authentication_Module SHALL 在内存中安全存储会话密钥
4. WHEN 会话结束时，THE Authentication_Module SHALL 安全清除会话密钥
5. THE System SHALL 定期轮换会话密钥（至少每 24 小时）
6. THE System SHALL 确保私钥永不以明文形式传输或记录到日志

### 需求 20：合规性要求

**用户故事**：作为系统，我希望符合国家密码法和相关标准，以便满足合规要求。

#### 验收标准

1. THE System SHALL 使用符合 GM/T 0003-2012 标准的 SM2 算法实现
2. THE System SHALL 使用符合 GM/T 0002-2012 标准的 SM4 算法实现
3. THE Certificate_Management_Module SHALL 颁发符合 GB/T 25056-2010 标准的证书
4. THE System SHALL 禁用所有非国密算法（在国密模式下）
5. THE System SHALL 确保证书私钥长度至少为 256 位
6. THE Audit_Module SHALL 记录所有密码学操作以支持合规审计
