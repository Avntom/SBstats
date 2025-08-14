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
    print(f"{'用户/标签':<30} {'方向':<8} {'流量':>15}")
    print("-" * 70)
    
    for data in stats.values():
        formatted_value = format_bytes(data["value"])
        print(f"{data['tag']:<30} {data['direction']:<8} {formatted_value:>15}")
    
    print("-" * 70)

def calculate_totals(stats):
    """计算总流量"""
    total_up = sum(d["value"] for d in stats.values() if d["direction"] == "uplink")
    total_down = sum(d["value"] for d in stats.values() if d["direction"] == "downlink")
    total_all = total_up + total_down
    return total_up, total_down, total_all

class StandardStatsServiceStub:
    """使用标准服务名称的存根"""
    def __init__(self, channel):
        self.channel = channel
        
    def QueryStats(self, request):
        """自定义 QueryStats 方法"""
        # 构建标准 gRPC 方法路径
        method_path = f'/{SERVICE_NAME}/QueryStats'
        
        # 创建 gRPC 调用
        return self.channel.unary_unary(
            method_path,
            request_serializer=stats_pb2.QueryStatsRequest.SerializeToString,
            response_deserializer=stats_pb2.QueryStatsResponse.FromString
        )(request)

def main():
    # 配置信息
    api_addr = "127.0.0.1:8080"  # sing-box API 地址
    reset_counters = False        # 是否重置计数器
    interval = 5                  # 刷新间隔（秒）
    
    print("=" * 70)
    print("Sing-box 流量监控 (标准 V2Ray API)")
    print("=" * 70)
    print(f"API 地址: {api_addr}")
    print(f"服务名称: {SERVICE_NAME}")
    print(f"刷新间隔: {interval} 秒")
    print(f"重置计数器: {'是' if reset_counters else '否'}")
    print("按 Ctrl+C 停止监控")
    print("=" * 70)
    
    try:
        # 创建 gRPC 通道
        channel = grpc.insecure_channel(api_addr)
        
        # 创建自定义存根
        stub = StandardStatsServiceStub(channel)
        
        # 主监控循环
        while True:
            try:
                # 获取当前时间
                timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                
                # 查询流量统计
                request = stats_pb2.QueryStatsRequest(reset=reset_counters)
                response = stub.QueryStats(request)
                
                # 解析统计数据
                user_stats = {}
                inbound_stats = {}
                outbound_stats = {}
                
                for stat in response.stat:
                    if stat.value <= 0:
                        continue
                    
                    # 使用正则表达式解析
                    match = TRAFFIC_REGEX.match(stat.name)
                    if not match or len(match.groups()) < 3:
                        continue
                    
                    resource = match.group(1)
                    tag = match.group(2)
                    direction = match.group(3)
                    
                    # 根据资源类型分类存储
                    key = f"{tag}_{direction}"
                    stat_data = {
                        "tag": tag, 
                        "direction": direction, 
                        "value": stat.value
                    }
                    
                    if resource == "user":
                        user_stats[key] = stat_data
                    elif resource == "inbound":
                        inbound_stats[key] = stat_data
                    elif resource == "outbound":
                        outbound_stats[key] = stat_data
                
                # 打印结果
                print(f"\n[{timestamp}] 流量统计")
                
                # 用户流量统计
                if user_stats:
                    print_stats_table("用户流量", user_stats)
                    user_up, user_down, user_total = calculate_totals(user_stats)
                    print(f"用户总上传: {format_bytes(user_up)}")
                    print(f"用户总下载: {format_bytes(user_down)}")
                    print(f"用户总流量: {format_bytes(user_total)}")
                else:
                    print("\n未检测到用户流量数据")
                
                # 入站流量统计
                if inbound_stats:
                    print_stats_table("入站流量", inbound_stats)
                    in_up, in_down, in_total = calculate_totals(inbound_stats)
                    print(f"入站总上传: {format_bytes(in_up)}")
                    print(f"入站总下载: {format_bytes(in_down)}")
                    print(f"入站总流量: {format_bytes(in_total)}")
                else:
                    print("\n未检测到入站流量数据")
                
                # 出站流量统计
                if outbound_stats:
                    print_stats_table("出站流量", outbound_stats)
                    out_up, out_down, out_total = calculate_totals(outbound_stats)
                    print(f"出站总上传: {format_bytes(out_up)}")
                    print(f"出站总下载: {format_bytes(out_down)}")
                    print(f"出站总流量: {format_bytes(out_total)}")
                else:
                    print("\n未检测到出站流量数据")
                
                # 等待下一次查询
                time.sleep(interval)
                
            except grpc.RpcError as e:
                error_msg = e.details()
                print(f"\n[错误] gRPC 连接失败: {error_msg}")
                
                # 针对特定错误提供解决方案
                if "unknown service" in error_msg:
                    print(f"当前服务名称: '{SERVICE_NAME}'")
                    print("可能的正确服务名称:")
                    print("1. experimental.v2rayapi.StatsService")
                    print("2. v2ray.core.app.stats.command.StatsService")
                    print("3. v2rayapi.StatsService")
                
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
