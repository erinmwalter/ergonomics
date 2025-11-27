import React, { useState } from 'react';
import { Container, Row, Col } from 'reactstrap';
import { Environment, Process } from '../../models';
import ProcessSetup from './ProcessSetup';
import WebcamViewer from './WebcamViewer';
import ProcessTracker from './ProcessTracker';
import ProcessResults from './ProcessResults';

type AnalyzeMode = 'setup' | 'webcam' | 'tracking' | 'results';

interface AnalysisSession {
  environment: Environment;
  process: Process;
  results?: any; // TODO: Define proper results interface
}

const AnalyzeProcess: React.FC = () => {
  const [mode, setMode] = useState<AnalyzeMode>('setup');
  const [session, setSession] = useState<AnalysisSession | null>(null);
  const [webcamActive, setWebcamActive] = useState(false);
  const [trackingActive, setTrackingActive] = useState(false);

  const handleSetupComplete = (environment: Environment, process: Process) => {
    setSession({ environment, process });
    setMode('webcam');
  };

  const handleWebcamReady = () => {
    setWebcamActive(true);
    setMode('tracking');
  };

  const handleTrackingStart = () => {
    setTrackingActive(true);
  };

  const handleTrackingComplete = (results: any) => {
    setTrackingActive(false);
    setSession(prev => prev ? { ...prev, results } : null);
    setMode('results');
  };

  const handleRestart = () => {
    setSession(null);
    setWebcamActive(false);
    setTrackingActive(false);
    setMode('setup');
  };

  const handleNewProcess = () => {
    if (session) {
      setSession({ environment: session.environment, process: session.process });
      setMode('tracking');
    }
  };

  return (
    <Container fluid className="mt-4">
      <Row>
        <Col>
          <h1>Process Analysis</h1>
          <p className="text-muted">
            Analyze process adherence using real-time hand tracking
          </p>

          {mode === 'setup' && (
            <ProcessSetup onSetupComplete={handleSetupComplete} />
          )}

          {mode === 'webcam' && session && (
            <WebcamViewer 
              onWebcamReady={handleWebcamReady}
              onBack={() => setMode('setup')}
            />
          )}

          {mode === 'tracking' && session && (
            <ProcessTracker
              environment={session.environment}
              process={session.process}
              webcamActive={webcamActive}
              onTrackingStart={handleTrackingStart}
              onTrackingComplete={handleTrackingComplete}
              onBack={() => setMode('webcam')}
            />
          )}

          {mode === 'results' && session && session.results && (
            <ProcessResults
              environment={session.environment}
              process={session.process}
              results={session.results}
              onRestart={handleRestart}
              onNewProcess={handleNewProcess}
            />
          )}
        </Col>
      </Row>
    </Container>
  );
};

export default AnalyzeProcess;