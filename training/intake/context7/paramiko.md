# Paramiko

Paramiko is a Python implementation of the SSHv2 protocol providing both client and server functionality. It supports authentication via passwords, private keys (RSA, ECDSA, Ed25519), and SSH agent forwarding.

## SSH Client with Command Execution

The high-level `SSHClient` class handles host key verification, authentication, and command execution:

```python
import paramiko

# Basic SSH client usage
client = paramiko.SSHClient()
client.set_missing_host_key_policy(paramiko.AutoAddPolicy())

client.connect(
    hostname="192.168.1.100",
    port=22,
    username="deploy",
    password="secret"
)

# Execute a command
stdin, stdout, stderr = client.exec_command("ls -la /var/log")
print(stdout.read().decode())
print(stderr.read().decode())

# Execute with timeout
stdin, stdout, stderr = client.exec_command("long_running_task", timeout=30)
exit_status = stdout.channel.recv_exit_status()
print(f"Exit status: {exit_status}")

# Execute multiple commands sequentially
commands = ["df -h", "free -m", "uptime"]
for cmd in commands:
    stdin, stdout, stderr = client.exec_command(cmd)
    print(f"=== {cmd} ===")
    print(stdout.read().decode())

client.close()
```

## Password Authentication

```python
import paramiko

client = paramiko.SSHClient()
client.set_missing_host_key_policy(paramiko.AutoAddPolicy())

# Password authentication
client.connect(
    hostname="server.example.com",
    port=22,
    username="admin",
    password="secure_password",
    timeout=10,
    banner_timeout=15
)

# Interactive password (for sudo or prompts)
stdin, stdout, stderr = client.exec_command("sudo apt update")
stdin.write("password\n")
stdin.flush()
output = stdout.read().decode()

client.close()
```

## Private Key Authentication

Authenticate using RSA, ECDSA, or Ed25519 private keys:

```python
import paramiko

client = paramiko.SSHClient()
client.set_missing_host_key_policy(paramiko.AutoAddPolicy())

# RSA key authentication
rsa_key = paramiko.RSAKey.from_private_key_file("/home/user/.ssh/id_rsa")
client.connect("server.example.com", username="deploy", pkey=rsa_key)

# RSA key with passphrase
rsa_key = paramiko.RSAKey.from_private_key_file(
    "/home/user/.ssh/id_rsa",
    password="key_passphrase"
)
client.connect("server.example.com", username="deploy", pkey=rsa_key)

# ECDSA key authentication
ecdsa_key = paramiko.ECDSAKey.from_private_key_file("/home/user/.ssh/id_ecdsa")
client.connect("server.example.com", username="deploy", pkey=ecdsa_key)

# Ed25519 key authentication
ed25519_key = paramiko.Ed25519Key.from_private_key_file("/home/user/.ssh/id_ed25519")
client.connect("server.example.com", username="deploy", pkey=ed25519_key)

# Key from string
from io import StringIO
key_str = """-----BEGIN RSA PRIVATE KEY-----
MIIEpAIBAAKCAQEA...
-----END RSA PRIVATE KEY-----"""
rsa_key = paramiko.RSAKey.from_private_key(StringIO(key_str))

# Using key_filename parameter (auto-detects key type)
client.connect(
    "server.example.com",
    username="deploy",
    key_filename="/home/user/.ssh/id_ed25519"
)

stdin, stdout, stderr = client.exec_command("whoami")
print(stdout.read().decode().strip())
client.close()
```

## Transport API

The low-level `Transport` class gives direct control over the SSH connection:

```python
import paramiko

# Create transport
transport = paramiko.Transport(("server.example.com", 22))
transport.connect(username="deploy", password="secret")

# Open a channel for command execution
channel = transport.open_session()
channel.exec_command("uname -a")

# Read output
output = b""
while True:
    data = channel.recv(4096)
    if not data:
        break
    output += data
print(output.decode())

exit_status = channel.recv_exit_status()
channel.close()

# Transport with key authentication
transport = paramiko.Transport(("server.example.com", 22))
rsa_key = paramiko.RSAKey.from_private_key_file("/home/user/.ssh/id_rsa")
transport.connect(username="deploy", pkey=rsa_key)

# Check transport status
print(f"Active: {transport.is_active()}")
print(f"Authenticated: {transport.is_authenticated()}")

transport.close()
```

## SFTP Context Manager

Transfer files over SSH using the SFTP subsystem:

```python
import paramiko
import os

client = paramiko.SSHClient()
client.set_missing_host_key_policy(paramiko.AutoAddPolicy())
client.connect("server.example.com", username="deploy", key_filename="/home/user/.ssh/id_rsa")

# SFTP as context manager
with client.open_sftp() as sftp:
    # Upload a file
    sftp.put("/local/path/config.json", "/remote/path/config.json")

    # Download a file
    sftp.get("/remote/path/data.csv", "/local/path/data.csv")

    # List directory
    for entry in sftp.listdir_attr("/remote/path"):
        print(f"{entry.filename} - {entry.st_size} bytes")

    # Create directory
    sftp.mkdir("/remote/path/new_dir")

    # Remove file
    sftp.remove("/remote/path/old_file.txt")

    # Stat a file
    stat = sftp.stat("/remote/path/config.json")
    print(f"Size: {stat.st_size}, Modified: {stat.st_mtime}")

    # Change permissions
    sftp.chmod("/remote/path/script.sh", 0o755)

    # Rename
    sftp.rename("/remote/path/old.txt", "/remote/path/new.txt")

client.close()

# SFTP via Transport (lower level)
transport = paramiko.Transport(("server.example.com", 22))
transport.connect(username="deploy", password="secret")
sftp = paramiko.SFTPClient.from_transport(transport)

sftp.put("local_file.txt", "/remote/file.txt")
sftp.close()
transport.close()
```
