from pydantic import BaseModel
from typing import List, Tuple, Optional, Dict, Any, Union

# --- Point 模型保持不变 ---
class PointGeometry(BaseModel):
    type: str = "Point"
    coordinates: Tuple[float, float]

# --- 新增：为 Polygon 模型创建一个精确的定义 ---
# GeoJSON的多边形坐标是一个三层嵌套的列表 List[List[List[float]]]
# [[ [x1,y1], [x2,y2], ... ]] -> 一个环
# [ [[...]], [[...]] ] -> 带洞的多边形
class PolygonGeometry(BaseModel):
    type: str = "Polygon"
    coordinates: List[List[List[float]]]

class MultiPolygonGeometry(BaseModel):
    type: str = "MultiPolygon"
    # MultiPolygon是四层嵌套列表
    coordinates: List[List[List[List[float]]]]


# --- 修改：让 GeoJSONFeature 能接受不同类型的几何 ---
#   (为了简单，我们先创建一个专门用于返回结果的模型)
class GeoJSONFeature_Point(BaseModel):
    type: str = "Feature"
    geometry: PointGeometry
    properties: Optional[Dict[str, Any]] = None
    
class GeoJSONFeature_Polygon(BaseModel):
    type: str = "Feature"
    geometry: PolygonGeometry
    properties: Optional[Dict[str, Any]] = None

class Feature_Point(BaseModel):
    type: str = "Feature"
    geometry: PointGeometry
    properties: Optional[Dict[str, Any]] = None

class Feature_Polygon(BaseModel):
    type: str = "Feature"
    geometry: Union[PolygonGeometry, MultiPolygonGeometry] # 城市面可能是Polygon或MultiPolygon
    properties: Optional[Dict[str, Any]] = None

# --- 修改：BufferRequest 依然接收点要素 ---
class BufferRequest(BaseModel):
    geojson_feature: GeoJSONFeature_Point # 明确要求输入是点
    radius_km: float

# 叠加分析请求模型，输入必须是面要素
class OverlayRequest(BaseModel):
    polygon_feature: Feature_Polygon

# --- 响应体模型 ---
# FeatureCollection响应模型，features列表里是面要素
class FeatureCollection_Polygon(BaseModel):
    type: str = "FeatureCollection"
    features: List[Feature_Polygon]