import grpc
import stats_pb2

API_ADDR = "127.0.0.1:8080"
SERVICE_NAME = "v2ray.core.app.stats.command.StatsService"

class StatsServiceStub:
    def __init__(self, channel):
        self.channel = channel
        
    def QueryStats(self, request):
        method_path = f'/{SERVICE_NAME}/QueryStats'
        return self.channel.unary_unary(
            method_path,
            request_serializer=stats_pb2.QueryStatsRequest.SerializeToString,
            response_deserializer=stats_pb2.QueryStatsResponse.FromString
        )(request)

def main():
    # 创建 gRPC 通道
    channel = grpc.insecure_channel(API_ADDR)
    
    # 创建存根
    stub = StatsServiceStub(channel)
    
    # 查询 mixed-in 流量
    request = stats_pb2.QueryStatsRequest(
        pattern="inbound>>>mixed-in>>>traffic>>>*", 
        reset=False
    )
    
    # 获取并显示结果
    response = stub.QueryStats(request)
    print("流量数据:")
    for stat in response.stat:
        print(f"{stat.name}: {stat.value}")

if __name__ == "__main__":
    main()