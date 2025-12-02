import React, { useState, useEffect } from 'react';
import { FormGroup, Label, Input, Button, Row, Col, Alert } from 'reactstrap';
import type { Environment } from '../../models';
import { apiService } from '../../services/ApiService';

interface EnvironmentSelectorProps {
  onEnvironmentSelect: (environment: Environment | null) => void;
  onCreateNew: () => void;
}

const EnvironmentSelector: React.FC<EnvironmentSelectorProps> = ({ 
  onEnvironmentSelect, 
  onCreateNew 
}) => {
  const [environments, setEnvironments] = useState<Environment[]>([]);
  const [selectedId, setSelectedId] = useState<string>('');
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const loadEnvironments = async () => {
    setLoading(true);
    setError(null);
    
    try {
      const data = await apiService.getEnvironments();
      setEnvironments(data);
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to load environments');
      console.error('Failed to load environments:', err);
      //TESTING ONLY - placeholder until the database is set up and running
      setEnvironments([
        { Id: 1, Name: 'Workstation A', ImagePath: '/uploads/station_a.jpg', CreatedAt: '2025-11-26', CreatedBy: 'admin', IsActive: true },
        { Id: 2, Name: 'Assembly Line 2', ImagePath: '/uploads/line_2.jpg', CreatedAt: '2025-11-26', CreatedBy: 'admin', IsActive: true }
      ]);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    loadEnvironments();
  }, []);

  const handleSelectionChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    const value = e.target.value;
    setSelectedId(value);
    
    if (value === '') {
      onEnvironmentSelect(null);
    } else {
      const selected = environments.find(env => env.Id.toString() === value);
      onEnvironmentSelect(selected || null);
    }
  };

  return (
    <Row className="mb-4">
      <Col md={12}>
        {error && (
          <Alert color="warning" className="mb-3">
            API connection failed - using placeholder data. Error: {error}
          </Alert>
        )}
      </Col>
      <Col md={8}>
        <FormGroup>
          <Label for="environmentSelect">Select Environment to Edit:</Label>
          <Input
            type="select"
            name="environmentSelect"
            id="environmentSelect"
            value={selectedId}
            onChange={handleSelectionChange}
            disabled={loading}
          >
            <option value="">
              {loading ? '-- Loading Environments --' : '-- Select an Environment --'}
            </option>
            {environments.map(env => (
              <option key={env.Id} value={env.Id}>
                {env.Name} (Created: {env.CreatedAt})
              </option>
            ))}
          </Input>
        </FormGroup>
      </Col>
      <Col md={4} className="d-flex align-items-end">
        <Button color="primary" onClick={onCreateNew} className="mb-3" disabled={loading}>
          Create New Environment
        </Button>
      </Col>
    </Row>
  );
};

export default EnvironmentSelector;