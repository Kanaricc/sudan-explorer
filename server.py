from flask import Flask, request, jsonify, Response, send_from_directory, send_file
import os
import subprocess
import platform
from typing import Dict, Any, Union, Tuple

# 获取当前脚本所在目录的绝对路径
BASE_DIR = os.path.dirname(os.path.abspath(__file__))

app = Flask(__name__)

@app.route('/open-config', methods=['POST'])
def open_config() -> Union[Response, Tuple[Response, int]]:
    """打开配置文件
    
    请求体格式：
    {
        "type": "节点类型",
        "id": "节点ID"
    }
    
    返回：
    {
        "success": bool,
        "message": str,
        "path": str
    }
    """
    data = request.json
    if not data or 'type' not in data or 'id' not in data:
        return jsonify({
            "success": False,
            "message": "请求参数不完整，需要提供type和id",
            "path": ""
        }), 400
    
    # 构建配置文件路径
    config_path = f"config/{data['type']}/{data['id']}.json"
    abs_path = os.path.abspath(config_path)
    
    if not os.path.exists(abs_path):
        return jsonify({
            "success": False,
            "message": f"配置文件不存在: {config_path}",
            "path": abs_path
        }), 404
    
    # 根据操作系统打开文件
    try:
        if platform.system() == "Darwin":  # macOS
            subprocess.run(["open", abs_path])
        elif platform.system() == "Windows":
            os.startfile(abs_path)
        else:  # Linux
            subprocess.run(["xdg-open", abs_path])
            
        return jsonify({
            "success": True,
            "message": f"已打开配置文件: {config_path}",
            "path": abs_path
        })
    except Exception as e:
        return jsonify({
            "success": False,
            "message": f"打开文件时出错: {str(e)}",
            "path": abs_path
        }), 500

@app.route('/')
def index() -> Response:
    # 返回show.html文件
    return send_file(os.path.join(BASE_DIR, 'show.html'))

@app.route('/graph.json')
def serve_graph_json() -> Union[Response, Tuple[Response, int]]:
    # 提供graph.json文件
    graph_path = os.path.join(BASE_DIR, 'graph.json')
    if os.path.exists(graph_path):
        return send_file(graph_path)
    else:
        return jsonify({
            "error": "graph.json文件不存在"
        }), 404

@app.route('/status')
def status() -> Response:
    return jsonify({"status": "running", "message": "苏丹剧情关系图配置文件服务器正在运行"})

if __name__ == "__main__":
    print(f"服务器已启动，请访问 http://127.0.0.1:5000/ 查看关系图")
    app.run(host='127.0.0.1', port=5000, debug=True)
