import React, { useState } from 'react';
import { Card, CardBody, CardTitle, Button, Form, FormGroup, Label, Input, Alert, Row, Col, ListGroup } from 'reactstrap';
import type { Zone, ProcessStep } from '../../models';
import ProcessStepCard from './ProcessStepCard';

interface ProcessStepsListProps {
  steps: ProcessStep[];
  zones: Zone[];
  onStepsChange: (steps: ProcessStep[]) => void;
  onAddStep: (stepData: { StepName: string; TargetZoneId: number; Duration: number; Description: string }) => void;
  canEdit: boolean;
}

const ProcessStepsList: React.FC<ProcessStepsListProps> = ({
  steps,
  zones,
  onStepsChange,
  onAddStep,
  canEdit
}) => {
  const [showAddForm, setShowAddForm] = useState(false);
  const [newStep, setNewStep] = useState({
    StepName: '',
    TargetZoneId: 0,
    Duration: 5,
    Description: ''
  });

  const handleAddStep = () => {
    if (newStep.StepName.trim() && newStep.TargetZoneId > 0 && newStep.Duration > 0) {
      onAddStep(newStep);
      setNewStep({ StepName: '', TargetZoneId: 0, Duration: 5, Description: '' });
      setShowAddForm(false);
    }
  };

  const handleDeleteStep = (stepIndex: number) => {
    const updatedSteps = steps.filter((_, index) => index !== stepIndex);
    const renumberedSteps = updatedSteps.map((step, index) => ({
      ...step,
      StepNumber: index + 1
    }));
    onStepsChange(renumberedSteps);
  };

  const handleMoveStep = (fromIndex: number, toIndex: number) => {
    const updatedSteps = [...steps];
    const [movedStep] = updatedSteps.splice(fromIndex, 1);
    updatedSteps.splice(toIndex, 0, movedStep);
    
    const renumberedSteps = updatedSteps.map((step, index) => ({
      ...step,
      StepNumber: index + 1
    }));
    
    onStepsChange(renumberedSteps);
  };

  return (
    <Card>
      <CardBody>
        <Row className="align-items-center mb-3">
          <Col>
            <CardTitle tag="h5">Process Steps ({steps.length})</CardTitle>
          </Col>
          {canEdit && (
            <Col xs="auto">
              <Button 
                color="success" 
                size="sm"
                onClick={() => setShowAddForm(true)}
                disabled={showAddForm}
              >
                Add Step
              </Button>
            </Col>
          )}
        </Row>

        {showAddForm && (
          <Card className="mb-3 border-success">
            <CardBody>
              <h6>Add New Step</h6>
              <Form>
                <Row>
                  <Col md={3}>
                    <FormGroup>
                      <Label for="stepName">Step Name *</Label>
                      <Input
                        type="text"
                        id="stepName"
                        value={newStep.StepName}
                        onChange={(e) => setNewStep(prev => ({ ...prev, StepName: e.target.value }))}
                        placeholder="e.g. Press button A"
                      />
                    </FormGroup>
                  </Col>
                  <Col md={3}>
                    <FormGroup>
                      <Label for="targetZone">Target Zone *</Label>
                      <Input
                        type="select"
                        id="targetZone"
                        value={newStep.TargetZoneId}
                        onChange={(e) => setNewStep(prev => ({ ...prev, TargetZoneId: parseInt(e.target.value) }))}
                      >
                        <option value={0}>Select a zone...</option>
                        {zones.map(zone => (
                          <option key={zone.Id} value={zone.Id}>
                            {zone.ZoneName}
                          </option>
                        ))}
                      </Input>
                    </FormGroup>
                  </Col>
                  <Col md={2}>
                    <FormGroup>
                      <Label for="stepDuration">Duration (sec) *</Label>
                      <Input
                        type="number"
                        id="stepDuration"
                        value={newStep.Duration}
                        onChange={(e) => setNewStep(prev => ({ ...prev, Duration: parseInt(e.target.value) || 1 }))}
                        min="1"
                        placeholder="5"
                      />
                    </FormGroup>
                  </Col>
                  <Col md={4}>
                    <FormGroup>
                      <Label for="stepDescription">Description</Label>
                      <Input
                        type="text"
                        id="stepDescription"
                        value={newStep.Description}
                        onChange={(e) => setNewStep(prev => ({ ...prev, Description: e.target.value }))}
                        placeholder="Step description..."
                      />
                    </FormGroup>
                  </Col>
                </Row>
                <div className="d-flex gap-2">
                  <Button 
                    color="success" 
                    size="sm"
                    onClick={handleAddStep}
                    disabled={!newStep.StepName.trim() || newStep.TargetZoneId === 0 || newStep.Duration <= 0}
                  >
                    Add Step
                  </Button>
                  <Button 
                    color="secondary" 
                    size="sm"
                    onClick={() => {
                      setShowAddForm(false);
                      setNewStep({ StepName: '', TargetZoneId: 0, Duration: 5, Description: '' });
                    }}
                  >
                    Cancel
                  </Button>
                </div>
              </Form>
            </CardBody>
          </Card>
        )}

        {zones.length === 0 ? (
          <Alert color="warning">
            No zones found for this environment. Please create zones in the Configuration page first.
          </Alert>
        ) : steps.length === 0 ? (
          <Alert color="info">
            No steps added yet. Click "Add Step" to create the first step of your process.
          </Alert>
        ) : (
          <ListGroup>
            {steps.map((step, index) => (
              <ProcessStepCard
                key={step.Id}
                step={step}
                stepNumber={index + 1}
                onDelete={() => handleDeleteStep(index)}
                onMoveUp={index > 0 ? () => handleMoveStep(index, index - 1) : undefined}
                onMoveDown={index < steps.length - 1 ? () => handleMoveStep(index, index + 1) : undefined}
                canEdit={canEdit}
              />
            ))}
          </ListGroup>
        )}

        {steps.length > 0 && (
          <div className="mt-3 p-3 bg-light rounded">
            <small className="text-muted">
              <strong>Process Flow:</strong> {steps.map((step, index) => 
                `Step ${index + 1}: ${step.StepName} (${step.Duration}s)`
              ).join(' → ')}
            </small>
            <br />
            <small className="text-muted">
              <strong>Total Estimated Time:</strong> {steps.reduce((total, step) => total + (step.Duration || 0), 0)} seconds
            </small>
          </div>
        )}
      </CardBody>
    </Card>
  );
};

export default ProcessStepsList;