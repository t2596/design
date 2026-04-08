"""证书颁发集成测试

演示完整的证书颁发工作流程。
"""

import pytest
from unittest.mock import Mock
from src.certificate_manager import issue_certificate
from src.models.certificate import SubjectInfo
from src.crypto.sm2 import generate_sm2_keypair, sm2_verify
from src.certificate_manager import encode_tbs_certificate


def test_complete_certificate_issuance_workflow():
    """测试完整的证书颁发工作流程
    
    此测试演示了从生成密钥对到颁发证书的完整流程：
    1. 生成 CA 密钥对
    2. 生成车辆密钥对
    3. 创建证书主体信息
    4. 颁发证书
    5. 验证证书签名
    """
    # 步骤 1：生成 CA 密钥对
    ca_private_key, ca_public_key = generate_sm2_keypair()
    print(f"\n✓ CA 密钥对生成成功")
    print(f"  - CA 私钥长度: {len(ca_private_key)} 字节")
    print(f"  - CA 公钥长度: {len(ca_public_key)} 字节")
    
    # 步骤 2：生成车辆密钥对
    vehicle_private_key, vehicle_public_key = generate_sm2_keypair()
    print(f"\n✓ 车辆密钥对生成成功")
    print(f"  - 车辆私钥长度: {len(vehicle_private_key)} 字节")
    print(f"  - 车辆公钥长度: {len(vehicle_public_key)} 字节")
    
    # 步骤 3：创建证书主体信息
    subject_info = SubjectInfo(
        vehicle_id="VIN-TEST-123456789",
        organization="Test Vehicle Manufacturer Co., Ltd.",
        country="CN"
    )
    print(f"\n✓ 证书主体信息创建成功")
    print(f"  - 车辆标识: {subject_info.vehicle_id}")
    print(f"  - 组织名称: {subject_info.organization}")
    print(f"  - 国家代码: {subject_info.country}")
    
    # 步骤 4：颁发证书（使用模拟数据库连接）
    mock_db_conn = Mock()
    mock_db_conn.execute_update = Mock()
    
    certificate = issue_certificate(
        subject_info=subject_info,
        public_key=vehicle_public_key,
        ca_private_key=ca_private_key,
        ca_public_key=ca_public_key,
        db_conn=mock_db_conn
    )
    
    print(f"\n✓ 证书颁发成功")
    print(f"  - 证书版本: {certificate.version}")
    print(f"  - 证书序列号: {certificate.serial_number}")
    print(f"  - 颁发者: {certificate.issuer}")
    print(f"  - 主体: {certificate.subject}")
    print(f"  - 有效期开始: {certificate.valid_from}")
    print(f"  - 有效期结束: {certificate.valid_to}")
    print(f"  - 签名算法: {certificate.signature_algorithm}")
    print(f"  - 签名长度: {len(certificate.signature)} 字节")
    
    # 步骤 5：验证证书签名
    tbs_certificate = encode_tbs_certificate(certificate)
    signature_valid = sm2_verify(tbs_certificate, certificate.signature, ca_public_key)
    
    print(f"\n✓ 证书签名验证: {'通过' if signature_valid else '失败'}")
    
    # 断言验证
    assert signature_valid, "证书签名验证失败"
    assert certificate.version == 3
    assert len(certificate.serial_number) == 64
    assert certificate.signature_algorithm == "SM2"
    assert len(certificate.signature) == 64
    assert certificate.valid_from < certificate.valid_to
    assert subject_info.vehicle_id in certificate.subject
    
    # 验证数据库操作被调用
    assert mock_db_conn.execute_update.call_count == 2  # 存储证书 + 审计日志
    
    print(f"\n✅ 完整的证书颁发工作流程测试通过！")


def test_multiple_certificates_have_unique_serial_numbers():
    """测试多个证书具有唯一的序列号
    
    验证需求 1.1：证书序列号必须唯一
    """
    # 生成 CA 密钥对
    ca_private_key, ca_public_key = generate_sm2_keypair()
    
    # 模拟数据库连接
    mock_db_conn = Mock()
    mock_db_conn.execute_update = Mock()
    
    # 颁发多个证书
    certificates = []
    for i in range(10):
        vehicle_private_key, vehicle_public_key = generate_sm2_keypair()
        subject_info = SubjectInfo(
            vehicle_id=f"VIN-{i:06d}",
            organization="Test Org",
            country="CN"
        )
        
        cert = issue_certificate(
            subject_info=subject_info,
            public_key=vehicle_public_key,
            ca_private_key=ca_private_key,
            ca_public_key=ca_public_key,
            db_conn=mock_db_conn
        )
        certificates.append(cert)
    
    # 验证所有序列号都是唯一的
    serial_numbers = [cert.serial_number for cert in certificates]
    assert len(serial_numbers) == len(set(serial_numbers)), "证书序列号不唯一"
    
    print(f"\n✅ 颁发了 {len(certificates)} 个证书，所有序列号都是唯一的")


def test_certificate_validity_period_is_one_year():
    """测试证书有效期为 1 年
    
    验证需求 1.3：证书有效期为 1 年
    """
    # 生成密钥对
    ca_private_key, ca_public_key = generate_sm2_keypair()
    vehicle_private_key, vehicle_public_key = generate_sm2_keypair()
    
    # 创建主体信息
    subject_info = SubjectInfo(
        vehicle_id="VIN-TEST",
        organization="Test Org",
        country="CN"
    )
    
    # 模拟数据库连接
    mock_db_conn = Mock()
    mock_db_conn.execute_update = Mock()
    
    # 颁发证书
    certificate = issue_certificate(
        subject_info=subject_info,
        public_key=vehicle_public_key,
        ca_private_key=ca_private_key,
        ca_public_key=ca_public_key,
        db_conn=mock_db_conn
    )
    
    # 计算有效期天数
    validity_period = certificate.valid_to - certificate.valid_from
    days = validity_period.days
    
    # 验证有效期为 1 年（允许 1 天误差）
    assert 364 <= days <= 366, f"证书有效期应为 365 天，实际为 {days} 天"
    
    print(f"\n✅ 证书有效期为 {days} 天（1 年）")


if __name__ == "__main__":
    # 运行测试
    test_complete_certificate_issuance_workflow()
    test_multiple_certificates_have_unique_serial_numbers()
    test_certificate_validity_period_is_one_year()
