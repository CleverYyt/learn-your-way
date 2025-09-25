import hashlib
import json
import time
import requests


def get_json_data(markdown):
    url = "http://sea-dify.chengjiukehu.com/v1/workflows/run"
    headers = {
        "Authorization": "Bearer app-9RXicDUqcFSUSVUjzP6W1sql",
        "Content-Type": "application/json"
    }
    
    data = {
        "inputs": {
            "user_content": markdown
        },
        "response_mode": "blocking",
        "user": "yyt"
    }
    print("调用dify开始")
    response = requests.post(url, headers=headers, data=json.dumps(data))
    print(f"dify 调用返回: {response.json()}")
    return response.json().get('data').get('outputs').get('integrated')


def generate_signature(app_id, secret, nonce=None, timestamp=None):
    """
    生成符合校验的 HTTP 请求头部
    :param app_id: 应用 ID
    :param secret: 应用密钥
    :param nonce: 随机字符串（如果为空则自动生成）
    :param timestamp: 时间戳（如果为空则使用当前时间戳）
    :return: 生成的 Header 字典
    """
    # 自动生成随机 nonce 和时间戳
    if nonce is None:
        nonce = "random12345"  # 可以根据需求改为动态生成
    if timestamp is None:
        timestamp = str(int(time.time()))  # 当前 Unix 时间戳

    # 拼接字符串
    raw_str = timestamp + nonce + app_id + secret

    # 计算 MD5 签名并转为小写
    signature = hashlib.md5(raw_str.encode()).hexdigest().lower()

    # 构造 Header
    headers = {
        "X-Tal-Nonce": nonce,
        "X-Tal-Timestamp": timestamp,
        "X-Tal-Sign": signature,
        "appId": app_id
    }

    return headers





if __name__ == "__main__":
    with open("/Users/tal/Desktop/learn you way/uploads/markdown/a295f644-d239-4545-909e-455d90c91d66_learnyourway_demo3.md", "r") as f:
        markdown = f.read()
    print(markdown)
    json_data = get_json_data(markdown)

    print(json_data)
