import React, { useState, useEffect } from 'react';
import { Card, CardBody, CardTitle, Button, Alert, Row, Col, Badge } from 'reactstrap';
import type { Environment, Process, Zone, ProcessStep } from '../../models';
import { apiService } from '../../services/ApiService';
import trackingService from '../../services/TrackingService';
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
  const [trackingAvailable, setTrackingAvailable] = useState<boolean>(false);
  const [checkingStatus, setCheckingStatus] = useState(true);
  const [streamUrl, setStreamUrl] = useState<string>('');

  // Load environment zones and process steps
  useEffect(() => {
    loadTrackingData();
    checkTrackingStatus();
  }, [environment.Id, process.Id]);

  const checkTrackingStatus = async () => {
    setCheckingStatus(true);
    try {
      const status = await trackingService.checkTrackingStatus();
      setTrackingAvailable(status.available && status.model_loaded);
      setCheckingStatus(false);
    } catch (err) {
      console.error('Error checking tracking status:', err);
      setTrackingAvailable(false);
      setCheckingStatus(false);
    }
  };

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

    if (!trackingAvailable) {
      setError('Tracking not available. Check webcam and YOLO model.');
      return;
    }

    try {
      // CRITICAL: Stop any active webcam streams from the frontend
      const stream = await navigator.mediaDevices.getUserMedia({ video: true });
      stream.getTracks().forEach(track => track.stop());
      console.log('Stopped any active webcam streams');

      // Small delay to ensure webcam is released
      await new Promise(resolve => setTimeout(resolve, 500));

      // Start analysis session
      const response = await apiService.startAnalysisSession(environment.Id, process.Id);
      setSessionId(response.sessionId);

      // Get stream URL with zones (conversion happens inside getStreamUrl)
      console.log('Zones being sent to tracking:', zones);
      const url = trackingService.getStreamUrl(zones, response.sessionId);
      console.log('Stream URL:', url);
      setStreamUrl(url);

      setTracking({
        isActive: true,
        startTime: Date.now(),
        currentStep: 0,
        stepEvents: []
      });

      onTrackingStart();
      
      // Start polling for step detection
      startStepDetectionPolling(response.sessionId);
      
      console.log('YOLO tracking started with session:', response.sessionId);
      console.log('Stream URL:', url);
      
    } catch (err) {
      console.error('Failed to start tracking:', err);
      setError('Failed to start tracking session');
    }
  };

  // Poll for step detection from backend
  const startStepDetectionPolling = (sessionId: string) => {
    const pollInterval = setInterval(async () => {
      try {
        const status = await apiService.getAnalysisStatus(sessionId);
        
        // Check if a new step was detected
        if (status.stepEvents && status.stepEvents.length > tracking.stepEvents.length) {
          const newStepEvent = status.stepEvents[status.stepEvents.length - 1];
          
          setTracking(prev => ({
            ...prev,
            currentStep: status.currentStep,
            stepEvents: status.stepEvents
          }));
          
          console.log('Step detected:', newStepEvent);
          
          // Check if complete
          if (status.currentStep >= processSteps.length) {
            clearInterval(pollInterval);
          }
        }
      } catch (err) {
        console.error('Error polling step detection:', err);
        clearInterval(pollInterval);
      }
    }, 500);
    
    return pollInterval;
  };

  const handleStopTracking = async () => {
    if (!tracking.isActive || !sessionId) return;

    try {
      // Stop analysis session
      const response = await apiService.stopAnalysisSession(sessionId);
      const results = response.results || calculateResults(0);
      
      setTracking({
        isActive: false,
        startTime: null,
        currentStep: 0,
        stepEvents: []
      });

      setStreamUrl('');

      // CRITICAL: Release the webcam by stopping backend stream
      // Wait a moment for the stream to close
      await new Promise(resolve => setTimeout(resolve, 500));

      // Save results
      await apiService.saveAnalysisResults(sessionId, results);

      onTrackingComplete(results);
      
    } catch (err) {
      console.error('Failed to stop tracking:', err);
      // Fallback
      const endTime = Date.now();
      const totalTime = tracking.startTime ? (endTime - tracking.startTime) / 1000 : 0;
      const results = calculateResults(totalTime);
      
      setStreamUrl('');
      
      onTrackingComplete(results);
    }
  };

  const calculateResults = (totalTime: number) => {
    const completedSteps = tracking.stepEvents.length;
    const totalSteps = processSteps.length;
    
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

  const canStartTracking = !loading && zones.length > 0 && processSteps.length > 0 && trackingAvailable && !checkingStatus;
  const isTrackingComplete = tracking.currentStep >= processSteps.length;

  // Show loading screen while checking YOLO availability
  if (checkingStatus) {
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
            </Row>
          </CardBody>
        </Card>

        <div className="text-center p-5">
          <div className="spinner-border text-primary mb-3" style={{ width: '3rem', height: '3rem' }} role="status">
            <span className="visually-hidden">Loading...</span>
          </div>
          <h5>Initializing YOLO Tracking System...</h5>
          <p className="text-muted">Please wait while we prepare the hand tracking system</p>
        </div>
      </div>
    );
  }

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

          {!checkingStatus && !trackingAvailable && (
            <Alert color="warning">
              YOLO model or webcam not available. Please check your setup.
            </Alert>
          )}

          {loading && (
            <div className="text-center p-4">
              <div className="spinner-border" role="status">
                <span className="visually-hidden">Loading...</span>
              </div>
            </div>
          )}
        </CardBody>
      </Card>

      <Row>
        <Col lg={8}>
          {/* YOLO Video Stream */}
          <Card className="mb-4">
            <CardBody>
              <h6 className="mb-3">
                Live YOLO Tracking Feed
                {tracking.isActive && (
                  <Badge color="success" className="ms-2">ACTIVE</Badge>
                )}
              </h6>
              
              {streamUrl && tracking.isActive ? (
                <div className="position-relative">
                  <img
                    key={streamUrl}
                    src={streamUrl}
                    alt="YOLO tracking feed"
                    style={{
                      width: '640px',
                      height: '480px',
                      border: '2px solid #333',
                      borderRadius: '4px',
                      backgroundColor: '#000'
                    }}
                    onError={(e) => {
                      console.error('Image failed to load');
                      e.currentTarget.style.display = 'none';
                    }}
                  />
                  <div className="mt-2">
                    <small className="text-muted">
                      🟢 Green: Keypoints | 🔵 Cyan/Yellow: Hand boxes | 
                      🟢 Green boxes: Zones | 🔴 Red: Active zone
                    </small>
                  </div>
                </div>
              ) : (
                <div 
                  className="d-flex align-items-center justify-content-center bg-dark text-white"
                  style={{ height: '360px', borderRadius: '4px' }}
                >
                  <div className="text-center">
                    <p>Click "Start Tracking" to begin YOLO pose detection</p>
                    {!trackingAvailable && (
                      <small className="text-warning">
                        ⚠ Tracking not available
                      </small>
                    )}
                  </div>
                </div>
              )}

              {tracking.isActive && processSteps[tracking.currentStep] && (
                <div className="mt-3">
                  <div className="alert alert-info">
                    <strong>Current Step: </strong>
                    {processSteps[tracking.currentStep].StepName}
                    <br />
                    <small>
                      Move your hand to the <strong>{processSteps[tracking.currentStep].ZoneName}</strong> zone.
                      The system will automatically detect when you complete the step.
                    </small>
                  </div>
                </div>
              )}

              {tracking.isActive && isTrackingComplete && (
                <div className="mt-3">
                  <div className="alert alert-success">
                    <h5>Process Complete!</h5>
                    <p>All {processSteps.length} steps detected. Click "Stop Tracking" to see results.</p>
                  </div>
                </div>
              )}
            </CardBody>
          </Card>

          {/* Zone Display */}
          {!loading && zones.length > 0 && (
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
                            marginRight: '10px',
                            borderRadius: '2px'
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

        {/* Tracking Status Sidebar */}
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