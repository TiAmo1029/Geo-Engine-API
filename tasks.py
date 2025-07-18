import time
from celery import Celery

# 1. 配置Celery
#    第一个参数是项目名，broker是消息队列的地址，backend是存储任务结果的地址
#    我们都使用本地的Redis
celery_app = Celery(
    'tasks',
    broker='redis://localhost:6379/0',
    backend='redis://localhost:6379/0'
)

# 2. 定义一个Celery任务
#    @celery_app.task 装饰器把它变成了一个可以被Celery工人执行的任务
@celery_app.task
def slow_gis_analysis(input_data: str):
    """
    一个模拟耗时的GIS分析任务。
    """
    print(f"开始处理任务，输入数据是: {input_data}")
    # 假装这个任务需要15秒
    time.sleep(15) 
    result = f"分析完成！处理了 '{input_data}'，结果是一张处理好的地图。"
    print(result)
    return result