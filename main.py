from fastapi import FastAPI, HTTPException # 导入HTTPException，用于处理错误
from typing import Optional,List
from pydantic import BaseModel
import json # 导入json库，用于处理geometry字符串

# 1. 从我们的services包中， 导入GeiAPICliect类和它的配置
import sys
import os
# --- 核心修复：将项目根目录添加到sys.path ---
# 1. 获取当前文件(main.py)的绝对路径
#    __file__ 是一个内置变量，代表当前脚本的文件名
current_file_path = os.path.abspath(__file__)

# 2. 从文件路径中，获取它所在的目录 (也就是geo-engine/这个目录)
current_dir = os.path.dirname(current_file_path)
# 3. 再从当前目录，获取它的父目录 (也就是Python_Projects/这个目录)
#    我们的目标是把项目的根目录(geo-engine)加进去，所以这一步可能不是必须的，
#    但更健壮的做法是，确保我们的项目根目录在sys.path中
#    最简单、最可靠的方法是直接把当前文件的目录（也就是项目根目录）加进去
#    os.path.dirname() 获取一个路径的目录部分
project_root = os.path.dirname(os.path.abspath(__file__))
# 将项目根目录添加到Python解释器的搜索路径列表的最前面
sys.path.insert(0, project_root)

from services.amap_client import GeoAPIClient, GAODE_API_KEY
from db import get_db_cursor
from models import BufferRequest,  GeoJSONFeature_Polygon,OverlayRequest, Feature_Polygon, FeatureCollection_Polygon
# 1. 从我们的tasks模块导入celery_app和定义的任务
from tasks import celery_app, slow_gis_analysis

app = FastAPI()

# --- 2. 创建一个GeoAPIClient的全局实例 ---
#    我们只需要在应用启动时创建一个实例，就可以在所有API中复用它
#    这比在每个请求里都new一个新对象要高效得多
amap_client = GeoAPIClient(key=GAODE_API_KEY)


# --- 根路径，保持不变 ---
@app.get("/")
def read_root():
    return {"message": "Welcome to Geo-Engine API!"}


# --- 3. 创建我们的地理编码API ---
@app.get("/api/geocode")
def get_geocode(address: str):
    """
    接收一个地址，返回其地理编码结果。
    """
    # 检查地址参数是否为空
    if not address:
        # 4. 使用HTTPException来返回一个标准的客户端错误响应
        raise HTTPException(status_code=400, detail="Address parameter cannot be empty.")

    # 5. 调用我们客户端实例的geocode方法
    result = amap_client.geocode(address)

    # 6. 处理可能出现的查询失败情况
    if not result:
        raise HTTPException(status_code=404, detail=f"Could not find geocode for address: {address}")
    
    # 7. 如果一切正常，直接返回结果
    return result

# --- (可选) 我们可以把逆地理编码也加上 ---
@app.get("/api/reverse-geocode")
def get_reverse_geocode(lon: float, lat: float):
    """
    接收经纬度，返回其逆地理编码结果。
    """
    location_tuple = (lon, lat)
    result = amap_client.reverse_geocode(location_tuple)
    
    if not result:
        raise HTTPException(status_code=404, detail=f"Could not find reverse geocode for location: {lon},{lat}")
        
    return result

# --- 新增：查询省份列表的API ---
@app.get("/api/provinces", response_model=List[dict]) # 2.使用response_model来定义相应的数据结构
def get_provinces(limit: int = 10):
    """
    从PostGIS数据库中查询省份列表。
    """

    # 3. 使用 with 语句来自动管理游标的获取和释放
    with get_db_cursor() as cur:
        # 保证表名和列名是正确的
        sql_query = """
            SELECT
                "name" as name,
                ST_AsGeoJSON(geom) as geometry -- 将几何转换为GeoJSON字符串
            FROM public.provinces_of_China
            LIMIT %s;
        """

        cur.execute(sql_query,(limit,))
        rows = cur.fetchall()

        # 如果没有查询到结果，可以返回一个清晰的错误
        if not rows:
            raise HTTPException(status_code=404,details = "No provinces found.")
        
        # 4. 将查询结果（元组列表）转换为字典列表，以便FastAPI序列化
        results = []
        # 获取列名，以便和值对应
        colnames = [desc[0] for desc in cur.description]
        for row in rows:
            results.append(dict(zip(colnames,row)))

        return results
    
# --- 新增：缓冲区分析API ---
@app.post("/api/analysis/buffer", response_model=GeoJSONFeature_Polygon) # 2. 定义响应模型
def create_buffer(request: BufferRequest): # 3. 请求体验证
    """
    为输入的GeoJSON点要素创建一个缓冲区
    """
    # 4. 从请求中提取需要的数据
    point_feature = request.geojson_feature
    radius_km = request.radius_km

    # 检查输入的几何类型是否为点
    if point_feature.geometry. type!= "Point":
        raise HTTPException(status_code=400,detail="Input geometry must be a point!")
    
    geometry_dict = point_feature.geometry.dict()
    # 将输入的GeoJSON几何对象转换为WKT文本，以便传入SQL
    # 我们需要先用json.dumps把Python字典变回JSON字符串
    input_geom_geojson_str = json.dumps(geometry_dict)

    # 5. 编写空间SQL，让PostGIS完成所有计算！
    #    ST_GeoFromGeoJSON：从GeoJSON字符串中创建几何对象
    #    ST_Transform：转换坐标系（因为ST_Buffer的单位取决于坐标系）
    #    ST_Buffer：创建缓冲区
    #    ST_AsGeoJSON；将计算结果转换回GeoJSON字符串
    sql_query = """
        SELECT ST_AsGeoJSON(
            ST_Transform(
                ST_Buffer(
                    ST_Transform(ST_GeomFromGeoJSON(%s::json), 3857), -- 1. 转换米制坐标系（Web墨卡托）
                    %s * 1000  -- 2. 创建缓冲区（米）
                ),
                4326  -- 3. 将结果转回 WGS84
            )
        ) AS buffer_geojson;
    """

    # 6. 执行SQL并获取结果
    with get_db_cursor() as cur:
        cur.execute(sql_query, (input_geom_geojson_str, radius_km))
        result_row = cur.fetchone()

        if not result_row or not result_row[0]:
            raise HTTPException(status_code=500, detail="Database failed to compute buffer.")
        
        # 7. 构造并返回最终的GeoJSON Feature
        buffer_geometry_str = result_row[0]
        buffer_geometry_dict = json.loads(buffer_geometry_str) # 将GeoJSON字符串变为Python字典


        return GeoJSONFeature_Polygon(
            geometry=buffer_geometry_dict,
            properties={"original_radius_km" : radius_km}
        ) 
    
# --- 新增：空间叠加分析API ---
@app.post(
    "/api/analysis/intersecting-cities", 
    response_model=FeatureCollection_Polygon # 2. 响应模型是精确的FeatureCollection
)
def get_intersecting_cities(request: OverlayRequest): # 3. 请求体验证使用OverlayRequest
    """
    根据输入的多边形，查询与之相交的所有城市面。
    """
    # 4. FastAPI已经帮你完成了所有输入数据的校验！
    #    我们能确定request.polygon_feature一定是个合格的面要素。
    input_polygon_feature = request.polygon_feature
    
    # 将输入的Pydantic模型转换回字典，再转成JSON字符串，以便传入SQL
    input_geom_geojson = json.dumps(input_polygon_feature.geometry.dict())

    # 5. 编写核心的空间SQL查询
    sql_query = """
        SELECT 
            "name" as city_name,
            ST_AsGeoJSON(geom) as geometry_str
        FROM 
            public.cities_of_china -- !!! 你的城市面数据表 !!!
        WHERE 
            ST_Intersects(
                geom,
                ST_SetSRID(ST_GeomFromGeoJSON(%s), 4326)
            );
    """

    # 6. 执行SQL并获取所有匹配的结果
    with get_db_cursor() as cur:
        cur.execute(sql_query, (input_geom_geojson,))
        rows = cur.fetchall()

        if not rows:
            return FeatureCollection_Polygon(features=[]) # 返回一个空的FeatureCollection

        # 7. 将查询到的多行结果，打包成一个Feature_Polygon对象的列表
        features_list = []
        for row in rows:
            city_name, geometry_str = row
            
            # 将geometry字符串转换回字典对象
            geometry_dict = json.loads(geometry_str)
            
            # 构建一个标准的Feature_Polygon实例
            feature = Feature_Polygon(
                geometry=geometry_dict,
                properties={"name": city_name}
            )
            features_list.append(feature)
            
        # 构造最终的FeatureCollection_Polygon实例并返回
        return FeatureCollection_Polygon(features=features_list)
    
# --- 最终的、经过验证的、可靠的空间查询API ---
# 我们把接口路径设计得更符合RESTful风格
@app.get("/api/provinces/{province_name}/cities", response_model=FeatureCollection_Polygon)
def get_cities_in_province(province_name: str):
    """
    根据省份中文名，查询该省份内的所有城市。
    """
    # 编写一个双表连接的SQL，在数据库内部完成所有事情
    # !!! 请确保你的表名和列名与这里的一致 !!!
    sql_query = """
        SELECT 
            c."name" as city_name,
            ST_AsGeoJSON(c.geom) as geometry_str
        FROM 
            public.cities_of_china AS c
        JOIN 
            public.provinces_of_china AS p ON ST_Intersects(p.geom, c.geom)
        WHERE 
            p."name" = %s;
    """
    
    with get_db_cursor() as cur:
        # 将省份名作为参数安全地传递
        cur.execute(sql_query, (province_name,))
        rows = cur.fetchall()

        if not rows:
            # 如果没有找到，返回一个空的FeatureCollection
            return FeatureCollection_Polygon(features=[])

        # 将查询到的多行结果，打包成一个Feature_Polygon对象的列表
        features_list = []
        for row in rows:
            city_name, geometry_str = row
            geometry_dict = json.loads(geometry_str)
            
            feature = Feature_Polygon(
                geometry=geometry_dict,
                properties={"name": city_name}
            )
            features_list.append(feature)
            
        return FeatureCollection_Polygon(features=features_list)
    
class TaskRequest(BaseModel):
    input_data: str

# --- 新增：提交异步任务的API ---
@app.post("/api/analysis/slow-task", status_code=202) # 202 Accepted 表示请求已被接受处理
def submit_slow_task(request: TaskRequest):
    # 2. 调用任务的.delay()方法，把任务扔到队列里
    #    .delay() 是 .apply_async() 的快捷方式，它不会阻塞
    task = slow_gis_analysis.delay(request.input_data)
    
    # 3. 立刻返回一个任务ID
    return {"message": "任务已成功提交到后台处理。", "task_id": task.id}

# --- 新增：查询任务状态的API ---
@app.get("/api/tasks/{task_id}")
def get_task_status(task_id: str):
    # 4. 使用任务ID，从backend(Redis)中获取任务的结果
    task_result = celery_app.AsyncResult(task_id)

    if task_result.ready():
        # 如果任务已完成
        if task_result.successful():
            return {"status": "SUCCESS", "result": task_result.get()}
        else:
            return {"status": "FAILURE", "error": str(task_result.info)} # 返回错误信息
    else:
        # 如果任务还在进行中
        return {"status": "PENDING"}