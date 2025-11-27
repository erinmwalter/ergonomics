import React, { useState, useEffect } from 'react';
import { Card, CardBody, CardTitle, Button, Form, FormGroup, Label, Input, Alert, Row, Col } from 'reactstrap';
import { Environment, Process, Zone, ProcessStep } from '../../models';
import { apiService } from '../../services/ApiService';
import ImageDisplay from '../config/ImageDisplay';
import ZoneBox from '../config/ZoneBox';
import ProcessStepsList from './ProcessStepsList';


interface ProcessEditorProps {
  environment: Environment;
  process: Process | null; // null for create mode
  onBack: () => void;
  onProcessCreated: (process: Process) => void;
}

interface ProcessFormData {
  ProcessName: string;
  Description: string;
  Duration: number;
}

interface StepFormData {
  StepName: string;
  TargetZoneId: number;
  Duration: number;
  Description: string;
}

const ProcessEditor: React.FC<ProcessEditorProps> = ({
  environment,
  process,
  onBack,
  onProcessCreated
}) => {
  const [processData, setProcessData] = useState<ProcessFormData>({
    ProcessName: process?.ProcessName || '',
    Description: process?.Description || '',
    Duration: process?.Duration || 10
  });

  const [zones, setZones] = useState<Zone[]>([]);
  const [steps, setSteps] = useState<ProcessStep[]>([]);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [currentProcess, setCurrentProcess] = useState<Process | null>(process);

  // Load zones and steps
  useEffect(() => {
    loadZones();
    if (currentProcess) {
      loadSteps();
    }
  }, [environment.Id, currentProcess?.Id]);

  const loadZones = async () => {
    try {
      const zonesData = await apiService.getZonesForEnvironment(environment.Id);
      setZones(zonesData);
    } catch (err) {
      console.error('Failed to load zones:', err);
      setError('Failed to load zones');
    }
  };

  const loadSteps = async () => {
    if (!currentProcess) return;
    
    try {
      const stepsData = await apiService.getProcessSteps(currentProcess.Id);
      setSteps(stepsData);
    } catch (err) {
      console.error('Failed to load steps:', err);
      setError('Failed to load process steps');
    }
  };

  const handleProcessDataChange = (field: keyof ProcessFormData, value: string | number) => {
    setProcessData(prev => ({ ...prev, [field]: value }));
  };

  const saveProcess = async () => {
    setLoading(true);
    setError(null);

    try {
      let savedProcess: Process;
      
      if (currentProcess) {
        // Update existing process
        savedProcess = await apiService.updateProcess(currentProcess.Id, processData);
      } else {
        // Create new process
        savedProcess = await apiService.createProcess({
          ...processData,
          EnvironmentId: environment.Id,
          CreatedBy: 'admin',
          IsActive: true
        });
        setCurrentProcess(savedProcess);
        onProcessCreated(savedProcess);
      }

      // Save steps if any
      if (steps.length > 0) {
        await saveSteps(savedProcess);
      }

    } catch (err) {
      console.error('Failed to save process:', err);
      setError('Failed to save process');
    }
    
    setLoading(false);
  };

  const saveSteps = async (processToSave: Process) => {
    try {
      const stepData = steps.map(step => ({
        StepName: step.StepName,
        TargetZoneId: step.TargetZoneId,
        Duration: step.Duration,
        Description: step.Description
      }));

      await apiService.saveProcessSteps(processToSave.Id, stepData);
      await loadSteps(); // Reload to get updated step data
    } catch (err) {
      console.error('Failed to save steps:', err);
      setError('Failed to save process steps');
    }
  };

  const addStep = (stepData: StepFormData) => {
    const newStep: ProcessStep = {
      Id: Date.now(), // Temporary ID
      ProcessId: currentProcess?.Id || 0,
      StepNumber: steps.length + 1,
      StepName: stepData.StepName,
      TargetZoneId: stepData.TargetZoneId,
      Duration: stepData.Duration,
      Description: stepData.Description,
      CreatedAt: new Date().toISOString(),
      CreatedBy: 'admin',
      IsActive: true,
      // Add zone info for display
      ZoneName: zones.find(z => z.Id === stepData.TargetZoneId)?.ZoneName || '',
      Color: zones.find(z => z.Id === stepData.TargetZoneId)?.Color || '#000000'
    };

    setSteps(prev => [...prev, newStep]);
  };

  const updateSteps = (updatedSteps: ProcessStep[]) => {
    setSteps(updatedSteps);
  };

  const isCreateMode = !process;

  return (
    <div>
      <Card className="mb-4">
        <CardBody>
          <Row className="align-items-center mb-3">
            <Col>
              <CardTitle tag="h4">
                {isCreateMode ? 'Create New Process' : `Edit Process: ${process.ProcessName}`}
              </CardTitle>
            </Col>
            <Col xs="auto">
              <Button color="secondary" onClick={onBack} className="me-2">
                Back to Processes
              </Button>
              <Button 
                color="primary" 
                onClick={saveProcess}
                disabled={loading || !processData.ProcessName.trim()}
              >
                {loading ? 'Saving...' : (isCreateMode ? 'Create Process' : 'Update Process')}
              </Button>
            </Col>
          </Row>

          {error && (
            <Alert color="danger">
              {error}
            </Alert>
          )}

          <Form>
            <Row>
              <Col md={6}>
                <FormGroup>
                  <Label for="processName">Process Name *</Label>
                  <Input
                    type="text"
                    id="processName"
                    value={processData.ProcessName}
                    onChange={(e) => handleProcessDataChange('ProcessName', e.target.value)}
                    placeholder="Enter process name"
                  />
                </FormGroup>
              </Col>
              <Col md={6}>
                <FormGroup>
                  <Label for="duration">Target Duration (seconds) *</Label>
                  <Input
                    type="number"
                    id="duration"
                    value={processData.Duration}
                    onChange={(e) => handleProcessDataChange('Duration', parseInt(e.target.value) || 0)}
                    min="1"
                    placeholder="Duration in seconds"
                  />
                </FormGroup>
              </Col>
            </Row>
            <FormGroup>
              <Label for="description">Description</Label>
              <Input
                type="textarea"
                id="description"
                value={processData.Description}
                onChange={(e) => handleProcessDataChange('Description', e.target.value)}
                placeholder="Describe this process..."
                rows={3}
              />
            </FormGroup>
          </Form>
        </CardBody>
      </Card>

      <Card className="mb-4">
        <CardBody>
          <CardTitle tag="h5">Environment: {environment.Name}</CardTitle>
          <p className="text-muted">Select zones below when adding process steps</p>
          
          <ImageDisplay
            imagePath={environment.ImagePath}
            alt={`Environment: ${environment.Name}`}
            onImageLoad={(dimensions) => console.log('Image loaded:', dimensions)}
          >
            {/* Zone overlays */}
            <div className="position-absolute top-0 start-0">
              {zones.map(zone => (
                <ZoneBox
                  key={zone.Id}
                  zone={zone}
                  isSelected={false}
                  onSelect={() => {}} // Read-only display
                  onUpdate={() => {}} // Read-only display
                />
              ))}
            </div>
          </ImageDisplay>
          
          <div className="mt-3">
            <small className="text-muted">
              <strong>Available Zones:</strong> {zones.map(zone => 
                `${zone.ZoneName}`
              ).join(', ') || 'No zones configured'}
            </small>
          </div>
        </CardBody>
      </Card>

      <ProcessStepsList
        steps={steps}
        zones={zones}
        onStepsChange={updateSteps}
        onAddStep={addStep}
        canEdit={!!currentProcess || isCreateMode}
      />
    </div>
  );
};

export default ProcessEditor;