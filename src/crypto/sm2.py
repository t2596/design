"""SM2 数字签名模块

提供 SM2 签名、验签和密钥对生成功能,符合 GM/T 0003-2012 标准。
"""

import os
from typing import Tuple
from gmssl import sm2, func


def _derive_public_key_from_private(private_key_hex: str) -> str:
    """从私钥推导公钥
    
    使用椭圆曲线点乘运算从私钥推导公钥。
    公钥 = 私钥 * G（生成元）
    
    参数:
        private_key_hex: 十六进制格式的私钥字符串
        
    返回:
        str: 十六进制格式的公钥字符串（64 字节，不含 0x04 前缀）
    """
    # SM2 曲线参数（国密标准曲线）
    # 这些参数来自 GM/T 0003-2012 标准
    p = int('FFFFFFFEFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFF00000000FFFFFFFFFFFFFFFF', 16)
    a = int('FFFFFFFEFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFF00000000FFFFFFFFFFFFFFFC', 16)
    b = int('28E9FA9E9D9F5E344D5A9E4BCF6509A7F39789F515AB8F92DDBCBD414D940E93', 16)
    n = int('FFFFFFFEFFFFFFFFFFFFFFFFFFFFFFFF7203DF6B21C6052B53BBF40939D54123', 16)
    gx = int('32C4AE2C1F1981195F9904466A39C9948FE30BBFF2660BE1715A4589334C74C7', 16)
    gy = int('BC3736A2F4F6779C59BDCEE36B692153D0A9877CC62A474002DF32E52139F0A0', 16)
    
    # 将私钥转换为整数
    d = int(private_key_hex, 16)
    
    # 椭圆曲线点加法和点乘运算
    def point_add(p1, p2):
        """椭圆曲线点加法"""
        if p1 is None:
            return p2
        if p2 is None:
            return p1
        
        x1, y1 = p1
        x2, y2 = p2
        
        if x1 == x2:
            if y1 == y2:
                # 点倍乘
                s = ((3 * x1 * x1 + a) * pow(2 * y1, p - 2, p)) % p
            else:
                return None
        else:
            s = ((y2 - y1) * pow(x2 - x1, p - 2, p)) % p
        
        x3 = (s * s - x1 - x2) % p
        y3 = (s * (x1 - x3) - y1) % p
        
        return (x3, y3)
    
    def point_multiply(k, point):
        """椭圆曲线点乘运算（使用二进制展开法）"""
        if k == 0:
            return None
        if k == 1:
            return point
        
        result = None
        addend = point
        
        while k:
            if k & 1:
                result = point_add(result, addend)
            addend = point_add(addend, addend)
            k >>= 1
        
        return result
    
    # 计算公钥：Q = d * G
    G = (gx, gy)
    Q = point_multiply(d, G)
    
    if Q is None:
        raise RuntimeError("公钥推导失败")
    
    qx, qy = Q
    
    # 将公钥坐标转换为十六进制字符串（各 32 字节）
    public_key_hex = format(qx, '064x') + format(qy, '064x')
    
    return public_key_hex


def generate_sm2_keypair() -> Tuple[bytes, bytes]:
    """生成 SM2 密钥对
    
    使用密码学安全随机数生成器（CSRNG）生成 SM2 密钥对。
    
    前置条件:
    - 系统必须有可用的密码学安全随机数生成器
    - SM2 椭圆曲线参数已正确配置
    
    后置条件:
    - 返回的 keyPair 包含有效的 privateKey 和 publicKey
    - privateKey 长度为 32 字节（256 位）
    - publicKey 为椭圆曲线上的点（非压缩格式 64 字节）
    - publicKey 可从 privateKey 推导得出
    - privateKey 具有足够的熵（256 位安全强度）
    - 每次调用生成的密钥对都是唯一的（概率上）
    
    返回:
        Tuple[bytes, bytes]: (私钥, 公钥)
        - 私钥: 32 字节
        - 公钥: 64 字节（非压缩格式，不含 0x04 前缀）
        
    验证需求: 10.3, 10.4, 10.5, 10.6
    """
    # 使用 os.urandom 生成密码学安全的随机私钥
    # SM2 私钥是 256 位（32 字节）的随机数
    private_key = os.urandom(32)
    
    # 将私钥转换为十六进制字符串
    private_key_hex = private_key.hex()
    
    # 从私钥推导公钥
    public_key_hex = _derive_public_key_from_private(private_key_hex)
    public_key = bytes.fromhex(public_key_hex)
    
    # 后置条件验证
    assert len(private_key) == 32, f"私钥长度不正确: {len(private_key)} != 32"
    assert len(public_key) == 64, f"公钥长度不正确: {len(public_key)} != 64"
    
    return private_key, public_key


def sm2_sign(data: bytes, private_key: bytes) -> bytes:
    """使用 SM2 算法对数据进行签名
    
    使用 SM2 椭圆曲线数字签名算法对数据进行签名。
    
    前置条件:
    - data 非空且长度大于 0
    - private_key 必须是有效的 SM2 私钥（32 字节）
    - private_key 必须与对应的公钥配对
    
    后置条件:
    - 返回的 signature 长度为 64 字节（r 和 s 各 32 字节）
    - signature 可通过对应的公钥验证
    - 相同的 data 和 private_key 每次生成的签名可能不同（因为包含随机数 k）
    - data 和 private_key 参数未被修改
    - 签名满足 SM2 算法的数学性质
    
    参数:
        data: 待签名数据
        private_key: SM2 私钥（32 字节）
        
    返回:
        bytes: 数字签名（64 字节）
        
    异常:
        ValueError: 如果 data 为空或 private_key 长度不正确
        RuntimeError: 如果签名失败
        
    验证需求: 7.1, 7.2
    """
    # 前置条件验证
    if not data:
        raise ValueError("待签名数据不能为空")
    
    if len(private_key) != 32:
        raise ValueError(f"SM2 私钥长度必须为 32 字节，当前为 {len(private_key)}")
    
    try:
        # 将私钥转换为十六进制字符串
        private_key_hex = private_key.hex()
        
        # 从私钥推导公钥（签名需要公钥）
        public_key_hex = _derive_public_key_from_private(private_key_hex)
        
        # 创建 SM2 签名实例
        sm2_crypt = sm2.CryptSM2(private_key=private_key_hex, public_key=public_key_hex)
        
        # 生成随机数 K（用于签名）
        # K 必须是一个随机的 256 位数（32 字节）
        k_bytes = os.urandom(32)
        k_hex = k_bytes.hex()
        
        # 对数据进行签名
        # gmssl 的 sign 方法返回十六进制字符串格式的签名
        signature_hex = sm2_crypt.sign(data, k_hex)
        
        # 将签名转换为字节
        signature = bytes.fromhex(signature_hex)
        
        # 后置条件验证
        assert signature is not None and len(signature) > 0, "签名失败：签名为空"
        assert len(signature) == 64, f"签名长度不正确: {len(signature)} != 64"
        
        return signature
        
    except Exception as e:
        if isinstance(e, (ValueError, AssertionError)):
            raise
        raise RuntimeError(f"SM2 签名失败: {str(e)}")


def sm2_verify(data: bytes, signature: bytes, public_key: bytes) -> bool:
    """使用 SM2 算法验证签名
    
    使用 SM2 椭圆曲线数字签名算法验证签名的有效性。
    
    前置条件:
    - data 非空且长度大于 0
    - signature 长度为 64 字节
    - public_key 必须是有效的 SM2 公钥（64 字节，非压缩格式）
    - signature 必须是通过 SM2 算法生成的
    
    后置条件:
    - 如果 signature 是使用对应私钥对 data 签名的结果，返回 True
    - 如果 signature 无效或 data 被篡改，返回 False
    - 所有输入参数未被修改
    - 验证操作无副作用
    
    参数:
        data: 原始数据
        signature: 数字签名（64 字节）
        public_key: SM2 公钥（64 字节，非压缩格式）
        
    返回:
        bool: 验证结果，True 表示签名有效，False 表示签名无效
        
    异常:
        ValueError: 如果 data 为空、signature 或 public_key 长度不正确
        
    验证需求: 7.3, 7.4
    """
    # 前置条件验证
    if not data:
        raise ValueError("待验证数据不能为空")
    
    if len(signature) != 64:
        raise ValueError(f"SM2 签名长度必须为 64 字节，当前为 {len(signature)}")
    
    if len(public_key) != 64:
        raise ValueError(f"SM2 公钥长度必须为 64 字节，当前为 {len(public_key)}")
    
    try:
        # 将公钥和签名转换为十六进制字符串
        public_key_hex = public_key.hex()
        signature_hex = signature.hex()
        
        # 创建 SM2 验签实例
        sm2_crypt = sm2.CryptSM2(private_key='', public_key=public_key_hex)
        
        # 验证签名
        # gmssl 的 verify 方法返回 True 表示验证成功，False 表示失败
        result = sm2_crypt.verify(signature_hex, data)
        
        return result
        
    except Exception as e:
        if isinstance(e, ValueError):
            raise
        # 验证失败返回 False，而不是抛出异常
        return False
