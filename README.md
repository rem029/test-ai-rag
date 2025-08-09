# 🤖 AI RAG Application

A comprehensive AI-powered Retrieval-Augmented Generation (RAG) application with multi-GPU support, featuring LLaMA models, embeddings, vision capabilities, and a modern chat interface.

## 🚀 Quick Start

### 1. Clone and Setup
```bash
git clone <repository-url>
cd test-ai-rag
```

### 2. Auto-Configure GPU Backend
```bash
# Auto-detect your GPU and configure the project
./gpu-setup.sh auto
```

### 3. Install Models
```bash
cd models
sh install-models.sh
cd ..
```

### 4. Start Services
```bash
# Start all services with auto-detected GPU backend
./gpu-setup.sh start

# Or manually with Docker Compose
docker compose --profile cuda up -d    # For NVIDIA GPUs
docker compose --profile vulkan up -d  # For AMD/Intel GPUs
```

### 5. Access Services
- **Open WebUI**: http://localhost:3000 (Chat Interface)
- **AI API**: http://localhost:8000 (FastAPI Backend)
- **PostgreSQL**: localhost:5433 (Database)
- **LLaMA Services**: Various ports (9001-9002)

---

## 📁 Project Structure

```
test-ai-rag/
├── apps/
│   └── ai/                    # Python FastAPI backend
│       ├── src/
│       │   ├── main.py        # FastAPI application
│       │   ├── controller/    # API controllers
│       │   ├── routes/        # API routes
│       │   ├── services/      # Business logic
│       │   └── utils/         # Utilities
│       └── requirements.txt
├── models/                    # AI models storage
│   └── install-models.sh      # Model installation script
├── docker-compose.yml         # Multi-GPU Docker setup
├── gpu-setup.sh              # GPU configuration script
├── .env                      # Environment configuration
└── .env.example              # Environment template
```

---

## 🔧 System Requirements

### Prerequisites
- **Docker & Docker Compose** (latest version)
- **Python 3.10+** (for local development)
- **pyenv** (recommended for Python management)

### GPU Support
- **NVIDIA GPUs**: RTX/GTX series, Tesla, Quadro (requires NVIDIA Container Toolkit)
- **AMD/Intel GPUs**: Radeon, Intel Arc, integrated graphics (requires Vulkan support)

---

## ⚙️ Configuration

### Environment Variables (`.env`)

Copy `.env.example` to `.env` and configure:

```bash
# Database Configuration
POSTGRES_USER=postgres
POSTGRES_PASSWORD=123
POSTGRES_DB=test_db
PG_PORT=5433

# Service Ports
WEBUI_PORT=3000           # Open WebUI
LLAMA_PORT=8000          # Main API
MODEL_MM_PORT=9001       # Vision/Multimodal service
MODEL_EMBED_PORT=9002    # Embedding service

# GPU Configuration (auto-configured by gpu-setup.sh)
GPU_BACKEND=cuda         # Options: 'cuda' or 'vulkan'
GPU_DEVICE_COUNT=1       # Number of GPUs to use
```

### GPU Backend Selection

The application automatically detects and configures the appropriate GPU backend:

#### 🟢 NVIDIA GPUs (CUDA)
- **Auto-detected for**: RTX 3060, RTX 4090, GTX 1080, Tesla, etc.
- **Requirements**: NVIDIA Container Toolkit
- **Services**: `llama-*-cuda`

#### 🔵 AMD/Intel GPUs (Vulkan)
- **Auto-detected for**: Radeon RX series, Intel Arc, integrated graphics
- **Requirements**: Vulkan drivers, `/dev/dri` devices
- **Services**: `llama-*-vulkan`

---

## 🐳 Docker Services

### Available Services

| Service | Purpose | Port | Profile |
|---------|---------|------|---------|
| `pgvector` | PostgreSQL with vector extension | 5433 | all |
| `open-webui` | Web chat interface | 3000 | all |
| `llama-full-cuda/vulkan` | Complete LLaMA chat model | - | cuda/vulkan |
| `llama-embed-cuda/vulkan` | Text embedding service | 9002 | cuda/vulkan |
| `llama-vision-cuda/vulkan` | Vision/multimodal service | 9001 | cuda/vulkan |

### Manual Docker Commands

```bash
# Start all CUDA services (NVIDIA GPUs)
docker compose --profile cuda up -d

# Start all Vulkan services (AMD/Intel GPUs)
docker compose --profile vulkan up -d

# Start specific services
docker compose --profile cuda up -d llama-embed-cuda pgvector

# Stop all services
docker compose down --remove-orphans
```

---

## 🎯 GPU Setup Script

The `gpu-setup.sh` script provides easy GPU configuration management:

```bash
# Auto-detect GPU and configure
./gpu-setup.sh auto

# Manual configuration
./gpu-setup.sh setup cuda      # Force NVIDIA/CUDA
./gpu-setup.sh setup vulkan    # Force AMD/Intel/Vulkan

# Service management
./gpu-setup.sh start           # Start all services
./gpu-setup.sh start llama-embed  # Start specific service
./gpu-setup.sh stop            # Stop all services
./gpu-setup.sh status          # Show current config

# Detection only
./gpu-setup.sh detect          # Show recommended backend
```

---

## 📦 Models

### Automatic Installation
```bash
cd models
sh install-models.sh  # Downloads required models
```

### Manual Installation
```bash
# Embedding model
wget -P ./models https://huggingface.co/nomic-ai/nomic-embed-text-v1.5-GGUF/resolve/main/nomic-embed-text-v1.5.Q4_K_M.gguf

# Vision/Multimodal model (Gemma-based)
wget -P ./models https://huggingface.co/lmstudio-community/gemma-2-2b-it-GGUF/resolve/main/gemma-2-2b-it-Q4_K_M.gguf

# Vision projection model
wget -P ./models https://huggingface.co/xtuner/llava-llama-3-8b-v1_1-gguf/resolve/main/llava-llama-3-8b-v1_1-mmproj-f16.gguf
```

---

## 🛠️ Development

### Local Python Development (apps/ai)

```bash
cd apps/ai

# Create virtual environment
python3 -m venv .venv
source .venv/bin/activate

# Install dependencies
pip install fastapi uvicorn ollama python-dotenv psycopg2-binary httpx rich pillow

# Run development server
uvicorn src.main:app --port 8000 --reload
```

### API Endpoints

- `GET /health` - Health check
- `POST /message` - Chat with streaming support
- `POST /embed` - Generate embeddings
- `GET /` - API documentation

### Features

- **🎨 Rich Console Output**: Beautiful terminal formatting with timestamps and session logging
- **🖼️ Image Preview**: ASCII art preview of images in terminal
- **📝 Session Logging**: Automatic logging of all interactions by session ID
- **🔄 Streaming Responses**: Real-time streaming chat responses
- **🎵 Audio Support**: Text-to-speech with automatic audio playback
- **🤖 Robot Navigation**: Vision-based navigation with safety-first policies

---

## 🔍 Troubleshooting

### GPU Issues

#### NVIDIA GPU Not Detected
```bash
# Check GPU
nvidia-smi

# Install NVIDIA Container Toolkit
curl -fsSL https://nvidia.github.io/libnvidia-container/gpgkey | sudo gpg --dearmor -o /usr/share/keyrings/nvidia-container-toolkit-keyring.gpg
curl -s -L https://nvidia.github.io/libnvidia-container/stable/deb/nvidia-container-toolkit.list | sed 's#deb https://#deb [signed-by=/usr/share/keyrings/nvidia-container-toolkit-keyring.gpg] https://#g' | sudo tee /etc/apt/sources.list.d/nvidia-container-toolkit.list
sudo apt-get update && sudo apt-get install -y nvidia-container-toolkit
sudo nvidia-ctk runtime configure --runtime=docker
sudo systemctl restart docker

# Test Docker GPU access
docker run --rm --gpus all nvidia/cuda:12.1-runtime-ubuntu22.04 nvidia-smi
```

#### AMD/Intel GPU Issues
```bash
# Check DRI devices
ls -la /dev/dri

# Install Vulkan support (Ubuntu/Debian)
sudo apt install vulkan-tools vulkan-utils mesa-vulkan-drivers

# Test Vulkan
vulkaninfo --summary
```

### Service Issues

```bash
# Check service logs
docker logs llama-embed
docker logs open-webui

# Reset configuration
./gpu-setup.sh auto

# Clean restart
docker compose down --remove-orphans
./gpu-setup.sh start
```

### WSL2 Specific

For Windows WSL2 users with NVIDIA GPUs:
- Ensure NVIDIA Container Toolkit is installed in WSL2
- Use CUDA backend (`GPU_BACKEND=cuda`)
- `/dev/dri` devices are not available in WSL2

---

## 🌟 Advanced Usage

### Multi-System Deployment

**On NVIDIA system**:
```bash
./gpu-setup.sh setup cuda
./gpu-setup.sh start
```

**On AMD system**:
```bash  
./gpu-setup.sh setup vulkan
./gpu-setup.sh start
```

### Custom Model Configuration

Edit `docker-compose.yml` to use different models:

```yaml
command:
  [
    "-m",
    "/models/your-custom-model.gguf",
    "--port",
    "8000",
    "--host", 
    "0.0.0.0",
  ]
```

### Resource Allocation

Configure GPU memory and compute resources in `.env`:

```bash
GPU_DEVICE_COUNT=2  # Use 2 GPUs
```

---

## 📚 API Documentation

Once running, visit:
- **Interactive API Docs**: http://localhost:8000/docs
- **ReDoc**: http://localhost:8000/redoc

---

## 🤝 Contributing

1. Fork the repository
2. Create a feature branch
3. Make your changes
4. Test with `./gpu-setup.sh auto` 
5. Submit a pull request

---

## 📄 License

This project is licensed under the MIT License - see the LICENSE file for details.
