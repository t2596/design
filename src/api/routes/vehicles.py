"""车辆状态监控 API

提供车辆在线状态查询、车辆详情查询和车辆搜索功能。

验证需求: 13.1, 13.2, 13.3, 13.4, 13.5
"""

from fastapi import APIRouter, HTTPException, Depends, Query
from pydantic import BaseModel
from typing import List, Optional, Dict, Any
from datetime import datetime
import json

from src.db.redis_client import RedisConnection
from src.db.postgres import PostgreSQLConnection
from config.database import RedisConfig, PostgreSQLConfig
from src.api.main import verify_token

router = APIRouter()


class VehicleStatus(BaseModel):
    """车辆状态模型"""
    vehicle_id: str
    status: str  # "online" 或 "offline"
    session_id: Optional[str] = None
    connected_at: Optional[datetime] = None
    last_activity: Optional[datetime] = None
    ip_address: Optional[str] = None


class VehicleListResponse(BaseModel):
    """车辆列表响应"""
    total: int
    vehicles: List[VehicleStatus]


@router.get("/online", response_model=VehicleListResponse)
async def get_online_vehicles(
    user: str = Depends(verify_token)
):
    """获取在线车辆列表
    
    返回当前所有在线车辆的状态信息。
    只返回最近 5 分钟内有活动的车辆。
    
    验证需求: 13.1, 13.2
    """
    try:
        redis_conn = RedisConnection(RedisConfig.from_env())
        redis_conn.connect()
        
        # 获取所有会话键
        session_keys = redis_conn.scan_keys("session:*")
        
        vehicles = []
        current_time = datetime.utcnow()
        timeout_seconds = 300  # 5 分钟超时
        
        for key in session_keys:
            session_data = redis_conn.get(key)
            if session_data:
                session_dict = json.loads(session_data.decode('utf-8'))
                
                # 检查最后活动时间
                last_activity_str = session_dict.get('last_activity_time')
                if last_activity_str:
                    last_activity = datetime.fromisoformat(last_activity_str)
                    time_diff = (current_time - last_activity).total_seconds()
                    
                    # 只返回最近 5 分钟内有活动的车辆
                    if time_diff <= timeout_seconds:
                        vehicle_status = VehicleStatus(
                            vehicle_id=session_dict.get('vehicle_id'),
                            status="online",
                            session_id=session_dict.get('session_id'),
                            connected_at=datetime.fromisoformat(session_dict.get('established_at')),
                            last_activity=last_activity,
                            ip_address=session_dict.get('ip_address', 'unknown')
                        )
                        vehicles.append(vehicle_status)
                    else:
                        # 超时的会话，删除它
                        redis_conn.delete(key)
                        vehicle_key = f"vehicle:{session_dict.get('vehicle_id')}:session"
                        redis_conn.delete(vehicle_key)
        
        redis_conn.close()
        
        return VehicleListResponse(
            total=len(vehicles),
            vehicles=vehicles
        )
        
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"获取在线车辆列表失败: {str(e)}"
        )


@router.get("/{vehicle_id}/status", response_model=VehicleStatus)
async def get_vehicle_status(
    vehicle_id: str,
    user: str = Depends(verify_token)
):
    """获取特定车辆的状态信息
    
    检查车辆是否在线，如果最后活动时间超过 5 分钟则视为离线。
    
    参数:
        vehicle_id: 车辆标识
        
    返回:
        VehicleStatus: 车辆状态信息
        
    验证需求: 13.3
    """
    try:
        redis_conn = RedisConnection(RedisConfig.from_env())
        redis_conn.connect()
        
        # 查找车辆的会话
        vehicle_key = f"vehicle:{vehicle_id}:session"
        session_id = redis_conn.get(vehicle_key)
        
        if not session_id:
            redis_conn.close()
            return VehicleStatus(
                vehicle_id=vehicle_id,
                status="offline"
            )
        
        # 获取会话详情
        session_key = f"session:{session_id.decode('utf-8')}"
        session_data = redis_conn.get(session_key)
        
        if not session_data:
            redis_conn.close()
            return VehicleStatus(
                vehicle_id=vehicle_id,
                status="offline"
            )
        
        session_dict = json.loads(session_data.decode('utf-8'))
        
        # 检查最后活动时间
        last_activity_str = session_dict.get('last_activity_time')
        if last_activity_str:
            last_activity = datetime.fromisoformat(last_activity_str)
            current_time = datetime.utcnow()
            time_diff = (current_time - last_activity).total_seconds()
            
            # 超过 5 分钟视为离线
            if time_diff > 300:
                # 删除过期会话
                redis_conn.delete(session_key)
                redis_conn.delete(vehicle_key)
                redis_conn.close()
                
                return VehicleStatus(
                    vehicle_id=vehicle_id,
                    status="offline"
                )
        
        redis_conn.close()
        
        return VehicleStatus(
            vehicle_id=vehicle_id,
            status="online",
            session_id=session_dict.get('session_id'),
            connected_at=datetime.fromisoformat(session_dict.get('established_at')),
            last_activity=datetime.fromisoformat(session_dict.get('last_activity_time')),
            ip_address=session_dict.get('ip_address', 'unknown')
        )
        
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"获取车辆状态失败: {str(e)}"
        )


@router.get("/search", response_model=VehicleListResponse)
async def search_vehicles(
    query: str = Query(..., description="搜索关键词（车辆标识）"),
    user: str = Depends(verify_token)
):
    """搜索车辆
    
    根据车辆标识搜索车辆。
    
    参数:
        query: 搜索关键词
        
    返回:
        VehicleListResponse: 匹配的车辆列表
        
    验证需求: 13.5
    """
    try:
        redis_conn = RedisConnection(RedisConfig.from_env())
        redis_conn.connect()
        
        # 获取所有会话键
        session_keys = redis_conn.scan_keys("session:*")
        
        vehicles = []
        for key in session_keys:
            session_data = redis_conn.get(key)
            if session_data:
                session_dict = json.loads(session_data.decode('utf-8'))
                vehicle_id = session_dict.get('vehicle_id')
                
                # 简单的字符串匹配
                if query.lower() in vehicle_id.lower():
                    vehicle_status = VehicleStatus(
                        vehicle_id=vehicle_id,
                        status="online",
                        session_id=session_dict.get('session_id'),
                        connected_at=datetime.fromisoformat(session_dict.get('established_at')),
                        last_activity=datetime.fromisoformat(session_dict.get('last_activity_time')),
                        ip_address=session_dict.get('ip_address', 'unknown')
                    )
                    vehicles.append(vehicle_status)
        
        redis_conn.close()
        
        return VehicleListResponse(
            total=len(vehicles),
            vehicles=vehicles
        )
        
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"搜索车辆失败: {str(e)}"
        )


@router.get("/{vehicle_id}/data/latest")
async def get_latest_vehicle_data(
    vehicle_id: str,
    user: str = Depends(verify_token)
):
    """获取车辆最新数据
    
    参数:
        vehicle_id: 车辆标识
        
    返回:
        dict: 车辆最新数据
    """
    try:
        db_conn = PostgreSQLConnection(PostgreSQLConfig.from_env())
        
        query = """
            SELECT * FROM latest_vehicle_data
            WHERE vehicle_id = %s
        """
        result = db_conn.execute_query(query, (vehicle_id,))
        db_conn.close()
        
        if not result:
            raise HTTPException(status_code=404, detail="车辆数据不存在")
        
        # execute_query 返回字典列表，直接使用字典键访问
        row = result[0]
        data = {
            "vehicle_id": row["vehicle_id"],
            "timestamp": row["timestamp"].isoformat() if row["timestamp"] else None,
            "received_at": row["received_at"].isoformat() if row["received_at"] else None,
            "state": row["state"],
            "gps": {
                "latitude": float(row["gps_latitude"]) if row["gps_latitude"] else None,
                "longitude": float(row["gps_longitude"]) if row["gps_longitude"] else None,
                "altitude": float(row["gps_altitude"]) if row["gps_altitude"] else None,
                "heading": float(row["gps_heading"]) if row["gps_heading"] else None,
                "satellites": row["gps_satellites"]
            },
            "motion": {
                "speed": float(row["motion_speed"]) if row["motion_speed"] else None,
                "acceleration": float(row["motion_acceleration"]) if row["motion_acceleration"] else None,
                "odometer": row["motion_odometer"],
                "trip_distance": float(row["motion_trip_distance"]) if row["motion_trip_distance"] else None
            },
            "fuel": {
                "level": float(row["fuel_level"]) if row["fuel_level"] else None,
                "consumption": float(row["fuel_consumption"]) if row["fuel_consumption"] else None,
                "range": float(row["fuel_range"]) if row["fuel_range"] else None
            },
            "temperature": {
                "engine": float(row["temp_engine"]) if row["temp_engine"] else None,
                "cabin": float(row["temp_cabin"]) if row["temp_cabin"] else None,
                "outside": float(row["temp_outside"]) if row["temp_outside"] else None
            },
            "battery": {
                "voltage": float(row["battery_voltage"]) if row["battery_voltage"] else None,
                "current": float(row["battery_current"]) if row["battery_current"] else None
            },
            "diagnostics": {
                "engine_load": float(row["diag_engine_load"]) if row["diag_engine_load"] else None,
                "rpm": row["diag_rpm"],
                "throttle_position": float(row["diag_throttle_position"]) if row["diag_throttle_position"] else None
            }
        }
        
        return data
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"获取车辆最新数据失败: {str(e)}"
        )


@router.get("/{vehicle_id}/data/history")
async def get_vehicle_data_history(
    vehicle_id: str,
    start_time: Optional[str] = None,
    end_time: Optional[str] = None,
    limit: int = Query(100, ge=1, le=1000),
    user: str = Depends(verify_token)
):
    """获取车辆历史数据
    
    参数:
        vehicle_id: 车辆标识
        start_time: 开始时间（ISO格式）
        end_time: 结束时间（ISO格式）
        limit: 返回记录数限制
        
    返回:
        dict: 包含历史数据列表和总数
    """
    try:
        db_conn = PostgreSQLConnection(PostgreSQLConfig.from_env())
        
        query = """
            SELECT 
                vehicle_id, timestamp, state,
                gps_latitude, gps_longitude, gps_altitude, gps_heading,
                motion_speed, motion_acceleration,
                fuel_level, temp_engine, temp_cabin,
                battery_voltage, diag_rpm
            FROM vehicle_data
            WHERE vehicle_id = %s
            AND (%s IS NULL OR timestamp >= %s)
            AND (%s IS NULL OR timestamp <= %s)
            ORDER BY timestamp DESC
            LIMIT %s
        """
        params = (vehicle_id, start_time, start_time, end_time, end_time, limit)
        result = db_conn.execute_query(query, params)
        db_conn.close()
        
        # execute_query 返回字典列表
        data_list = []
        for row in result:
            data_list.append({
                "vehicle_id": row["vehicle_id"],
                "timestamp": row["timestamp"].isoformat() if row["timestamp"] else None,
                "state": row["state"],
                "gps_latitude": float(row["gps_latitude"]) if row["gps_latitude"] else None,
                "gps_longitude": float(row["gps_longitude"]) if row["gps_longitude"] else None,
                "gps_altitude": float(row["gps_altitude"]) if row["gps_altitude"] else None,
                "gps_heading": float(row["gps_heading"]) if row["gps_heading"] else None,
                "motion_speed": float(row["motion_speed"]) if row["motion_speed"] else None,
                "motion_acceleration": float(row["motion_acceleration"]) if row["motion_acceleration"] else None,
                "fuel_level": float(row["fuel_level"]) if row["fuel_level"] else None,
                "temp_engine": float(row["temp_engine"]) if row["temp_engine"] else None,
                "temp_cabin": float(row["temp_cabin"]) if row["temp_cabin"] else None,
                "battery_voltage": float(row["battery_voltage"]) if row["battery_voltage"] else None,
                "diag_rpm": row["diag_rpm"]
            })
        
        return {"data": data_list, "total": len(data_list)}
        
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"获取车辆历史数据失败: {str(e)}"
        )


@router.get("/{vehicle_id}/data/track")
async def get_vehicle_track(
    vehicle_id: str,
    start_time: Optional[str] = None,
    end_time: Optional[str] = None,
    limit: int = Query(500, ge=1, le=2000),
    user: str = Depends(verify_token)
):
    """获取车辆GPS轨迹
    
    参数:
        vehicle_id: 车辆标识
        start_time: 开始时间（ISO格式）
        end_time: 结束时间（ISO格式）
        limit: 返回记录数限制
        
    返回:
        dict: 包含GPS轨迹点列表
    """
    try:
        db_conn = PostgreSQLConnection(PostgreSQLConfig.from_env())
        
        query = """
            SELECT 
                timestamp,
                gps_latitude, gps_longitude, gps_altitude, gps_heading,
                motion_speed
            FROM vehicle_data
            WHERE vehicle_id = %s
            AND gps_latitude IS NOT NULL
            AND gps_longitude IS NOT NULL
            AND (%s IS NULL OR timestamp >= %s)
            AND (%s IS NULL OR timestamp <= %s)
            ORDER BY timestamp ASC
            LIMIT %s
        """
        params = (vehicle_id, start_time, start_time, end_time, end_time, limit)
        result = db_conn.execute_query(query, params)
        db_conn.close()
        
        # execute_query 返回字典列表
        track_points = []
        for row in result:
            track_points.append({
                "timestamp": row["timestamp"].isoformat() if row["timestamp"] else None,
                "latitude": float(row["gps_latitude"]) if row["gps_latitude"] else None,
                "longitude": float(row["gps_longitude"]) if row["gps_longitude"] else None,
                "altitude": float(row["gps_altitude"]) if row["gps_altitude"] else None,
                "heading": float(row["gps_heading"]) if row["gps_heading"] else None,
                "speed": float(row["motion_speed"]) if row["motion_speed"] else None
            })
        
        return {"track": track_points, "total": len(track_points)}
        
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"获取车辆轨迹失败: {str(e)}"
        )
