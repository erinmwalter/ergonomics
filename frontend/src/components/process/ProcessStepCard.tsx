import React from 'react';
import { ListGroupItem, Button, Badge } from 'reactstrap';
import { ProcessStep } from '../../models';


interface ProcessStepCardProps {
  step: ProcessStep;
  stepNumber: number;
  onDelete: () => void;
  onMoveUp?: () => void;
  onMoveDown?: () => void;
  canEdit: boolean;
}

const ProcessStepCard: React.FC<ProcessStepCardProps> = ({
  step,
  stepNumber,
  onDelete,
  onMoveUp,
  onMoveDown,
  canEdit
}) => {
  return (
    <ListGroupItem className="d-flex justify-content-between align-items-center">
      <div className="d-flex align-items-center flex-grow-1">
        <Badge 
          color="primary" 
          pill 
          className="me-3"
          style={{ fontSize: '0.9em', minWidth: '30px' }}
        >
          {stepNumber}
        </Badge>
        
        <div className="flex-grow-1">
          <div className="d-flex align-items-center mb-1">
            <h6 className="mb-0 me-2">{step.StepName}</h6>
            <Badge 
              color="secondary" 
              style={{ 
                backgroundColor: step.Color || '#6c757d',
                borderColor: step.Color || '#6c757d'
              }}
            >
              {step.ZoneName || 'Unknown Zone'}
            </Badge>
          </div>
          {step.Description && (
            <small className="text-muted">{step.Description}</small>
          )}
        </div>
      </div>

      {canEdit && (
        <div className="d-flex align-items-center gap-1">
          {onMoveUp && (
            <Button
              color="outline-secondary"
              size="sm"
              onClick={onMoveUp}
              title="Move up"
            >
              ↑
            </Button>
          )}
          
          {onMoveDown && (
            <Button
              color="outline-secondary"
              size="sm"
              onClick={onMoveDown}
              title="Move down"
            >
              ↓
            </Button>
          )}
          
          <Button
            color="outline-danger"
            size="sm"
            onClick={onDelete}
            title="Delete step"
          >
            ×
          </Button>
        </div>
      )}
    </ListGroupItem>
  );
};

export default ProcessStepCard;