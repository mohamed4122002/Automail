#!/bin/bash
# Startup script for local development (Linux/Mac)
# Starts all required services for the marketing automation platform

echo "🚀 Starting Marketing Automation Platform - Local Development"
echo ""

# Check if Docker is running
if ! docker info > /dev/null 2>&1; then
    echo "❌ Docker is not running. Please start Docker first."
    exit 1
fi

echo "✓ Docker is running"
echo ""

# Start infrastructure with Docker Compose
echo "📦 Starting infrastructure (PostgreSQL, Redis, Backend, Celery Worker, Celery Beat)..."
docker-compose up -d

if [ $? -ne 0 ]; then
    echo "❌ Failed to start Docker services"
    exit 1
fi

echo ""
echo "⏳ Waiting for services to be healthy..."
sleep 5

# Check service health
echo ""
echo "🔍 Checking service status..."
docker-compose ps

echo ""
echo "✅ Backend services started successfully!"
echo ""
echo "📋 Service URLs:"
echo "   - Backend API: http://localhost:8000"
echo "   - API Docs: http://localhost:8000/docs"
echo "   - PostgreSQL: localhost:5432"
echo "   - Redis: localhost:6379"
echo ""
echo "🔧 Useful Commands:"
echo "   - View logs: docker-compose logs -f [service_name]"
echo "   - Stop all: docker-compose down"
echo "   - Restart service: docker-compose restart [service_name]"
echo ""
echo "📊 Check system health: curl http://localhost:8000/api/system/health"
echo ""

# Ask if user wants to start frontend
read -p "Start frontend development server? (y/n) " -n 1 -r
echo
if [[ $REPLY =~ ^[Yy]$ ]]; then
    echo ""
    echo "🎨 Starting frontend..."
    cd frontend
    npm run dev &
    cd ..
    echo "✓ Frontend started"
    echo "   - Frontend URL: http://localhost:5173"
fi

echo ""
echo "🎉 All services are running!"
echo ""
