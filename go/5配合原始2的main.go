package main

import (
	"encoding/json"
	"flag"
	"fmt"
	"log"
	"net/http"
	"os"
	"path/filepath"
	"time"

	"context"

	"google.golang.org/grpc"
	"google.golang.org/grpc/credentials/insecure"

	statsService "github.com/v2fly/v2ray-core/v5/app/stats/command"
)

// Config 结构体用于解析JSON配置文件
type Config struct {
	APIAddr  string `json:"api_addr"`
	HTTPAddr string `json:"http_addr"`
	HTMLPath string `json:"html_path"` // 新增：HTML文件路径配置
}

// TrafficData 表示流量数据
type TrafficData struct {
	Name  string `json:"name"`
	Value int64  `json:"value"`
}

// 全局变量
var cfg Config

func main() {
	// 解析命令行参数
	var configFile string
	flag.StringVar(&configFile, "c", "config.json", "配置文件路径")
	flag.Parse()

	// 读取配置文件
	configData, err := os.ReadFile(configFile)
	if err != nil {
		log.Fatalf("无法读取配置文件: %v\n", err)
	}

	// 解析JSON配置
	if err := json.Unmarshal(configData, &cfg); err != nil {
		log.Fatalf("解析配置文件失败: %v\n", err)
	}

	if cfg.APIAddr == "" {
		log.Fatal("配置文件中缺少有效的api_addr")
	}

	if cfg.HTTPAddr == "" {
		cfg.HTTPAddr = ":8080" // 默认HTTP端口
	}

	// 设置HTML文件路径（如果未配置）
	if cfg.HTMLPath == "" {
		// 获取当前可执行文件所在目录
		exePath, err := os.Executable()
		if err != nil {
			log.Fatalf("无法获取可执行文件路径: %v", err)
		}
		exeDir := filepath.Dir(exePath)
		cfg.HTMLPath = filepath.Join(exeDir, "index.html")
	}

	// 检查HTML文件是否存在
	if _, err := os.Stat(cfg.HTMLPath); os.IsNotExist(err) {
		log.Printf("警告: HTML文件不存在于 %s", cfg.HTMLPath)
		
		// 尝试在当前工作目录查找
		wd, err := os.Getwd()
		if err != nil {
			log.Fatalf("无法获取工作目录: %v", err)
		}
		cfg.HTMLPath = filepath.Join(wd, "index.html")
		log.Printf("尝试使用路径: %s", cfg.HTMLPath)
		
		if _, err := os.Stat(cfg.HTMLPath); os.IsNotExist(err) {
			log.Fatalf("HTML文件不存在于 %s", cfg.HTMLPath)
		}
	}

	log.Printf("使用HTML文件: %s", cfg.HTMLPath)

	// 设置HTTP路由
	http.HandleFunc("/", serveHome)
	http.HandleFunc("/api/traffic", getTrafficData)

	// 启动HTTP服务器
	log.Printf("HTTP服务器启动在 %s", cfg.HTTPAddr)
	log.Fatal(http.ListenAndServe(cfg.HTTPAddr, nil))
}

// serveHome 处理首页请求
func serveHome(w http.ResponseWriter, r *http.Request) {
	// 检查请求路径是否为根路径
	if r.URL.Path != "/" {
		http.NotFound(w, r)
		return
	}

	// 读取index.html文件
	content, err := os.ReadFile(cfg.HTMLPath)
	if err != nil {
		http.Error(w, fmt.Sprintf("无法读取HTML文件: %v", err), http.StatusInternalServerError)
		return
	}

	// 设置Content-Type并返回内容
	w.Header().Set("Content-Type", "text/html; charset=utf-8")
	w.Write(content)
}

// getTrafficData 处理API请求，返回流量数据
func getTrafficData(w http.ResponseWriter, r *http.Request) {
	// 设置CORS头，允许前端访问
	w.Header().Set("Access-Control-Allow-Origin", "*")
	w.Header().Set("Access-Control-Allow-Methods", "GET")
	w.Header().Set("Content-Type", "application/json")

	// 获取流量数据
	trafficData, err := fetchTrafficData()
	if err != nil {
		http.Error(w, fmt.Sprintf("获取流量数据失败: %v", err), http.StatusInternalServerError)
		return
	}

	// 将数据编码为JSON并返回
	json.NewEncoder(w).Encode(trafficData)
}

// fetchTrafficData 从V2Ray API获取流量数据
func fetchTrafficData() ([]TrafficData, error) {
	// 创建 gRPC 连接
	conn, err := grpc.NewClient(cfg.APIAddr, grpc.WithTransportCredentials(insecure.NewCredentials()))
	if err != nil {
		return nil, fmt.Errorf("无法连接: %v", err)
	}
	defer conn.Close()

	// 创建客户端
	client := statsService.NewStatsServiceClient(conn)

	// 查询流量
	ctx, cancel := context.WithTimeout(context.Background(), 10*time.Second)
	defer cancel()

	req := &statsService.QueryStatsRequest{
		Pattern: "*>>>*>>>traffic>>>*",
		Reset_:  false,
	}

	// 获取结果
	resp, err := client.QueryStats(ctx, req)
	if err != nil {
		return nil, fmt.Errorf("查询失败: %v", err)
	}

	// 转换数据格式
	var trafficData []TrafficData
	for _, stat := range resp.Stat {
		trafficData = append(trafficData, TrafficData{
			Name:  stat.Name,
			Value: stat.Value,
		})
	}

	return trafficData, nil
}
