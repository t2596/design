"""审计日志记录功能测试"""

import pytest
import json
import csv
import io
from unittest.mock import MagicMock, patch
from datetime import datetime
from src.audit_logger import AuditLogger, create_audit_logger
from src.models.audit import AuditLog
from src.models.enums import EventType
from config import PostgreSQLConfig


class TestAuditLogger:
    """审计日志记录器测试"""
    
    @pytest.fixture
    def mock_db_connection(self):
        """创建 Mock 数据库连接"""
        mock_db = MagicMock()
        mock_db.execute_update.return_value = 1  # 模拟成功插入
        return mock_db
    
    @pytest.fixture
    def audit_logger(self, mock_db_connection):
        """创建审计日志记录器实例"""
        return AuditLogger(mock_db_connection)
    
    def test_generate_log_id_uniqueness(self, audit_logger):
        """测试生成唯一日志标识符（需求 11.5）"""
        log_ids = set()
        
        # 生成 1000 个日志 ID
        for _ in range(1000):
            log_id = audit_logger._generate_log_id()
            log_ids.add(log_id)
        
        # 验证所有 ID 都是唯一的
        assert len(log_ids) == 1000
    
    def test_generate_log_id_format(self, audit_logger):
        """测试日志 ID 格式为 UUID"""
        log_id = audit_logger._generate_log_id()
        
        # UUID 格式验证：8-4-4-4-12 个十六进制字符
        parts = log_id.split('-')
        assert len(parts) == 5
        assert len(parts[0]) == 8
        assert len(parts[1]) == 4
        assert len(parts[2]) == 4
        assert len(parts[3]) == 4
        assert len(parts[4]) == 12
    
    def test_truncate_details_short_text(self, audit_logger):
        """测试短文本不被截断"""
        short_text = "这是一段短文本"
        result = audit_logger._truncate_details(short_text)
        
        assert result == short_text
        assert len(result) == len(short_text)
    
    def test_truncate_details_exactly_1024_chars(self, audit_logger):
        """测试恰好 1024 字符的文本不被截断"""
        text_1024 = "A" * 1024
        result = audit_logger._truncate_details(text_1024)
        
        assert result == text_1024
        assert len(result) == 1024
    
    def test_truncate_details_long_text(self, audit_logger):
        """测试长文本被截断到 1024 字符（需求 11.6）"""
        long_text = "B" * 2000
        result = audit_logger._truncate_details(long_text)
        
        assert len(result) == 1024
        assert result == "B" * 1024
    
    def test_log_auth_event_success(self, audit_logger, mock_db_connection):
        """测试记录认证成功事件（需求 11.1）"""
        vehicle_id = "VIN123456789"
        event_type = EventType.AUTHENTICATION_SUCCESS
        result = True
        ip_address = "192.168.1.100"
        
        log_id = audit_logger.log_auth_event(
            vehicle_id=vehicle_id,
            event_type=event_type,
            result=result,
            ip_address=ip_address
        )
        
        # 验证返回的日志 ID 不为空
        assert log_id is not None
        assert len(log_id) > 0
        
        # 验证数据库插入被调用
        mock_db_connection.execute_update.assert_called_once()
        
        # 验证插入的参数
        call_args = mock_db_connection.execute_update.call_args
        query, params = call_args[0]
        
        assert "INSERT INTO audit_logs" in query
        assert params[0] == log_id  # log_id
        assert params[2] == event_type.value  # event_type
        assert params[3] == vehicle_id  # vehicle_id
        assert params[4] == result  # operation_result
        assert params[6] == ip_address  # ip_address
    
    def test_log_auth_event_failure(self, audit_logger, mock_db_connection):
        """测试记录认证失败事件（需求 11.1）"""
        vehicle_id = "VIN987654321"
        event_type = EventType.AUTHENTICATION_FAILURE
        result = False
        
        log_id = audit_logger.log_auth_event(
            vehicle_id=vehicle_id,
            event_type=event_type,
            result=result
        )
        
        assert log_id is not None
        
        # 验证数据库插入被调用
        call_args = mock_db_connection.execute_update.call_args
        query, params = call_args[0]
        
        assert params[2] == event_type.value
        assert params[3] == vehicle_id
        assert params[4] == result  # False
    
    def test_log_auth_event_with_custom_details(self, audit_logger, mock_db_connection):
        """测试记录认证事件时使用自定义详细信息"""
        vehicle_id = "VIN123456789"
        event_type = EventType.AUTHENTICATION_SUCCESS
        result = True
        custom_details = "自定义认证详细信息"
        
        log_id = audit_logger.log_auth_event(
            vehicle_id=vehicle_id,
            event_type=event_type,
            result=result,
            details=custom_details
        )
        
        assert log_id is not None
        
        call_args = mock_db_connection.execute_update.call_args
        query, params = call_args[0]
        
        assert params[5] == custom_details  # details
    
    def test_log_auth_event_default_ip_address(self, audit_logger, mock_db_connection):
        """测试认证事件默认 IP 地址"""
        vehicle_id = "VIN123456789"
        event_type = EventType.AUTHENTICATION_SUCCESS
        result = True
        
        log_id = audit_logger.log_auth_event(
            vehicle_id=vehicle_id,
            event_type=event_type,
            result=result
        )
        
        call_args = mock_db_connection.execute_update.call_args
        query, params = call_args[0]
        
        assert params[6] == "unknown"  # 默认 IP 地址
    
    def test_log_data_transfer_encrypted(self, audit_logger, mock_db_connection):
        """测试记录加密数据传输事件（需求 11.2）"""
        vehicle_id = "VIN123456789"
        data_size = 1024
        encrypted = True
        ip_address = "192.168.1.100"
        
        log_id = audit_logger.log_data_transfer(
            vehicle_id=vehicle_id,
            data_size=data_size,
            encrypted=encrypted,
            ip_address=ip_address
        )
        
        assert log_id is not None
        
        # 验证数据库插入被调用
        call_args = mock_db_connection.execute_update.call_args
        query, params = call_args[0]
        
        assert params[2] == EventType.DATA_ENCRYPTED.value  # 加密事件
        assert params[3] == vehicle_id
        assert params[4] == True  # operation_result
        assert "1024 字节" in params[5]  # details 包含数据大小
        assert "加密" in params[5]  # details 包含加密状态
    
    def test_log_data_transfer_unencrypted(self, audit_logger, mock_db_connection):
        """测试记录未加密数据传输事件（需求 11.2）"""
        vehicle_id = "VIN987654321"
        data_size = 2048
        encrypted = False
        
        log_id = audit_logger.log_data_transfer(
            vehicle_id=vehicle_id,
            data_size=data_size,
            encrypted=encrypted
        )
        
        assert log_id is not None
        
        call_args = mock_db_connection.execute_update.call_args
        query, params = call_args[0]
        
        assert params[2] == EventType.DATA_DECRYPTED.value  # 未加密事件
        assert "2048 字节" in params[5]
        assert "未加密" in params[5]
    
    def test_log_data_transfer_with_custom_details(self, audit_logger, mock_db_connection):
        """测试记录数据传输事件时使用自定义详细信息"""
        vehicle_id = "VIN123456789"
        data_size = 512
        encrypted = True
        custom_details = "自定义数据传输详细信息"
        
        log_id = audit_logger.log_data_transfer(
            vehicle_id=vehicle_id,
            data_size=data_size,
            encrypted=encrypted,
            details=custom_details
        )
        
        call_args = mock_db_connection.execute_update.call_args
        query, params = call_args[0]
        
        assert params[5] == custom_details
    
    def test_log_certificate_operation_issued(self, audit_logger, mock_db_connection):
        """测试记录证书颁发操作（需求 11.3）"""
        operation = "issued"
        cert_id = "CERT123456"
        vehicle_id = "VIN123456789"
        ip_address = "192.168.1.100"
        
        log_id = audit_logger.log_certificate_operation(
            operation=operation,
            cert_id=cert_id,
            vehicle_id=vehicle_id,
            ip_address=ip_address
        )
        
        assert log_id is not None
        
        call_args = mock_db_connection.execute_update.call_args
        query, params = call_args[0]
        
        assert params[2] == EventType.CERTIFICATE_ISSUED.value
        assert params[3] == vehicle_id
        assert cert_id in params[5]  # details 包含证书 ID
        assert "颁发" in params[5]
    
    def test_log_certificate_operation_revoked(self, audit_logger, mock_db_connection):
        """测试记录证书撤销操作（需求 11.3）"""
        operation = "revoked"
        cert_id = "CERT987654"
        vehicle_id = "VIN987654321"
        
        log_id = audit_logger.log_certificate_operation(
            operation=operation,
            cert_id=cert_id,
            vehicle_id=vehicle_id
        )
        
        assert log_id is not None
        
        call_args = mock_db_connection.execute_update.call_args
        query, params = call_args[0]
        
        assert params[2] == EventType.CERTIFICATE_REVOKED.value
        assert cert_id in params[5]
        assert "撤销" in params[5]
    
    def test_log_certificate_operation_without_vehicle_id(self, audit_logger, mock_db_connection):
        """测试记录证书操作时不提供车辆 ID"""
        operation = "issued"
        cert_id = "CERT123456"
        
        log_id = audit_logger.log_certificate_operation(
            operation=operation,
            cert_id=cert_id
        )
        
        call_args = mock_db_connection.execute_update.call_args
        query, params = call_args[0]
        
        assert params[3] == "system"  # 默认使用 "system"
    
    def test_log_certificate_operation_with_custom_details(self, audit_logger, mock_db_connection):
        """测试记录证书操作时使用自定义详细信息"""
        operation = "issued"
        cert_id = "CERT123456"
        custom_details = "自定义证书操作详细信息"
        
        log_id = audit_logger.log_certificate_operation(
            operation=operation,
            cert_id=cert_id,
            details=custom_details
        )
        
        call_args = mock_db_connection.execute_update.call_args
        query, params = call_args[0]
        
        assert params[5] == custom_details
    
    def test_log_certificate_operation_case_insensitive(self, audit_logger, mock_db_connection):
        """测试证书操作类型不区分大小写"""
        # 测试大写
        log_id1 = audit_logger.log_certificate_operation(
            operation="ISSUED",
            cert_id="CERT1"
        )
        call_args1 = mock_db_connection.execute_update.call_args
        params1 = call_args1[0][1]
        assert params1[2] == EventType.CERTIFICATE_ISSUED.value
        
        # 测试混合大小写
        log_id2 = audit_logger.log_certificate_operation(
            operation="Revoked",
            cert_id="CERT2"
        )
        call_args2 = mock_db_connection.execute_update.call_args
        params2 = call_args2[0][1]
        assert params2[2] == EventType.CERTIFICATE_REVOKED.value
    
    def test_persist_log_success(self, audit_logger, mock_db_connection):
        """测试成功持久化日志（需求 11.7）"""
        from src.models.audit import AuditLog
        
        log = AuditLog(
            log_id="LOG123456",
            timestamp=datetime.now(),
            event_type=EventType.AUTHENTICATION_SUCCESS,
            vehicle_id="VIN123456789",
            operation_result=True,
            details="测试日志",
            ip_address="192.168.1.100"
        )
        
        mock_db_connection.execute_update.return_value = 1
        result = audit_logger._persist_log(log)
        
        assert result is True
        mock_db_connection.execute_update.assert_called_once()
    
    def test_persist_log_failure(self, audit_logger, mock_db_connection):
        """测试持久化日志失败时的处理"""
        from src.models.audit import AuditLog
        
        log = AuditLog(
            log_id="LOG123456",
            timestamp=datetime.now(),
            event_type=EventType.AUTHENTICATION_SUCCESS,
            vehicle_id="VIN123456789",
            operation_result=True,
            details="测试日志",
            ip_address="192.168.1.100"
        )
        
        # 模拟数据库异常
        mock_db_connection.execute_update.side_effect = Exception("Database error")
        
        # 不应该抛出异常
        result = audit_logger._persist_log(log)
        
        assert result is False
    
    def test_persist_log_zero_rows_affected(self, audit_logger, mock_db_connection):
        """测试持久化日志时没有行被影响"""
        from src.models.audit import AuditLog
        
        log = AuditLog(
            log_id="LOG123456",
            timestamp=datetime.now(),
            event_type=EventType.AUTHENTICATION_SUCCESS,
            vehicle_id="VIN123456789",
            operation_result=True,
            details="测试日志",
            ip_address="192.168.1.100"
        )
        
        mock_db_connection.execute_update.return_value = 0
        result = audit_logger._persist_log(log)
        
        assert result is False
    
    def test_log_auth_event_truncates_long_details(self, audit_logger, mock_db_connection):
        """测试认证事件自动截断长详细信息"""
        vehicle_id = "VIN123456789"
        event_type = EventType.AUTHENTICATION_SUCCESS
        result = True
        long_details = "X" * 2000
        
        log_id = audit_logger.log_auth_event(
            vehicle_id=vehicle_id,
            event_type=event_type,
            result=result,
            details=long_details
        )
        
        call_args = mock_db_connection.execute_update.call_args
        query, params = call_args[0]
        
        # 验证详细信息被截断到 1024 字符
        assert len(params[5]) == 1024
    
    def test_log_data_transfer_truncates_long_details(self, audit_logger, mock_db_connection):
        """测试数据传输事件自动截断长详细信息"""
        vehicle_id = "VIN123456789"
        data_size = 1024
        encrypted = True
        long_details = "Y" * 2000
        
        log_id = audit_logger.log_data_transfer(
            vehicle_id=vehicle_id,
            data_size=data_size,
            encrypted=encrypted,
            details=long_details
        )
        
        call_args = mock_db_connection.execute_update.call_args
        query, params = call_args[0]
        
        assert len(params[5]) == 1024
    
    def test_log_certificate_operation_truncates_long_details(self, audit_logger, mock_db_connection):
        """测试证书操作事件自动截断长详细信息"""
        operation = "issued"
        cert_id = "CERT123456"
        long_details = "Z" * 2000
        
        log_id = audit_logger.log_certificate_operation(
            operation=operation,
            cert_id=cert_id,
            details=long_details
        )
        
        call_args = mock_db_connection.execute_update.call_args
        query, params = call_args[0]
        
        assert len(params[5]) == 1024
    
    def test_create_audit_logger(self):
        """测试创建审计日志记录器便捷函数"""
        config = PostgreSQLConfig(
            host="localhost",
            port=5432,
            database="test_db",
            user="test_user",
            password="test_pass"
        )
        
        logger = create_audit_logger(config)
        
        assert logger is not None
        assert isinstance(logger, AuditLogger)
        assert logger.db is not None
    
    def test_multiple_log_entries_unique_ids(self, audit_logger, mock_db_connection):
        """测试多个日志条目具有唯一 ID"""
        log_ids = []
        
        # 记录多个不同类型的日志
        log_ids.append(audit_logger.log_auth_event(
            vehicle_id="VIN1",
            event_type=EventType.AUTHENTICATION_SUCCESS,
            result=True
        ))
        
        log_ids.append(audit_logger.log_data_transfer(
            vehicle_id="VIN2",
            data_size=1024,
            encrypted=True
        ))
        
        log_ids.append(audit_logger.log_certificate_operation(
            operation="issued",
            cert_id="CERT1"
        ))
        
        # 验证所有 ID 都是唯一的
        assert len(log_ids) == len(set(log_ids))
        assert len(log_ids) == 3


class TestAuditLogQuery:
    """审计日志查询功能测试"""
    
    @pytest.fixture
    def mock_db_connection(self):
        """创建 Mock 数据库连接"""
        mock_db = MagicMock()
        return mock_db
    
    @pytest.fixture
    def audit_logger(self, mock_db_connection):
        """创建审计日志记录器实例"""
        return AuditLogger(mock_db_connection)
    
    @pytest.fixture
    def sample_logs_data(self):
        """创建示例日志数据"""
        return [
            {
                'log_id': 'LOG001',
                'timestamp': datetime(2024, 1, 1, 10, 0, 0),
                'event_type': 'AUTHENTICATION_SUCCESS',
                'vehicle_id': 'VIN123',
                'operation_result': True,
                'details': '认证成功',
                'ip_address': '192.168.1.100'
            },
            {
                'log_id': 'LOG002',
                'timestamp': datetime(2024, 1, 1, 11, 0, 0),
                'event_type': 'AUTHENTICATION_FAILURE',
                'vehicle_id': 'VIN456',
                'operation_result': False,
                'details': '认证失败',
                'ip_address': '192.168.1.101'
            },
            {
                'log_id': 'LOG003',
                'timestamp': datetime(2024, 1, 1, 12, 0, 0),
                'event_type': 'DATA_ENCRYPTED',
                'vehicle_id': 'VIN123',
                'operation_result': True,
                'details': '数据加密',
                'ip_address': '192.168.1.100'
            }
        ]
    
    def test_query_audit_logs_no_filters(self, audit_logger, mock_db_connection, sample_logs_data):
        """测试查询所有审计日志（无过滤条件）（需求 12.1, 12.2, 12.3, 12.4）"""
        mock_db_connection.execute_query.return_value = sample_logs_data
        
        logs = audit_logger.query_audit_logs()
        
        # 验证返回的日志数量
        assert len(logs) == 3
        
        # 验证查询被调用
        mock_db_connection.execute_query.assert_called_once()
        
        # 验证查询语句
        call_args = mock_db_connection.execute_query.call_args
        query = call_args[0][0]
        assert "SELECT log_id, timestamp, event_type, vehicle_id" in query
        assert "FROM audit_logs" in query
        assert "ORDER BY timestamp DESC" in query
    
    def test_query_audit_logs_by_time_range(self, audit_logger, mock_db_connection, sample_logs_data):
        """测试按时间范围过滤审计日志（需求 12.1）"""
        mock_db_connection.execute_query.return_value = sample_logs_data[:2]
        
        start_time = datetime(2024, 1, 1, 9, 0, 0)
        end_time = datetime(2024, 1, 1, 11, 30, 0)
        
        logs = audit_logger.query_audit_logs(
            start_time=start_time,
            end_time=end_time
        )
        
        # 验证返回的日志数量
        assert len(logs) == 2
        
        # 验证查询参数
        call_args = mock_db_connection.execute_query.call_args
        query, params = call_args[0]
        
        assert "timestamp >= %s" in query
        assert "timestamp <= %s" in query
        assert params[0] == start_time
        assert params[1] == end_time
    
    def test_query_audit_logs_by_start_time_only(self, audit_logger, mock_db_connection, sample_logs_data):
        """测试仅按开始时间过滤审计日志"""
        mock_db_connection.execute_query.return_value = sample_logs_data[1:]
        
        start_time = datetime(2024, 1, 1, 10, 30, 0)
        
        logs = audit_logger.query_audit_logs(start_time=start_time)
        
        assert len(logs) == 2
        
        call_args = mock_db_connection.execute_query.call_args
        query, params = call_args[0]
        
        assert "timestamp >= %s" in query
        assert "timestamp <= %s" not in query
        assert params[0] == start_time
    
    def test_query_audit_logs_by_end_time_only(self, audit_logger, mock_db_connection, sample_logs_data):
        """测试仅按结束时间过滤审计日志"""
        mock_db_connection.execute_query.return_value = sample_logs_data[:2]
        
        end_time = datetime(2024, 1, 1, 11, 30, 0)
        
        logs = audit_logger.query_audit_logs(end_time=end_time)
        
        assert len(logs) == 2
        
        call_args = mock_db_connection.execute_query.call_args
        query, params = call_args[0]
        
        assert "timestamp >= %s" not in query
        assert "timestamp <= %s" in query
        assert params[0] == end_time
    
    def test_query_audit_logs_by_vehicle_id(self, audit_logger, mock_db_connection, sample_logs_data):
        """测试按车辆标识过滤审计日志（需求 12.2）"""
        # 只返回 VIN123 的日志
        filtered_logs = [log for log in sample_logs_data if log['vehicle_id'] == 'VIN123']
        mock_db_connection.execute_query.return_value = filtered_logs
        
        logs = audit_logger.query_audit_logs(vehicle_id='VIN123')
        
        # 验证返回的日志数量
        assert len(logs) == 2
        
        # 验证所有日志都属于指定车辆
        for log in logs:
            assert log.vehicle_id == 'VIN123'
        
        # 验证查询参数
        call_args = mock_db_connection.execute_query.call_args
        query, params = call_args[0]
        
        assert "vehicle_id = %s" in query
        assert params[0] == 'VIN123'
    
    def test_query_audit_logs_by_event_type(self, audit_logger, mock_db_connection, sample_logs_data):
        """测试按事件类型过滤审计日志（需求 12.3）"""
        # 只返回认证成功的日志
        filtered_logs = [sample_logs_data[0]]
        mock_db_connection.execute_query.return_value = filtered_logs
        
        logs = audit_logger.query_audit_logs(
            event_type=EventType.AUTHENTICATION_SUCCESS
        )
        
        # 验证返回的日志数量
        assert len(logs) == 1
        
        # 验证日志的事件类型
        assert logs[0].event_type == EventType.AUTHENTICATION_SUCCESS
        
        # 验证查询参数
        call_args = mock_db_connection.execute_query.call_args
        query, params = call_args[0]
        
        assert "event_type = %s" in query
        assert params[0] == EventType.AUTHENTICATION_SUCCESS.value
    
    def test_query_audit_logs_by_operation_result_success(self, audit_logger, mock_db_connection, sample_logs_data):
        """测试按操作结果过滤审计日志 - 成功（需求 12.4）"""
        # 只返回成功的日志
        filtered_logs = [log for log in sample_logs_data if log['operation_result']]
        mock_db_connection.execute_query.return_value = filtered_logs
        
        logs = audit_logger.query_audit_logs(operation_result=True)
        
        # 验证返回的日志数量
        assert len(logs) == 2
        
        # 验证所有日志的操作结果都是成功
        for log in logs:
            assert log.operation_result is True
        
        # 验证查询参数
        call_args = mock_db_connection.execute_query.call_args
        query, params = call_args[0]
        
        assert "operation_result = %s" in query
        assert params[0] is True
    
    def test_query_audit_logs_by_operation_result_failure(self, audit_logger, mock_db_connection, sample_logs_data):
        """测试按操作结果过滤审计日志 - 失败（需求 12.4）"""
        # 只返回失败的日志
        filtered_logs = [log for log in sample_logs_data if not log['operation_result']]
        mock_db_connection.execute_query.return_value = filtered_logs
        
        logs = audit_logger.query_audit_logs(operation_result=False)
        
        # 验证返回的日志数量
        assert len(logs) == 1
        
        # 验证日志的操作结果是失败
        assert logs[0].operation_result is False
        
        # 验证查询参数
        call_args = mock_db_connection.execute_query.call_args
        query, params = call_args[0]
        
        assert "operation_result = %s" in query
        assert params[0] is False
    
    def test_query_audit_logs_multiple_filters(self, audit_logger, mock_db_connection, sample_logs_data):
        """测试使用多个过滤条件查询审计日志"""
        # 返回符合所有条件的日志
        filtered_logs = [sample_logs_data[0]]
        mock_db_connection.execute_query.return_value = filtered_logs
        
        start_time = datetime(2024, 1, 1, 9, 0, 0)
        end_time = datetime(2024, 1, 1, 10, 30, 0)
        
        logs = audit_logger.query_audit_logs(
            start_time=start_time,
            end_time=end_time,
            vehicle_id='VIN123',
            event_type=EventType.AUTHENTICATION_SUCCESS,
            operation_result=True
        )
        
        # 验证返回的日志数量
        assert len(logs) == 1
        
        # 验证日志符合所有条件
        assert logs[0].vehicle_id == 'VIN123'
        assert logs[0].event_type == EventType.AUTHENTICATION_SUCCESS
        assert logs[0].operation_result is True
        
        # 验证查询参数
        call_args = mock_db_connection.execute_query.call_args
        query, params = call_args[0]
        
        assert "timestamp >= %s" in query
        assert "timestamp <= %s" in query
        assert "vehicle_id = %s" in query
        assert "event_type = %s" in query
        assert "operation_result = %s" in query
        
        assert len(params) == 5
    
    def test_query_audit_logs_empty_result(self, audit_logger, mock_db_connection):
        """测试查询无结果的情况"""
        mock_db_connection.execute_query.return_value = []
        
        logs = audit_logger.query_audit_logs(vehicle_id='NONEXISTENT')
        
        # 验证返回空列表
        assert len(logs) == 0
        assert logs == []
    
    def test_query_audit_logs_returns_audit_log_objects(self, audit_logger, mock_db_connection, sample_logs_data):
        """测试查询返回 AuditLog 对象"""
        mock_db_connection.execute_query.return_value = sample_logs_data
        
        logs = audit_logger.query_audit_logs()
        
        # 验证返回的是 AuditLog 对象
        assert all(isinstance(log, AuditLog) for log in logs)
        
        # 验证对象属性
        assert logs[0].log_id == 'LOG001'
        assert logs[0].vehicle_id == 'VIN123'
        assert logs[0].event_type == EventType.AUTHENTICATION_SUCCESS
        assert logs[0].operation_result is True
    
    def test_query_audit_logs_ordered_by_timestamp_desc(self, audit_logger, mock_db_connection, sample_logs_data):
        """测试查询结果按时间戳降序排序"""
        mock_db_connection.execute_query.return_value = sample_logs_data
        
        logs = audit_logger.query_audit_logs()
        
        # 验证查询语句包含排序
        call_args = mock_db_connection.execute_query.call_args
        query = call_args[0][0]
        
        assert "ORDER BY timestamp DESC" in query
    
    def test_query_audit_logs_database_error(self, audit_logger, mock_db_connection):
        """测试数据库查询错误时的处理"""
        # 模拟数据库异常
        mock_db_connection.execute_query.side_effect = Exception("Database error")
        
        # 不应该抛出异常，应该返回空列表
        logs = audit_logger.query_audit_logs()
        
        assert logs == []
    
    def test_query_audit_logs_with_none_params(self, audit_logger, mock_db_connection, sample_logs_data):
        """测试所有参数为 None 时的查询"""
        mock_db_connection.execute_query.return_value = sample_logs_data
        
        logs = audit_logger.query_audit_logs(
            start_time=None,
            end_time=None,
            vehicle_id=None,
            event_type=None,
            operation_result=None
        )
        
        # 验证返回所有日志
        assert len(logs) == 3
        
        # 验证查询参数为 None 或空元组
        call_args = mock_db_connection.execute_query.call_args
        query, params = call_args[0]
        
        # 参数应该是 None 或空元组
        assert params is None or params == ()
    
    def test_query_audit_logs_preserves_log_details(self, audit_logger, mock_db_connection):
        """测试查询保留日志的所有详细信息"""
        detailed_log = {
            'log_id': 'LOG999',
            'timestamp': datetime(2024, 1, 1, 15, 30, 45),
            'event_type': 'CERTIFICATE_ISSUED',
            'vehicle_id': 'VIN999',
            'operation_result': True,
            'details': '证书 CERT999 颁发（车辆: VIN999）',
            'ip_address': '10.0.0.1'
        }
        
        mock_db_connection.execute_query.return_value = [detailed_log]
        
        logs = audit_logger.query_audit_logs()
        
        # 验证所有字段都被正确保留
        assert len(logs) == 1
        log = logs[0]
        
        assert log.log_id == 'LOG999'
        assert log.timestamp == datetime(2024, 1, 1, 15, 30, 45)
        assert log.event_type == EventType.CERTIFICATE_ISSUED
        assert log.vehicle_id == 'VIN999'
        assert log.operation_result is True
        assert log.details == '证书 CERT999 颁发（车辆: VIN999）'
        assert log.ip_address == '10.0.0.1'
    
    def test_query_audit_logs_different_event_types(self, audit_logger, mock_db_connection):
        """测试查询不同事件类型的日志"""
        event_types = [
            EventType.VEHICLE_CONNECT,
            EventType.VEHICLE_DISCONNECT,
            EventType.DATA_DECRYPTED,
            EventType.CERTIFICATE_REVOKED,
            EventType.SIGNATURE_VERIFIED,
            EventType.SIGNATURE_FAILED
        ]
        
        for event_type in event_types:
            log_data = [{
                'log_id': f'LOG_{event_type.value}',
                'timestamp': datetime.now(),
                'event_type': event_type.value,
                'vehicle_id': 'VIN123',
                'operation_result': True,
                'details': f'测试 {event_type.value}',
                'ip_address': '192.168.1.1'
            }]
            
            mock_db_connection.execute_query.return_value = log_data
            
            logs = audit_logger.query_audit_logs(event_type=event_type)
            
            assert len(logs) == 1
            assert logs[0].event_type == event_type


class TestAuditReportExport:
    """审计报告导出功能测试"""
    
    @pytest.fixture
    def mock_db_connection(self):
        """创建 Mock 数据库连接"""
        mock_db = MagicMock()
        return mock_db
    
    @pytest.fixture
    def audit_logger(self, mock_db_connection):
        """创建审计日志记录器实例"""
        return AuditLogger(mock_db_connection)
    
    @pytest.fixture
    def sample_logs_data(self):
        """创建示例日志数据"""
        return [
            {
                'log_id': 'LOG001',
                'timestamp': datetime(2024, 1, 1, 10, 0, 0),
                'event_type': 'AUTHENTICATION_SUCCESS',
                'vehicle_id': 'VIN123',
                'operation_result': True,
                'details': '认证成功',
                'ip_address': '192.168.1.100'
            },
            {
                'log_id': 'LOG002',
                'timestamp': datetime(2024, 1, 1, 11, 0, 0),
                'event_type': 'AUTHENTICATION_FAILURE',
                'vehicle_id': 'VIN456',
                'operation_result': False,
                'details': '认证失败',
                'ip_address': '192.168.1.101'
            },
            {
                'log_id': 'LOG003',
                'timestamp': datetime(2024, 1, 1, 12, 0, 0),
                'event_type': 'DATA_ENCRYPTED',
                'vehicle_id': 'VIN123',
                'operation_result': True,
                'details': '数据加密',
                'ip_address': '192.168.1.100'
            }
        ]
    
    def test_export_audit_report_json_format(self, audit_logger, mock_db_connection, sample_logs_data):
        """测试导出 JSON 格式的审计报告（需求 12.5）"""
        mock_db_connection.execute_query.return_value = sample_logs_data
        
        start_time = datetime(2024, 1, 1, 9, 0, 0)
        end_time = datetime(2024, 1, 1, 13, 0, 0)
        
        report = audit_logger.export_audit_report(
            start_time=start_time,
            end_time=end_time,
            format="json"
        )
        
        # 验证返回的是字符串
        assert isinstance(report, str)
        
        # 解析 JSON
        report_data = json.loads(report)
        
        # 验证报告元数据
        assert "report_metadata" in report_data
        assert "logs" in report_data
        
        metadata = report_data["report_metadata"]
        assert "generated_at" in metadata
        assert metadata["start_time"] == start_time.isoformat()
        assert metadata["end_time"] == end_time.isoformat()
        assert metadata["total_logs"] == 3
        
        # 验证日志数据
        logs = report_data["logs"]
        assert len(logs) == 3
        
        # 验证第一条日志
        assert logs[0]["log_id"] == "LOG001"
        assert logs[0]["event_type"] == "AUTHENTICATION_SUCCESS"
        assert logs[0]["vehicle_id"] == "VIN123"
        assert logs[0]["operation_result"] is True
    
    def test_export_audit_report_csv_format(self, audit_logger, mock_db_connection, sample_logs_data):
        """测试导出 CSV 格式的审计报告（需求 12.5）"""
        mock_db_connection.execute_query.return_value = sample_logs_data
        
        start_time = datetime(2024, 1, 1, 9, 0, 0)
        end_time = datetime(2024, 1, 1, 13, 0, 0)
        
        report = audit_logger.export_audit_report(
            start_time=start_time,
            end_time=end_time,
            format="csv"
        )
        
        # 验证返回的是字符串
        assert isinstance(report, str)
        
        # 解析 CSV
        lines = report.strip().split('\n')
        
        # 验证表头
        assert len(lines) >= 1
        header = lines[0]
        assert "log_id" in header
        assert "timestamp" in header
        assert "event_type" in header
        assert "vehicle_id" in header
        assert "operation_result" in header
        assert "details" in header
        assert "ip_address" in header
        
        # 验证数据行数（表头 + 3 条日志）
        assert len(lines) == 4
        
        # 验证第一条日志数据
        assert "LOG001" in lines[1]
        assert "AUTHENTICATION_SUCCESS" in lines[1]
        assert "VIN123" in lines[1]
    
    def test_export_audit_report_default_format(self, audit_logger, mock_db_connection, sample_logs_data):
        """测试导出报告时使用默认格式（JSON）"""
        mock_db_connection.execute_query.return_value = sample_logs_data
        
        start_time = datetime(2024, 1, 1, 9, 0, 0)
        end_time = datetime(2024, 1, 1, 13, 0, 0)
        
        # 不指定 format 参数，应该默认使用 JSON
        report = audit_logger.export_audit_report(
            start_time=start_time,
            end_time=end_time
        )
        
        # 验证是有效的 JSON
        report_data = json.loads(report)
        assert "report_metadata" in report_data
        assert "logs" in report_data
    
    def test_export_audit_report_empty_logs(self, audit_logger, mock_db_connection):
        """测试导出空日志的报告"""
        mock_db_connection.execute_query.return_value = []
        
        start_time = datetime(2024, 1, 1, 9, 0, 0)
        end_time = datetime(2024, 1, 1, 13, 0, 0)
        
        # JSON 格式
        json_report = audit_logger.export_audit_report(
            start_time=start_time,
            end_time=end_time,
            format="json"
        )
        
        report_data = json.loads(json_report)
        assert report_data["report_metadata"]["total_logs"] == 0
        assert len(report_data["logs"]) == 0
        
        # CSV 格式
        csv_report = audit_logger.export_audit_report(
            start_time=start_time,
            end_time=end_time,
            format="csv"
        )
        
        lines = csv_report.strip().split('\n')
        # 只有表头，没有数据行
        assert len(lines) == 1
    
    def test_export_audit_report_invalid_format(self, audit_logger, mock_db_connection):
        """测试使用不支持的格式导出报告"""
        start_time = datetime(2024, 1, 1, 9, 0, 0)
        end_time = datetime(2024, 1, 1, 13, 0, 0)
        
        with pytest.raises(ValueError) as exc_info:
            audit_logger.export_audit_report(
                start_time=start_time,
                end_time=end_time,
                format="xml"
            )
        
        assert "Unsupported format" in str(exc_info.value)
        assert "xml" in str(exc_info.value)
    
    def test_export_audit_report_json_contains_all_fields(self, audit_logger, mock_db_connection):
        """测试 JSON 报告包含所有日志字段"""
        log_data = [{
            'log_id': 'LOG999',
            'timestamp': datetime(2024, 1, 1, 15, 30, 45),
            'event_type': 'CERTIFICATE_ISSUED',
            'vehicle_id': 'VIN999',
            'operation_result': True,
            'details': '证书 CERT999 颁发',
            'ip_address': '10.0.0.1'
        }]
        
        mock_db_connection.execute_query.return_value = log_data
        
        start_time = datetime(2024, 1, 1, 9, 0, 0)
        end_time = datetime(2024, 1, 1, 16, 0, 0)
        
        report = audit_logger.export_audit_report(
            start_time=start_time,
            end_time=end_time,
            format="json"
        )
        
        report_data = json.loads(report)
        log = report_data["logs"][0]
        
        # 验证所有字段都存在
        assert log["log_id"] == "LOG999"
        assert log["timestamp"] == "2024-01-01T15:30:45"
        assert log["event_type"] == "CERTIFICATE_ISSUED"
        assert log["vehicle_id"] == "VIN999"
        assert log["operation_result"] is True
        assert log["details"] == "证书 CERT999 颁发"
        assert log["ip_address"] == "10.0.0.1"
    
    def test_export_audit_report_csv_contains_all_fields(self, audit_logger, mock_db_connection):
        """测试 CSV 报告包含所有日志字段"""
        log_data = [{
            'log_id': 'LOG888',
            'timestamp': datetime(2024, 1, 1, 14, 20, 30),
            'event_type': 'DATA_DECRYPTED',
            'vehicle_id': 'VIN888',
            'operation_result': True,
            'details': '数据解密成功',
            'ip_address': '172.16.0.1'
        }]
        
        mock_db_connection.execute_query.return_value = log_data
        
        start_time = datetime(2024, 1, 1, 9, 0, 0)
        end_time = datetime(2024, 1, 1, 16, 0, 0)
        
        report = audit_logger.export_audit_report(
            start_time=start_time,
            end_time=end_time,
            format="csv"
        )
        
        # 使用 csv.DictReader 解析 CSV
        csv_reader = csv.DictReader(io.StringIO(report))
        rows = list(csv_reader)
        
        assert len(rows) == 1
        row = rows[0]
        
        # 验证所有字段都存在
        assert row["log_id"] == "LOG888"
        assert row["timestamp"] == "2024-01-01T14:20:30"
        assert row["event_type"] == "DATA_DECRYPTED"
        assert row["vehicle_id"] == "VIN888"
        assert row["operation_result"] == "True"
        assert row["details"] == "数据解密成功"
        assert row["ip_address"] == "172.16.0.1"
    
    def test_export_audit_report_time_range_filtering(self, audit_logger, mock_db_connection, sample_logs_data):
        """测试报告导出时正确应用时间范围过滤"""
        mock_db_connection.execute_query.return_value = sample_logs_data
        
        start_time = datetime(2024, 1, 1, 9, 0, 0)
        end_time = datetime(2024, 1, 1, 13, 0, 0)
        
        audit_logger.export_audit_report(
            start_time=start_time,
            end_time=end_time,
            format="json"
        )
        
        # 验证查询时使用了正确的时间范围
        call_args = mock_db_connection.execute_query.call_args
        query, params = call_args[0]
        
        assert "timestamp >= %s" in query
        assert "timestamp <= %s" in query
        assert params[0] == start_time
        assert params[1] == end_time
    
    def test_export_audit_report_json_readable_format(self, audit_logger, mock_db_connection, sample_logs_data):
        """测试 JSON 报告使用可读格式（带缩进）"""
        mock_db_connection.execute_query.return_value = sample_logs_data[:1]
        
        start_time = datetime(2024, 1, 1, 9, 0, 0)
        end_time = datetime(2024, 1, 1, 13, 0, 0)
        
        report = audit_logger.export_audit_report(
            start_time=start_time,
            end_time=end_time,
            format="json"
        )
        
        # 验证 JSON 包含换行和缩进（可读格式）
        assert '\n' in report
        assert '  ' in report  # 缩进
    
    def test_export_audit_report_json_chinese_characters(self, audit_logger, mock_db_connection):
        """测试 JSON 报告正确处理中文字符"""
        log_data = [{
            'log_id': 'LOG777',
            'timestamp': datetime(2024, 1, 1, 10, 0, 0),
            'event_type': 'AUTHENTICATION_SUCCESS',
            'vehicle_id': 'VIN777',
            'operation_result': True,
            'details': '车辆认证成功，使用国密算法',
            'ip_address': '192.168.1.1'
        }]
        
        mock_db_connection.execute_query.return_value = log_data
        
        start_time = datetime(2024, 1, 1, 9, 0, 0)
        end_time = datetime(2024, 1, 1, 11, 0, 0)
        
        report = audit_logger.export_audit_report(
            start_time=start_time,
            end_time=end_time,
            format="json"
        )
        
        # 验证中文字符没有被转义
        assert '车辆认证成功' in report
        assert '国密算法' in report
        
        # 验证 JSON 可以正确解析
        report_data = json.loads(report)
        assert report_data["logs"][0]["details"] == "车辆认证成功，使用国密算法"
    
    def test_export_audit_report_large_dataset(self, audit_logger, mock_db_connection):
        """测试导出大量日志的报告"""
        # 生成 1000 条日志
        large_logs_data = []
        for i in range(1000):
            large_logs_data.append({
                'log_id': f'LOG{i:04d}',
                'timestamp': datetime(2024, 1, 1, 10, 0, i % 60),
                'event_type': 'AUTHENTICATION_SUCCESS',
                'vehicle_id': f'VIN{i % 100}',
                'operation_result': True,
                'details': f'日志条目 {i}',
                'ip_address': f'192.168.{i // 256}.{i % 256}'
            })
        
        mock_db_connection.execute_query.return_value = large_logs_data
        
        start_time = datetime(2024, 1, 1, 9, 0, 0)
        end_time = datetime(2024, 1, 1, 13, 0, 0)
        
        # JSON 格式
        json_report = audit_logger.export_audit_report(
            start_time=start_time,
            end_time=end_time,
            format="json"
        )
        
        report_data = json.loads(json_report)
        assert report_data["report_metadata"]["total_logs"] == 1000
        assert len(report_data["logs"]) == 1000
        
        # CSV 格式
        csv_report = audit_logger.export_audit_report(
            start_time=start_time,
            end_time=end_time,
            format="csv"
        )
        
        lines = csv_report.strip().split('\n')
        # 表头 + 1000 条数据
        assert len(lines) == 1001
    
    def test_export_audit_report_metadata_accuracy(self, audit_logger, mock_db_connection, sample_logs_data):
        """测试报告元数据的准确性"""
        mock_db_connection.execute_query.return_value = sample_logs_data
        
        start_time = datetime(2024, 1, 1, 9, 0, 0)
        end_time = datetime(2024, 1, 1, 13, 0, 0)
        
        # 记录导出前的时间
        before_export = datetime.now()
        
        report = audit_logger.export_audit_report(
            start_time=start_time,
            end_time=end_time,
            format="json"
        )
        
        # 记录导出后的时间
        after_export = datetime.now()
        
        report_data = json.loads(report)
        metadata = report_data["report_metadata"]
        
        # 验证生成时间在合理范围内
        generated_at = datetime.fromisoformat(metadata["generated_at"])
        assert before_export <= generated_at <= after_export
        
        # 验证时间范围准确
        assert metadata["start_time"] == start_time.isoformat()
        assert metadata["end_time"] == end_time.isoformat()
        
        # 验证日志总数准确
        assert metadata["total_logs"] == len(sample_logs_data)

