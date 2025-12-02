import React, { useState, useEffect } from 'react';
import { Card, CardBody, CardTitle, Button, ListGroup, ListGroupItem, Alert, Row, Col } from 'reactstrap';
import { apiService } from '../../services/ApiService';
import type { Environment, Process } from '../../models';

interface ProcessSelectorProps {
  environment: Environment;
  onProcessSelect: (process: Process | null) => void;
  onBack: () => void;
}

const ProcessSelector: React.FC<ProcessSelectorProps> = ({
  environment,
  onProcessSelect,
  onBack
}) => {
  const [processes, setProcesses] = useState<Process[]>([]);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const loadProcesses = async () => {
    setLoading(true);
    setError(null);
    try {
      const data = await apiService.getProcessesForEnvironment(environment.Id);
      setProcesses(data);
    } catch (err) {
      console.error('Failed to load processes:', err);
      setError('Failed to load processes');
      setProcesses([]);
    }
    setLoading(false);
  };

  useEffect(() => {
    loadProcesses();
  }, [environment.Id]);

  return (
    <Card>
      <CardBody>
        <Row className="align-items-center mb-3">
          <Col>
            <CardTitle tag="h4">
              Processes for "{environment.Name}"
            </CardTitle>
          </Col>
          <Col xs="auto">
            <Button color="secondary" onClick={onBack} className="me-2">
              Back to Environments
            </Button>
            <Button color="primary" onClick={() => onProcessSelect(null)}>
              Create New Process
            </Button>
          </Col>
        </Row>

        {error && (
          <Alert color="danger">
            {error}
          </Alert>
        )}

        {loading ? (
          <div className="text-center p-4">
            <div className="spinner-border" role="status">
              <span className="sr-only">Loading...</span>
            </div>
          </div>
        ) : processes.length === 0 ? (
          <Alert color="info">
            No processes found for this environment. Click "Create New Process" to get started.
          </Alert>
        ) : (
          <ListGroup>
            {processes.map((process) => (
              <ListGroupItem
                key={process.Id}
                className="d-flex justify-content-between align-items-center"
              >
                <div>
                  <h6 className="mb-1">{process.ProcessName}</h6>
                  <p className="mb-1 text-muted">{process.Description}</p>
                  <small>Duration: {process.Duration} seconds</small>
                </div>
                <Button
                  color="outline-primary"
                  size="sm"
                  onClick={() => onProcessSelect(process)}
                >
                  Edit Process
                </Button>
              </ListGroupItem>
            ))}
          </ListGroup>
        )}
      </CardBody>
    </Card>
  );
};

export default ProcessSelector;