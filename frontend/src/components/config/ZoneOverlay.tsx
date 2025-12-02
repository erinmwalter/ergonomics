import React, { useState } from 'react';
import type { Zone } from '../../models';

interface ZoneOverlayProps {
  zones: Zone[];
  selectedZoneId: number | null;
  onZoneSelect: (zone: Zone | null) => void;
  onZoneUpdate: (zone: Zone) => void;
  onAddZone: (x: number, y: number) => void;
  isAddingZone: boolean;
}

const ZoneOverlay: React.FC<ZoneOverlayProps> = ({
  zones,
  selectedZoneId,
  onZoneSelect,
  onZoneUpdate,
  onAddZone,
  isAddingZone
}) => {
  const [dragState, setDragState] = useState<{
    isDragging: boolean;
    zoneId: number | null;
    startX: number;
    startY: number;
    initialLeft: number;
    initialTop: number;
  } | null>(null);

  return (
    <div className="position-absolute top-0 start-0 w-100 h-100">
      {zones.map(zone => (
        <div key={zone.Id}>
          Zone: {zone.ZoneName}
        </div>
      ))}
    </div>
  );
};

export default ZoneOverlay;