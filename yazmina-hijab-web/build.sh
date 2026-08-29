#!/bin/bash
# Build script for Render.com deployment

echo "=== Building Yazmina Hijab Web ==="

# Install backend dependencies
echo "Installing backend dependencies..."
cd backend
pip install -r requirements.txt
cd ..

# Build frontend
echo "Building frontend..."
cd frontend
npm install
npm run build
cd ..

echo "=== Build complete ==="
