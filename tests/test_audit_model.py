"""审计日志数据模型测试"""

import pytest
from datetime import datetime
from src.models.audit import AuditLog
from src.models.enums import EventType


class TestAuditLog:
    """审计日志模型测试"""
    
    def test_audit_log_creation(self):
        """测试审计日志创建"""
        log = AuditLog(
            log_id="LOG123456",
            timestamp=datetime(2024, 1, 1, 12, 0, 0),
            event_type=EventType.AUTHENTICATION_SUCCESS,
            vehicle_id="VIN123456789",
            operation_result=True,
            details="用户认证成功",
            ip_address="192.168.1.100"
        )
        
        assert log.log_id == "LOG123456"
        assert log.timestamp == datetime(2024, 1, 1, 12, 0, 0)
        assert log.event_type == EventType.AUTHENTICATION_SUCCESS
        assert log.vehicle_id == "VIN123456789"
        assert log.operation_result is True
        assert log.details == "用户认证成功"
        assert log.ip_address == "192.168.1.100"
    
    def test_audit_log_details_truncation(self):
        """测试审计日志详细信息截断（需求 11.6）"""
        long_details = "A" * 2000  # 超过 1024 字符
        log = AuditLog(
            log_id="LOG123456",
            timestamp=datetime.now(),
            event_type=EventType.AUTHENTICATION_FAILURE,
            vehicle_id="VIN123456789",
            operation_result=False,
            details=long_details,
            ip_address="192.168.1.100"
        )
        
        # 验证详细信息被截断到 1024 字符
        assert len(log.details) == 1024
        assert log.details == "A" * 1024
    
    def test_audit_log_serialization(self):
        """测试审计日志序列化"""
        log = AuditLog(
            log_id="LOG123456",
            timestamp=datetime(2024, 1, 1, 12, 0, 0),
            event_type=EventType.DATA_ENCRYPTED,
            vehicle_id="VIN123456789",
            operation_result=True,
            details="数据加密成功",
            ip_address="192.168.1.100"
        )
        
        data = log.to_dict()
        
        assert data["log_id"] == "LOG123456"
        assert data["timestamp"] == "2024-01-01T12:00:00"
        assert data["event_type"] == "DATA_ENCRYPTED"
        assert data["vehicle_id"] == "VIN123456789"
        assert data["operation_result"] is True
        assert data["details"] == "数据加密成功"
        assert data["ip_address"] == "192.168.1.100"
    
    def test_audit_log_deserialization(self):
        """测试审计日志反序列化"""
        data = {
            "log_id": "LOG123456",
            "timestamp": "2024-01-01T12:00:00",
            "event_type": "CERTIFICATE_ISSUED",
            "vehicle_id": "VIN123456789",
            "operation_result": True,
            "details": "证书颁发成功",
            "ip_address": "192.168.1.100"
        }
        
        log = AuditLog.from_dict(data)
        
        assert log.log_id == "LOG123456"
        assert log.timestamp == datetime(2024, 1, 1, 12, 0, 0)
        assert log.event_type == EventType.CERTIFICATE_ISSUED
        assert log.vehicle_id == "VIN123456789"
        assert log.operation_result is True
        assert log.details == "证书颁发成功"
        assert log.ip_address == "192.168.1.100"
    
    def test_audit_log_roundtrip(self):
        """测试审计日志序列化和反序列化往返"""
        original_log = AuditLog(
            log_id="LOG123456",
            timestamp=datetime(2024, 1, 1, 12, 0, 0),
            event_type=EventType.SIGNATURE_VERIFIED,
            vehicle_id="VIN123456789",
            operation_result=True,
            details="签名验证成功",
            ip_address="192.168.1.100"
        )
        
        # 序列化
        data = original_log.to_dict()
        
        # 反序列化
        restored_log = AuditLog.from_dict(data)
        
        # 验证往返后数据一致
        assert restored_log.log_id == original_log.log_id
        assert restored_log.timestamp == original_log.timestamp
        assert restored_log.event_type == original_log.event_type
        assert restored_log.vehicle_id == original_log.vehicle_id
        assert restored_log.operation_result == original_log.operation_result
        assert restored_log.details == original_log.details
        assert restored_log.ip_address == original_log.ip_address
    
    def test_audit_log_all_event_types(self):
        """测试所有事件类型的审计日志"""
        event_types = [
            EventType.VEHICLE_CONNECT,
            EventType.VEHICLE_DISCONNECT,
            EventType.AUTHENTICATION_SUCCESS,
            EventType.AUTHENTICATION_FAILURE,
            EventType.DATA_ENCRYPTED,
            EventType.DATA_DECRYPTED,
            EventType.CERTIFICATE_ISSUED,
            EventType.CERTIFICATE_REVOKED,
            EventType.SIGNATURE_VERIFIED,
            EventType.SIGNATURE_FAILED
        ]
        
        for event_type in event_types:
            log = AuditLog(
                log_id=f"LOG_{event_type.value}",
                timestamp=datetime.now(),
                event_type=event_type,
                vehicle_id="VIN123456789",
                operation_result=True,
                details=f"测试事件: {event_type.value}",
                ip_address="192.168.1.100"
            )
            
            assert log.event_type == event_type
            
            # 验证序列化和反序列化
            data = log.to_dict()
            restored_log = AuditLog.from_dict(data)
            assert restored_log.event_type == event_type
    
    def test_audit_log_with_datetime_object(self):
        """测试使用 datetime 对象反序列化"""
        data = {
            "log_id": "LOG123456",
            "timestamp": datetime(2024, 1, 1, 12, 0, 0),  # datetime 对象而非字符串
            "event_type": EventType.VEHICLE_CONNECT,  # EventType 对象而非字符串
            "vehicle_id": "VIN123456789",
            "operation_result": True,
            "details": "车辆连接",
            "ip_address": "192.168.1.100"
        }
        
        log = AuditLog.from_dict(data)
        
        assert log.timestamp == datetime(2024, 1, 1, 12, 0, 0)
        assert log.event_type == EventType.VEHICLE_CONNECT
    
    def test_audit_log_empty_details(self):
        """测试空详细信息"""
        log = AuditLog(
            log_id="LOG123456",
            timestamp=datetime.now(),
            event_type=EventType.VEHICLE_DISCONNECT,
            vehicle_id="VIN123456789",
            operation_result=True,
            details="",
            ip_address="192.168.1.100"
        )
        
        assert log.details == ""
        assert len(log.details) == 0
    
    def test_audit_log_exactly_1024_chars(self):
        """测试恰好 1024 字符的详细信息"""
        details_1024 = "B" * 1024
        log = AuditLog(
            log_id="LOG123456",
            timestamp=datetime.now(),
            event_type=EventType.DATA_DECRYPTED,
            vehicle_id="VIN123456789",
            operation_result=True,
            details=details_1024,
            ip_address="192.168.1.100"
        )
        
        assert len(log.details) == 1024
        assert log.details == details_1024
