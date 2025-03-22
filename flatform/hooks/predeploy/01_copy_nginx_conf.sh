#!/bin/bash
# Nginx 설정 파일을 올바른 위치로 복사

mkdir -p /var/app/current/nginx
cp /var/app/current/nginx/nginx.conf /var/app/current/nginx/default.conf