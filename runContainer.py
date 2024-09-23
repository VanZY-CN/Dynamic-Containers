from flask import Flask, request, jsonify, render_template
import docker
from apscheduler.schedulers.background import BackgroundScheduler
import random
import socket
import time
from datetime import datetime, timedelta
import os

app = Flask(__name__)
client = docker.from_env()

# 定时任务调度器
scheduler = BackgroundScheduler()
scheduler.start()

# 用于存储容器的映射，key 为 IP 地址，value 为 {'container_id': 容器ID, 'port': 映射的端口}
containers = {}

host_ip = os.popen("curl ip.me").read().split("\n")[0]

# 获取请求 IP 地址
def get_client_ip():
    if request.headers.get('X-Forwarded-For'):
        ip = request.headers.get('X-Forwarded-For').split(',')[0]
    else:
        ip = request.remote_addr
    return ip

# 检查端口是否可用
def is_port_available(port):
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        return s.connect_ex(('0.0.0.0', port)) != 0  # 返回0表示端口被占用

# 获取随机可用端口
def get_random_port():
    while True:
        port = random.randint(20000, 40000)
        if is_port_available(port):
            return port

# 渲染首页
@app.route('/')
def index():
    return render_template('index.html')

# 启动容器的服务
@app.route('/start_container', methods=['POST'])
def start_container():
    ip_address = get_client_ip()

    # 检查该 IP 是否已经有一个正在运行的容器
    if ip_address in containers:
        return jsonify({
            "message": "Container already running for this IP", 
            "container_id": containers[ip_address]['container_id'], 
            "challenge": host_ip + ":" + str(containers[ip_address]['port'])
        }), 200

    # 获取随机可用的端口
    host_port = get_random_port()

    # 创建新的容器，使用指定的镜像 ID 和随机端口映射
    try:
        container = client.containers.run(
            "3977",
            detach=True,
            ports={'3000/tcp': host_port} 
        )
        container_id = container.short_id
        containers[ip_address] = {'container_id': container_id, 'port': host_port}

        # 计算销毁时间，设置为半小时后
        destroy_time = datetime.now() + timedelta(seconds=1800)

        # 设置半小时后自动销毁容器的任务
        scheduler.add_job(func=destroy_container, args=[container_id, ip_address], trigger='date', run_date=destroy_time)

        return jsonify({"message": "Container started", "container_id": container_id, "ip_address": ip_address, "challenge": host_ip + ":" + str(host_port)}), 200

    except Exception as e:
        return jsonify({"error": str(e)}), 500

# 手动销毁容器的路由
@app.route('/stop_container', methods=['POST'])
def stop_container():
    ip_address = get_client_ip()

    # 检查该 IP 是否有运行的容器
    if ip_address not in containers:
        return jsonify({"message": "No running container found for this IP"}), 404

    # 获取该 IP 关联的容器 ID
    container_id = containers[ip_address]['container_id']

    # 手动销毁容器
    try:
        destroy_container(container_id, ip_address)
        return jsonify({"message": f"Container {container_id} stopped and removed successfully."}), 200
    except Exception as e:
        return jsonify({"error": str(e)}), 500

# 销毁容器的函数
def destroy_container(container_id, ip_address):
    try:
        container = client.containers.get(container_id)
        container.stop()
        container.remove()
        print(f"Container {container_id} for IP {ip_address} has been destroyed.")
        # 移除 IP 和容器的映射
        containers.pop(ip_address, None)
    except docker.errors.NotFound:
        print(f"Container {container_id} not found. It might have been destroyed already.")
    except Exception as e:
        print(f"Error destroying container {container_id}: {str(e)}")

# 启动 Flask 应用
if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000)

