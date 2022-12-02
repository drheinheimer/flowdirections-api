server {
    server_name api.flowdirections.io;
    location / {
        proxy_pass http://0.0.0.0:8000;
    }
}
