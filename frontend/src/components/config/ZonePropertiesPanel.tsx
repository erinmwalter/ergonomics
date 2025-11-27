import React, { useState, useEffect } from 'react';
import { Card, CardBody, FormGroup, Label, Input, Button, Row, Col } from 'reactstrap';
import type { Zone } from '../../models';

interface ZonePropertiesPanelProps {
  zone: Zone | null;
  onZoneUpdate: (zone: Zone) => void;
  onZoneDelete?: (zoneId: number) => void;
  imageDimensions?: { width: number; height: number } | null;
}

const ZonePropertiesPanel: React.FC<ZonePropertiesPanelProps> = ({
  zone,
  onZoneUpdate,
  onZoneDelete,
  imageDimensions
}) => {
  const [editedZone, setEditedZone] = useState<Zone | null>(null);
  const [hasChanges, setHasChanges] = useState(false);

  // Update local state when zone prop changes
  useEffect(() => {
    setEditedZone(zone);
    setHasChanges(false);
  }, [zone]);

  const handleFieldChange = (field: keyof Zone, value: string | number) => {
    if (!editedZone) return;

    const updatedZone = { ...editedZone, [field]: value };
    setEditedZone(updatedZone);
    setHasChanges(true);
  };

  const handleCoordinateChange = (coord: 'Xstart' | 'Ystart' | 'Xend' | 'Yend', value: string) => {
    const numValue = parseInt(value) || 0;
    handleFieldChange(coord, Math.max(0, numValue));
  };

  const handleSave = () => {
    if (editedZone && hasChanges) {
      // Ensure coordinates are valid
      const validatedZone = {
        ...editedZone,
        Xstart: Math.min(editedZone.Xstart, editedZone.Xend - 20),
        Ystart: Math.min(editedZone.Ystart, editedZone.Yend - 20),
        Xend: Math.max(editedZone.Xend, editedZone.Xstart + 20),
        Yend: Math.max(editedZone.Yend, editedZone.Ystart + 20)
      };
      
      onZoneUpdate(validatedZone);
      setHasChanges(false);
    }
  };

  const handleReset = () => {
    setEditedZone(zone);
    setHasChanges(false);
  };

  const handleDelete = () => {
    if (editedZone && onZoneDelete && window.confirm(`Are you sure you want to delete zone "${editedZone.ZoneName}"?`)) {
      onZoneDelete(editedZone.Id);
    }
  };

  if (!editedZone) {
    return (
      <Card>
        <CardBody>
          <h5>Zone Properties</h5>
          <p className="text-muted">Select a zone to edit its properties</p>
          
          {imageDimensions && (
            <div className="mt-3 pt-3 border-top">
              <p className="text-muted small">
                Image: {imageDimensions.width} x {imageDimensions.height}px
              </p>
            </div>
          )}
        </CardBody>
      </Card>
    );
  }

  const width = editedZone.Xend - editedZone.Xstart;
  const height = editedZone.Yend - editedZone.Ystart;

  return (
    <Card>
      <CardBody>
        <h5>Zone Properties</h5>
        
        {/* Zone Name */}
        <FormGroup>
          <Label for="zoneName">Zone Name</Label>
          <Input
            type="text"
            id="zoneName"
            value={editedZone.ZoneName}
            onChange={(e) => handleFieldChange('ZoneName', e.target.value)}
          />
        </FormGroup>

        {/* Zone Color */}
        <FormGroup>
          <Label for="zoneColor">Color</Label>
          <Row>
            <Col xs={8}>
              <Input
                type="text"
                id="zoneColor"
                value={editedZone.Color}
                onChange={(e) => handleFieldChange('Color', e.target.value)}
                placeholder="#FF0000"
              />
            </Col>
            <Col xs={4}>
              <Input
                type="color"
                value={editedZone.Color}
                onChange={(e) => handleFieldChange('Color', e.target.value)}
                style={{ height: '38px' }}
              />
            </Col>
          </Row>
        </FormGroup>

        {/* Position & Size */}
        <FormGroup>
          <Label>Position & Size</Label>
          <Row>
            <Col xs={6}>
              <Label for="xstart" className="form-label small">X Start</Label>
              <Input
                type="number"
                id="xstart"
                value={editedZone.Xstart}
                onChange={(e) => handleCoordinateChange('Xstart', e.target.value)}
                min="0"
              />
            </Col>
            <Col xs={6}>
              <Label for="ystart" className="form-label small">Y Start</Label>
              <Input
                type="number"
                id="ystart"
                value={editedZone.Ystart}
                onChange={(e) => handleCoordinateChange('Ystart', e.target.value)}
                min="0"
              />
            </Col>
          </Row>
          <Row className="mt-2">
            <Col xs={6}>
              <Label for="xend" className="form-label small">X End</Label>
              <Input
                type="number"
                id="xend"
                value={editedZone.Xend}
                onChange={(e) => handleCoordinateChange('Xend', e.target.value)}
                min={editedZone.Xstart + 20}
              />
            </Col>
            <Col xs={6}>
              <Label for="yend" className="form-label small">Y End</Label>
              <Input
                type="number"
                id="yend"
                value={editedZone.Yend}
                onChange={(e) => handleCoordinateChange('Yend', e.target.value)}
                min={editedZone.Ystart + 20}
              />
            </Col>
          </Row>
          <div className="mt-2">
            <small className="text-muted">
              Size: {width} x {height}px
            </small>
          </div>
        </FormGroup>

        {/* Action Buttons */}
        <div className="d-grid gap-2">
          {hasChanges && (
            <>
              <Button color="primary" onClick={handleSave}>
                Save Changes
              </Button>
              <Button color="secondary" onClick={handleReset}>
                Reset
              </Button>
            </>
          )}
          
          {onZoneDelete && (
            <Button color="danger" outline onClick={handleDelete}>
              Delete Zone
            </Button>
          )}
        </div>

        {/* Zone Info */}
        <div className="mt-3 pt-3 border-top">
          <small className="text-muted">
            Created by {editedZone.CreatedBy} on {editedZone.CreatedAt}
          </small>
        </div>

        {imageDimensions && (
          <div className="mt-2">
            <small className="text-muted">
              Image: {imageDimensions.width} x {imageDimensions.height}px
            </small>
          </div>
        )}
      </CardBody>
    </Card>
  );
};

export default ZonePropertiesPanel;