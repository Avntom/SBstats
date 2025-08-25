package main

import (
	"context"
	"embed"
	"encoding/json"
	"flag"
	"fmt"
	"log"
	"net/http"
	"os"

	"google.golang.org/grpc"
	"google.golang.org/grpc/credentials/insecure"

	statsService "github.com/v2fly/v2ray-core/v5/app/stats/command"
)

//go:embed index.html
var content embed.FS

// Config 结构体用于解析JSON配置文件
type Config struct {
	APIAddr string `json:"api_addr"`
}

func main() {
	// 解析命令行参数
	var configFile string
	var httpPort string
	flag.StringVar(&configFile, "c", "config.json", "配置文件路径")
	flag.StringVar(&httpPort, "p", "8080", "HTTP服务器端口")
	flag.Parse()

	// 读取配置文件
	configData, err := os.ReadFile(configFile)
	if err != nil {
		log.Fatalf("无法读取配置文件: %v\n", err)
	}

	// 解析JSON配置
	var cfg Config
	if err := json.Unmarshal(configData, &cfg); err != nil {
		log.Fatalf("解析配置文件失败: %v\n", err)
	}

	if cfg.APIAddr == "" {
		log.Fatal("配置文件中缺少有效的api_addr")
	}

	// 创建 gRPC 连接
	conn, err := grpc.NewClient(cfg.APIAddr, grpc.WithTransportCredentials(insecure.NewCredentials()))
	if err != nil {
		log.Fatalf("无法连接 gRPC: %v\n", err)
	}
	defer conn.Close()

	// 创建客户端
	client := statsService.NewStatsServiceClient(conn)

	// 设置 HTTP 处理器 - API
	http.HandleFunc("/api/stats", func(w http.ResponseWriter, r *http.Request) {
		// 查询流量
		req := &statsService.QueryStatsRequest{
			Pattern: "*>>>*>>>traffic>>>*",
			Reset_:  false,
		}

		resp, err := client.QueryStats(context.Background(), req)
		if err != nil {
			http.Error(w, fmt.Sprintf("查询失败: %v", err), http.StatusInternalServerError)
			return
		}

		// 返回 JSON，格式为 { "stats": [...] }
		w.Header().Set("Content-Type", "application/json")
		json.NewEncoder(w).Encode(map[string]interface{}{
			"stats": resp.Stat,
		})
	})

	// 设置 HTTP 处理器 - 前端页面
	http.HandleFunc("/", func(w http.ResponseWriter, r *http.Request) {
		data, err := content.ReadFile("index.html")
		if err != nil {
			http.Error(w, "无法加载页面", http.StatusInternalServerError)
			return
		}
		w.Header().Set("Content-Type", "text/html")
		w.Write(data)
	})

	// 启动 HTTP 服务器
	log.Printf("启动 HTTP 服务器于端口 %s", httpPort)
	if err := http.ListenAndServe(":"+httpPort, nil); err != nil {
		log.Fatalf("启动服务器失败: %v", err)
	}
}
