import React, { useRef, useEffect, useState, useCallback } from 'react';

interface YOLOTrackerProps {
  sessionId: string | null;
  isTracking: boolean;
  onStepDetected?: (stepNumber: number) => void;
}

const YOLOTracker: React.FC<YOLOTrackerProps> = ({ 
  sessionId, 
  isTracking, 
  onStepDetected 
}) => {
  const videoRef = useRef<HTMLVideoElement>(null);
  const canvasRef = useRef<HTMLCanvasElement>(null);
  const [stream, setStream] = useState<MediaStream | null>(null);
  const [error, setError] = useState<string | null>(null);

  const startWebcam = useCallback(async () => {
    try {
      console.log('YOLOTracker: Starting webcam...');
      const mediaStream = await navigator.mediaDevices.getUserMedia({
        video: { width: 640, height: 480 }
      });
      
      setStream(mediaStream);
      
      if (videoRef.current) {
        videoRef.current.srcObject = mediaStream;
        console.log('YOLOTracker: Webcam started successfully');
      }
    } catch (err) {
      console.error('YOLOTracker: Failed to start webcam:', err);
      setError('Failed to start webcam');
    }
  }, []);

  const stopWebcam = useCallback(() => {
    if (stream) {
      stream.getTracks().forEach(track => track.stop());
      setStream(null);
    }
    if (videoRef.current) {
      videoRef.current.srcObject = null;
    }
    console.log('YOLOTracker: Webcam stopped');
  }, [stream]);

  useEffect(() => {
    startWebcam();
    return () => stopWebcam();
  }, [startWebcam, stopWebcam]);

  return (
    <div className="position-relative">
      {error && (
        <div className="alert alert-danger">
          {error}
        </div>
      )}
      
      <video
        ref={videoRef}
        autoPlay
        muted
        style={{
          width: '100%',
          height: 'auto',
          backgroundColor: '#000'
        }}
      />
      
      <canvas
        ref={canvasRef}
        className="position-absolute top-0 start-0"
        style={{ 
          pointerEvents: 'none',
          display: 'none'
        }}
      />
      
      <div className="position-absolute top-0 start-0 p-2">
        {stream && (
          <span className="badge bg-success">Camera Active</span>
        )}
        {isTracking && (
          <span className="badge bg-primary ms-2">Tracking Mode</span>
        )}
      </div>
    </div>
  );
};

export default YOLOTracker;