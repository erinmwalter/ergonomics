import React, { useState, useEffect } from 'react';
import { Card, CardBody, CardTitle, Button, Row, Col } from 'reactstrap';
import type { Environment, Zone } from '../../models';
import { apiService } from '../../services/ApiService';
import ImageDisplay from './ImageDisplay';
import ZoneBox from './ZoneBox';
import ZonePropertiesPanel from './ZonePropertiesPanel';

interface EnvironmentEditorProps {
  environment: Environment;
  onBack: () => void;
}

const EnvironmentEditor: React.FC<EnvironmentEditorProps> = ({ 
  environment, 
  onBack 
}) => {
  const [zones, setZones] = useState<Zone[]>([]);
  const [loading, setLoading] = useState(false);
  const [selectedZone, setSelectedZone] = useState<Zone | null>(null);
  const [imageDimensions, setImageDimensions] = useState<{ width: number; height: number } | null>(null);
  const [hasUnsavedChanges, setHasUnsavedChanges] = useState(false);
  const [isSaving, setIsSaving] = useState(false);

  const loadZones = async () => {
    setLoading(true);
    try {
      const data = await apiService.getZonesForEnvironment(environment.Id);
      setZones(data);
    } catch (error) {
      console.error('Failed to load zones:', error);
      // Fallback placeholder zones for testing
      setZones([
        { Id: 1, EnvironmentId: environment.Id, ZoneName: 'Button A', Xstart: 100, Ystart: 100, Xend: 200, Yend: 200, Color: '#FF0000', CreatedAt: '2025-11-26', CreatedBy: 'admin', IsActive: true },
        { Id: 2, EnvironmentId: environment.Id, ZoneName: 'Safety Switch', Xstart: 300, Ystart: 150, Xend: 400, Yend: 250, Color: '#00FF00', CreatedAt: '2025-11-26', CreatedBy: 'admin', IsActive: true }
      ]);
    }
    setLoading(false);
  };

  useEffect(() => {
    loadZones();
  }, [environment.Id]);

  const handleImageLoad = (dimensions: { width: number; height: number }) => {
    setImageDimensions(dimensions);
  };

  const handleSaveChanges = async () => {
  setIsSaving(true);
  try {
    const savedZones = await apiService.saveZonesForEnvironment(environment.Id, zones);
    setZones(savedZones);
    setHasUnsavedChanges(false);
  } catch (error) {
    console.error('Failed to save zones:', error);
  } finally {
    setIsSaving(false);
  }
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
  setHasUnsavedChanges(true); 
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
      EnvironmentId: environment.Id,
      ZoneName: `New Zone ${zones.length + 1}`,
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

  return (
    <div>
      {/* Environment Header */}
      <Card className="mb-3">
        <CardBody>
          <Row>
            <Col md={8}>
              <CardTitle tag="h4">Editing: {environment.Name}</CardTitle>
              <p className="text-muted mb-0">
                Created by {environment.CreatedBy} on {environment.CreatedAt}
              </p>
            </Col>
            <Col md={4} className="text-end">
              <Button color="secondary" onClick={onBack} className="me-2">
                Back to Selection
              </Button>
              <Button color="success" onClick={handleSaveChanges} disabled={!hasUnsavedChanges || isSaving}>
                {isSaving ? 'Saving...' : hasUnsavedChanges ? 'Save Changes' : 'Saved'}
              </Button>
            </Col>
          </Row>
        </CardBody>
      </Card>

      {/* Main Editor Area */}
      <Row>
        <Col lg={9}>
          {/* Image Display + Zone Overlay */}
          <Card>
            <CardBody>
              <div className="d-flex justify-content-between align-items-center mb-3">
                <h5 className="mb-0">Environment Image & Zones</h5>
                <Button color="primary" size="sm" onClick={handleAddNewZone}>
                  Add New Zone
                </Button>
              </div>
              
              <ImageDisplay
                imagePath={environment.ImagePath}
                alt={`Environment: ${environment.Name}`}
                onImageLoad={handleImageLoad}
              >
                {/* Zone overlays using ZoneBox components */}
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
              
              {loading && (
                <div className="text-center mt-3">
                  <div className="spinner-border" role="status">
                    <span className="visually-hidden">Loading zones...</span>
                  </div>
                </div>
              )}
            </CardBody>
          </Card>
        </Col>
        
        <Col lg={3}>
          {/* Zone Properties Panel */}
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

export default EnvironmentEditor;