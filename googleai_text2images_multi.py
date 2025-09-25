import json
import requests
import base64
import os
import re
from datetime import datetime
import concurrent.futures

def process_content(index, content, prompt_template, url, headers):
    print(f"正在处理第 {index+1} 条内容...")
    print(f"内容摘要: {content[:100]}...")
    
    try:
        # 第一步：先调用gemini-2.5-flash-preview模型生成详细的个性化提示词
        print(f"第 {index+1} 条内容：正在生成个性化提示词...")
        
        # gemini-2.5-flash-preview模型的API配置
        preview_url = 'http://ai-flow-internal.tal.com/v1/chat/completions'
        preview_headers = {
            'Authorization': 'Bearer 300000182:ed2cf372e844d7699079de387e1b830f',
            'Content-Type': 'application/json'
        }
        
        # 构建生成个性化提示词的请求
        preview_payload = {
            "model": "gemini-2.5-flash-preview",
            "messages": [
                {
                    "role": "system",
                    "content": prompt_template  # system角色的content为提示词模板
                },
                {
                    "role": "user",
                    "content": content  # user角色的content为json文件解析的content内容
                }
            ]
        }
        
        # 发送请求生成个性化提示词
        preview_response = requests.post(
            preview_url,
            headers=preview_headers,
            json=preview_payload,
            timeout=30
        )
        
        # 提取生成的个性化提示词
        personalized_prompt = None
        # 尝试从常见响应格式中提取提示词
        if preview_response.status_code == 200:
            preview_result = preview_response.json()
            try:
                # 尝试从常见响应格式中提取提示词
                if "choices" in preview_result and preview_result["choices"] and "message" in preview_result["choices"][0]:
                    personalized_prompt = preview_result["choices"][0]["message"].get("content", "")
                elif "content" in preview_result:
                    personalized_prompt = preview_result["content"]
                
                if not personalized_prompt or len(personalized_prompt.strip()) == 0:
                    print(f"第 {index+1} 条内容：未能提取到生成的提示词，使用原始模板")
                    personalized_prompt = prompt_template.format(content=content)
                else:
                    print(f"第 {index+1} 条内容：成功生成个性化提示词")
                    # 不打印个性化提示词摘要
            except Exception as e:
                print(f"第 {index+1} 条内容：解析提示词响应时发生错误：{str(e)}，使用原始模板")
                personalized_prompt = prompt_template.format(content=content)
        else:
            print(f"第 {index+1} 条内容：生成提示词请求失败，状态码: {preview_response.status_code}，使用原始模板")
            print(f"错误信息: {preview_response.text}")
            personalized_prompt = prompt_template.format(content=content)
        
    except Exception as e:
        print(f"第 {index+1} 条内容：生成提示词时发生异常：{str(e)}，使用原始模板")
        personalized_prompt = prompt_template.format(content=content)
    
    # 第二步：使用生成的个性化提示词请求生成图片
    print(f"第 {index+1} 条内容：正在生成图片...")
    image_generation_payload = {
        "model": "gemini-2.5-flash-image",
        "messages": [
            {
                "role": "user",
                "content": personalized_prompt
            }
        ],
        "modalities": ["text", "image"]
    }
    
    try:
        response = requests.post(
            url,
            headers=headers,
            json=image_generation_payload,
            timeout=30
        )
        
        # 检查响应状态
        if response.status_code == 200:
            # 解析响应
            result = response.json()
            
            # 生成时间戳，用于创建图片文件名
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            
            # 尝试多种可能的图片数据位置
            image_data = None
            image_source = None
            
            # 可能性1: 检查常见API响应格式 (choices[0].message.images[0].image_url.url)
            try:
                image_data_uri = result["choices"][0]["message"]["images"][0]["image_url"]["url"]
                match = re.search(r"data:image/\w+;base64,(.+)", image_data_uri)
                if match:
                    image_data = base64.b64decode(match.group(1))
                    image_source = "标准API格式"
            except (KeyError, IndexError, TypeError):
                pass  # 不是这种格式，继续尝试其他可能性
            
            # 可能性2: 递归搜索嵌套结构中的图片数据
            if image_data is None:
                try:
                    # 递归搜索可能包含图片数据的字段
                    def find_image_data(obj):
                        if isinstance(obj, dict):
                            for k, v in obj.items():
                                if isinstance(v, str) and len(v) > 1000 and ("image" in k.lower() or "data" in k.lower()):
                                    try:
                                        return base64.b64decode(v)
                                    except:
                                        pass
                                result = find_image_data(v)
                                if result is not None:
                                    return result
                        elif isinstance(obj, list):
                            for item in obj:
                                result = find_image_data(item)
                                if result is not None:
                                    return result
                        return None
                    
                    
                    image_data = find_image_data(result)
                    if image_data:
                        image_source = "递归搜索"
                except:
                    pass
            
            # 如果找到图片数据，保存到本地
            if image_data:
                os.makedirs("generated_images", exist_ok=True)
                filename = f"generated_images/generated_image_{index}_{timestamp}.png"

                with open(filename, "wb") as f:
                    f.write(image_data)

                print(f"图片已成功保存到: {filename}")
                print(f"图片来源: {image_source}")
                
                # 上传图片到blob并获取URL
                try:
                    blob_url = upload_to_blob(filename, os.path.basename(filename))
                    print(f"成功获取图片URL: {blob_url}")
                    return blob_url
                except Exception as e:
                    print(f"上传图片失败: {str(e)}")
                    return None
            else:
                print("未能找到图片数据，请检查API响应格式")
                return None
        else:
            print(f"请求失败，状态码: {response.status_code}")
            print(f"错误信息: {response.text}")
            return None
        
    except requests.exceptions.RequestException as e:
        print(f"请求异常: {str(e)}")
        return None
    except Exception as e:
        print(f"处理响应时发生错误: {str(e)}")
        import traceback
        traceback.print_exc()
        return None



def upload_to_blob(file_path, file_name):
    print("上传blob开始")
    url = 'http://10.224.129.212:8080/inner/public/blob/form-data/upload'
    headers = {'Content-Type': 'multipart/form-data'}

    # 构建查询参数
    params = {
        'containerName': "601public101",
        'targetPath': "/learnyourway",
        'fileName': f"/upload/pdf/{file_name}"
    }

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
        print(response.text)
        blob_url = response.json()['data']['url']

        print(f"上传blob完成: {blob_url}")
        return blob_url


def json2json(original_data):
    
    # 提取所有content - knowledge_extension 节点在 chapters 下
    contents = []
    content_references = []  # 保存每个content对应的原始位置引用
    
    # 确保数据中有chapters字段并且是一个数组
    if "chapters" in original_data and isinstance(original_data["chapters"], list):
        # 遍历chapters数组
        for chapter in original_data["chapters"]:
            # 检查每个chapter中是否有knowledge_extension字段
            if "knowledge_extension" in chapter and "paragraphs" in chapter["knowledge_extension"]:
                # 从knowledge_extension中获取paragraphs数组
                for paragraph in chapter["knowledge_extension"]["paragraphs"]:
                    if "content" in paragraph:
                        contents.append(paragraph["content"])
                        # 保存引用关系，以便后续更新
                        content_references.append(paragraph)
    
    print(f"成功提取到 {len(contents)} 条content内容")
    
    # 存储所有生成的图片URL
    generated_image_urls = [None] * len(contents)  # 预分配空间
    
    # 设置API参数
    url = "http://ai-service.tal.com/openai-compatible/v1/chat/completions"
    headers = {
        "api-key": "300000298:ddd56d685698ec7a93e459762b9f7c1e",
        "Content-Type": "application/json"
    }
    
    # 增强版提示词模板 - 用于指导gemini-2.5-flash-preview生成详细的个性化提示词
    prompt_template = '''You are a professional educational illustration designer, specializing in creating illustrations for primary, middle, and high school educational content. Based on the article content provided by the user, generate a detailed illustration design description that will be directly used to create the actual illustration.

Please generate a detailed illustration design description following this structure:
1. Illustration Theme: Clearly summarize the core theme that the illustration should express
2. Art Style: Describe the overall artistic style, such as simple cartoon, watercolor style, etc.
3. Main Elements: List key elements that need to be included (characters, objects, scenes, etc.)
4. Element Layout: Describe the position and layout of each element in the画面
5. Color Scheme: Suggest color combinations and tones to use
6. Text Labels: Suggest English labels to add and their positions
7. Educational Significance: Explain how the illustration helps in understanding the article content

Please ensure the description is detailed and specific enough to be directly used for generating high-quality educational illustrations.'''
    
    # 分批次处理，每批最多10个线程
    batch_size = 10
    total_contents = len(contents)
    
    for batch_start in range(0, total_contents, batch_size):
        batch_end = min(batch_start + batch_size, total_contents)
        current_batch_size = batch_end - batch_start
        
        print(f"开始处理批次: {batch_start//batch_size + 1}/{(total_contents + batch_size - 1)//batch_size}")
        print(f"本批次处理第 {batch_start+1} 到第 {batch_end} 条内容，共 {current_batch_size} 条")
        
        # 创建线程池，线程数为当前批次的大小
        with concurrent.futures.ThreadPoolExecutor(max_workers=current_batch_size) as executor:
            # 提交任务到线程池
            future_to_index = {
                executor.submit(process_content, i, contents[i], prompt_template, url, headers): i
                for i in range(batch_start, batch_end)
            }
            
            # 收集结果
            for future in concurrent.futures.as_completed(future_to_index):
                index = future_to_index[future]
                try:
                    blob_url = future.result()
                    generated_image_urls[index] = blob_url
                except Exception as e:
                    print(f"处理第 {index+1} 条内容时发生异常: {str(e)}")
                    generated_image_urls[index] = None
    
    # 将生成的图片URL按顺序拼接到content同级下的image节点
    for i, paragraph in enumerate(content_references):
        if i < len(generated_image_urls) and generated_image_urls[i]:
            paragraph["image"] = generated_image_urls[i]
            print(f"已为第{i+1}条内容添加图片URL")
        else:
            # 如果没有生成图片URL，设置默认值或保持原样
            if "image" not in paragraph:
                paragraph["image"] = ""
                print(f"第{i+1}条内容未生成图片，设置为空")
    
    # 直接写回到原始的data.json文件中
    with open("data.json", "w") as f:
        json.dump(original_data, f, ensure_ascii=False, indent=2)
    
    print("已成功将image节点添加到data.json文件中")
    
    # 返回修改后的数据
    return original_data


if __name__ == "__main__":
    print("开始处理...")
    result = json2json()
    
    print("处理完成")