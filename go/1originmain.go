package main

import (
	"context"
	"fmt"

	"google.golang.org/grpc"
	"google.golang.org/grpc/credentials/insecure"

	statsService "github.com/v2fly/v2ray-core/v5/app/stats/command"
)

const API_ADDR = "127.0.0.1:8080"

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

	// 查询流量
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
}
