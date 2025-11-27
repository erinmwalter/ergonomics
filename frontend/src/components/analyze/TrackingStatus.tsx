import React, { useState, useEffect } from 'react';
import { Card, CardBody, Badge } from 'reactstrap';
import { ProcessStep } from '../../models';


interface TrackingStatusProps {
  processSteps: ProcessStep[];
  currentStep: number;
  isTracking: boolean;
  stepEvents: Array<{
    stepNumber: number;
    stepName: string;
    completedAt: number;
    duration: number;
    targetDuration: number;
  }>;
  startTime: number | null;
}

const TrackingStatus: React.FC<TrackingStatusProps> = ({
  processSteps,
  currentStep,
  isTracking,
  stepEvents,
  startTime
}) => {
  const [elapsedTime, setElapsedTime] = useState(0);

  // Update elapsed time every second when tracking
  useEffect(() => {
    let interval: NodeJS.Timeout;
    
    if (isTracking && startTime) {
      interval = setInterval(() => {
        setElapsedTime((Date.now() - startTime) / 1000);
      }, 100); // Update every 100ms for smooth display
    } else {
      setElapsedTime(0);
    }

    return () => {
      if (interval) clearInterval(interval);
    };
  }, [isTracking, startTime]);

  const formatTime = (seconds: number) => {
    const mins = Math.floor(seconds / 60);
    const secs = Math.floor(seconds % 60);
    const ms = Math.floor((seconds % 1) * 10);
    return `${mins}:${secs.toString().padStart(2, '0')}.${ms}`;
  };

  const getStepStatus = (stepIndex: number) => {
    if (stepIndex < currentStep) return 'completed';
    if (stepIndex === currentStep && isTracking) return 'active';
    return 'pending';
  };

  const getStepBadgeColor = (status: string) => {
    switch (status) {
      case 'completed': return 'success';
      case 'active': return 'primary';
      default: return 'secondary';
    }
  };

  const progress = processSteps.length > 0 ? (currentStep / processSteps.length) * 100 : 0;
  const totalTargetTime = processSteps.reduce((sum, step) => sum + step.Duration, 0);
  const isComplete = currentStep >= processSteps.length;

  return (
    <div>
      {/* Overall Status */}
      <Card className="mb-3">
        <CardBody>
          <h6 className="d-flex justify-content-between align-items-center">
            Process Status
            <Badge color={isTracking ? 'success' : isComplete ? 'info' : 'secondary'}>
              {isTracking ? 'ACTIVE' : isComplete ? 'COMPLETE' : 'READY'}
            </Badge>
          </h6>
          
          {/* Progress Bar */}
          <div className="mb-3">
            <div className="d-flex justify-content-between mb-1">
              <small>Progress</small>
              <small>{currentStep}/{processSteps.length} steps</small>
            </div>
            <div className="progress">
              <div 
                className={`progress-bar ${isTracking ? 'progress-bar-animated' : ''}`}
                style={{ width: `${progress}%` }}
              />
            </div>
          </div>

          {/* Timing */}
          <div className="row text-center">
            <div className="col-6">
              <div className="border-end">
                <div className="h5 mb-0">{formatTime(elapsedTime)}</div>
                <small className="text-muted">Elapsed</small>
              </div>
            </div>
            <div className="col-6">
              <div className="h5 mb-0">{totalTargetTime}s</div>
              <small className="text-muted">Target</small>
            </div>
          </div>
        </CardBody>
      </Card>

      {/* Current Step */}
      {isTracking && currentStep < processSteps.length && (
        <Card className="mb-3 border-primary">
          <CardBody>
            <h6 className="text-primary">Current Step</h6>
            <div className="d-flex align-items-center mb-2">
              <Badge color="primary" className="me-2">
                {currentStep + 1}
              </Badge>
              <strong>{processSteps[currentStep].StepName}</strong>
            </div>
            
            <div className="mb-2">
              <small className="text-muted">Target Zone: </small>
              <Badge 
                style={{ 
                  backgroundColor: processSteps[currentStep].Color,
                  color: 'white'
                }}
              >
                {processSteps[currentStep].ZoneName}
              </Badge>
            </div>

            <div className="mb-2">
              <small className="text-muted">Target Time: </small>
              <span className="fw-bold">{processSteps[currentStep].Duration}s</span>
            </div>

            {processSteps[currentStep].Description && (
              <div>
                <small className="text-muted">Instructions: </small>
                <div className="small">{processSteps[currentStep].Description}</div>
              </div>
            )}
          </CardBody>
        </Card>
      )}

      {/* Steps List */}
      <Card>
        <CardBody>
          <h6>Process Steps</h6>
          
          {processSteps.map((step, index) => {
            const status = getStepStatus(index);
            const stepEvent = stepEvents.find(e => e.stepNumber === index + 1);
            
            return (
              <div 
                key={step.Id}
                className={`d-flex align-items-center p-2 rounded mb-2 ${
                  status === 'active' ? 'bg-primary bg-opacity-10' : ''
                }`}
              >
                <Badge 
                  color={getStepBadgeColor(status)}
                  className="me-2"
                  style={{ minWidth: '24px' }}
                >
                  {index + 1}
                </Badge>

                <div className="flex-grow-1">
                  <div className="fw-bold">{step.StepName}</div>
                  <div className="d-flex align-items-center gap-2">
                    <small 
                      className="px-2 py-1 rounded"
                      style={{ 
                        backgroundColor: step.Color,
                        color: 'white',
                        fontSize: '0.7rem'
                      }}
                    >
                      {step.ZoneName}
                    </small>
                    <small className="text-muted">{step.Duration}s</small>
                  </div>
                </div>

                {/* Step Status Icons */}
                <div className="ms-2">
                  {status === 'completed' && (
                    <span className="text-success">✓</span>
                  )}
                  {status === 'active' && (
                    <span className="text-primary">👁️</span>
                  )}
                  {status === 'pending' && (
                    <span className="text-muted">⏳</span>
                  )}
                </div>
              </div>
            );
          })}
        </CardBody>
      </Card>

      {/* Completed Steps Summary */}
      {stepEvents.length > 0 && (
        <Card className="mt-3">
          <CardBody>
            <h6>Completed Steps</h6>
            {stepEvents.map((event, index) => (
              <div key={index} className="d-flex justify-content-between align-items-center mb-1">
                <small>Step {event.stepNumber}: {event.stepName}</small>
                <small className={
                  event.duration <= event.targetDuration ? 'text-success' : 'text-warning'
                }>
                  {event.duration.toFixed(1)}s / {event.targetDuration}s
                </small>
              </div>
            ))}
          </CardBody>
        </Card>
      )}
    </div>
  );
};

export default TrackingStatus;