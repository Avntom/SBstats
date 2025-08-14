package main

import (
	"context"
	"fmt"

	"google.golang.org/grpc"
	"google.golang.org/grpc/credentials/insecure"

	statsService "github.com/v2fly/v2ray-core/v5/app/stats/command"
)

const API_ADDR = "127.0.0.1:8080"

// 新增系统统计函数
/*
	获取运行数据, 如下
	NumGoroutine:17  NumGC:2  Alloc:1711192  TotalAlloc:2359880  Sys:14440840  Mallocs:19101  Frees:7242  LiveObjects:11859  PauseTotalNs:4983200  Uptime:31
*/
func getSysStats(c statsService.StatsServiceClient) (stats *statsService.SysStatsResponse, err error) {
	stats, err = c.GetSysStats(context.Background(), &statsService.SysStatsRequest{})
	return
}

func main() {
	// 创建 gRPC 连接
	conn, err := grpc.NewClient(API_ADDR, grpc.WithTransportCredentials(insecure.NewCredentials()))
	if err != nil {
		fmt.Printf("无法连接: %v\n", err)
		return
	}
	defer conn.Close()

	// 创建客户端
	client := statsService.NewStatsServiceClient(conn)

	// 查询 mixed-in 流量
	req := &statsService.QueryStatsRequest{
		//Pattern: "inbound>>>mixed-in>>>traffic>>>*",
		Pattern: "*>>>*>>>traffic>>>*",
		Reset_:  false,
		//Reset_:  true,
	}

	// 获取并显示结果
	resp, err := client.QueryStats(context.Background(), req)
	if err != nil {
		fmt.Printf("查询失败: %v\n", err)
		return
	}
	fmt.Println("流量数据:")
	for _, stat := range resp.Stat {
		fmt.Printf("%s: %d\n", stat.Name, stat.Value)
	}

	// 新增系统统计查询
	sysStats, err := getSysStats(client)
	if err != nil {
		fmt.Printf("获取系统统计失败: %v\n", err)
		return
	}
	
	fmt.Println("\n系统运行数据:")
	fmt.Printf("NumGoroutine:%d  NumGC:%d  Alloc:%d  TotalAlloc:%d  Sys:%d  Mallocs:%d  Frees:%d  LiveObjects:%d  PauseTotalNs:%d  Uptime:%d\n",
		sysStats.NumGoroutine,
		sysStats.NumGC,
		sysStats.Alloc,
		sysStats.TotalAlloc,
		sysStats.Sys,
		sysStats.Mallocs,
		sysStats.Frees,
		sysStats.LiveObjects,
		sysStats.PauseTotalNs,
		sysStats.Uptime,
	)
}
