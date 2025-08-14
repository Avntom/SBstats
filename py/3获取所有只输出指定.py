import grpc
import time
from datetime import datetime
import re
import sys
import stats_pb2
import stats_pb2_grpc
from collections import defaultdict

# 流量统计正则表达式 - 简化版本
TRAFFIC_REGEX = re.compile(r"(inbound|outbound)>>>([^>]+)>>>traffic>>>(downlink|uplink)")

# 使用标准服务名称
SERVICE_NAME = "v2ray.core.app.stats.command.StatsService"

# 配置信息
API_ADDR = "127.0.0.1:8080"  # sing-box API 地址
RESET_COUNTERS = False       # 是否重置计数器
INTERVAL = 5                 # 刷新间隔（秒）

# 只监控一个入站和一个出站
MONITORED_INBOUNDS = ["mixed-in"]
MONITORED_OUTBOUNDS = ["🌐代理"]

# 强制开启调试模式
DEBUG_MODE = True

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

def print_stats(title, stats):
    """打印统计数据"""
    if not stats:
        print(f"{title}: 无数据")
        return
    
    print(f"\n{title}:")
    for tag, data in stats.items():
        up = data.get("uplink", 0)
        down = data.get("downlink", 0)
        total = up + down
        
        print(f"  - {tag}:")
        print(f"     上传: {format_bytes(up)}")
        print(f"     下载: {format_bytes(down)}")
        print(f"     总计: {format_bytes(total)}")

class StatsServiceStub:
    """自定义存根以匹配服务名称"""
    def __init__(self, channel):
        self.channel = channel
        
    def QueryStats(self, request):
        """自定义 QueryStats 方法"""
        method_path = f'/{SERVICE_NAME}/QueryStats'
        return self.channel.unary_unary(
            method_path,
            request_serializer=stats_pb2.QueryStatsRequest.SerializeToString,
            response_deserializer=stats_pb2.QueryStatsResponse.FromString
        )(request)

def get_traffic_data(response):
    """解析流量统计数据"""
    inbound_stats = defaultdict(lambda: {"uplink": 0, "downlink": 0})
    outbound_stats = defaultdict(lambda: {"uplink": 0, "downlink": 0})
    
    # 显示所有统计项用于调试
    print("\n[DEBUG] 所有统计项:")
    for stat in response.stat:
        print(f"  - {stat.name}: {stat.value}")
        
        # 解析统计项名称
        match = TRAFFIC_REGEX.match(stat.name)
        if not match or len(match.groups()) < 3:
            print(f"    [不匹配] 跳过")
            continue
        
        resource = match.group(1)   # inbound/outbound
        tag = match.group(2)        # 标签
        direction = match.group(3)  # downlink/uplink
        
        print(f"    [匹配] 类型: {resource}, 标签: '{tag}', 方向: {direction}")
        
        # 处理入站流量
        if resource == "inbound" and tag in MONITORED_INBOUNDS:
            print(f"    [入站] 添加到 '{tag}'")
            inbound_stats[tag][direction] += stat.value
        
        # 处理出站流量
        elif resource == "outbound" and tag in MONITORED_OUTBOUNDS:
            print(f"    [出站] 添加到 '{tag}'")
            outbound_stats[tag][direction] += stat.value
    
    return dict(inbound_stats), dict(outbound_stats)

def main():
    print("=" * 80)
    print("Sing-box 流量监控 (简化调试版)".center(80))
    print("=" * 80)
    print(f"API 地址: {API_ADDR}")
    print(f"服务名称: {SERVICE_NAME}")
    print(f"刷新间隔: {INTERVAL} 秒")
    print(f"重置计数器: {'是' if RESET_COUNTERS else '否'}")
    print(f"监控入站: {', '.join(MONITORED_INBOUNDS)}")
    print(f"监控出站: {', '.join(MONITORED_OUTBOUNDS)}")
    print("调试模式: 强制开启")
    print("按 Ctrl+C 停止监控")
    print("=" * 80)
    
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
                
                print(f"\n[{timestamp}] 查询流量统计...")
                
                # 查询流量统计
                request = stats_pb2.QueryStatsRequest(
                    pattern="",  # 获取所有统计项
                    reset=RESET_COUNTERS
                )
                response = stub.QueryStats(request)
                
                # 解析统计数据
                inbound_stats, outbound_stats = get_traffic_data(response)
                
                # 打印结果
                print("\n[结果]")
                print_stats("入站流量", inbound_stats)
                print_stats("出站流量", outbound_stats)
                
                # 检查是否有数据
                if not inbound_stats and not outbound_stats:
                    print("\n[警告] 未检测到任何流量数据")
                    print("可能原因:")
                    print("1. 没有流量通过代理")
                    print("2. 标签不匹配")
                    print("3. 统计服务未正确配置")
                    print("4. 正则表达式匹配失败")
                
                # 等待下一次查询
                time.sleep(INTERVAL)
                
            except grpc.RpcError as e:
                error_msg = e.details()
                print(f"\n[错误] gRPC 连接失败: {error_msg}")
                print("可能原因:")
                print("1. sing-box 未运行或未启用 gRPC API")
                print("2. API 地址配置错误")
                print(f"  当前配置: {API_ADDR}")
                print("3. 端口被防火墙阻止")
                print("等待 10 秒后重试...")
                time.sleep(10)
                
            except Exception as e:
                print(f"\n[错误] 发生异常: {str(e)}")
                import traceback
                traceback.print_exc()
                print("等待 10 秒后重试...")
                time.sleep(10)
                
    except KeyboardInterrupt:
        print("\n监控已停止")
    except Exception as e:
        print(f"发生未处理错误: {str(e)}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":

    main()
