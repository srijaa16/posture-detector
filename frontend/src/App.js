import React, { useState, useRef, useEffect } from "react";
import axios from "axios";
import Webcam from "react-webcam";
import "./App.css";

function App() {
  const [mode, setMode] = useState("upload");
  const [videoFile, setVideoFile] = useState(null);
  const [capturedBlob, setCapturedBlob] = useState(null);
  const [result, setResult] = useState(null);
  const [liveWarning, setLiveWarning] = useState(null);
  const [loading, setLoading] = useState(false);
  const webcamRef = useRef(null);

  const handleVideoChange = (e) => {
    setVideoFile(e.target.files[0]);
    setCapturedBlob(null);
    setResult(null);
    setLiveWarning(null);
  };

  const handleCapture = () => {
    if (webcamRef.current) {
      const canvas = webcamRef.current.getCanvas();
      canvas.toBlob((blob) => {
        setCapturedBlob(blob);
        setVideoFile(null);
        setResult(null);
        setLiveWarning(null);
      }, "image/jpeg");
    }
  };

  const handleSubmit = async () => {
    const formData = new FormData();
    if (mode === "upload" && videoFile) {
      formData.append("file", videoFile);
    } else if (mode === "webcam" && capturedBlob) {
      formData.append("file", capturedBlob, "webcam_capture.jpg");
    } else {
      alert("Please upload or capture a video first.");
      return;
    }

    try {
      setLoading(true);
      setResult(null);
      setLiveWarning(null);
      const res = await axios.post("http://localhost:8007/analyze", formData, {
        headers: { "Content-Type": "multipart/form-data" },
      });
      setResult(res.data);
    } catch (error) {
      console.error("Error during analysis:", error);
      alert("Something went wrong during posture analysis.");
    } finally {
      setLoading(false);
    }
  };

  const exportToCSV = () => {
    if (!result || !result.bad_postures || result.bad_postures.length === 0) return;

    const headers = "Frame,Issue\n";
    const rows = result.bad_postures.map((item) => `${item.frame},"${item.issue}"`).join("\n");
    const csv = headers + rows;

    const blob = new Blob([csv], { type: "text/csv" });
    const url = window.URL.createObjectURL(blob);
    const a = document.createElement("a");
    a.href = url;
    a.download = "posture_issues.csv";
    a.click();
    window.URL.revokeObjectURL(url);
  };

  useEffect(() => {
    let interval;
    if (mode === "webcam" && webcamRef.current) {
      interval = setInterval(async () => {
        const canvas = webcamRef.current.getCanvas();
        if (canvas) {
          canvas.toBlob(async (blob) => {
            const formData = new FormData();
            formData.append("file", blob, "frame.jpg");
            try {
              const res = await axios.post("http://localhost:8007/analyze-frame", formData, {
                headers: { "Content-Type": "multipart/form-data" },
              });

              if (res.data.issues && res.data.issues.length > 0) {
                setLiveWarning("⚠️ " + res.data.issues.join(", "));
              } else {
                setLiveWarning("✅ Good posture");
              }
            } catch (err) {
              console.error("Live frame analysis failed:", err);
            }
          }, "image/jpeg");
        }
      }, 1000);
    }

    return () => clearInterval(interval);
  }, [mode]);

  return (
    <div className="app-container">
      <header className="header">
        <h1>🧍‍♂️ Posture Detection App</h1>
        <p className="tagline">Detect & Improve Your Sitting and Squat Postures</p>
      </header>

      <section className="mode-selector">
        <button onClick={() => setMode("upload")} disabled={loading} className={mode === "upload" ? "btn active" : "btn"}>📤 Upload Video</button>
        <button onClick={() => setMode("webcam")} disabled={loading} className={mode === "webcam" ? "btn active" : "btn"}>📷 Live Webcam</button>
      </section>

      <section className="input-section">
        {mode === "upload" && (
          <>
            <input type="file" accept="video/*" onChange={handleVideoChange} disabled={loading} className="file-input" />
            {videoFile && <video className="video-preview" controls src={URL.createObjectURL(videoFile)} />}
          </>
        )}

        {mode === "webcam" && (
          <div className="webcam-wrapper">
            <Webcam
              ref={webcamRef}
              audio={false}
              height={360}
              width={480}
              screenshotFormat="image/jpeg"
              videoConstraints={{ facingMode: "user" }}
              className="webcam"
            />
            <button onClick={handleCapture} disabled={loading} className="btn capture">📸 Capture Frame</button>
            {liveWarning && <p className={liveWarning.includes("✅") ? "success-text" : "warning-text"}>{liveWarning}</p>}
          </div>
        )}

        <button onClick={handleSubmit} disabled={loading} className="btn analyze">
          {loading ? "⏳ Analyzing..." : "🔍 Analyze"}
        </button>
        {loading && <p className="loading-text">⏳ Processing...</p>}
      </section>

      {result && (
        <section className="results">
          <div className="result-box">
            <h3>📋 Detected Issues</h3>
            {result.bad_postures.length > 0 ? (
              <>
                <ul className="issue-list">
                  {result.bad_postures.map((item, idx) => (
                    <li key={idx}>Frame {item.frame}: {item.issue}</li>
                  ))}
                </ul>
                <button onClick={exportToCSV} className="btn export">📄 Export CSV</button>
              </>
            ) : (
              <p className="success-text">✅ No posture issues found</p>
            )}
            <p className="score-text" style={{ color: result.score >= 70 ? "green" : "red" }}>🧮 Posture Score: {result.score}/100</p>
          </div>

          {result.video_url && (
            <div className="result-box">
              <h3>🎬 Annotated Video</h3>
              <video width="480" height="360" controls key={result.video_url} className="annotated-video">
                <source src={result.video_url} type="video/mp4" />
                Your browser does not support the video tag.
              </video>
              <br />
              <a href={result.video_url} download className="btn download">🎞️ Download Video</a>
            </div>
          )}
        </section>
      )}
    </div>
  );
}

export default App;
