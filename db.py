import psycopg2
from psycopg2.pool import SimpleConnectionPool

from contextlib import contextmanager
import os

# 从我们的配置文件中读取数据库信息
# （我们稍后会把DB_CONFIG也移到config.ini中）
DB_CONFIG = {
    "host": "localhost",
    "port": "5432",
    "user": "postgres",
    "password": "123456",
    "dbname": "gisdb"
}

# --- 1. 创建一个全局的数据库连接池 ---
#        应用启动时，这个代码块就会执行一次，创建好连接池
try:
    # minconn =1, maxconn = 10 表示池中至少有1个，最多有10个连接
    connection_pool = SimpleConnectionPool(minconn =1, maxconn = 10, **DB_CONFIG)
    print("数据库连接池创建成功！")
except psycopg2.Error as e:
    print(f"创建数据库连接池失败:{e}")
    connection_pool = None

# --- 2. 创建一个“上下文管理器” 来获取和释放连接 ---
#     这是一个非常优雅和专业的Python技巧
@contextmanager
def get_db_connection():
    """
    一个用于安全地从连接池获取和归还连接的上下文管理器。
    """
    if connection_pool is None:
        raise Exception("数据库连接池未初始化！")
    
    conn = None
    try:
        # 从池中获取一个连接
        conn = connection_pool.getconn()
        # 将连接对象“产出（yield）”给调用者使用
        yield conn
    finally:
        # 无论调用者那边发生什么（成功或异常），
        # 最终都会回到这里，把连接归还到池中
        if conn:
            connection_pool.putconn(conn)


@contextmanager
def get_db_cursor(commit=False):
    """
    一个更方便的上下文管理器，直接获取游标。
    """
    with get_db_connection() as conn:
        cursor = conn.cursor()
        try:
            yield cursor
            if commit:
                conn.commit() # 如果需要，提交事务
        finally:
            cursor.close()