import http.server
import socketserver
import os
import json
import uuid
from pathlib import Path
import time

import requests

from googleai_text2images_multi import json2json
from pdf_2_markdown import pdf_to_markdown

markdown_polish_prmpt = """
You are a Markdown Formatting Specialist. Your sole purpose is to reformat and beautify the provided Markdown text. You act like an automated code linter or beautifier, but for Markdown.
Your actions are governed by two unbreakable Golden Rules:
Golden Rule #1: ABSOLUTE CONTENT INTEGRITY
- You are strictly forbidden to modify, rephrase, add, or delete any of the original words or sentences. The text content must remain 100% identical.
Golden Rule #2: COMPLETE IMAGE PRESERVATION
- You must preserve all image tags (![alt text](url)) in their original position. The alt text and the URL must remain completely unchanged.
Your formatting tasks are limited to the following checklist. You must apply these rules while strictly obeying the two Golden Rules above:
1.Heading Consistency: Apply a logical hierarchy of headings (#, ##, ###).
2.Spacing and Readability: Ensure proper blank lines between paragraphs, around lists, headings, code blocks, and images for clarity.
3.List Formatting: Unify list styles (e.g., all use -) and correct indentation for nested lists.
4.Emphasis Correction: Fix broken bold (**text**) and italic (*text*) tags without adding new emphasis.
5.Code Blocks: Properly format inline `code` and fenced ``` code blocks.
6.Blockquotes and Rules: Correctly format blockquotes (>) and horizontal rules (---).
Your final output should be only the cleaned, well-formatted Markdown text, and nothing else.

"""


pdf_to_markdown_prompt = """

"""




PORT = 8000
UPLOADS_DIR = "uploads"

# 确保uploads目录存在
Path(UPLOADS_DIR).mkdir(exist_ok=True)



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
        blob_url= response.json()['data']['url']

        print(f"上传blob完成: {blob_url}")
        return blob_url


def markdown_polish_payload(markdown):
    return {
        "model": "gemini-2.5-pro",
        "messages": [
            {
                "role": "system",
                "content": markdown_polish_prmpt,
            },
            {
                "role": "user",
                "content": markdown
            }
        ]
    }

def get_pdf_payload(pdf_url) :
    return {
        "model": "gemini-2.5-pro",
        "messages": [
            {
                "role": "system",
                "content": pdf_to_markdown_prompt,
            },
            {
                "role": "user",
                "content": [
                    {
                        "type": "file_url",
                        "file_url": {
                            "url": pdf_url,
                            "mime_type": "application/pdf"
                        }
                    }
                ]
            }
        ]
    }

def gemini_query(payload):
    print("调用gemini开始")
    url = 'http://ai-service-test.tal.com/openai-compatible/v1/chat/completions'

    headers = {
        'Authorization': 'Bearer 300000182:ed2cf372e844d7699079de387e1b830f',
        'Content-Type': 'application/json'
    }


    try:
        response = requests.post(url, headers=headers, data=json.dumps(payload))
        response.raise_for_status()  # 如果响应状态码不是200，将引发HTTPError异常
        print("调用gemini完成")
        return response.json()['choices'][0]['message']['content']


    except requests.exceptions.HTTPError as errh:
        print(f"HTTP Error: {errh}")
    except requests.exceptions.ConnectionError as errc:
        print(f"Error Connecting: {errc}")
    except requests.exceptions.Timeout as errt:
        print(f"Timeout Error: {errt}")
    except requests.exceptions.RequestException as err:
        print(f"Request Exception: {err}")
    except json.JSONDecodeError:
        print("Response is not valid JSON")
        print(f"Raw response: {response.text}")


def get_json_data(markdown):
    url = "http://10.43.99.144/v1/workflows/run"
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


class CustomHandler(http.server.SimpleHTTPRequestHandler):
    def do_POST(self):
        if self.path == '/upload':
            self.handle_upload()
        else:
            self.send_error(404)

    def handle_upload(self):
        try:
            # 解析multipart/form-data
            content_type = self.headers['content-type']
            if not content_type.startswith('multipart/form-data'):
                self.send_error(400, "Expected multipart/form-data")
                return

            # 获取boundary
            boundary = content_type.split('boundary=')[1]

            # 读取请求体
            content_length = int(self.headers['Content-Length'])
            post_data = self.rfile.read(content_length)

            # 解析文件数据
            file_data, filename = self.parse_multipart_data(post_data, boundary)

            if not file_data or not filename:
                self.send_error(400, "No file uploaded")
                return

            # 检查文件类型
            if not filename.lower().endswith('.pdf'):
                self.send_error(400, "Only PDF files are allowed")
                return

            # 生成唯一文件名
            unique_filename = f"{uuid.uuid4()}_{filename}"
            file_path = os.path.join(UPLOADS_DIR, unique_filename)

            # 保存文件
            with open(file_path, 'wb') as f:
                f.write(file_data)

            # 处理文件
            self.process_uploaded_file(file_path, unique_filename)

        except Exception as e:
            print(f"Upload error: {e}")
            self.send_error(500, f"Upload failed: {str(e)}")
    
    def parse_multipart_data(self, data, boundary):
        boundary = boundary.encode()
        parts = data.split(b'--' + boundary)
        
        for part in parts:
            if b'Content-Disposition: form-data' in part and b'filename=' in part:
                # 提取文件名
                lines = part.split(b'\r\n')
                for line in lines:
                    if b'Content-Disposition' in line:
                        filename_start = line.find(b'filename="') + 10
                        filename_end = line.find(b'"', filename_start)
                        filename = line[filename_start:filename_end].decode('utf-8')
                        break
                
                # 提取文件数据
                data_start = part.find(b'\r\n\r\n') + 4
                file_data = part[data_start:].rstrip(b'\r\n')
                
                return file_data, filename
        
        return None, None

    def process_uploaded_file(self, file_path, filename):
        try:
            start_time = time.time()  # 记录总时间

            print(f"Processing uploaded file: {filename}")
            step_start = time.time()  # 记录步骤开始时间

            # 上传到 Blob
            blob_url = upload_to_blob(file_path, filename)
            print(f"Step: Uploaded to blob. Time taken: {time.time() - step_start:.2f} seconds")

            step_start = time.time()  # 更新步骤开始时间

            # 保存 markdown 文件
            file_prefix = os.path.splitext(os.path.basename(filename))[0]
            md_filename = file_prefix + ".md"
            md_filepath = "uploads/origin_markdown/origin_" + md_filename
            # 生成 markdown
            pdf_to_markdown(blob_url, md_filepath)

            with open(md_filepath, "r") as f:
                file_data = f.read()

            markdown_content = gemini_query(markdown_polish_payload(file_data))
            print(f"Step: Generated markdown. Time taken: {time.time() - step_start:.2f} seconds")

            step_start = time.time()  # 更新步骤开始时间

            with open(f"uploads/markdown/{md_filename}", 'w', encoding='utf-8') as f:
                f.write(markdown_content)

            print(f"Step: Saved markdown file. Time taken: {time.time() - step_start:.2f} seconds")

            step_start = time.time()  # 更新步骤开始时间

            # 生成 JSON 数据
            json_data = get_json_data(markdown_content)
            print(f"Step: Generated JSON data. Time taken: {time.time() - step_start:.2f} seconds")

            step_start = time.time()  # 更新步骤开始时间

            # 扩展图片生成逻辑
            json_data = json2json(json.loads(json_data))
            print(f"Step: Image generation completed. Time taken: {time.time() - step_start:.2f} seconds")

            step_start = time.time()  # 更新步骤开始时间

            # 保存 JSON 文件
            data_file = file_prefix + ".json"
            data_str = json.dumps(json_data)

            with open(f"uploads/data/{data_file}", 'w', encoding='utf-8') as f:
                f.write(data_str)
            print(f"Step: Saved JSON file to uploads/data/. Time taken: {time.time() - step_start:.2f} seconds")

            step_start = time.time()  # 更新步骤开始时间

            # 替换 data.json
            with open(f"data.json", 'w', encoding='utf-8') as f:
                f.write(data_str)
            print(f"Step: Replaced page data in data.json. Time taken: {time.time() - step_start:.2f} seconds")

            # 记录总耗时
            total_time = time.time() - start_time
            print(f"Total processing time: {total_time:.2f} seconds")

            # 发送成功响应
            self.send_response(200)
            self.send_header('Content-type', 'application/json')
            self.send_header('Access-Control-Allow-Origin', '*')
            self.end_headers()

            response = {
                'status': 'success',
                'message': 'File processed successfully',
            }

            self.wfile.write(json.dumps(response).encode())

        except Exception as e:
            print(f"Processing error: {e}")
            self.send_response(500)
            self.send_header('Content-type', 'application/json')
            self.send_header('Access-Control-Allow-Origin', '*')
            self.end_headers()

            response = {
                'status': 'error',
                'message': f'Processing failed: {str(e)}'
            }

            self.wfile.write(json.dumps(response).encode())

    def end_headers(self):
        # 添加CORS头
        self.send_header('Access-Control-Allow-Origin', '*')
        self.send_header('Access-Control-Allow-Methods', 'GET, POST, OPTIONS')
        self.send_header('Access-Control-Allow-Headers', 'Content-Type')
        super().end_headers()

    def do_OPTIONS(self):
        self.send_response(200)
        self.send_header('Access-Control-Allow-Origin', '*')
        self.send_header('Access-Control-Allow-Methods', 'GET, POST, OPTIONS')
        self.send_header('Access-Control-Allow-Headers', 'Content-Type')
        self.end_headers()

class ThreadedHTTPServer(socketserver.ThreadingTCPServer):
    # 允许服务器重用地址，防止"Address already in use"错误
    allow_reuse_address = True
    # 设置线程守护模式，这样服务器关闭时线程也会自动关闭
    daemon_threads = True

if __name__ == "__main__":
    with ThreadedHTTPServer(("", PORT), CustomHandler) as httpd:
        print(f"Serving at http://localhost:{PORT}")
        print(f"Server is running with concurrency support (ThreadingTCPServer)")
        try:
            httpd.serve_forever()
        except KeyboardInterrupt:
            print("\nShutting down server...")
            httpd.server_close()



