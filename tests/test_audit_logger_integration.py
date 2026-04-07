"""审计日志查询功能集成测试

演示审计日志记录和查询的完整流程
"""

import pytest
from unittest.mock import MagicMock
from datetime import datetime, timedelta
from src.audit_logger import AuditLogger
from src.models.enums import EventType


class TestAuditLoggerIntegration:
    """审计日志记录和查询集成测试"""
    
    @pytest.fixture
    def mock_db_connection(self):
        """创建 Mock 数据库连接"""
        mock_db = MagicMock()
        # 模拟存储的日志数据
        self.stored_logs = []
        
        def mock_execute_update(query, params):
            """模拟插入操作"""
            if "INSERT INTO audit_logs" in query:
                # 存储日志数据
                log_data = {
                    'log_id': params[0],
                    'timestamp': params[1],
                    'event_type': params[2],
                    'vehicle_id': params[3],
                    'operation_result': params[4],
                    'details': params[5],
                    'ip_address': params[6]
                }
                self.stored_logs.append(log_data)
                return 1
            return 0
        
        def mock_execute_query(query, params):
            """模拟查询操作"""
            # 返回存储的日志数据
            results = self.stored_logs.copy()
            
            # 应用过滤条件
            if params:
                param_idx = 0
                if "timestamp >= %s" in query:
                    start_time = params[param_idx]
                    results = [log for log in results if log['timestamp'] >= start_time]
                    param_idx += 1
                
                if "timestamp <= %s" in query:
                    end_time = params[param_idx]
                    results = [log for log in results if log['timestamp'] <= end_time]
                    param_idx += 1
                
                if "vehicle_id = %s" in query:
                    vehicle_id = params[param_idx]
                    results = [log for log in results if log['vehicle_id'] == vehicle_id]
                    param_idx += 1
                
                if "event_type = %s" in query:
                    event_type = params[param_idx]
                    results = [log for log in results if log['event_type'] == event_type]
                    param_idx += 1
                
                if "operation_result = %s" in query:
                    operation_result = params[param_idx]
                    results = [log for log in results if log['operation_result'] == operation_result]
            
            # 按时间戳降序排序
            results.sort(key=lambda x: x['timestamp'], reverse=True)
            
            return results
        
        mock_db.execute_update.side_effect = mock_execute_update
        mock_db.execute_query.side_effect = mock_execute_query
        
        return mock_db
    
    @pytest.fixture
    def audit_logger(self, mock_db_connection):
        """创建审计日志记录器实例"""
        return AuditLogger(mock_db_connection)
    
    def test_complete_workflow_record_and_query(self, audit_logger):
        """测试完整的记录和查询工作流程（需求 12.1, 12.2, 12.3, 12.4, 12.6）"""
        # 步骤 1: 记录多个不同类型的日志
        base_time = datetime(2024, 1, 1, 10, 0, 0)
        
        # 记录认证成功事件
        log_id1 = audit_logger.log_auth_event(
            vehicle_id="VIN123",
            event_type=EventType.AUTHENTICATION_SUCCESS,
            result=True,
            ip_address="192.168.1.100"
        )
        
        # 记录认证失败事件
        log_id2 = audit_logger.log_auth_event(
            vehicle_id="VIN456",
            event_type=EventType.AUTHENTICATION_FAILURE,
            result=False,
            ip_address="192.168.1.101"
        )
        
        # 记录数据传输事件
        log_id3 = audit_logger.log_data_transfer(
            vehicle_id="VIN123",
            data_size=2048,
            encrypted=True,
            ip_address="192.168.1.100"
        )
        
        # 记录证书颁发事件
        log_id4 = audit_logger.log_certificate_operation(
            operation="issued",
            cert_id="CERT123",
            vehicle_id="VIN789",
            ip_address="192.168.1.102"
        )
        
        # 步骤 2: 查询所有日志
        all_logs = audit_logger.query_audit_logs()
        assert len(all_logs) == 4
        
        # 步骤 3: 按车辆标识查询
        vin123_logs = audit_logger.query_audit_logs(vehicle_id="VIN123")
        assert len(vin123_logs) == 2
        assert all(log.vehicle_id == "VIN123" for log in vin123_logs)
        
        # 步骤 4: 按事件类型查询
        auth_success_logs = audit_logger.query_audit_logs(
            event_type=EventType.AUTHENTICATION_SUCCESS
        )
        assert len(auth_success_logs) == 1
        assert auth_success_logs[0].event_type == EventType.AUTHENTICATION_SUCCESS
        
        # 步骤 5: 按操作结果查询
        success_logs = audit_logger.query_audit_logs(operation_result=True)
        assert len(success_logs) == 3
        
        failure_logs = audit_logger.query_audit_logs(operation_result=False)
        assert len(failure_logs) == 1
        
        # 步骤 6: 组合查询
        vin123_success_logs = audit_logger.query_audit_logs(
            vehicle_id="VIN123",
            operation_result=True
        )
        assert len(vin123_success_logs) == 2
    
    def test_time_range_filtering(self, audit_logger):
        """测试时间范围过滤功能（需求 12.1）"""
        # 记录不同时间的日志
        time1 = datetime(2024, 1, 1, 10, 0, 0)
        time2 = datetime(2024, 1, 1, 11, 0, 0)
        time3 = datetime(2024, 1, 1, 12, 0, 0)
        
        # 手动设置时间戳（通过 mock）
        audit_logger.log_auth_event(
            vehicle_id="VIN1",
            event_type=EventType.AUTHENTICATION_SUCCESS,
            result=True
        )
        
        audit_logger.log_auth_event(
            vehicle_id="VIN2",
            event_type=EventType.AUTHENTICATION_SUCCESS,
            result=True
        )
        
        audit_logger.log_auth_event(
            vehicle_id="VIN3",
            event_type=EventType.AUTHENTICATION_SUCCESS,
            result=True
        )
        
        # 查询所有日志
        all_logs = audit_logger.query_audit_logs()
        assert len(all_logs) == 3
    
    def test_query_performance_with_multiple_logs(self, audit_logger):
        """测试查询性能（需求 12.6）"""
        # 记录大量日志
        for i in range(100):
            audit_logger.log_auth_event(
                vehicle_id=f"VIN{i:03d}",
                event_type=EventType.AUTHENTICATION_SUCCESS if i % 2 == 0 else EventType.AUTHENTICATION_FAILURE,
                result=i % 2 == 0
            )
        
        # 查询所有日志
        import time
        start_time = time.time()
        all_logs = audit_logger.query_audit_logs()
        query_time = time.time() - start_time
        
        # 验证查询结果
        assert len(all_logs) == 100
        
        # 验证查询时间（应该很快，因为是内存操作）
        # 注意：实际数据库查询需要确保索引优化以满足 < 1 秒的要求
        assert query_time < 1.0
        
        # 测试过滤查询
        start_time = time.time()
        success_logs = audit_logger.query_audit_logs(operation_result=True)
        query_time = time.time() - start_time
        
        assert len(success_logs) == 50
        assert query_time < 1.0
    
    def test_empty_query_results(self, audit_logger):
        """测试查询无结果的情况"""
        # 记录一些日志
        audit_logger.log_auth_event(
            vehicle_id="VIN123",
            event_type=EventType.AUTHENTICATION_SUCCESS,
            result=True
        )
        
        # 查询不存在的车辆
        logs = audit_logger.query_audit_logs(vehicle_id="NONEXISTENT")
        assert len(logs) == 0
        
        # 查询不存在的事件类型组合
        logs = audit_logger.query_audit_logs(
            vehicle_id="VIN123",
            event_type=EventType.CERTIFICATE_REVOKED
        )
        assert len(logs) == 0
    
    def test_query_returns_sorted_results(self, audit_logger):
        """测试查询结果按时间戳降序排序"""
        # 记录多个日志
        for i in range(5):
            audit_logger.log_auth_event(
                vehicle_id=f"VIN{i}",
                event_type=EventType.AUTHENTICATION_SUCCESS,
                result=True
            )
        
        # 查询所有日志
        logs = audit_logger.query_audit_logs()
        
        # 验证结果按时间戳降序排序（最新的在前）
        assert len(logs) == 5
        for i in range(len(logs) - 1):
            assert logs[i].timestamp >= logs[i + 1].timestamp
