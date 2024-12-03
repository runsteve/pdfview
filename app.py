from flask import Flask, request, jsonify, send_file, send_from_directory, Response
from flask_cors import CORS
import os
from werkzeug.utils import secure_filename
import base64
import io
from PIL import Image
import urllib.parse
import requests
from bs4 import BeautifulSoup
import re
import time

app = Flask(__name__)
CORS(app)

UPLOAD_FOLDER = 'uploads'
if not os.path.exists(UPLOAD_FOLDER):
    os.makedirs(UPLOAD_FOLDER)

def modify_html_content(content, base_url):
    # 使用BeautifulSoup解析HTML
    soup = BeautifulSoup(content, 'html.parser')
    
    # 修改所有相对路径为绝对路径
    for tag in soup.find_all(['img', 'script', 'link']):
        for attr in ['src', 'href']:
            if tag.get(attr):
                url = tag.get(attr)
                if not url.startswith(('http://', 'https://', 'data:', '//')):
                    if url.startswith('/'):
                        tag[attr] = base_url + url
                    else:
                        tag[attr] = base_url + '/' + url

    # 注入自定义JavaScript
    script_tag = soup.new_tag('script')
    script_tag.string = """
    document.addEventListener('DOMContentLoaded', function() {
        // 处理图片点击
        const images = document.getElementsByTagName('img');
        Array.from(images).forEach(img => {
            img.style.cursor = 'pointer';
            img.addEventListener('click', async function(e) {
                e.preventDefault();
                try {
                    const response = await fetch('http://localhost:5000/extract-image', {
                        method: 'POST',
                        headers: {
                            'Content-Type': 'application/json',
                        },
                        body: JSON.stringify({
                            imageUrl: this.src
                        })
                    });
                    const data = await response.json();
                    if (data.success) {
                        alert('图片已成功提取并保存！');
                    }
                } catch (error) {
                    console.error('Error:', error);
                }
            });
        });

        // 处理文本选择
        document.addEventListener('mouseup', async function() {
            const selectedText = window.getSelection().toString().trim();
            if (selectedText) {
                try {
                    const response = await fetch('http://localhost:5000/extract-text', {
                        method: 'POST',
                        headers: {
                            'Content-Type': 'application/json',
                        },
                        body: JSON.stringify({
                            text: selectedText,
                            url: window.location.href
                        })
                    });
                    const data = await response.json();
                    if (data.success) {
                        alert('文本已成功保存！');
                    }
                } catch (error) {
                    console.error('Error:', error);
                }
            }
        });
    });
    """
    soup.body.append(script_tag)
    
    return str(soup)

@app.route('/proxy')
def proxy():
    url = request.args.get('url')
    if not url:
        return jsonify({'error': 'No URL provided'}), 400

    try:
        # 获取基础URL（用于处理相对路径）
        parsed_url = urllib.parse.urlparse(url)
        base_url = f"{parsed_url.scheme}://{parsed_url.netloc}"

        # 发送请求获取页面内容
        headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
        }
        response = requests.get(url, headers=headers)
        response.raise_for_status()

        # 修改页面内容
        modified_content = modify_html_content(response.text, base_url)

        return Response(modified_content, content_type='text/html; charset=utf-8')

    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/extract-text', methods=['POST'])
def extract_text():
    data = request.json
    if not data or 'text' not in data:
        return jsonify({'error': 'No text provided'}), 400
    
    try:
        # 获取文本和来源URL
        text = data['text']
        source_url = data.get('url', 'Unknown source')
        
        # 生成文件名
        timestamp = time.strftime('%Y%m%d_%H%M%S')
        filename = f"text_{timestamp}.txt"
        filepath = os.path.join(UPLOAD_FOLDER, filename)
        
        # 保存文本
        with open(filepath, 'w', encoding='utf-8') as f:
            f.write(f"Source: {source_url}\n")
            f.write(f"Timestamp: {time.strftime('%Y-%m-%d %H:%M:%S')}\n")
            f.write("\n" + text)
        
        return jsonify({
            'success': True,
            'filename': filename,
            'path': filepath
        }), 200
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/extract-image', methods=['POST'])
def extract_image():
    data = request.json
    if not data or 'imageUrl' not in data:
        return jsonify({'error': 'No image URL provided'}), 400
    
    try:
        # 获取图片URL
        image_url = data['imageUrl']
        
        # 如果是base64图片数据
        if image_url.startswith('data:image'):
            image_data = image_url.split(',')[1]
            image_binary = base64.b64decode(image_data)
            image = Image.open(io.BytesIO(image_binary))
            filename = f"extracted_{len(os.listdir(UPLOAD_FOLDER))}.png"
        else:
            # 如果是URL，下载图片
            response = requests.get(image_url, stream=True)
            response.raise_for_status()
            
            # 从URL或Content-Disposition中获取文件名
            filename = os.path.basename(urllib.parse.urlparse(image_url).path)
            if not filename or '.' not in filename:
                content_disposition = response.headers.get('content-disposition')
                if content_disposition:
                    filename = re.findall("filename=(.+)", content_disposition)[0]
                else:
                    filename = f"extracted_{len(os.listdir(UPLOAD_FOLDER))}.png"
            
            image = Image.open(io.BytesIO(response.content))
        
        # 保存图片
        filepath = os.path.join(UPLOAD_FOLDER, filename)
        image.save(filepath)
        return jsonify({
            'success': True,
            'filename': filename,
            'path': filepath
        }), 200
    except Exception as e:
        return jsonify({'error': str(e)}), 500

if __name__ == '__main__':
    app.run(debug=True) 