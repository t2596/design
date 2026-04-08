#!/bin/bash

# Docker镜像构建和推送脚本
# 用于构建包含问题2和问题3修复的镜像

set -e

# 配置变量（请根据实际情况修改）
REGISTRY="your-username"  # Docker Hub用户名或镜像仓库地址
IMAGE_NAME="vehicle-iot-gateway"
VERSION="v1.0"

# 颜色输出
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# 打印带颜色的消息
print_info() {
    echo -e "${BLUE}ℹ ${1}${NC}"
}

print_success() {
    echo -e "${GREEN}✓ ${1}${NC}"
}

print_warning() {
    echo -e "${YELLOW}⚠ ${1}${NC}"
}

print_error() {
    echo -e "${RED}✗ ${1}${NC}"
}

print_header() {
    echo -e "${GREEN}========================================${NC}"
    echo -e "${GREEN}${1}${NC}"
    echo -e "${GREEN}========================================${NC}"
}

# 显示使用说明
show_usage() {
    echo "使用方法: $0 [选项]"
    echo ""
    echo "选项:"
    echo "  -r, --registry REGISTRY   镜像仓库地址（默认: your-username）"
    echo "  -n, --name NAME           镜像名称（默认: vehicle-iot-gateway）"
    echo "  -v, --version VERSION     镜像版本（默认: v1.0）"
    echo "  -p, --push                构建后自动推送"
    echo "  -h, --help                显示此帮助信息"
    echo ""
    echo "示例:"
    echo "  $0 -r myusername -v v1.1 -p"
    echo "  $0 --registry registry.cn-hangzhou.aliyuncs.com/myns --push"
}

# 解析命令行参数
AUTO_PUSH=false

while [[ $# -gt 0 ]]; do
    case $1 in
        -r|--registry)
            REGISTRY="$2"
            shift 2
            ;;
        -n|--name)
            IMAGE_NAME="$2"
            shift 2
            ;;
        -v|--version)
            VERSION="$2"
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
    print_header "Docker镜像构建和推送"
    echo ""
    
    print_info "配置信息:"
    echo "  镜像仓库: ${REGISTRY}"
    echo "  镜像名称: ${IMAGE_NAME}"
    echo "  镜像版本: ${VERSION}"
    echo "  自动推送: ${AUTO_PUSH}"
    echo ""
    
    # 步骤1：检查Docker
    print_info "步骤1: 检查Docker状态..."
    if ! docker info > /dev/null 2>&1; then
        print_error "Docker未运行，请先启动Docker"
        exit 1
    fi
    print_success "Docker运行正常"
    echo ""
    
    # 步骤2：检查Dockerfile
    print_info "步骤2: 检查Dockerfile..."
    if [ ! -f "Dockerfile" ]; then
        print_error "找不到Dockerfile文件"
        exit 1
    fi
    print_success "Dockerfile存在"
    echo ""
    
    # 步骤3：构建镜像
    print_info "步骤3: 构建Docker镜像..."
    print_info "这可能需要几分钟时间..."
    
    FULL_IMAGE_NAME="${REGISTRY}/${IMAGE_NAME}:${VERSION}"
    LATEST_IMAGE_NAME="${REGISTRY}/${IMAGE_NAME}:latest"
    
    if docker build -t ${FULL_IMAGE_NAME} .; then
        print_success "镜像构建成功"
        
        # 同时打上latest标签
        docker tag ${FULL_IMAGE_NAME} ${LATEST_IMAGE_NAME}
        print_success "已打上latest标签"
    else
        print_error "镜像构建失败"
        exit 1
    fi
    echo ""
    
    # 步骤4：查看镜像信息
    print_info "步骤4: 查看构建的镜像..."
    docker images | grep ${IMAGE_NAME} | head -5
    echo ""
    
    # 步骤5：测试镜像（可选）
    print_info "步骤5: 测试镜像..."
    read -p "是否测试运行镜像? (y/n) " -n 1 -r
    echo
    if [[ $REPLY =~ ^[Yy]$ ]]; then
        print_info "启动测试容器..."
        CONTAINER_ID=$(docker run -d -p 8000:8000 ${FULL_IMAGE_NAME})
        
        if [ $? -eq 0 ]; then
            print_success "容器启动成功，ID: ${CONTAINER_ID}"
            print_info "等待5秒..."
            sleep 5
            
            print_info "查看容器日志:"
            docker logs ${CONTAINER_ID} | tail -20
            
            print_info "停止并删除测试容器..."
            docker stop ${CONTAINER_ID} > /dev/null
            docker rm ${CONTAINER_ID} > /dev/null
            print_success "测试容器已清理"
        else
            print_error "容器启动失败"
        fi
    else
        print_warning "跳过测试步骤"
    fi
    echo ""
    
    # 步骤6：推送镜像
    if [ "$AUTO_PUSH" = true ]; then
        PUSH_CONFIRM="y"
    else
        print_info "步骤6: 推送镜像到仓库..."
        read -p "是否推送镜像到仓库? (y/n) " -n 1 -r
        echo
        PUSH_CONFIRM=$REPLY
    fi
    
    if [[ $PUSH_CONFIRM =~ ^[Yy]$ ]]; then
        print_info "推送镜像: ${FULL_IMAGE_NAME}"
        
        if docker push ${FULL_IMAGE_NAME}; then
            print_success "版本镜像推送成功"
        else
            print_error "镜像推送失败"
            print_warning "提示: 请先运行 'docker login' 登录镜像仓库"
            exit 1
        fi
        
        print_info "推送镜像: ${LATEST_IMAGE_NAME}"
        if docker push ${LATEST_IMAGE_NAME}; then
            print_success "latest镜像推送成功"
        else
            print_warning "latest镜像推送失败"
        fi
    else
        print_warning "跳过推送步骤"
    fi
    
    echo ""
    print_header "完成！"
    echo ""
    
    print_success "镜像信息:"
    echo "  完整名称: ${FULL_IMAGE_NAME}"
    echo "  Latest: ${LATEST_IMAGE_NAME}"
    echo ""
    
    print_info "下一步操作:"
    echo "  1. 更新 deployment/kubernetes/gateway-deployment.yaml"
    echo "     将 image 字段改为: ${FULL_IMAGE_NAME}"
    echo ""
    echo "  2. 应用更新:"
    echo "     kubectl apply -f deployment/kubernetes/gateway-deployment.yaml"
    echo ""
    echo "  3. 重启Gateway:"
    echo "     kubectl rollout restart deployment/gateway -n vehicle-iot-gateway"
    echo ""
    echo "  4. 查看状态:"
    echo "     kubectl get pods -n vehicle-iot-gateway"
    echo ""
}

# 执行主流程
main
