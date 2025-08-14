import grpc
import time
from datetime import datetime
import re
import sys
import stats_pb2
import stats_pb2_grpc

# 流量统计正则表达式
TRAFFIC_REGEX = re.compile(r"(inbound|outbound|user)>>>([^>]+)>>>traffic>>>(downlink|uplink)")

# 使用标准服务名称
SERVICE_NAME = "v2ray.core.app.stats.command.StatsService"

# 配置信息 - 根据您的需求定制
API_ADDR = "127.0.0.1:8080"  # sing-box API 地址
RESET_COUNTERS = False       # 是否重置计数器
INTERVAL = 5                 # 刷新间隔（秒）

# 要监控的入站和出站列表（根据您的配置）
MONITORED_INBOUNDS = ["mixed-in"]
MONITORED_OUTBOUNDS = [
    "🌐代理", "➡️直连", "CN"
]

def format_bytes(size):
    """格式化字节大小为易读格式"""
    if size <= 0:
        return "0 B"
    
    units = ['B', 'KB', 'MB', 'GB', 'TB']
    unit_idx = 0
    while size >= 1024 and unit_idx < len(units) - 1:
        size /= 1024.0
        unit_idx += 1
    return f"{size:.2f} {units[unit_idx]}"

def print_stats_table(title, stats):
    """打印统计表格"""
    if not stats:
        return
    
    print(f"\n{title}:")
    print("-" * 70)
    print(f"{'名称':<25} {'方向':<8} {'流量':>15}")
    print("-" * 70)
    
    for name, data in stats.items():
        for direction, value in data.items():
            formatted_value = format_bytes(value)
            print(f"{name:<25} {direction:<8} {formatted_value:>15}")
    
    print("-" * 70)

class StatsServiceStub:
    """自定义存根以匹配服务名称"""
    def __init__(self, channel):
        self.channel = channel
        
    def QueryStats(self, request):
        """自定义 QueryStats 方法"""
        # 构建 gRPC 方法路径
        method_path = f'/{SERVICE_NAME}/QueryStats'
        
        # 创建 gRPC 调用
        return self.channel.unary_unary(
            method_path,
            request_serializer=stats_pb2.QueryStatsRequest.SerializeToString,
            response_deserializer=stats_pb2.QueryStatsResponse.FromString
        )(request)

def get_traffic_data(response):
    """解析流量统计数据"""
    user_stats = {}
    inbound_stats = {}
    outbound_stats = {}
    
    for stat in response.stat:
        if stat.value <= 0:
            continue
        
        # 解析统计项名称
        match = TRAFFIC_REGEX.match(stat.name)
        if not match or len(match.groups()) < 3:
            continue
        
        resource = match.group(1)   # inbound/outbound/user
        tag = match.group(2)        # 用户邮箱或入站标签
        direction = match.group(3)  # downlink/uplink
        
        # 处理用户流量
        if resource == "user":
            if tag not in user_stats:
                user_stats[tag] = {"uplink": 0, "downlink": 0}
            user_stats[tag][direction] += stat.value
        
        # 处理入站流量
        elif resource == "inbound" and tag in MONITORED_INBOUNDS:
            if tag not in inbound_stats:
                inbound_stats[tag] = {"uplink": 0, "downlink": 0}
            inbound_stats[tag][direction] += stat.value
        
        # 处理出站流量
        elif resource == "outbound" and tag in MONITORED_OUTBOUNDS:
            if tag not in outbound_stats:
                outbound_stats[tag] = {"uplink": 0, "downlink": 0}
            outbound_stats[tag][direction] += stat.value
    
    return user_stats, inbound_stats, outbound_stats

def main():
    print("=" * 70)
    print("Sing-box 综合流量监控")
    print("=" * 70)
    print(f"API 地址: {API_ADDR}")
    print(f"服务名称: {SERVICE_NAME}")
    print(f"刷新间隔: {INTERVAL} 秒")
    print(f"重置计数器: {'是' if RESET_COUNTERS else '否'}")
    print(f"监控入站: {', '.join(MONITORED_INBOUNDS)}")
    print(f"监控出站: {', '.join(MONITORED_OUTBOUNDS)}")
    print("按 Ctrl+C 停止监控")
    print("=" * 70)
    
    try:
        # 创建 gRPC 通道
        channel = grpc.insecure_channel(API_ADDR)
        
        # 创建自定义存根
        stub = StatsServiceStub(channel)
        
        # 主监控循环
        while True:
            try:
                # 获取当前时间
                timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                
                # 查询流量统计
                request = stats_pb2.QueryStatsRequest(
                    pattern=">>>traffic>>>",  # 获取所有流量统计
                    reset=RESET_COUNTERS
                )
                response = stub.QueryStats(request)
                
                # 解析统计数据
                user_stats, inbound_stats, outbound_stats = get_traffic_data(response)
                
                # 打印结果
                print(f"\n[{timestamp}] 流量统计")
                
                # 用户流量统计
                if user_stats:
                    print_stats_table("用户流量", user_stats)
                    
                    # 计算用户总流量
                    total_up = sum(data["uplink"] for data in user_stats.values())
                    total_down = sum(data["downlink"] for data in user_stats.values())
                    print(f"用户总上传: {format_bytes(total_up)}")
                    print(f"用户总下载: {format_bytes(total_down)}")
                    print(f"用户总流量: {format_bytes(total_up + total_down)}")
                
                # 入站流量统计
                if inbound_stats:
                    print_stats_table("入站流量", inbound_stats)
                    
                    # 计算入站总流量
                    total_in_up = sum(data["uplink"] for data in inbound_stats.values())
                    total_in_down = sum(data["downlink"] for data in inbound_stats.values())
                    print(f"入站总上传: {format_bytes(total_in_up)}")
                    print(f"入站总下载: {format_bytes(total_in_down)}")
                
                # 出站流量统计
                if outbound_stats:
                    print_stats_table("出站流量", outbound_stats)
                    
                    # 计算出站总流量
                    total_out_up = sum(data["uplink"] for data in outbound_stats.values())
                    total_out_down = sum(data["downlink"] for data in outbound_stats.values())
                    print(f"出站总上传: {format_bytes(total_out_up)}")
                    print(f"出站总下载: {format_bytes(total_out_down)}")
                
                # 如果没有数据
                if not user_stats and not inbound_stats and not outbound_stats:
                    print("未检测到流量数据")
                    print("请确认:")
                    print("1. 有流量通过代理")
                    print("2. 配置文件中启用了流量统计")
                    print("3. 监控列表配置正确")
                
                # 等待下一次查询
                time.sleep(INTERVAL)
                
            except grpc.RpcError as e:
                error_msg = e.details()
                print(f"\n[错误] gRPC 连接失败: {error_msg}")
                print("等待 10 秒后重试...")
                time.sleep(10)
                
            except Exception as e:
                print(f"\n[错误] 发生异常: {str(e)}")
                print("等待 10 秒后重试...")
                time.sleep(10)
                
    except KeyboardInterrupt:
        print("\n监控已停止")
    except Exception as e:
        print(f"发生未处理错误: {str(e)}")

if __name__ == "__main__":
    main()