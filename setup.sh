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
    local inference_mode=$2
    local lm_studio_url=$3
    
    if [ ! -f "$ENV_FILE" ]; then
        print_info "Creating $ENV_FILE from .env.example..."
        if [ -f ".env.example" ]; then
            cp .env.example "$ENV_FILE"
        else
            touch "$ENV_FILE"
        fi
    fi
    
    # Clean the .env file of relevant entries
    if [ -f "$ENV_FILE" ]; then
        grep -v -E "(GPU_BACKEND=|INFERENCE_MODE=|LM_STUDIO_URL=|\\[0;|✅|ℹ️|cuda$|vulkan$)" "$ENV_FILE" > "$ENV_FILE.tmp" || true
        mv "$ENV_FILE.tmp" "$ENV_FILE"
    fi
    
    # Add clean entries
    echo "GPU_BACKEND=$gpu_backend" >> "$ENV_FILE"
    echo "INFERENCE_MODE=$inference_mode" >> "$ENV_FILE"
    [ -n "$lm_studio_url" ] && echo "LM_STUDIO_URL=$lm_studio_url" >> "$ENV_FILE"
    
    print_success "Configuration saved to $ENV_FILE"
    print_info "Backend: $gpu_backend, Mode: $inference_mode"
}

# Function to interactive setup
interactive_setup() {
    print_header "Interactive GPU & Inference Setup"
    
    echo -e "Choose your inference mode:"
    echo -e "1) ${CYAN}llama.cpp (Docker)${NC} - Managed locally via containers (Recommended)"
    echo -e "2) ${CYAN}LM Studio API${NC} - Use an existing LM Studio instance"
    read -p "Selection [1-2]: " mode_choice

    local inference_mode="llamacpp"
    local lm_studio_url=""
    
    if [ "$mode_choice" == "2" ]; then
        inference_mode="lmstudio"
        read -p "Enter LM Studio Base URL [http://localhost:1234/v1]: " lm_studio_url
        lm_studio_url=${lm_studio_url:-"http://localhost:1234/v1"}
    fi

    local detected_gpu=$(detect_gpu_silent)
    echo -e "\nDetected GPU: ${GREEN}$detected_gpu${NC}"
    read -p "Use this backend? (y/n) [y]: " use_detected
    
    local gpu_backend=$detected_gpu
    if [[ "$use_detected" =~ ^[Nn]$ ]]; then
        echo -e "Choose backend:"
        echo -e "1) cuda (NVIDIA)"
        echo -e "2) vulkan (AMD/Intel/Generic)"
        read -p "Selection [1-2]: " backend_choice
        [ "$backend_choice" == "1" ] && gpu_backend="cuda" || gpu_backend="vulkan"
    fi

    setup_env "$gpu_backend" "$inference_mode" "$lm_studio_url"
}

# Function to show current configuration
show_config() {
    print_header "Current Configuration"
    
    if [ -f "$ENV_FILE" ]; then
        local gpu_backend=$(grep "^GPU_BACKEND=" "$ENV_FILE" | tail -1 | cut -d'=' -f2)
        local inference_mode=$(grep "^INFERENCE_MODE=" "$ENV_FILE" | tail -1 | cut -d'=' -f2)
        local lm_studio_url=$(grep "^LM_STUDIO_URL=" "$ENV_FILE" | tail -1 | cut -d'=' -f2)

        gpu_backend=${gpu_backend:-$DEFAULT_GPU_BACKEND}
        inference_mode=${inference_mode:-"llamacpp"}

        echo -e "GPU Backend:    ${GREEN}$gpu_backend${NC}"
        echo -e "Inference Mode: ${GREEN}$inference_mode${NC}"
        [ -n "$lm_studio_url" ] && echo -e "LM Studio URL:  ${CYAN}$lm_studio_url${NC}"
        
        # Show relevant services
        if [ "$inference_mode" == "llamacpp" ]; then
            if [ "$gpu_backend" = "cuda" ]; then
                echo -e "Services:       ${CYAN}llama-full-cuda, llama-embed-cuda, llama-vision-cuda${NC}"
            else
                echo -e "Services:       ${CYAN}llama-full-vulkan, llama-embed-vulkan, llama-vision-vulkan${NC}"
            fi
        else
            echo -e "Services:       ${YELLOW}External API (Python apps only)${NC}"
        fi
    else
        echo -e "No $ENV_FILE found. Run '${BLUE}./gpu-setup.sh setup${NC}'"
    fi
}


# Function to start services with correct profile
start_services() {
    local gpu_backend=$1
    local services=$2
    
    local inference_mode=$(grep "^INFERENCE_MODE=" "$ENV_FILE" | tail -1 | cut -d'=' -f2)
    inference_mode=${inference_mode:-"llamacpp"}

    detect_container_engine
    
    if [ "$inference_mode" == "lmstudio" ]; then
        print_info "Inference mode is LM Studio. Starting only core services (DB, WebUI)..."
        # Filter out llama services if starting "all"
        if [ -z "$services" ]; then
            $CONTAINER_CMD compose up -d pgvector searxng open-webui
        else
            $CONTAINER_CMD compose up -d $services
        fi
    else
        print_info "Starting services with $gpu_backend backend..."
        if [ -z "$services" ]; then
            $CONTAINER_CMD compose --profile "$gpu_backend" up -d
        else
            $CONTAINER_CMD compose --profile "$gpu_backend" up -d $services
        fi
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
    echo "  setup               - Interactive setup (GPU + Inference Mode)"
    echo "  start [services...] - Start services with current backend"
    echo "  stop                - Stop all services"
    echo "  status              - Show current configuration"
    echo "  auto                - Auto-detect GPU and setup (defaults to llama.cpp)"
    echo ""
    echo "Examples:"
    echo "  $0 setup                    # Run interactive setup"
    echo "  $0 auto                     # Auto-detect and setup"
}

# Main script logic
case "$1" in
    "detect")
        detected_gpu=$(detect_gpu)
        echo "Recommended backend: $detected_gpu"
        ;;
    
    "setup")
        if [ -n "$2" ]; then
            # Support legacy setup command syntax if someone still uses 'setup cuda'
            if [ "$2" == "cuda" ] || [ "$2" == "vulkan" ]; then
                setup_env "$2" "llamacpp" ""
            else
                print_error "Invalid backend. Use 'cuda' or 'vulkan' or run without arguments for interactive setup."
                exit 1
            fi
        else
            interactive_setup
        fi
        ;;
    
    "auto")
        print_header "Auto-detecting GPU and setting up configuration..."
        detected_gpu=$(detect_gpu_silent)
        print_info "Detected GPU backend: $detected_gpu"
        setup_env "$detected_gpu" "llamacpp" ""
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
