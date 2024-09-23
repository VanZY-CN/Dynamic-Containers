# Dynamic Containers
基于Python Flask编写的动态容器启动服务
应用于不支持动态容器的CTF平台的场景

## Usage
修改此处(3977)为你的镜像id，3000处为你需要映射的端口
```
container = client.containers.run(
            "3977",
            detach=True,
            ports={'3000/tcp': host_port} 
        )
```


```
python runContainer.py
```
访问5000端口即可

## Update Note：
### Beta v1.0
提供基本的开启和删除功能，仅支持单机使用
