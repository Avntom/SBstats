package main

import (
	"fmt"
	"context"           // 用于传递上下文信息（如取消信号、超时等）

	"flag"              // 用于解析命令行参数
	"os"                // 用于读取文件
	"encoding/json"     // 用于解析JSON配置文件

	"google.golang.org/grpc"
	"google.golang.org/grpc/credentials/insecure"

	statsService "github.com/v2fly/v2ray-core/v5/app/stats/command"
)

// Config 结构体用于解析JSON配置文件
type Config struct {
	APIAddr string `json:"api_addr"`
}

func main() {
	// 解析命令行参数
	var configFile string
	flag.StringVar(&configFile, "c", "config.json", "配置文件路径")
	flag.Parse()

	// 读取配置文件
	configData, err := os.ReadFile(configFile)
	if err != nil {
		fmt.Printf("无法读取配置文件: %v\n", err)
		return
	}

	// 解析JSON配置
	var cfg Config
	if err := json.Unmarshal(configData, &cfg); err != nil {
		fmt.Printf("解析配置文件失败: %v\n", err)
		return
	}

	if cfg.APIAddr == "" {
		fmt.Println("配置文件中缺少有效的api_addr")
		return
	}

	// 创建 gRPC 连接
	conn, err := grpc.NewClient(cfg.APIAddr, grpc.WithTransportCredentials(insecure.NewCredentials()))
	if err != nil {
		fmt.Printf("无法连接: %v\n", err)
		return
	}
	defer conn.Close()

	// 创建客户端
	client := statsService.NewStatsServiceClient(conn)

	// 查询流量
	req := &statsService.QueryStatsRequest{
		Pattern: "*>>>*>>>traffic>>>*",
		Reset_:  false,
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
