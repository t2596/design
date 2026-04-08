#!/bin/bash

# 构建所有镜像的脚本（Gateway + Web）

set -e

# 配置变量
REGISTRY="your-username"
GATEWAY_VERSION="v1.0"
WEB_VERSION="v1.0"

# 颜色输出
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
BLUE='\033[0;34m'
NC='\033[0m'

print_header() {
    echo -e "${GREEN}========================================${NC}"
    echo -e "${GREEN}${1}${NC}"
    echo -e "${GREEN}========================================${NC}"
}

print_info() {
    echo -e "${BLUE}ℹ ${1}${NC}"
}

print_success() {
    echo -e "${GREEN}✓ ${1}${NC}"
}

print_error() {
    echo -e "${RED}✗ ${1}${NC}"
}

# 显示使用说明
show_usage() {
    echo "使用方法: $0 [选项]"
    echo ""
    echo "选项:"
    echo "  -r, --registry REGISTRY   镜像仓库地址（默认: your-username）"
    echo "  -g, --gateway-version VER Gateway版本（默认: v1.0）"
    echo "  -w, --web-version VER     Web版本（默认: v1.0）"
    echo "  -p, --push                构建后自动推送"
    echo "  -h, --help                显示此帮助信息"
    echo ""
    echo "示例:"
    echo "  $0 -r myusername -g v1.1 -w v1.1 -p"
}

# 解析命令行参数
AUTO_PUSH=false

while [[ $# -gt 0 ]]; do
    case $1 in
        -r|--registry)
            REGISTRY="$2"
            shift 2
            ;;
        -g|--gateway-version)
            GATEWAY_VERSION="$2"
            shift 2
            ;;
        -w|--web-version)
            WEB_VERSION="$2"
            shift 2
            ;;
        -p|--push)
            AUTO_PUSH=true
            shift
            ;;
        -h|--help)
            show_usage
            exit 0
            ;;
        *)
            print_error "未知选项: $1"
            show_usage
            exit 1
            ;;
    esac
done

# 主流程
main() {
    print_header "构建所有镜像"
    echo ""
    
    print_info "配置信息:"
    echo "  镜像仓库: ${REGISTRY}"
    echo "  Gateway版本: ${GATEWAY_VERSION}"
    echo "  Web版本: ${WEB_VERSION}"
    echo "  自动推送: ${AUTO_PUSH}"
    echo ""
    
    # 检查Docker
    print_info "检查Docker状态..."
    if ! docker info > /dev/null 2>&1; then
        print_error "Docker未运行，请先启动Docker"
        exit 1
    fi
    print_success "Docker运行正常"
    echo ""
    
    # 构建Gateway镜像
    print_header "1. 构建Gateway镜像"
    echo ""
    
    print_info "构建 vehicle-iot-gateway:${GATEWAY_VERSION}..."
    if docker build -t ${REGISTRY}/vehicle-iot-gateway:${GATEWAY_VERSION} .; then
        docker tag ${REGISTRY}/vehicle-iot-gateway:${GATEWAY_VERSION} ${REGISTRY}/vehicle-iot-gateway:latest
        print_success "Gateway镜像构建成功"
    else
        print_error "Gateway镜像构建失败"
        exit 1
    fi
    
    echo ""
    
    # 构建Web镜像
    print_header "2. 构建Web镜像"
    echo ""
    
    print_info "构建 vehicle-iot-web:${WEB_VERSION}..."
    cd web
    if docker build -t ${REGISTRY}/vehicle-iot-web:${WEB_VERSION} .; then
        docker tag ${REGISTRY}/vehicle-iot-web:${WEB_VERSION} ${REGISTRY}/vehicle-iot-web:latest
        print_success "Web镜像构建成功"
    else
        print_error "Web镜像构建失败"
        exit 1
    fi
    cd ..
    
    echo ""
    
    # 显示镜像信息
    print_header "3. 镜像信息"
    echo ""
    docker images | grep -E "vehicle-iot-(gateway|web)" | head -10
    
    echo ""
    
    # 推送镜像
    if [ "$AUTO_PUSH" = true ]; then
        PUSH_CONFIRM="y"
    else
        read -p "是否推送所有镜像到仓库? (y/n) " -n 1 -r
        echo
        PUSH_CONFIRM=$REPLY
    fi
    
    if [[ $PUSH_CONFIRM =~ ^[Yy]$ ]]; then
        print_header "4. 推送镜像"
        echo ""
        
        # 推送Gateway镜像
        print_info "推送Gateway镜像..."
        docker push ${REGISTRY}/vehicle-iot-gateway:${GATEWAY_VERSION}
        docker push ${REGISTRY}/vehicle-iot-gateway:latest
        print_success "Gateway镜像推送成功"
        
        echo ""
        
        # 推送Web镜像
        print_info "推送Web镜像..."
        docker push ${REGISTRY}/vehicle-iot-web:${WEB_VERSION}
        docker push ${REGISTRY}/vehicle-iot-web:latest
        print_success "Web镜像推送成功"
    fi
    
    echo ""
    print_header "完成！"
    echo ""
    
    print_success "构建的镜像:"
    echo "  Gateway: ${REGISTRY}/vehicle-iot-gateway:${GATEWAY_VERSION}"
    echo "  Web:     ${REGISTRY}/vehicle-iot-web:${WEB_VERSION}"
    echo ""
    
    print_info "下一步操作:"
    echo "  1. 更新Kubernetes配置:"
    echo "     - deployment/kubernetes/gateway-deployment.yaml"
    echo "     - deployment/kubernetes/web-deployment.yaml"
    echo ""
    echo "  2. 部署到Kubernetes:"
    echo "     cd deployment/kubernetes"
    echo "     bash deploy-all.sh"
    echo ""
    echo "  3. 验证部署:"
    echo "     kubectl get pods -n vehicle-iot-gateway"
    echo ""
}

# 执行主流程
main
