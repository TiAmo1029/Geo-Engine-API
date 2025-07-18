# Geo-Engine: 一个高性能GIS空间分析微服务

本项目是一个基于 **Python**, **FastAPI** 和 **PostGIS** 构建的高性能GIS空间分析微服务。旨在将常用的地理空间分析功能封装成一套标准化的RESTful API，实现“分析即服务 (Analysis as a Service)”。

### ✨ 项目核心功能

*   **高性能API服务:** 基于 **FastAPI** 的**异步**特性构建，具备高并发处理能力。
*   **自动化交互式文档:** 利用FastAPI的特性，自动生成并托管 **Swagger UI** 和 ReDoc 交互式API文档。
*   **数据库驱动的分析:** 与 **PostgreSQL/PostGIS** 深度集成，利用强大的空间SQL函数（如`ST_Intersects`, `ST_Buffer`）进行高性能的后端计算。
*   **核心分析API:**
    *   `GET /api/geocode`: 封装第三方地图服务，提供稳定、统一的**地理编码**服务。
    *   `POST /api/analysis/buffer`: 为输入的GeoJSON点要素，在后端实时创建**缓冲区**并返回结果。
    *   `POST /api/analysis/intersecting-cities`: 实现**空间叠加分析**，可根据用户提供的任意多边形，查询出所有与之相交的城市要素。
*   **容器化部署:** 项目已完全**Docker化**，提供了`Dockerfile`，确保环境一致性，可实现一键构建与部署。

### 🚀 技术栈

*   **Web框架:** FastAPI, Uvicorn
*   **数据库:** PostgreSQL + PostGIS
*   **GIS核心库:** Psycopg2 (用于数据库连接), Pydantic (用于数据建模)
*   **异步任务 (规划中):** Celery, Redis
*   **部署:** Docker

### 🔧 如何在本地运行

**前提条件:**
*   Python 3.10+
*   PostgreSQL + PostGIS 已安装并正在运行。
*   Docker Desktop 已安装并正在运行。

**步骤:**

1.  **克隆本仓库:**
    ```bash
    git clone https://github.com/你的用户名/geo-engine-api.git
    cd geo-engine-api
    ```

2.  **创建并激活Python虚拟环境:**
    ```bash
    python -m venv .venv
    # Windows
    .\.venv\Scripts\activate
    # macOS / Linux
    # source .venv/bin/activate
    ```

3.  **安装Python依赖:**
    ```bash
    pip install -r requirements.txt
    ```
    
4.  **配置数据库与API Key:**
    *   将 `config.ini.template` 文件复制为 `config.ini`。
    *   在 `config.ini` 文件中，填入你自己的PostgreSQL数据库连接信息和高德地图API Key。

5.  **构建Docker镜像:**
    ```bash
    docker build -t geo-engine-app .
    ```

6.  **运行Docker容器:**
    ```bash
    # 该命令会将容器的8000端口映射到你电脑的8001端口
    docker run -d -p 8001:8000 --name my-geo-engine-container geo-engine-app
    ```

7.  **访问API服务:**
    *   **API主页:** `http://127.0.0.1:8001`
    *   **交互式API文档:** `http://127.0.0.1:8001/docs`
