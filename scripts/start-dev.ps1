#!/usr/bin/env pwsh
# Startup script for local development
# Starts all required services for the marketing automation platform

Write-Host "🚀 Starting Marketing Automation Platform - Local Development" -ForegroundColor Cyan
Write-Host ""

# Check if Docker is running
$dockerRunning = docker info 2>$null
if ($LASTEXITCODE -ne 0) {
    Write-Host "❌ Docker is not running. Please start Docker Desktop first." -ForegroundColor Red
    exit 1
}

Write-Host "✓ Docker is running" -ForegroundColor Green
Write-Host ""

# Start infrastructure with Docker Compose
Write-Host "📦 Starting infrastructure (PostgreSQL, Redis, Backend, Celery Worker, Celery Beat)..." -ForegroundColor Yellow
docker-compose up -d

if ($LASTEXITCODE -ne 0) {
    Write-Host "❌ Failed to start Docker services" -ForegroundColor Red
    exit 1
}

Write-Host ""
Write-Host "⏳ Waiting for services to be healthy..." -ForegroundColor Yellow
Start-Sleep -Seconds 5

# Check service health
Write-Host ""
Write-Host "🔍 Checking service status..." -ForegroundColor Yellow
docker-compose ps

Write-Host ""
Write-Host "✅ Backend services started successfully!" -ForegroundColor Green
Write-Host ""
Write-Host "📋 Service URLs:" -ForegroundColor Cyan
Write-Host "   - Backend API: http://localhost:8000" -ForegroundColor White
Write-Host "   - API Docs: http://localhost:8000/docs" -ForegroundColor White
Write-Host "   - PostgreSQL: localhost:5432" -ForegroundColor White
Write-Host "   - Redis: localhost:6379" -ForegroundColor White
Write-Host ""
Write-Host "🔧 Useful Commands:" -ForegroundColor Cyan
Write-Host "   - View logs: docker-compose logs -f [service_name]" -ForegroundColor White
Write-Host "   - Stop all: docker-compose down" -ForegroundColor White
Write-Host "   - Restart service: docker-compose restart [service_name]" -ForegroundColor White
Write-Host ""
Write-Host "📊 Check system health: curl http://localhost:8000/api/system/health" -ForegroundColor Cyan
Write-Host ""

# Ask if user wants to start frontend
$startFrontend = Read-Host "Start frontend development server? (y/n)"
if ($startFrontend -eq "y" -or $startFrontend -eq "Y") {
    Write-Host ""
    Write-Host "🎨 Starting frontend..." -ForegroundColor Yellow
    Set-Location frontend
    Start-Process powershell -ArgumentList "-NoExit", "-Command", "npm run dev"
    Set-Location ..
    Write-Host "✓ Frontend started in new window" -ForegroundColor Green
    Write-Host "   - Frontend URL: http://localhost:5173" -ForegroundColor White
}

Write-Host ""
Write-Host "🎉 All services are running!" -ForegroundColor Green
Write-Host ""
