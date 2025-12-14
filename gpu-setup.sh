#!/bin/bash

# GPU Backend Setup Script for AI RAG Docker Compose
# This script helps configure and run services with different GPU backends

set -e

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
CYAN='\033[0;36m'

NC='\033[0m' # No Color

# Detect container engine (docker or podman)
detect_container_engine() {
    if command -v docker &> /dev/null; then
        CONTAINER_CMD="docker"
    elif command -v podman &> /dev/null; then
        CONTAINER_CMD="podman"
    else
        print_error "Neither Docker nor Podman is installed. Please install one to continue."
        exit 1
    fi
    print_info "Using container engine: $CONTAINER_CMD"
}

# Default values
DEFAULT_GPU_BACKEND="vulkan"
ENV_FILE=".env"

# Function to print colored output
print_info() {
    echo -e "${BLUE}ℹ️  $1${NC}"
}

print_success() {
    echo -e "${GREEN}✅ $1${NC}"
}

print_warning() {
    echo -e "${YELLOW}⚠️  $1${NC}"
}

print_error() {
    echo -e "${RED}❌ $1${NC}"
}

print_header() {
    echo -e "${CYAN}🚀 $1${NC}"
}

# Function to detect GPU (silent detection)
detect_gpu_silent() {
    if command -v nvidia-smi &> /dev/null; then
        if nvidia-smi &> /dev/null; then
            echo "cuda"
            return
        fi
    fi
    
    if [ -d "/dev/dri" ]; then
        echo "vulkan"
        return
    fi
    
    echo "vulkan"
}

# Function to detect GPU (with output)
detect_gpu() {
    print_info "Detecting GPU hardware..."
    
    if command -v nvidia-smi &> /dev/null; then
        if nvidia-smi &> /dev/null; then
            print_success "NVIDIA GPU detected"
            echo "cuda"
            return
        fi
    fi
    
    if [ -d "/dev/dri" ]; then
        print_success "DRI devices found (likely AMD/Intel GPU)"
        echo "vulkan"
        return
    fi
    
    print_warning "No GPU detected, defaulting to Vulkan"
    echo "vulkan"
}

# Function to create or update .env file
setup_env() {
    local gpu_backend=$1
    
    if [ ! -f "$ENV_FILE" ]; then
        print_info "Creating $ENV_FILE from .env.example..."
        cp .env.example "$ENV_FILE"
    fi
    
    # Clean the .env file of any contaminated entries first
    if [ -f "$ENV_FILE" ]; then
        # Remove any lines with color codes or GPU_BACKEND entries
        grep -v -E "(GPU_BACKEND=|\\[0;|✅|ℹ️|cuda$|vulkan$)" "$ENV_FILE" > "$ENV_FILE.tmp" || true
        mv "$ENV_FILE.tmp" "$ENV_FILE"
    fi
    
    # Add clean GPU_BACKEND entry
    echo "GPU_BACKEND=$gpu_backend" >> "$ENV_FILE"
    
    print_success "Set GPU_BACKEND=$gpu_backend in $ENV_FILE"
}

# Function to show current configuration
show_config() {
    print_header "Current Configuration"
    
    if [ -f "$ENV_FILE" ]; then
        local gpu_backend=$(grep "^GPU_BACKEND=" "$ENV_FILE" | tail -1 | cut -d'=' -f2)
        if [ -z "$gpu_backend" ]; then
            gpu_backend=$DEFAULT_GPU_BACKEND
        fi
        echo -e "GPU Backend: ${GREEN}$gpu_backend${NC}"
        
        # Show relevant services
        if [ "$gpu_backend" = "cuda" ]; then
            echo -e "Services: ${CYAN}llama-full-cuda, llama-embed-cuda, llama-vision-cuda${NC}"
        else
            echo -e "Services: ${CYAN}llama-full-vulkan, llama-embed-vulkan, llama-vision-vulkan${NC}"
        fi
    else
        echo -e "No $ENV_FILE found, using default: ${GREEN}$DEFAULT_GPU_BACKEND${NC}"
    fi
}


# Function to start services with correct profile
start_services() {
    local gpu_backend=$1
    local services=$2

    detect_container_engine
    print_info "Starting services with $gpu_backend backend..."

    if [ -z "$services" ]; then
        # Start all services with the specified profile
        $CONTAINER_CMD compose --profile "$gpu_backend" up -d
    else
        # Start specific services
        $CONTAINER_CMD compose --profile "$gpu_backend" up -d $services
    fi

    print_success "Services started successfully!"
}

# Function to stop all services
stop_services() {
    detect_container_engine
    print_info "Stopping all services..."
    $CONTAINER_CMD compose --profile cuda --profile vulkan down
    print_success "All services stopped!"
}

# Function to show usage
show_usage() {
    echo "Usage: $0 [COMMAND] [OPTIONS]"
    echo ""
    echo "Commands:"
    echo "  detect              - Detect GPU and suggest backend"
    echo "  setup [cuda|vulkan] - Setup GPU backend in .env file"
    echo "  start [services...] - Start services with current backend"
    echo "  stop                - Stop all services"
    echo "  status              - Show current configuration"
    echo "  auto                - Auto-detect GPU and setup"
    echo ""
    echo "Examples:"
    echo "  $0 auto                     # Auto-detect and setup"
    echo "  $0 setup cuda               # Setup for NVIDIA GPU"
    echo "  $0 setup vulkan             # Setup for AMD/Intel GPU"
    echo "  $0 start                    # Start all services"
    echo "  $0 start llama-embed        # Start only embed service"
    echo "  $0 stop                     # Stop all services"
}

# Main script logic
case "$1" in
    "detect")
        detected_gpu=$(detect_gpu)
        echo "Recommended backend: $detected_gpu"
        ;;
    
    "setup")
        if [ -z "$2" ]; then
            print_error "Please specify backend: cuda or vulkan"
            exit 1
        fi
        if [ "$2" != "cuda" ] && [ "$2" != "vulkan" ]; then
            print_error "Invalid backend. Use 'cuda' or 'vulkan'"
            exit 1
        fi
        setup_env "$2"
        ;;
    
    "auto")
        print_header "Auto-detecting GPU and setting up configuration..."
        detected_gpu=$(detect_gpu_silent)
        print_info "Detected GPU backend: $detected_gpu"
        setup_env "$detected_gpu"
        show_config
        ;;
    
    "start")
        if [ ! -f "$ENV_FILE" ]; then
            print_warning "$ENV_FILE not found. Running auto-setup..."
            detected_gpu=$(detect_gpu)
            setup_env "$detected_gpu"
        fi
        
        gpu_backend=$(grep "^GPU_BACKEND=" "$ENV_FILE" | cut -d'=' -f2)
        if [ -z "$gpu_backend" ]; then
            gpu_backend=$DEFAULT_GPU_BACKEND
        fi
        
        shift # Remove 'start' from arguments
        start_services "$gpu_backend" "$*"
        ;;
    
    "stop")
        stop_services
        ;;
    
    "status"|"config")
        show_config
        ;;
    
    "help"|"-h"|"--help")
        show_usage
        ;;
    
    *)
        if [ -z "$1" ]; then
            show_config
            echo ""
            show_usage
        else
            print_error "Unknown command: $1"
            show_usage
            exit 1
        fi
        ;;
esac
