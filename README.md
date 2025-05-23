# 📺 Youtube Crawler API

A **FastAPI-based YouTube Crawler** that extracts video, channel, playlist, and comment data from YouTube using internal (unofficial) APIs.

---

## ✨ Features

- 🔍 Search videos by keyword
- 📺 Get video details: title, duration, views, etc.
- 📂 Fetch all videos from a specific channel (by ID or handle)
- 📃 Retrieve all playlists from a channel
- 📼 Extract all videos inside a playlist
- 💬 Get full comments and replies count of a video
- 👥 Get channel metadata: banner, avatar, subscribers, description
- 🔴 Get livestreams from a channel or globally  
- 📈 Discover trending videos on YouTube 
- 🌍 Get full videos by location (with grid-based radius and async fetching)  
- 🌐 Proxy support (optional)
- ⚡ High-performance async crawler using `httpx` and FastAPI

---

## 🖥️ Swagger UI Preview

> Auto-generated docs with FastAPI:

---

## 📦 Installation

```bash
git clone https://github.com/yourname/youtube-crawler-api.git
cd youtube-crawler-api

# Create virtual env (optional)
python -m venv venv
source venv/bin/activate

# Install dependencies
pip install -r requirements.txt
