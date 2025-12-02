import React, { useState, useRef, useEffect } from 'react';

interface ImageDisplayProps {
  imagePath: string;
  alt: string;
  children?: React.ReactNode;
  onImageLoad?: (dimensions: { width: number; height: number }) => void;
}

const ImageDisplay: React.FC<ImageDisplayProps> = ({ 
  imagePath, 
  alt, 
  children,
  onImageLoad 
}) => {
  const [imageLoaded, setImageLoaded] = useState(false);
  const [imageError, setImageError] = useState(false);
  const imgRef = useRef<HTMLImageElement>(null);
  const containerRef = useRef<HTMLDivElement>(null);

  const handleImageLoad = () => {
    setImageLoaded(true);
    setImageError(false);
    
    if (imgRef.current && onImageLoad) {
      const { naturalWidth, naturalHeight } = imgRef.current;
      onImageLoad({ width: naturalWidth, height: naturalHeight });
    }
  };

  const handleImageError = () => {
    setImageError(true);
    setImageLoaded(false);
  };

  const getImageSrc = (path: string) => {
    if (path.startsWith('data:')) {
    return path;
  }

  if (path.startsWith('/uploads/')) {
    return path.replace('/uploads/', '/images/');
  }
  
  if (path.startsWith('uploads/')) {
    return `/images/${path.slice(8)}`;
  }
  
  if (path.startsWith('/images/') || !path.startsWith('/')) {
    return path.startsWith('/') ? path : `/${path}`;
  }
  
  const cleanPath = path.startsWith('/') ? path.slice(1) : path;
  return `/images/${cleanPath}`;
};

  return (
    <div 
      ref={containerRef}
      className="position-relative d-inline-block"
      style={{
        border: '1px solid #dee2e6',
        borderRadius: '0.375rem',
        overflow: 'hidden',
        maxWidth: '100%',
        backgroundColor: '#f8f9fa'
      }}
    >
      {imageError ? (
        <div 
          style={{ 
            width: '800px', 
            height: '600px',
            display: 'flex',
            alignItems: 'center',
            justifyContent: 'center',
            backgroundColor: '#f8f9fa',
            border: '2px dashed #dee2e6'
          }}
        >
          <div className="text-center text-muted">
            <p><strong>Image not found</strong></p>
          </div>
        </div>
      ) : (
        <>
          <img
            ref={imgRef}
            src={getImageSrc(imagePath)}
            alt={alt}
            onLoad={handleImageLoad}
            onError={handleImageError}
            style={{
              maxWidth: '800px',
              maxHeight: '600px',
              width: 'auto',
              height: 'auto',
              display: 'block'
            }}
          />
          
          {!imageLoaded && !imageError && (
            <div 
              className="position-absolute top-0 start-0 w-100 h-100 d-flex align-items-center justify-content-center"
              style={{ backgroundColor: 'rgba(248, 249, 250, 0.8)' }}
            >
              <div className="text-center">
                <div className="spinner-border" role="status">
                  <span className="visually-hidden">Loading image...</span>
                </div>
                <p className="mt-2 mb-0">Loading image...</p>
              </div>
            </div>
          )}
          
          {imageLoaded && children}
        </>
      )}
    </div>
  );
};

export default ImageDisplay;