import React, { useState, useRef } from 'react';
import type { Zone } from '../../models';

interface ZoneBoxProps {
  zone: Zone;
  isSelected: boolean;
  onSelect: (zone: Zone) => void;
  onUpdate: (zone: Zone) => void;
}

type ResizeDirection = 'se' | 'ne' | 'sw' | 'nw' | 'n' | 's' | 'e' | 'w' | null;

const ZoneBox: React.FC<ZoneBoxProps> = ({
  zone,
  isSelected,
  onSelect,
  onUpdate
}) => {
  const [isDragging, setIsDragging] = useState(false);
  const [isResizing, setIsResizing] = useState<ResizeDirection>(null);
  const [dragStart, setDragStart] = useState({ x: 0, y: 0, zoneStart: { x: 0, y: 0, width: 0, height: 0 } });
  const zoneRef = useRef<HTMLDivElement>(null);

  const width = zone.Xend - zone.Xstart;
  const height = zone.Yend - zone.Ystart;

  const handleZoneMouseDown = (e: React.MouseEvent) => {
    e.preventDefault();
    e.stopPropagation();
    
    // Select the zone
    onSelect(zone);
    
    // Start dragging
    setIsDragging(true);
    setDragStart({
      x: e.clientX,
      y: e.clientY,
      zoneStart: {
        x: zone.Xstart,
        y: zone.Ystart,
        width: width,
        height: height
      }
    });
  };

  const handleResizeMouseDown = (e: React.MouseEvent, direction: ResizeDirection) => {
    e.preventDefault();
    e.stopPropagation();
    
    setIsResizing(direction);
    setDragStart({
      x: e.clientX,
      y: e.clientY,
      zoneStart: {
        x: zone.Xstart,
        y: zone.Ystart,
        width: width,
        height: height
      }
    });
  };

  const handleMouseMove = (e: MouseEvent) => {
    const deltaX = e.clientX - dragStart.x;
    const deltaY = e.clientY - dragStart.y;

    if (isDragging) {
      // Handle zone dragging
      const newX = dragStart.zoneStart.x + deltaX;
      const newY = dragStart.zoneStart.y + deltaY;

      const updatedZone: Zone = {
        ...zone,
        Xstart: Math.max(0, newX),
        Ystart: Math.max(0, newY),
        Xend: Math.max(0, newX + dragStart.zoneStart.width),
        Yend: Math.max(0, newY + dragStart.zoneStart.height)
      };

      onUpdate(updatedZone);
    } else if (isResizing) {
      // Handle zone resizing
      let newXstart = dragStart.zoneStart.x;
      let newYstart = dragStart.zoneStart.y;
      let newXend = dragStart.zoneStart.x + dragStart.zoneStart.width;
      let newYend = dragStart.zoneStart.y + dragStart.zoneStart.height;

      switch (isResizing) {
        case 'se': // Southeast - bottom-right
          newXend = dragStart.zoneStart.x + dragStart.zoneStart.width + deltaX;
          newYend = dragStart.zoneStart.y + dragStart.zoneStart.height + deltaY;
          break;
        case 'sw': // Southwest - bottom-left
          newXstart = dragStart.zoneStart.x + deltaX;
          newYend = dragStart.zoneStart.y + dragStart.zoneStart.height + deltaY;
          break;
        case 'ne': // Northeast - top-right
          newXend = dragStart.zoneStart.x + dragStart.zoneStart.width + deltaX;
          newYstart = dragStart.zoneStart.y + deltaY;
          break;
        case 'nw': // Northwest - top-left
          newXstart = dragStart.zoneStart.x + deltaX;
          newYstart = dragStart.zoneStart.y + deltaY;
          break;
      }

      // Ensure minimum size and valid coordinates
      const minSize = 20;
      if (newXend - newXstart >= minSize && newYend - newYstart >= minSize) {
        const updatedZone: Zone = {
          ...zone,
          Xstart: Math.max(0, newXstart),
          Ystart: Math.max(0, newYstart),
          Xend: Math.max(newXstart + minSize, newXend),
          Yend: Math.max(newYstart + minSize, newYend)
        };

        onUpdate(updatedZone);
      }
    }
  };

  const handleMouseUp = () => {
    setIsDragging(false);
    setIsResizing(null);
  };

  // Add global mouse event listeners when dragging or resizing
  React.useEffect(() => {
    if (isDragging || isResizing) {
      document.addEventListener('mousemove', handleMouseMove);
      document.addEventListener('mouseup', handleMouseUp);
      return () => {
        document.removeEventListener('mousemove', handleMouseMove);
        document.removeEventListener('mouseup', handleMouseUp);
      };
    }
  }, [isDragging, isResizing, dragStart]);

  const zoneStyle: React.CSSProperties = {
    position: 'absolute',
    left: `${zone.Xstart}px`,
    top: `${zone.Ystart}px`,
    width: `${width}px`,
    height: `${height}px`,
    border: isSelected ? `3px solid ${zone.Color}` : `2px solid ${zone.Color}`,
    backgroundColor: `${zone.Color}20`,
    cursor: isDragging ? 'grabbing' : 'grab',
    userSelect: 'none',
    boxSizing: 'border-box'
  };

  const labelStyle: React.CSSProperties = {
    fontSize: '12px',
    fontWeight: 'bold',
    color: zone.Color,
    padding: '2px 6px',
    backgroundColor: 'rgba(255, 255, 255, 0.9)',
    borderRadius: '3px',
    display: 'inline-block',
    maxWidth: '100%',
    overflow: 'hidden',
    textOverflow: 'ellipsis',
    whiteSpace: 'nowrap'
  };

  const handleStyle = {
    position: 'absolute' as const,
    width: '8px',
    height: '8px',
    backgroundColor: zone.Color,
    border: '1px solid #fff',
    borderRadius: '50%'
  };

  return (
    <div
      ref={zoneRef}
      style={zoneStyle}
      onMouseDown={handleZoneMouseDown}
    >
      <div style={labelStyle}>
        {zone.ZoneName}
      </div>
      
      {/* Resize handles - only show when selected */}
      {isSelected && (
        <>
          {/* Corner resize handles */}
          <div
            style={{
              ...handleStyle,
              top: '-4px',
              left: '-4px',
              cursor: 'nw-resize'
            }}
            onMouseDown={(e) => handleResizeMouseDown(e, 'nw')}
          />
          <div
            style={{
              ...handleStyle,
              top: '-4px',
              right: '-4px',
              cursor: 'ne-resize'
            }}
            onMouseDown={(e) => handleResizeMouseDown(e, 'ne')}
          />
          <div
            style={{
              ...handleStyle,
              bottom: '-4px',
              left: '-4px',
              cursor: 'sw-resize'
            }}
            onMouseDown={(e) => handleResizeMouseDown(e, 'sw')}
          />
          <div
            style={{
              ...handleStyle,
              bottom: '-4px',
              right: '-4px',
              cursor: 'se-resize'
            }}
            onMouseDown={(e) => handleResizeMouseDown(e, 'se')}
          />
        </>
      )}
    </div>
  );
};

export default ZoneBox;