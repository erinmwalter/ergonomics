import React, { useState } from 'react';
import { Container, Row, Col, Card, CardBody, CardTitle } from 'reactstrap';
import type { Environment } from '../../models';
import EnvironmentSelector from './EnvironmentSelector';
import EnvironmentEditor from './EnvironmentEditor';
import EnvironmentCreator from './EnvironmentCreator';

const ConfigPage: React.FC = () => {
  const [selectedEnvironment, setSelectedEnvironment] = useState<Environment | null>(null);
  const [mode, setMode] = useState<'select' | 'edit' | 'create'>('select');

  const handleEnvironmentSelect = (environment: Environment | null) => {
    setSelectedEnvironment(environment);
    setMode(environment ? 'edit' : 'select');
  };

  const handleCreateNew = () => {
    setSelectedEnvironment(null);
    setMode('create');
  };

  const handleBackToSelect = () => {
    setSelectedEnvironment(null);
    setMode('select');
  };

  const handleEnvironmentCreated = (environment: Environment) => {
    setSelectedEnvironment(environment);
    setMode('edit');
  };

  return (
    <Container fluid className="mt-4">
      <Row>
        <Col>
          <h1>SOP Configuration</h1>
          
          {mode === 'select' && (
            <Card>
              <CardBody>
                <CardTitle>Environment Setup</CardTitle>
                <EnvironmentSelector 
                  onEnvironmentSelect={handleEnvironmentSelect}
                  onCreateNew={handleCreateNew}
                />
              </CardBody>
            </Card>
          )}

          {mode === 'edit' && selectedEnvironment && (
            <EnvironmentEditor 
              environment={selectedEnvironment}
              onBack={handleBackToSelect}
            />
          )}

          {mode === 'create' && (
            <EnvironmentCreator
              onBack={handleBackToSelect}
              onEnvironmentCreated={handleEnvironmentCreated}
            />
          )}
        </Col>
      </Row>
    </Container>
  );
};

export default ConfigPage;