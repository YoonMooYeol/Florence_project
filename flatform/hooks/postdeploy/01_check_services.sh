#!/bin/bash
# 서비스가 올바르게 실행되었는지 확인
echo "Checking services..."
docker ps
docker-compose ps