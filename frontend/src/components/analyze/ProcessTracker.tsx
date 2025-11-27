import React, { useState, useRef, useEffect } from 'react';
import { Card, CardBody, CardTitle, Button, Alert, Row, Col } from 'reactstrap';
import type { Environment, Process, Zone, ProcessStep } from '../../models';
import { apiService } from '../../services/ApiService';
import TrackingStatus from './TrackingStatus';

interface ProcessTrackerProps {
  environment: Environment;
  process: Process;
  webcamActive: boolean;
  onTrackingStart: () => void;
  onTrackingComplete: (results: any) => void;
  onBack: () => void;
}

interface TrackingSession {
  isActive: boolean;
  startTime: number | null;
  currentStep: number;
  stepEvents: Array<{
    stepNumber: number;
    stepName: string;
    completedAt: number;
    duration: number;
    targetDuration: number;
  }>;
}

const ProcessTracker: React.FC<ProcessTrackerProps> = ({
  environment,
  process,
  webcamActive,
  onTrackingStart,
  onTrackingComplete,
  onBack
}) => {
  const [zones, setZones] = useState<Zone[]>([]);
  const [processSteps, setProcessSteps] = useState<ProcessStep[]>([]);
  const [sessionId, setSessionId] = useState<string | null>(null);
  const [tracking, setTracking] = useState<TrackingSession>({
    isActive: false,
    startTime: null,
    currentStep: 0,
    stepEvents: []
  });
  const [error, setError] = useState<string | null>(null);
  const [loading, setLoading] = useState(true);

  // Load environment zones and process steps
  useEffect(() => {
    loadTrackingData();
  }, [environment.Id, process.Id]);

  const loadTrackingData = async () => {
    setLoading(true);
    setError(null);

    try {
      // Load zones for environment
      const zonesData = await apiService.getZonesForEnvironment(environment.Id);
      setZones(zonesData);

      // Load steps for process  
      const stepsData = await apiService.getProcessSteps(process.Id);
      setProcessSteps(stepsData);

      if (zonesData.length === 0) {
        setError('No zones found for this environment. Please configure zones first.');
      } else if (stepsData.length === 0) {
        setError('No steps found for this process. Please configure process steps first.');
      }

    } catch (err) {
      console.error('Failed to load tracking data:', err);
      setError('Failed to load process data');
    }

    setLoading(false);
  };

  const handleStartTracking = async () => {
    if (processSteps.length === 0 || zones.length === 0) {
      setError('Cannot start tracking - missing process steps or zones');
      return;
    }

    try {
      // Start analysis session with the Python YOLO service
      const response = await apiService.startAnalysisSession(environment.Id, process.Id);
      setSessionId(response.sessionId);

      // Start the actual Python YOLO tracking
      await fetch(`/api/analysis/start-tracking/${response.sessionId}`, {
        method: 'POST'
      });

      setTracking({
        isActive: true,
        startTime: Date.now(),
        currentStep: 0,
        stepEvents: []
      });

      onTrackingStart();
      
      // Start polling for automatic step detection from YOLO
      startStepDetectionPolling(response.sessionId);
      
      console.log('Real YOLO analysis session started:', response.sessionId);
      console.log('Python service will automatically detect hand-to-zone contact');
      
    } catch (err) {
      console.error('Failed to start YOLO tracking session:', err);
      setError('Failed to start YOLO tracking session');
    }
  };

  // Poll the backend for automatic step completion detected by YOLO
  const startStepDetectionPolling = (sessionId: string) => {
    const pollInterval = setInterval(async () => {
      try {
        const status = await apiService.getAnalysisStatus(sessionId);
        
        // Check if YOLO detected a new step completion
        if (status.stepEvents && status.stepEvents.length > tracking.stepEvents.length) {
          const newStepEvent = status.stepEvents[status.stepEvents.length - 1];
          
          setTracking(prev => ({
            ...prev,
            currentStep: status.currentStep,
            stepEvents: status.stepEvents
          }));
          
          console.log('YOLO automatically detected step completion:', newStepEvent);
          
          // Check if process is complete
          if (status.currentStep >= processSteps.length) {
            clearInterval(pollInterval);
          }
        }
      } catch (err) {
        console.error('Error polling step detection:', err);
        clearInterval(pollInterval);
      }
    }, 500); // Poll every 500ms for real-time detection
    
    return pollInterval;
  };

  const handleStopTracking = async () => {
    if (!tracking.isActive || !sessionId) return;

    try {
      // Stop analysis session and get results
      const response = await apiService.stopAnalysisSession(sessionId);
      const results = response.results || calculateResults(0);
      
      setTracking({
        isActive: false,
        startTime: null,
        currentStep: 0,
        stepEvents: []
      });

      // Save results
      await apiService.saveAnalysisResults(sessionId, results);

      onTrackingComplete(results);
      
    } catch (err) {
      console.error('Failed to stop analysis session:', err);
      // Fallback to local calculation
      const endTime = Date.now();
      const totalTime = tracking.startTime ? (endTime - tracking.startTime) / 1000 : 0;
      const results = calculateResults(totalTime);
      onTrackingComplete(results);
    }
  };

  const calculateResults = (totalTime: number) => {
    const completedSteps = tracking.stepEvents.length;
    const totalSteps = processSteps.length;
    
    // Basic adherence calculation
    const completionRate = (completedSteps / totalSteps) * 100;
    const targetTime = processSteps.reduce((sum, step) => sum + step.Duration, 0);
    const timeAdherence = Math.max(0, 100 - Math.abs(totalTime - targetTime) / targetTime * 100);
    
    const overallAdherence = (completionRate * 0.7) + (timeAdherence * 0.3);

    return {
      overall_adherence: Math.round(overallAdherence),
      completion_adherence: Math.round(completionRate),
      timing_adherence: Math.round(timeAdherence),
      completed_steps: completedSteps,
      total_steps: totalSteps,
      total_time: Math.round(totalTime),
      target_total_time: targetTime,
      step_details: tracking.stepEvents
    };
  };

  const canStartTracking = !loading && zones.length > 0 && processSteps.length > 0;
  const isTrackingComplete = tracking.currentStep >= processSteps.length;

  return (
    <div>
      <Card className="mb-4">
        <CardBody>
          <Row className="align-items-center mb-3">
            <Col>
              <CardTitle tag="h4">Step 4: Process Tracking</CardTitle>
              <p className="text-muted mb-0">
                Track hand movements for process: <strong>{process.ProcessName}</strong>
              </p>
            </Col>
            <Col xs="auto">
              <Button color="secondary" onClick={onBack} className="me-2">
                ← Back to Webcam
              </Button>
              
              {!tracking.isActive ? (
                <Button 
                  color="success" 
                  onClick={handleStartTracking}
                  disabled={!canStartTracking}
                >
                  Start Tracking
                </Button>
              ) : (
                <Button 
                  color="danger" 
                  onClick={handleStopTracking}
                >
                  Stop Tracking
                </Button>
              )}
            </Col>
          </Row>

          {error && (
            <Alert color="danger">
              {error}
            </Alert>
          )}

          {loading && (
            <div className="text-center p-4">
              <div className="spinner-border" role="status">
                <span className="sr-only">Loading process data...</span>
              </div>
            </div>
          )}
        </CardBody>
      </Card>

      {/* Webcam Feed - Always render so videoRef is available */}
      <Row>
        <Col lg={8}>
          <Card className="mb-4">
            <CardBody>
              <h6>Live YOLO Tracking Feed</h6>
              
              <div className="position-relative">
                {/* Working video feed */}
                <video
                  autoPlay
                  muted
                  style={{
                    width: '100%',
                    height: '360px',
                    objectFit: 'cover',
                    backgroundColor: '#000'
                  }}
                  ref={(video) => {
                    if (video && !video.srcObject) {
                      navigator.mediaDevices.getUserMedia({ video: { width: 640, height: 480 } })
                        .then(stream => {
                          video.srcObject = stream;
                          console.log('ProcessTracker: Video working');
                        })
                        .catch(err => console.error('Video error:', err));
                    }
                  }}
                />
                
                {/* Zone overlays on top of video */}
                {zones.map(zone => {
                  const isTargetZone = processSteps[tracking.currentStep]?.TargetZoneId === zone.Id;
                  return (
                    <div
                      key={zone.Id}
                      className={`position-absolute ${isTargetZone ? 'border-warning border-4' : 'border-light border-2'}`}
                      style={{
                        left: `${(zone.Xstart / 640) * 100}%`,
                        top: `${(zone.Ystart / 480) * 100}%`,
                        width: `${((zone.Xend - zone.Xstart) / 640) * 100}%`,
                        height: `${((zone.Yend - zone.Ystart) / 480) * 100}%`,
                        backgroundColor: isTargetZone ? 'rgba(255, 255, 0, 0.3)' : 'rgba(0, 123, 255, 0.2)',
                        border: '3px solid',
                        pointerEvents: 'none' // Display only - YOLO handles detection
                      }}
                    >
                      <div className="position-absolute top-0 start-0 bg-dark text-white px-2 py-1" style={{ fontSize: '12px' }}>
                        {zone.ZoneName} {isTargetZone && 'TARGET'}
                      </div>
                    </div>
                  );
                })}
                
                {/* Status indicators */}
                <div className="position-absolute top-0 end-0 p-2">
                  <span className="badge bg-success">Camera</span>
                  {tracking.isActive && (
                    <span className="badge bg-primary ms-2">Tracking</span>
                  )}
                </div>
              </div>
              
              {/* Zone Info */}
              <div className="mt-2 p-2 bg-light rounded">
                <small>
                  <strong>Active Zones:</strong> {zones.map(z => z.ZoneName).join(', ')}
                </small>
              </div>

              {/* Real YOLO Tracking Status */}
              {tracking.isActive && !isTrackingComplete && (
                <div className="mt-3">
                  <div className="alert alert-info">
                    <h6><strong>YOLO Auto-Detection Active</strong></h6>
                    <p className="mb-2">
                      <strong>Current Target:</strong> {processSteps[tracking.currentStep]?.ZoneName}<br/>
                      <strong>Action Required:</strong> {processSteps[tracking.currentStep]?.StepName}<br/>
                      <strong>Time Target:</strong> {processSteps[tracking.currentStep]?.Duration}s
                    </p>
                    <p className="mb-0">
                      <strong>Instructions:</strong> Move your hands to the highlighted target zone. 
                      The system will automatically detect when you complete the step.
                    </p>
                  </div>
                </div>
              )}

              {tracking.isActive && isTrackingComplete && (
                <div className="mt-3">
                  <div className="alert alert-success">
                    <h5>Process Complete!</h5>
                    <p>All {processSteps.length} steps automatically detected. Click "Stop Tracking" to see results.</p>
                  </div>
                </div>
              )}
            </CardBody>
          </Card>

          {!loading && (
            <Card>
              <CardBody>
                <h6>Environment Zones</h6>
                <Row>
                  {zones.map(zone => (
                    <Col md={6} key={zone.Id} className="mb-2">
                      <div 
                        className="p-2 border rounded d-flex align-items-center"
                        style={{ borderColor: zone.Color }}
                      >
                        <div 
                          style={{
                            width: '20px',
                            height: '20px', 
                            backgroundColor: zone.Color,
                            marginRight: '10px'
                          }}
                        />
                        <span>{zone.ZoneName}</span>
                      </div>
                    </Col>
                  ))}
                </Row>
              </CardBody>
            </Card>
          )}
        </Col>

        <Col lg={4}>
          {!loading && (
            <TrackingStatus
              processSteps={processSteps}
              currentStep={tracking.currentStep}
              isTracking={tracking.isActive}
              stepEvents={tracking.stepEvents}
              startTime={tracking.startTime}
            />
          )}
        </Col>
      </Row>
    </div>
  );
};

export default ProcessTracker;