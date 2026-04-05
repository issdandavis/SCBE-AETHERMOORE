# NGINX
> Source: Context7 MCP | Category: infra
> Fetched: 2026-04-04

### Using nginx as HTTP load balancer — Introduction

Source: https://nginx.org/en/docs/http/load_balancing.html

Load balancing across multiple application instances is a fundamental technique for optimizing resource utilization, maximizing throughput, and reducing latency. By distributing traffic across several application servers, NGINX acts as an efficient HTTP load balancer that improves the overall performance, scalability, and fault tolerance of web applications. This reverse proxy implementation supports various protocols including HTTP, HTTPS, FastCGI, uwsgi, SCGI, memcached, and gRPC.

---

### Load Balancing Methods

Source: https://nginx.org/en/docs/http/load_balancing.html

NGINX supports several load balancing mechanisms:
- **Round-robin** (default) — distributes requests sequentially among servers
- **Least-connected** — assigns the next request to the server with the fewest active connections
- **IP-hash** — uses a hash function based on the client's IP address to determine server selection, ensuring consistent routing

---

### Configure Default Round-Robin Load Balancing

Source: https://nginx.org/en/docs/http/load_balancing.html

```nginx
http {
    upstream myapp1 {
        server srv1.example.com;
        server srv2.example.com;
        server srv3.example.com;
    }

    server {
        listen 80;

        location / {
            proxy_pass http://myapp1;
        }
    }
}
```

---

### Configure Least-Connected Load Balancing

Source: https://nginx.org/en/docs/http/load_balancing.html

```nginx
upstream myapp1 {
    least_conn;
    server srv1.example.com;
    server srv2.example.com;
    server srv3.example.com;
}
```

---

### ngx_http_upstream_module Overview

Source: https://nginx.org/en/docs/http/ngx_http_upstream_module.html

The `ngx_http_upstream_module` module is used to define groups of servers that can be referenced by the proxy_pass, fastcgi_pass, uwsgi_pass, scgi_pass, memcached_pass, and grpc_pass directives. It is fundamental for implementing load balancing and high availability in NGINX.

**Key Directives:**
- `upstream` — Defines a server group
- `server` — Specifies a backend server within a group
- `zone` — Configures shared memory zone for dynamic configuration
- `hash` — Implements hashing load balancing algorithm
- `ip_hash` — Implements IP-based hashing load balancing
- `keepalive` — Configures keepalive connections to backend servers
- `least_conn` — Implements least connection load balancing algorithm
- `least_time` — Implements least response time load balancing algorithm
- `random` — Implements random load balancing algorithm
- `sticky` — Implements session persistence (sticky sessions)

**Basic Example:**

```nginx
upstream backend {
    server backend1.example.com       weight=5;
    server backend2.example.com:8080;
    server unix:/tmp/backend3;

    server backup1.example.com:8080   backup;
    server backup2.example.com:8080   backup;
}

server {
    location / {
        proxy_pass http://backend;
    }
}
```

**Dynamic with Health Checks (commercial):**

```nginx
resolver 10.0.0.1;

upstream dynamic {
    zone upstream_dynamic 64k;

    server backend1.example.com      weight=5;
    server backend2.example.com:8080 fail_timeout=5s slow_start=30s;
    server 192.0.2.1                 max_fails=3;
    server backend3.example.com      resolve;
    server backend4.example.com      service=http resolve;

    server backup1.example.com:8080  backup;
    server backup2.example.com:8080  backup;
}

server {
    location / {
        proxy_pass http://dynamic;
        health_check;
    }
}
```
