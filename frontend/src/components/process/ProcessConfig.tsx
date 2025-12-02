import React, { useState } from 'react';
import { Container, Row, Col, Card, CardBody, CardTitle } from 'reactstrap';
import ProcessEditor from './ProcessEditor';
import { Environment, Process } from '../../models';
import EnvironmentSelector from '../config/EnvironmentSelector';
import ProcessSelector from './ProcessSelector';

const ProcessConfig: React.FC = () => {
  const [selectedEnvironment, setSelectedEnvironment] = useState<Environment | null>(null);
  const [selectedProcess, setSelectedProcess] = useState<Process | null>(null);
  const [mode, setMode] = useState<'selectEnvironment' | 'selectProcess' | 'editProcess' | 'createProcess'>('selectEnvironment');

  const handleEnvironmentSelect = (environment: Environment | null) => {
    setSelectedEnvironment(environment);
    setSelectedProcess(null);
    if (environment) {
      setMode('selectProcess');
    } else {
      setMode('selectEnvironment');
    }
  };

  const handleProcessSelect = (process: Process | null) => {
    setSelectedProcess(process);
    setMode(process ? 'editProcess' : 'createProcess');
  };

  const handleBackToEnvironments = () => {
    setSelectedEnvironment(null);
    setSelectedProcess(null);
    setMode('selectEnvironment');
  };

  const handleBackToProcesses = () => {
    setSelectedProcess(null);
    setMode('selectProcess');
  };

  const handleProcessCreated = (process: Process) => {
    setSelectedProcess(process);
    setMode('editProcess');
  };

  const handleCreateNewEnvironment = () => {
    //TODO : Implement this
    console.log('Environment creation not implemented in process config');
  };

  return (
    <Container fluid className="mt-4">
      <Row>
        <Col>
          <h1>Process Configuration</h1>
          
          {mode === 'selectEnvironment' && (
            <Card>
              <CardBody>
                <CardTitle>Select Environment</CardTitle>
                <EnvironmentSelector 
                  onEnvironmentSelect={handleEnvironmentSelect}
                  onCreateNew={handleCreateNewEnvironment}
                />
              </CardBody>
            </Card>
          )}

          {mode === 'selectProcess' && selectedEnvironment && (
            <ProcessSelector
              environment={selectedEnvironment}
              onProcessSelect={handleProcessSelect}
              onBack={handleBackToEnvironments}
            />
          )}

          {(mode === 'editProcess' || mode === 'createProcess') && selectedEnvironment && (
            <ProcessEditor
              environment={selectedEnvironment}
              process={selectedProcess}
              onBack={handleBackToProcesses}
              onProcessCreated={handleProcessCreated}
            />
          )}
        </Col>
      </Row>
    </Container>
  );
};

export default ProcessConfig;