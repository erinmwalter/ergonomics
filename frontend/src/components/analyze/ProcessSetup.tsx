import React, { useState, useEffect } from 'react';
import { Card, CardBody, CardTitle, Button, Alert, Row, Col } from 'reactstrap';
import { Environment, Process } from '../../models';
import { apiService } from '../../services/ApiService';
import EnvironmentSelector from '../config/EnvironmentSelector';


interface ProcessSetupProps {
  onSetupComplete: (environment: Environment, process: Process) => void;
}

const ProcessSetup: React.FC<ProcessSetupProps> = ({ onSetupComplete }) => {
  const [selectedEnvironment, setSelectedEnvironment] = useState<Environment | null>(null);
  const [processes, setProcesses] = useState<Process[]>([]);
  const [selectedProcess, setSelectedProcess] = useState<Process | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  // Load processes when environment is selected
  useEffect(() => {
    if (selectedEnvironment) {
      loadProcesses();
    } else {
      setProcesses([]);
      setSelectedProcess(null);
    }
  }, [selectedEnvironment]);

  const loadProcesses = async () => {
    if (!selectedEnvironment) return;
    
    setLoading(true);
    setError(null);
    
    try {
      const data = await apiService.getProcessesForEnvironment(selectedEnvironment.Id);
      setProcesses(data);
      
      if (data.length === 0) {
        setError('No processes found for this environment. Please create a process first.');
      }
    } catch (err) {
      console.error('Failed to load processes:', err);
      setError('Failed to load processes');
      setProcesses([]);
    }
    
    setLoading(false);
  };

  const handleEnvironmentSelect = (environment: Environment | null) => {
    setSelectedEnvironment(environment);
    setSelectedProcess(null);
  };

  const handleProcessSelect = (process: Process) => {
    setSelectedProcess(process);
  };

  const handleStartAnalysis = () => {
    if (selectedEnvironment && selectedProcess) {
      onSetupComplete(selectedEnvironment, selectedProcess);
    }
  };

  const canProceed = selectedEnvironment && selectedProcess;

  return (
    <div>
      <Card className="mb-4">
        <CardBody>
          <CardTitle tag="h4">Step 1: Select Environment</CardTitle>
          <EnvironmentSelector
            onEnvironmentSelect={handleEnvironmentSelect}
            onCreateNew={() => {
              // For analysis, we don't create new environments
              alert('Please use the Configuration page to create new environments.');
            }}
          />
        </CardBody>
      </Card>

      {selectedEnvironment && (
        <Card className="mb-4">
          <CardBody>
            <CardTitle tag="h4">Step 2: Select Process</CardTitle>
            <p className="text-muted">
              Choose the process you want to analyze for environment: <strong>{selectedEnvironment.Name}</strong>
            </p>

            {error && (
              <Alert color="warning">
                {error}
                {error.includes('No processes found') && (
                  <div className="mt-2">
                    <Button color="primary" size="sm" onClick={() => window.location.href = '/process'}>
                      Create Process
                    </Button>
                  </div>
                )}
              </Alert>
            )}

            {loading ? (
              <div className="text-center p-4">
                <div className="spinner-border" role="status">
                  <span className="sr-only">Loading processes...</span>
                </div>
              </div>
            ) : processes.length > 0 ? (
              <Row>
                {processes.map((process) => (
                  <Col md={6} key={process.Id} className="mb-3">
                    <Card 
                      className={`h-100 ${selectedProcess?.Id === process.Id ? 'border-primary bg-light' : ''}`}
                      style={{ cursor: 'pointer' }}
                      onClick={() => handleProcessSelect(process)}
                    >
                      <CardBody>
                        <h6 className="card-title">{process.ProcessName}</h6>
                        <p className="card-text text-muted small">{process.Description}</p>
                        <div className="d-flex justify-content-between align-items-center">
                          <small className="text-muted">
                            Target: {process.Duration}s
                          </small>
                          {selectedProcess?.Id === process.Id && (
                            <span className="badge bg-primary">Selected</span>
                          )}
                        </div>
                      </CardBody>
                    </Card>
                  </Col>
                ))}
              </Row>
            ) : null}
          </CardBody>
        </Card>
      )}

      {canProceed && (
        <Card className="mb-4 border-success">
          <CardBody>
            <CardTitle tag="h4" className="text-success">Ready to Start</CardTitle>
            <Row>
              <Col md={6}>
                <h6>Selected Environment:</h6>
                <p className="mb-2">{selectedEnvironment.Name}</p>
                
                <h6>Selected Process:</h6>
                <p className="mb-2">{selectedProcess.ProcessName}</p>
                <small className="text-muted">{selectedProcess.Description}</small>
              </Col>
              <Col md={6} className="d-flex align-items-center justify-content-end">
                <Button 
                  color="success" 
                  size="lg"
                  onClick={handleStartAnalysis}
                >
                  Start Analysis →
                </Button>
              </Col>
            </Row>
          </CardBody>
        </Card>
      )}
    </div>
  );
};

export default ProcessSetup;