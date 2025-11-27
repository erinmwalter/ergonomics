import React, { useRef, useEffect, useState } from 'react';
import { Card, CardBody, CardTitle, Button, Alert, Row, Col } from 'reactstrap';

interface WebcamViewerProps {
  onWebcamReady: () => void;
  onBack: () => void;
}

const WebcamViewer: React.FC<WebcamViewerProps> = ({ onWebcamReady, onBack }) => {
  const videoRef = useRef<HTMLVideoElement>(null);
  const [webcamActive, setWebcamActive] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [loading, setLoading] = useState(false);

  const startWebcam = async () => {
    setLoading(true);
    setError(null);
    
    console.log('Attempting to start webcam...');

    try {
      // Check if mediaDevices is supported
      if (!navigator.mediaDevices || !navigator.mediaDevices.getUserMedia) {
        throw new Error('Camera access not supported in this browser');
      }

      console.log('Requesting camera permissions...');
      
      const stream = await navigator.mediaDevices.getUserMedia({ 
        video: { 
          width: 640, 
          height: 480 
        } 
      });

      console.log('Camera stream obtained:', stream);

      // Wait a bit for the video element to be available
      const maxRetries = 10;
      let retries = 0;
      
      const setVideoStream = () => {
        if (videoRef.current) {
          console.log('Video element found, setting stream');
          videoRef.current.srcObject = stream;
          
          // Wait for video to load metadata
          videoRef.current.onloadedmetadata = () => {
            console.log('Video metadata loaded, webcam should be active');
            setWebcamActive(true);
            setLoading(false);
          };
          
          // Handle video errors
          videoRef.current.onerror = (e) => {
            console.error('Video element error:', e);
            setError('Failed to display video stream');
            setLoading(false);
          };
          
        } else if (retries < maxRetries) {
          console.log(`Video element not ready, retrying... (${retries + 1}/${maxRetries})`);
          retries++;
          setTimeout(setVideoStream, 100);
        } else {
          throw new Error('Video element not found after retries');
        }
      };
      
      setVideoStream();
      
    } catch (err) {
      console.error('Failed to access webcam:', err);
      
      let errorMessage = 'Failed to access webcam.';
      
      if (err instanceof Error) {
        if (err.name === 'NotAllowedError') {
          errorMessage = 'Camera access denied. Please allow camera permissions and try again.';
        } else if (err.name === 'NotFoundError') {
          errorMessage = 'No camera found. Please connect a camera and try again.';
        } else if (err.name === 'NotSupportedError') {
          errorMessage = 'Camera not supported on this device/browser.';
        } else {
          errorMessage = `Camera error: ${err.message}`;
        }
      }
      
      setError(errorMessage);
      setLoading(false);
    }
  };

  const stopWebcam = () => {
    if (videoRef.current?.srcObject) {
      const stream = videoRef.current.srcObject as MediaStream;
      stream.getTracks().forEach(track => track.stop());
      videoRef.current.srcObject = null;
      setWebcamActive(false);
    }
  };

  const handleProceed = () => {
    onWebcamReady();
  };

  // Cleanup on unmount
  useEffect(() => {
    return () => {
      stopWebcam();
    };
  }, []);

  return (
    <div>
      <Card className="mb-4">
        <CardBody>
          <Row className="align-items-center mb-3">
            <Col>
              <CardTitle tag="h4">Step 3: Setup Webcam</CardTitle>
              <p className="text-muted mb-0">
                Test your webcam feed before starting process tracking
              </p>
            </Col>
            <Col xs="auto">
              <Button color="secondary" onClick={onBack} className="me-2">
                ← Back to Setup
              </Button>
            </Col>
          </Row>

          {error && (
            <Alert color="danger">
              {error}
            </Alert>
          )}

          <Row>
            <Col lg={8}>
              <Card className="bg-dark">
                <CardBody className="text-center p-0">
                  <div style={{ height: '360px', position: 'relative', overflow: 'hidden' }}>
                  {/* Always render video element but control visibility */}
                  <video
                    ref={videoRef}
                    autoPlay
                    muted
                    style={{ 
                      width: '100%', 
                      height: '100%',
                      objectFit: 'cover', // This will make it fill the container
                      display: webcamActive ? 'block' : 'none'
                    }}
                  />
                  
                  {/* Show placeholder when webcam not active */}
                  {!webcamActive && (
                    <div 
                      className="d-flex align-items-center justify-content-center position-absolute top-0 start-0 w-100 h-100"
                      style={{ backgroundColor: '#343a40' }}
                    >
                      <div className="text-center text-light">
                        <h5>Webcam Preview</h5>
                        <p className="mb-0">Click "Start Webcam" to begin</p>
                      </div>
                    </div>
                  )}
                </div>
                </CardBody>
              </Card>
            </Col>

            <Col lg={4}>
              <Card className="h-100">
                <CardBody>
                  <h6>Webcam Instructions</h6>
                  
                  <ol className="small">
                    <li>Click <strong>"Start Webcam"</strong> below</li>
                    <li>Allow camera permissions if prompted</li>
                    <li>Position yourself in front of the camera</li>
                    <li>Ensure good lighting and clear view of your hands</li>
                    <li>Click <strong>"Continue to Tracking"</strong> when ready</li>
                  </ol>

                  <div className="mt-4">
                    <h6>Tips for Best Results:</h6>
                    <ul className="small text-muted">
                      <li>Stand/sit 3-6 feet from camera</li>
                      <li>Ensure hands are visible</li>
                      <li>Avoid cluttered background</li>
                      <li>Good lighting on your workspace</li>
                    </ul>
                  </div>
                </CardBody>
              </Card>
            </Col>
          </Row>

          <div className="mt-3 text-center">
            {!webcamActive ? (
              <div>
                <Button 
                  color="primary" 
                  size="lg"
                  onClick={startWebcam}
                  disabled={loading}
                >
                  {loading ? (
                    <>
                      <span className="spinner-border spinner-border-sm me-2" />
                      Starting Webcam...
                    </>
                  ) : (
                    <>
                      Start Webcam
                    </>
                  )}
                </Button>
                
                <div className="mt-2">
                  <small className="text-muted">
                    Having issues? Check browser console for errors.
                  </small>
                </div>
              </div>
            ) : (
              <div>
                <div className="mb-3">
                  <span className="badge bg-success fs-6 px-3 py-2">
                    Webcam Works!
                  </span>
                </div>
                
                <div className="d-flex justify-content-center gap-3">
                  <Button 
                    color="warning" 
                    onClick={stopWebcam}
                  >
                    Stop Webcam
                  </Button>
                  <Button 
                    color="primary" 
                    onClick={startWebcam}
                  >
                    Restart Webcam
                  </Button>
                  <Button 
                    color="success"
                    size="lg"
                    onClick={handleProceed}
                  >
                    Continue to Tracking →
                  </Button>
                </div>
              </div>
            )}
          </div>
        </CardBody>
      </Card>
    </div>
  );
};

export default WebcamViewer;