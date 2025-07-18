import requests
import configparser
from typing import Dict,Optional, Tuple # 更精准的类型提示

# --- 1. 读取配置文件 ---
config = configparser.ConfigParser()
config.read('config.ini')

# 从配置文件中获取API Key，如果找不到会报错，更安全
try:
    GAODE_API_KEY = config['amap']['key']
except KeyError:
    print("错误：无法在 config.ini 文件中找到[amap]-> key 配置！")
    exit() # 直接退出程序


class GeoAPIClient:
    """
    一个面向对象的高德地图 Web服务 API客户端
    """

    GEOCODE_URL = "https://restapi.amap.com/v3/geocode/geo"
    REVERSE_GEOCODE_URL = "https://restapi.amap.com/v3/geocode/regeo"

    def __init__(self, key: str, timeout: int = 5):
        """
        初始化客户端。
        :param key: 高德API Key。
        :param timeout: 请求超时时间，单位秒。
        """
        self.key = key
        self.timeout = timeout
        # 在内部创建一个Session对象，所有请求都通过它发起
        self.session = requests.session()
        print("GeoAPIClient 初始化成功！")

    def _make_request(self, url: str, params: dict)-> Optional[dict]:
        """
        一个内部使用的、通用的请求方法，封装了请求和异常处理逻辑。
        方法名前的下划线’_‘是一种约定，表示这是一个”内部“方法，不建议外部直接调用。
        :param url: 高德地图 Web 服务提供 url
        :param params: 请求参数
        :return: json()
        """
        # 将API Key自动加入到每个请求的参数中
        params['key'] = self.key

        try:
            response = self.session.get(url, params=params, timeout=self.timeout)
            response.raise_for_status()
            return response.json()
        except requests.exceptions.RequestException as e:
            print(f"网络请求错误：{e}")
            return None

    def geocode(self, address: str)-> Optional[Dict[str,str]]:
        """
        地理编码：将地址转换为坐标。
        """
        params = {'address': address}
        result = self._make_request(self.GEOCODE_URL, params)

        if result and result.get('status') == '1' and int(result.get('count', 0)) > 0:
            geocode_info = result['geocodes'][0]
            return {
                'formatted_address': geocode_info.get('formatted_address'),
                'location': geocode_info.get('location')
            }

        else:
            print(f"地理编码失败：{result.get('info','未知错误') if result else '网络错误'}")
            return None

    def reverse_geocode(self, location: Tuple[float, float]) -> Optional[Dict[str, str]]:
        """
        逆地理编码：将坐标转换为地址。
        注意：参数类型改成了元组，更符合坐标的本质
        """
        # 将坐标元组转换为API需要的字符串格式
        location_str = f"{location[0]},{location[1]}"

        # 我们可以打印出来验证一下
        print(f"DEBUG: 发送给高德API的location参数是: '{location_str}'")

        params = {'location': location_str}
        result = self._make_request(self.REVERSE_GEOCODE_URL, params)

        if result and result.get('status') == '1':
            # 先安全地获取 regeocode 字典
            regeocode_info = result.get('regeocode', {})

            # 核心修改在这里！
            # 1. 安全地获取 formatted_address 的值
            address = regeocode_info.get('formatted_address')

            # 2. 检查 address 是否是一个非空的字符串
            #    `if address and isinstance(address, str):` 是一个非常严谨的写法
            #    `if address:` 是一个更简洁的写法，因为 None, 空字符串'', 空列表[] 在if判断中都为False
            if address and isinstance(address, str):
                # 只有当 address 是一个有效的、非空的字符串时，才返回结果
                return {
                    'formatted_address': address
                }
            else:
                # 如果 address 是 None, 空字符串, 或者像你遇到的空列表[]，我们都认为没有找到有效地址
                print("逆地理编码业务成功，但未返回有效的地址文本。")
                return None  # 返回 None，清晰地表示失败或无结果
        else:
            print(f"逆地理编码失败: {result.get('info', '未知错误') if result else '网络错误'}")
            return None

# --- 测试代码块 ---
if __name__ == "__main__":
    # 1. 实例化我们的客户端， 传入从配置文件读取的Key
    client = GeoAPIClient(key=GAODE_API_KEY)

    # 2. 调用实例的方法
    address = "北京市海淀区北京大学"
    print(f"\n---查询地址：‘{address}’ ---")
    location_data = client.geocode(address)
    if location_data:
        print(f" 查询结果：{location_data}")

        # 3. 链式调用
        # 先获取坐标字符串， 再解析它，然后传给下一个函数
        lon_str, lat_str = location_data['location'].split(',')
        coords_tuple = (float(lon_str), float(lat_str))

        print(f"\n--- 基于以上坐标进行逆地理编码查询 ---")
        address_data = client.reverse_geocode(coords_tuple)
        if address_data:
            print(f" 查询结果：{address_data}")

        else:
            # 如果还是失败，就打印我们自定义的错误信息
            print("  逆地理编码查询失败或无有效结果。")


