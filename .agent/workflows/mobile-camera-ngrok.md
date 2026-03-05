---
description: How to enable mobile camera access for self-enrollment using ngrok
---

# Mobile Camera Access with ngrok

## Problem

Mobile browsers require HTTPS for camera access (`getUserMedia`). Running Flask locally on HTTP doesn't allow mobile camera.

## Solution

Use ngrok to create a public HTTPS tunnel to your local Flask server.

## Steps

### 1. Install ngrok (one-time)

Download from https://ngrok.com/download or:

```bash
npm install -g ngrok
```

### 2. Start Flask server normally

```bash
python app.py
```

### 3. In a separate terminal, start ngrok

```bash
ngrok http 5000
```

### 4. Get your ngrok URL

ngrok will display something like:

```
Forwarding: https://abc123.ngrok-free.app -> http://localhost:5000
```

### 5. Set the BASE_URL environment variable

Before creating enrollment links, set:

**Windows (PowerShell):**

```powershell
$env:BASE_URL = "https://abc123.ngrok-free.app"
```

**Windows (CMD):**

```cmd
set BASE_URL=https://abc123.ngrok-free.app
```

**Linux/Mac:**

```bash
export BASE_URL="https://abc123.ngrok-free.app"
```

### 6. Restart Flask and create enrollment links

The generated links will now use the ngrok HTTPS URL, accessible on mobile!

## Notes

- ngrok free tier gives you a random URL each time
- The URL changes every time you restart ngrok
- For persistent URLs, consider ngrok paid plan or alternatives like localtunnel
