import requests
import time
import os
import zipfile
import io
import re

# 配置信息
token = "eyJ0eXBlIjoiSldUIiwiYWxnIjoiSFM1MTIifQ.eyJqdGkiOiI1MDA1OTUxOSIsInJvbCI6IlJPTEVfUkVHSVNURVIiLCJpc3MiOiJPcGVuWExhYiIsImlhdCI6MTc1ODQ1NjQ0MywiY2xpZW50SWQiOiJsa3pkeDU3bnZ5MjJqa3BxOXgydyIsInBob25lIjoiIiwib3BlbklkIjpudWxsLCJ1dWlkIjoiYjIyN2VlY2UtMGY4ZS00MWY4LWIzMmItY2NkNzgzZmJmYmUyIiwiZW1haWwiOiIiLCJleHAiOjE3NTk2NjYwNDN9.g4VdcjE4Q1yX8mOyOJ-0b7pWdKciUaB-a3UA26t9n_yTYJNQSLIbhp-EWivh4kvIXUD5veUvDzlbKkLIrTkLmA"
headers = {
    "Content-Type": "application/json",
    "Authorization": f"Bearer {token}"
}


def create_extract_task(pdf_url):
    """创建提取任务"""
    create_url = "https://mineru.net/api/v4/extract/task"
    task_data = {
        "url": pdf_url,
        "is_ocr": True,
        "enable_formula": False,
    }
    
    try:
        response = requests.post(create_url, headers=headers, json=task_data)
        response.raise_for_status()  # 检查请求是否成功
        result = response.json()
        
        print(f"创建任务响应: {result}")
        
        if result.get('code') == 0 and 'data' in result:
            print(f"任务创建成功，任务ID: {result['data']['task_id']}")
            return result['data']['task_id']
        else:
            print(f"任务创建失败: {result}")
            return None
    except Exception as e:
        print(f"创建任务时发生错误: {str(e)}")
        return None

def check_task_status(task_id):
    """检查任务状态，直到任务完成"""
    check_url = f"https://mineru.net/api/v4/extract/task/{task_id}"
    max_retries = 60  # 最多检查60次
    retry_interval = 5  # 每5秒检查一次
    
    for i in range(max_retries):
        try:
            response = requests.get(check_url, headers=headers)
            response.raise_for_status()
            result = response.json()
            
            print(f"检查任务状态响应 (第{i+1}次): {result}")
            
            if result.get('code') == 0 and 'data' in result:
                task_state = result['data'].get('state')
                print(f"任务状态: {task_state}, 第 {i+1}/{max_retries} 次检查")
                
                if task_state == 'completed' or task_state == 'done':
                    print("任务已完成")
                    return result['data']
                elif task_state == 'failed':
                    print(f"任务失败: {result['data'].get('err_msg', '未知错误')}")
                    return None
            else:
                print(f"获取任务状态失败: {result}")
        except Exception as e:
            print(f"检查任务状态时发生错误: {str(e)}")
        
        # 如果不是最后一次尝试，则等待
        if i < max_retries - 1:
            time.sleep(retry_interval)
    
    print(f"任务超时，已达到最大重试次数 ({max_retries})")
    return None

def download_and_extract_zip(zip_url, output_dir='extracted_files'):
    """下载并解压ZIP文件"""
    try:
        print(f"开始下载ZIP文件: {zip_url}")
        response = requests.get(zip_url, stream=True)
        response.raise_for_status()
        
        # 创建输出目录
        os.makedirs(output_dir, exist_ok=True)
        
        # 解压ZIP文件
        with zipfile.ZipFile(io.BytesIO(response.content)) as zip_ref:
            zip_ref.extractall(output_dir)
            print(f"ZIP文件已解压到: {output_dir}")
            
            # 查找Markdown文件
            markdown_path = None
            for file in zip_ref.namelist():
                if file.lower().endswith('.md'):
                    markdown_path = os.path.join(output_dir, file)
                    print(f"找到Markdown文件: {markdown_path}")
                    with open(markdown_path, 'r', encoding='utf-8') as f:
                        return f.read(), markdown_path, output_dir
        
        print("未在ZIP文件中找到Markdown文件")
        return "", None, None
    except Exception as e:
        print(f"下载或解压ZIP文件时发生错误: {str(e)}")
        return "", None, None

def upload_to_blob(file_path, file_name):
    """上传图片到OSS并返回公网地址"""
    print("上传blob开始")
    url = 'http://10.224.129.212:8080/inner/public/blob/form-data/upload'
    headers = {'Content-Type': 'multipart/form-data'}
    
    # 构建查询参数
    params = {
        'containerName': "601public101",
        'targetPath': "/learnyourway",
        'fileName': f"/upload/pdf/{file_name}"
    }
    
    try:
        # 打开文件
        with open(file_path, 'rb') as f:
            # 构建multipart/form-data请求
            files = {'file': (file_name, f, 'application/octet-stream')}
            
            # 发送请求
            response = requests.post(
                url,
                params=params,
                files=files
            )
            print(f"上传响应: {response.text}")
            
            # 检查响应状态
            if response.status_code == 200:
                blob_url = response.json()['data']['url']
                print(f"上传blob完成: {blob_url}")
                return blob_url
            else:
                print(f"上传失败，状态码: {response.status_code}")
                return None
    except Exception as e:
        print(f"上传文件时发生错误: {str(e)}")
        return None

def process_images_and_update_markdown(markdown_content, markdown_path, output_dir):
    """处理图片上传并更新Markdown文件中的图片路径"""
    try:
        # 获取images文件夹路径
        images_dir = os.path.join(output_dir, 'images')
        print(f"查找images文件夹: {images_dir}")
        
        if not os.path.exists(images_dir):
            print("images文件夹不存在，跳过图片处理")
            return markdown_content
        
        # 创建图片映射字典 {本地图片名: 公网地址}
        image_mapping = {}
        
        # 遍历images文件夹中的所有图片文件
        for file_name in os.listdir(images_dir):
            if file_name.lower().endswith(('.jpg', '.jpeg', '.png', '.gif', '.bmp')):
                file_path = os.path.join(images_dir, file_name)
                print(f"处理图片: {file_path}")
                
                # 上传图片到OSS
                blob_url = upload_to_blob(file_path, file_name)
                if blob_url:
                    image_mapping[file_name] = blob_url
        
        # 替换Markdown文件中的图片路径
        updated_content = markdown_content
        for file_name, blob_url in image_mapping.items():
            # 查找类似 ![](images/文件名.jpg) 的模式并替换
            pattern = r'\!\[\]\(images/' + re.escape(file_name) + r'\)' 
            updated_content = re.sub(pattern, f'![]({blob_url})', updated_content)
            print(f"已替换图片路径: images/{file_name} -> {blob_url}")
        
        return updated_content
    except Exception as e:
        print(f"处理图片和更新Markdown时发生错误: {str(e)}")
        return markdown_content

def save_markdown_result(data, output_file='output.md'):
    """保存Markdown结果到文件"""
    try:
        markdown_content = ""
        markdown_path = None
        output_dir = None
        
        # 检查是否有full_zip_url字段
        if 'full_zip_url' in data:
            zip_url = data['full_zip_url'].strip('`')  # 去除可能的反引号
            print(f"检测到full_zip_url: {zip_url}")
            markdown_content, markdown_path, output_dir = download_and_extract_zip(zip_url)
        # 检查是否有markdown字段
        elif 'markdown' in data:
            markdown_content = data['markdown']
        
        if markdown_content:
            # 处理图片并更新Markdown
            if markdown_path and output_dir:
                markdown_content = process_images_and_update_markdown(
                    markdown_content, markdown_path, output_dir
                )
            
            # 保存更新后的Markdown
            with open(output_file, 'w', encoding='utf-8') as f:
                f.write(markdown_content)
            print(f"Markdown结果已保存到: {output_file}")
        else:
            print("未找到Markdown内容")
    except Exception as e:
        print(f"保存Markdown结果时发生错误: {str(e)}")

def pdf_to_markdown(pdf_url, output_file):
    """主函数"""
    print("开始PDF转Markdown处理...")
    
    # 1. 创建提取任务
    task_id = create_extract_task(pdf_url)
    if not task_id:
        print("任务创建失败，程序退出")
        return
    
    # 2. 等待任务完成并获取结果
    result_data = check_task_status(task_id)
    if not result_data:
        print("任务执行失败，程序退出")
        return
    
    # 3. 保存Markdown结果
    save_markdown_result(result_data, output_file)
    
    print("PDF转Markdown处理完成！")

if __name__ == "__main__":
    # PDF URL
    pdf_url = "https://taloversea.blob.core.chinacloudapi.cn/pubpad/pubpad/uploads/20250922/BIOLOGY%20II-2%20Blk%207A-B%20Jiang%202025%20S1-6.pdf"

    pdf_to_markdown(pdf_url)