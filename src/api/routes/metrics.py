"""安全指标监控 API

提供实时安全指标和历史指标查询功能。

验证需求: 14.1, 14.2, 14.3, 14.4, 14.5, 14.6
"""

from fastapi import APIRouter, HTTPException, Depends, Query
from pydantic import BaseModel
from typing import List, Optional
from datetime import datetime, timedelta

from src.db.postgres import PostgreSQLConnection
from config.database import PostgreSQLConfig
from src.models.enums import EventType
from src.api.main import verify_token

router = APIRouter()


class RealtimeMetrics(BaseModel):
    """实时安全指标"""
    timestamp: datetime
    online_vehicles: int
    auth_success_rate: float
    auth_failure_count: int
    data_transfer_volume: int  # 字节
    signature_failure_count: int
    security_anomaly_count: int


class HistoricalMetrics(BaseModel):
    """历史安全指标"""
    start_time: datetime
    end_time: datetime
    metrics: List[RealtimeMetrics]


@router.get("/realtime", response_model=RealtimeMetrics)
async def get_realtime_metrics(
    user: str = Depends(verify_token)
):
    """获取实时安全指标
    
    返回当前的安全通信指标，包括：
    - 在线车辆数
    - 认证成功率
    - 认证失败次数
    - 数据传输量
    - 签名验证失败次数
    - 安全异常次数
    
    验证需求: 14.1, 14.2, 14.3, 14.4, 14.5, 14.6
    """
    try:
        db_conn = PostgreSQLConnection(PostgreSQLConfig.from_env())
        
        # 获取最近 5 分钟的统计数据
        five_minutes_ago = datetime.now() - timedelta(minutes=5)
        
        # 查询认证成功次数
        auth_success_query = """
            SELECT COUNT(*) as count
            FROM audit_logs
            WHERE event_type = %s
            AND timestamp >= %s
        """
        auth_success_result = db_conn.execute_query(
            auth_success_query,
            (EventType.AUTHENTICATION_SUCCESS.value, five_minutes_ago)
        )
        auth_success_count = auth_success_result[0]['count'] if auth_success_result else 0
        
        # 查询认证失败次数
        auth_failure_query = """
            SELECT COUNT(*) as count
            FROM audit_logs
            WHERE event_type = %s
            AND timestamp >= %s
        """
        auth_failure_result = db_conn.execute_query(
            auth_failure_query,
            (EventType.AUTHENTICATION_FAILURE.value, five_minutes_ago)
        )
        auth_failure_count = auth_failure_result[0]['count'] if auth_failure_result else 0
        
        # 计算认证成功率
        total_auth = auth_success_count + auth_failure_count
        auth_success_rate = (auth_success_count / total_auth * 100) if total_auth > 0 else 100.0
        
        # 查询数据传输量（从审计日志的 details 字段提取）
        data_transfer_query = """
            SELECT details
            FROM audit_logs
            WHERE event_type IN (%s, %s)
            AND timestamp >= %s
        """
        data_transfer_result = db_conn.execute_query(
            data_transfer_query,
            (EventType.DATA_ENCRYPTED.value, EventType.DATA_DECRYPTED.value, five_minutes_ago)
        )
        
        # 简化实现：假设每次数据传输 1KB
        data_transfer_volume = len(data_transfer_result) * 1024 if data_transfer_result else 0
        
        # 查询签名验证失败次数
        signature_failure_query = """
            SELECT COUNT(*) as count
            FROM audit_logs
            WHERE event_type = %s
            AND timestamp >= %s
        """
        signature_failure_result = db_conn.execute_query(
            signature_failure_query,
            (EventType.SIGNATURE_FAILED.value, five_minutes_ago)
        )
        signature_failure_count = signature_failure_result[0]['count'] if signature_failure_result else 0
        
        # 查询安全异常次数（认证失败 + 签名失败）
        security_anomaly_count = auth_failure_count + signature_failure_count
        
        # 获取在线车辆数（从 Redis）
        from src.db.redis_client import RedisConnection
        from config.database import RedisConfig
        
        redis_conn = RedisConnection(RedisConfig.from_env())
        redis_conn.connect()
        session_keys = redis_conn.scan_keys("session:*")
        online_vehicles = len(session_keys)
        redis_conn.close()
        
        db_conn.close()
        
        return RealtimeMetrics(
            timestamp=datetime.now(),
            online_vehicles=online_vehicles,
            auth_success_rate=round(auth_success_rate, 2),
            auth_failure_count=auth_failure_count,
            data_transfer_volume=data_transfer_volume,
            signature_failure_count=signature_failure_count,
            security_anomaly_count=security_anomaly_count
        )
        
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"获取实时指标失败: {str(e)}"
        )


@router.get("/history", response_model=HistoricalMetrics)
async def get_historical_metrics(
    start_time: datetime = Query(..., description="开始时间"),
    end_time: datetime = Query(..., description="结束时间"),
    user: str = Depends(verify_token)
):
    """获取历史安全指标
    
    返回指定时间范围内的安全指标历史数据。
    
    参数:
        start_time: 开始时间
        end_time: 结束时间
        
    返回:
        HistoricalMetrics: 历史指标数据
        
    验证需求: 14.6
    """
    try:
        db_conn = PostgreSQLConnection(PostgreSQLConfig.from_env())
        
        # 按小时聚合数据
        metrics = []
        current_time = start_time
        
        while current_time < end_time:
            next_time = current_time + timedelta(hours=1)
            
            # 查询该小时的统计数据
            auth_success_query = """
                SELECT COUNT(*) as count
                FROM audit_logs
                WHERE event_type = %s
                AND timestamp >= %s
                AND timestamp < %s
            """
            auth_success_result = db_conn.execute_query(
                auth_success_query,
                (EventType.AUTHENTICATION_SUCCESS.value, current_time, next_time)
            )
            auth_success_count = auth_success_result[0]['count'] if auth_success_result else 0
            
            auth_failure_query = """
                SELECT COUNT(*) as count
                FROM audit_logs
                WHERE event_type = %s
                AND timestamp >= %s
                AND timestamp < %s
            """
            auth_failure_result = db_conn.execute_query(
                auth_failure_query,
                (EventType.AUTHENTICATION_FAILURE.value, current_time, next_time)
            )
            auth_failure_count = auth_failure_result[0]['count'] if auth_failure_result else 0
            
            total_auth = auth_success_count + auth_failure_count
            auth_success_rate = (auth_success_count / total_auth * 100) if total_auth > 0 else 100.0
            
            # 简化实现：其他指标设为 0
            metric = RealtimeMetrics(
                timestamp=current_time,
                online_vehicles=0,  # 历史数据不统计在线车辆数
                auth_success_rate=round(auth_success_rate, 2),
                auth_failure_count=auth_failure_count,
                data_transfer_volume=0,
                signature_failure_count=0,
                security_anomaly_count=auth_failure_count
            )
            metrics.append(metric)
            
            current_time = next_time
        
        db_conn.close()
        
        return HistoricalMetrics(
            start_time=start_time,
            end_time=end_time,
            metrics=metrics
        )
        
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"获取历史指标失败: {str(e)}"
        )
