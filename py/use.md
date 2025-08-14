pip install requests
pip install grpcio grpcio-tools protobuf requests

在脚本同目录下创建 protos 文件夹，并在其中放入 stats.proto 文件
运行生成 stats_pb2.py 和 stats_pb2_grpc.py
python -m grpc_tools.protoc -Iprotos --python_out=. --grpc_python_out=. protos/stats.proto

