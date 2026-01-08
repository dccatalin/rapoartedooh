# RapoarteDOOH Deployment Guide (Apache)

This archive contains the files necessary to run the RapoarteDOOH application on a server.

## Prerequisites
1. Linux server with Python 3.9+ installed.
2. Apache with `mod_proxy` and `mod_proxy_wstunnel` enabled.

## Setup Instructions
1. Extract the archive to `/var/www/rapoartedooh`.
2. Create a virtual environment: `python3 -m venv .venv`.
3. Activate `.venv`: `source .venv/bin/activate`.
4. Install dependencies: `pip install -r requirements.txt`.
5. Run the application: `./run_server.sh`.

## Apache Configuration
Add the following to your Apache virtual host configuration:

```apache
<VirtualHost *:80>
    ServerName yourdomain.com

    ProxyPreserveHost On
    ProxyPass / http://localhost:8501/
    ProxyPassReverse / http://localhost:8501/

    # WebSocket support for Streamlit
    RewriteEngine On
    RewriteCond %{HTTP:Upgrade} =websocket [NC]
    RewriteCond %{HTTP:Connection} upgrade [NC]
    RewriteRule ^/?(.*) "ws://localhost:8501/$1" [P,L]
</VirtualHost>
```

Remember to restart Apache: `sudo systemctl restart apache2`
