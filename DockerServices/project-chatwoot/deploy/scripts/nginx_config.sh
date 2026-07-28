
sudo cp ../nginx/chatwoot /etc/nginx/sites-available

sudo ln -s /etc/nginx/sites-available/chatwoot /etc/nginx/sites-enabled

sudo nginx -t && sudo systemctl restart nginx.service