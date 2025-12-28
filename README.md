# 🚀 Posture Detector

Real-time posture analysis using React frontend + Python OpenCV/MediaPipe backend. Detects slouching, forward head posture, and provides live feedback.

## ✨ Features
- Real-time pose detection** using MediaPipe Pose
- Posture scoring (0-100) with visual feedback
- Docker deployment ready
- Responsive React UI with live camera feed
- Cross-platform (Web/Desktop)

## 🛠 Tech Stack
```
Frontend: React 18, Tailwind CSS
Backend: Python 3.11, Flask, OpenCV, MediaPipe
Deployment: Docker Compose
```

## 🚀 Quick Start

### 1. Clone & Install
```
git clone https://github.com/srijaa16/posture-detector.git
cd posture-detector
```

### 2. Backend (Terminal 1)
```
cd backend
pip install -r requirements.txt
python main.py
```

### 3. Frontend (Terminal 2)
```
cd frontend
npm install
npm start
```

### 4. Docker (Recommended)
```
docker-compose up --build
```

## 📱 Access
- **Frontend**: http://localhost:3000
- **Backend API**: http://localhost:5000/analyze

## 🎯 Live Demo
Enable webcam → See real-time posture analysis + score!

## 📁 Project Structure
```
posture-detector/
├── backend/          # Flask + OpenCV/MediaPipe
├── frontend/         # React + Tailwind
├── Dockerfile
└── docker-compose.yml
```

## 🤝 Contributing
1. Fork repo
2. Create feature branch
3. PR to `main`

## 📄 License
MIT License - Free to use/modify
