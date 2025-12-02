import React, { useState, useRef } from 'react';
import { Card, CardBody, CardTitle, Button, Row, Col, FormGroup, Label, Input, Alert } from 'reactstrap';
import type { Environment, Zone } from '../../models';
import { apiService } from '../../services/ApiService';
import ImageDisplay from './ImageDisplay';
import ZoneBox from './ZoneBox';
import ZonePropertiesPanel from './ZonePropertiesPanel';

interface EnvironmentCreatorProps {
  onBack: () => void;
  onEnvironmentCreated: (environment: Environment) => void;
}

type CreationStep = 'setup' | 'capture' | 'configure';

const EnvironmentCreator: React.FC<EnvironmentCreatorProps> = ({
  onBack,
  onEnvironmentCreated
}) => {
  const [currentStep, setCurrentStep] = useState<CreationStep>('setup');
  const [environmentName, setEnvironmentName] = useState('');
  const [imageSrc, setImageSrc] = useState<string | null>(null);
  const [zones, setZones] = useState<Zone[]>([]);
  const [selectedZone, setSelectedZone] = useState<Zone | null>(null);
  const [imageDimensions, setImageDimensions] = useState<{ width: number; height: number } | null>(null);
  const [isCapturing, setIsCapturing] = useState(false);
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const videoRef = useRef<HTMLVideoElement>(null);
  const canvasRef = useRef<HTMLCanvasElement>(null);
  const fileInputRef = useRef<HTMLInputElement>(null);

  const handleFileUpload = async (event: React.ChangeEvent<HTMLInputElement>) => {
  const file = event.target.files?.[0];
  if (file) {
    try {
      const reader = new FileReader();
      reader.onload = async (e) => {
        const imageData = e.target?.result as string;
        
        const imagePath = await apiService.uploadImage(imageData);
        
        setImageSrc(imagePath);
        setCurrentStep('configure');
      };
      reader.readAsDataURL(file);
    } catch (error) {
      console.error('Failed to upload image:', error);
      setError('Failed to upload image. Please try again.');
    }
  }
};

  const startWebcamCapture = async () => {
  try {
    setError(null);
    setIsCapturing(true);
    
    console.log('Requesting webcam access...');
    const stream = await navigator.mediaDevices.getUserMedia({ 
      video: { width: 640, height: 480 } 
    });
    
    console.log('Got webcam stream:', stream);
    
    setCurrentStep('capture');
    
    setTimeout(() => {
      if (videoRef.current) {
        console.log('Setting stream on video element');
        videoRef.current.srcObject = stream;
        videoRef.current.play().catch(err => {
          console.error('Video play failed:', err);
        });
        setIsCapturing(false);
      }
    }, 100);
    
  } catch (err) {
    console.error('Webcam error:', err);
    setError('Failed to access webcam. Please check permissions.');
    setIsCapturing(false);
  }
};

  const capturePhoto = async () => {
  if (!videoRef.current || !canvasRef.current) return;

  const canvas = canvasRef.current;
  const video = videoRef.current;
  
  canvas.width = video.videoWidth;
  canvas.height = video.videoHeight;
  
  const ctx = canvas.getContext('2d');
  if (ctx) {
    ctx.drawImage(video, 0, 0);
    const imageData = canvas.toDataURL('image/jpeg', 0.8);
    
    try {
      const imagePath = await apiService.uploadImage(imageData);
      
      const stream = video.srcObject as MediaStream;
      stream.getTracks().forEach(track => track.stop());
      
      setImageSrc(imagePath);
      setCurrentStep('configure');
      setIsCapturing(false);
      
    } catch (error) {
      console.error('Failed to upload image:', error);
      setError('Failed to save image. Please try again.');
    }
  }
};

  const stopWebcam = () => {
    if (videoRef.current) {
      const stream = videoRef.current.srcObject as MediaStream;
      if (stream) {
        stream.getTracks().forEach(track => track.stop());
      }
    }
    setCurrentStep('setup');
    setIsCapturing(false);
  };

  const handleImageLoad = (dimensions: { width: number; height: number }) => {
    setImageDimensions(dimensions);
  };

  const handleZoneSelect = (zone: Zone) => {
    setSelectedZone(zone);
  };

  const handleZoneUpdate = (updatedZone: Zone) => {
    setZones(prevZones => 
      prevZones.map(zone => 
        zone.Id === updatedZone.Id ? updatedZone : zone
      )
    );
    if (selectedZone?.Id === updatedZone.Id) {
      setSelectedZone(updatedZone);
    }
  };

  const handleZoneDelete = (zoneId: number) => {
    setZones(prevZones => prevZones.filter(zone => zone.Id !== zoneId));
    if (selectedZone?.Id === zoneId) {
      setSelectedZone(null);
    }
  };

  const handleAddNewZone = () => {
    const newZone: Zone = {
      Id: Math.max(...zones.map(z => z.Id), 0) + 1,
      EnvironmentId: 0,
      ZoneName: `Zone ${zones.length + 1}`,
      Xstart: 50,
      Ystart: 50,
      Xend: 150,
      Yend: 150,
      Color: '#0066CC',
      CreatedAt: new Date().toISOString().split('T')[0],
      CreatedBy: 'admin',
      IsActive: true
    };

    setZones(prevZones => [...prevZones, newZone]);
    setSelectedZone(newZone);
  };

 const handleSave = async () => {
  if (!environmentName.trim() || !imageSrc) {
    setError('Please provide environment name and image');
    return;
  }

  setSaving(true);
  setError(null);

  try {
    const environment = await apiService.createEnvironment(
      environmentName.trim(),
      imageSrc,
      'admin'
    );

    if (zones.length > 0) {
      const zonesWithEnvironmentId = zones.map(zone => ({
        ...zone,
        EnvironmentId: environment.Id
      }));

      try {
        await apiService.saveZonesForEnvironment(environment.Id, zonesWithEnvironmentId);
      } catch (zoneError) {
        console.error('Failed to save zones:', zoneError);
       
        setError('Environment created but some zones failed to save. You can edit them later.');
      }
    }

    onEnvironmentCreated(environment);
  } catch (err) {
    setError('Failed to create environment. Please try again.');
  } finally {
    setSaving(false);
  }
};

  if (currentStep === 'setup') {
    return (
      <Card>
        <CardBody>
          <CardTitle>Create New Environment</CardTitle>
          
          {error && <Alert color="danger">{error}</Alert>}
          
          <FormGroup>
            <Label for="environmentName">Environment Name</Label>
            <Input
              type="text"
              id="environmentName"
              value={environmentName}
              onChange={(e) => setEnvironmentName(e.target.value)}
              placeholder="e.g., Assembly Line A, Workstation 1"
            />
          </FormGroup>

          <FormGroup>
            <Label>Choose Image Source</Label>
            <div className="d-grid gap-2">
              <Button 
                color="primary" 
                onClick={() => fileInputRef.current?.click()}
                disabled={!environmentName.trim()}
              >
                Upload Image File
              </Button>
              <Button 
                color="primary" 
                onClick={startWebcamCapture}
                disabled={!environmentName.trim() || isCapturing}
              >
                {isCapturing ? 'Starting Camera...' : 'Capture from Webcam'}
              </Button>
            </div>
          </FormGroup>

          <input
            ref={fileInputRef}
            type="file"
            accept="image/*"
            onChange={handleFileUpload}
            style={{ display: 'none' }}
          />

          <div className="mt-3">
            <Button color="secondary" onClick={onBack}>
              Back to Selection
            </Button>
          </div>
        </CardBody>
      </Card>
    );
  }

  if (currentStep === 'capture') {
    return (
      <Card>
        <CardBody>
          <CardTitle>Capture Environment Photo</CardTitle>
          
          <div className="text-center mb-3">
            <video
              ref={videoRef}
              autoPlay
              playsInline
              muted
              style={{
                width: '100%',
                maxWidth: '640px',
                height: 'auto',
                border: '2px solid #dee2e6',
                borderRadius: '8px',
                backgroundColor: '#000'
              }}
            />
          </div>

          <div className="d-grid gap-2">
            <Button 
              color="success" 
              size="lg"
              onClick={capturePhoto}
            >
              Capture Environment
            </Button>
            <Button color="secondary" onClick={stopWebcam}>
              Cancel / Back to Setup
            </Button>
          </div>

          <canvas ref={canvasRef} style={{ display: 'none' }} />
        </CardBody>
      </Card>
    );
  }

  return (
    <div>
      <Card className="mb-3">
        <CardBody>
          <Row>
            <Col md={8}>
              <CardTitle tag="h4">Configure: {environmentName}</CardTitle>
              <p className="text-muted mb-0">Add zones to define interactive areas</p>
            </Col>
            <Col md={4} className="text-end">
              <Button color="secondary" onClick={() => setCurrentStep('setup')} className="me-2">
                Back to Setup
              </Button>
              <Button 
                color="success" 
                onClick={handleSave}
                disabled={saving || !environmentName.trim()}
              >
                {saving ? 'Saving...' : 'Save Environment'}
              </Button>
            </Col>
          </Row>
        </CardBody>
      </Card>

      {error && <Alert color="danger">{error}</Alert>}

      <Row>
        <Col lg={9}>
          <Card>
            <CardBody>
              <div className="d-flex justify-content-between align-items-center mb-3">
                <h5 className="mb-0">Environment Image & Zones</h5>
                <Button color="primary" size="sm" onClick={handleAddNewZone}>
                  Add New Zone
                </Button>
              </div>
              
              {imageSrc && (
                <ImageDisplay
                  imagePath={imageSrc}
                  alt={`Environment: ${environmentName}`}
                  onImageLoad={handleImageLoad}
                >
                  <div className="position-absolute top-0 start-0">
                    {zones.map(zone => (
                      <ZoneBox
                        key={zone.Id}
                        zone={zone}
                        isSelected={selectedZone?.Id === zone.Id}
                        onSelect={handleZoneSelect}
                        onUpdate={handleZoneUpdate}
                      />
                    ))}
                  </div>
                </ImageDisplay>
              )}
            </CardBody>
          </Card>
        </Col>
        
        <Col lg={3}>
          <ZonePropertiesPanel
            zone={selectedZone}
            onZoneUpdate={handleZoneUpdate}
            onZoneDelete={handleZoneDelete}
            imageDimensions={imageDimensions}
          />
        </Col>
      </Row>
    </div>
  );
};

export default EnvironmentCreator;