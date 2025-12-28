from fastapi import FastAPI, UploadFile, File, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse, JSONResponse
import cv2
import numpy as np
import tempfile
import mediapipe as mp
import os
import uuid
from pathlib import Path

app = FastAPI()

# CORS for frontend
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Update to your frontend domain in production
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Video storage
VIDEOS_DIR = Path("videos")
VIDEOS_DIR.mkdir(parents=True, exist_ok=True)

app.mount("/video", StaticFiles(directory=str(VIDEOS_DIR)), name="video")

@app.get("/stream/{filename}")
def stream_video(filename: str):
    path = VIDEOS_DIR / filename
    if not path.exists():
        raise HTTPException(status_code=404, detail="Video not found")
    return FileResponse(path=path, media_type="video/mp4", filename=filename)

mp_pose = mp.solutions.pose
mp_drawing = mp.solutions.drawing_utils

def get_angle(a, b, c):
    a, b, c = np.array(a), np.array(b), np.array(c)
    radians = np.arctan2(c[1] - b[1], c[0] - b[0]) - np.arctan2(a[1] - b[1], a[0] - b[0])
    angle = np.abs(radians * 180.0 / np.pi)
    return angle if angle <= 180 else 360 - angle

def is_visible(*landmarks, threshold=0.5):
    return all(lm.visibility > threshold for lm in landmarks)

@app.post("/analyze")
async def analyze_video(file: UploadFile = File(...)):
    temp_input = tempfile.NamedTemporaryFile(delete=False, suffix=".mp4")
    temp_input.write(await file.read())
    temp_input.close()

    cap = cv2.VideoCapture(temp_input.name)
    pose = mp_pose.Pose()
    bad_postures = []
    total_frames = 0
    bad_frame_set = set()

    fps = cap.get(cv2.CAP_PROP_FPS)
    width = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
    height = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))

    output_filename = f"output_{uuid.uuid4().hex}.mp4"
    output_path = VIDEOS_DIR / output_filename

    out = cv2.VideoWriter(str(output_path), cv2.VideoWriter_fourcc(*"avc1"), fps, (width, height))

    while cap.isOpened():
        ret, frame = cap.read()
        if not ret:
            break

        total_frames += 1
        image_rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
        results = pose.process(image_rgb)

        if results.pose_landmarks:
            lm = results.pose_landmarks.landmark
            mp_drawing.draw_landmarks(frame, results.pose_landmarks, mp_pose.POSE_CONNECTIONS)

            try:
                issues_in_frame = []

                shoulder, hip, knee = lm[mp_pose.PoseLandmark.LEFT_SHOULDER], lm[mp_pose.PoseLandmark.LEFT_HIP], lm[mp_pose.PoseLandmark.LEFT_KNEE]
                if is_visible(shoulder, hip, knee):
                    back_angle = get_angle((shoulder.x, shoulder.y), (hip.x, hip.y), (knee.x, knee.y))
                    if back_angle < 150:
                        issues_in_frame.append(f"Back angle < 150 deg ({int(back_angle)} deg)")
                        cv2.putText(frame, f"Back angle < 150 deg ({int(back_angle)} deg)", (10, 30), cv2.FONT_HERSHEY_SIMPLEX, 1, (0, 0, 255), 2)
                    else:
                        cv2.putText(frame, f"Back angle: {int(back_angle)} deg", (10, 30), cv2.FONT_HERSHEY_SIMPLEX, 1, (0, 255, 0), 2)

                knee = lm[mp_pose.PoseLandmark.LEFT_KNEE]
                toe = lm[mp_pose.PoseLandmark.LEFT_FOOT_INDEX]
                if is_visible(knee, toe):
                    if knee.x > toe.x + 0.02:
                        issues_in_frame.append("Knee goes beyond toe")
                        cv2.putText(frame, "Knee goes beyond toe", (10, 60), cv2.FONT_HERSHEY_SIMPLEX, 1, (0, 0, 255), 2)
                    else:
                        cv2.putText(frame, "Knee in safe range", (10, 60), cv2.FONT_HERSHEY_SIMPLEX, 1, (0, 255, 0), 2)

                shoulder, ear, nose = lm[mp_pose.PoseLandmark.LEFT_SHOULDER], lm[mp_pose.PoseLandmark.LEFT_EAR], lm[mp_pose.PoseLandmark.NOSE]
                if is_visible(shoulder, ear, nose):
                    neck_angle = get_angle((shoulder.x, shoulder.y), (ear.x, ear.y), (nose.x, nose.y))
                    if neck_angle > 30:
                        issues_in_frame.append(f"Neck bend > 30 deg ({int(neck_angle)} deg)")
                        cv2.putText(frame, f"Neck bend > 30 deg ({int(neck_angle)} deg)", (10, 90), cv2.FONT_HERSHEY_SIMPLEX, 1, (0, 0, 255), 2)
                    else:
                        cv2.putText(frame, f"Neck angle: {int(neck_angle)} deg", (10, 90), cv2.FONT_HERSHEY_SIMPLEX, 1, (0, 255, 0), 2)

                if issues_in_frame:
                    bad_frame_set.add(total_frames)
                    for issue in issues_in_frame:
                        bad_postures.append({"frame": total_frames, "issue": issue})

            except Exception:
                pass

        out.write(frame)

    cap.release()
    out.release()
    os.unlink(temp_input.name)

    score = max(0, 100 - int((len(bad_frame_set) / total_frames) * 100)) if total_frames else 0

    return JSONResponse({
        "bad_postures": bad_postures,
        "video_url": f"http://localhost:8007/video/{output_filename}",
        "stream_url": f"http://localhost:8007/stream/{output_filename}",
        "score": score
    })

@app.post("/analyze-frame")
async def analyze_frame(file: UploadFile = File(...)):
    contents = await file.read()
    image = cv2.imdecode(np.frombuffer(contents, np.uint8), cv2.IMREAD_COLOR)
    pose = mp_pose.Pose()
    results = pose.process(cv2.cvtColor(image, cv2.COLOR_BGR2RGB))

    issues = []

    if results.pose_landmarks:
        lm = results.pose_landmarks.landmark
        try:
            shoulder, hip, knee = lm[mp_pose.PoseLandmark.LEFT_SHOULDER], lm[mp_pose.PoseLandmark.LEFT_HIP], lm[mp_pose.PoseLandmark.LEFT_KNEE]
            if is_visible(shoulder, hip, knee):
                back_angle = get_angle((shoulder.x, shoulder.y), (hip.x, hip.y), (knee.x, knee.y))
                if back_angle < 150:
                    issues.append(f"Back angle < 150 deg ({int(back_angle)} deg)")

            knee = lm[mp_pose.PoseLandmark.LEFT_KNEE]
            toe = lm[mp_pose.PoseLandmark.LEFT_FOOT_INDEX]
            if is_visible(knee, toe) and knee.x > toe.x + 0.02:
                issues.append("Knee goes beyond toe")

            shoulder, ear, nose = lm[mp_pose.PoseLandmark.LEFT_SHOULDER], lm[mp_pose.PoseLandmark.LEFT_EAR], lm[mp_pose.PoseLandmark.NOSE]
            if is_visible(shoulder, ear, nose):
                neck_angle = get_angle((shoulder.x, shoulder.y), (ear.x, ear.y), (nose.x, nose.y))
                if neck_angle > 30:
                    issues.append(f"Neck bend > 30 deg ({int(neck_angle)} deg)")
        except:
            pass

    return {"issues": issues}
