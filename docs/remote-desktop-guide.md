# Remote Desktop Guide

## Accessing Bytebot Desktop

- **Local Access:** [http://192.168.1.104:9990](http://192.168.1.104:9990)
- **LAN Access:** Use your host IP on the same Wi-Fi network.
- **Remote Access (secure):**

```bash
ssh -L 9990:localhost:9990 sysop@your_public_ip
```

or with Cloudflare Tunnel / ngrok for encrypted remote use.

