'use client';

import { useCallback, useState, DragEvent, ChangeEvent, useRef } from 'react';
import { Upload, X, Image as ImageIcon, FileIcon } from 'lucide-react';
import { cn } from '@/utils/cn';
import { Button } from '@/components/ui/Button';

interface DropZoneProps {
  onFileSelect: (file: File | null) => void;
  acceptedTypes?: string[];
  maxSizeMB?: number;
  preview?: string | null;
  disabled?: boolean;
}

export function DropZone({ 
  onFileSelect, 
  acceptedTypes = ['image/jpeg', 'image/png', 'image/webp'],
  maxSizeMB = 10,
  preview,
  disabled = false 
}: DropZoneProps) {
  const [isDragActive, setIsDragActive] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const fileInputRef = useRef<HTMLInputElement>(null);

  const validateFile = useCallback((file: File): boolean => {
    if (!acceptedTypes.includes(file.type)) {
      setError(`Unsupported file type. Allowed: ${acceptedTypes.join(', ')}`);
      return false;
    }
    if (file.size > maxSizeMB * 1024 * 1024) {
      setError(`File size exceeds ${maxSizeMB}MB limit`);
      return false;
    }
    setError(null);
    return true;
  }, [acceptedTypes, maxSizeMB]);

  const handleFileSelect = useCallback((file: File | null) => {
    if (file && !validateFile(file)) {
      onFileSelect(null);
      return;
    }
    onFileSelect(file);
  }, [validateFile, onFileSelect]);

  const handleDrag = useCallback((e: DragEvent<HTMLDivElement>) => {
    e.preventDefault();
    e.stopPropagation();
    if (e.type === 'dragenter' || e.type === 'dragover') {
      setIsDragActive(true);
    } else if (e.type === 'dragleave') {
      setIsDragActive(false);
    }
  }, []);

  const handleDrop = useCallback((e: DragEvent<HTMLDivElement>) => {
    e.preventDefault();
    e.stopPropagation();
    setIsDragActive(false);
    
    if (e.dataTransfer.files.length > 0) {
      handleFileSelect(e.dataTransfer.files[0]);
    }
  }, [handleFileSelect]);

  const handleClick = useCallback(() => {
    fileInputRef.current?.click();
  }, []);

  const handleFileInputChange = useCallback((e: ChangeEvent<HTMLInputElement>) => {
    if (e.target.files?.length) {
      handleFileSelect(e.target.files[0]);
    }
  }, [handleFileSelect]);

  const removeFile = useCallback(() => {
    handleFileSelect(null);
  }, [handleFileSelect]);

  if (preview) {
    return (
      <div className="relative">
        <div className="relative aspect-video rounded-xl overflow-hidden border border-card-border bg-muted">
          <img 
            src={preview} 
            alt="Preview" 
            className="w-full h-full object-cover"
          />
          <button
            onClick={removeFile}
            className="absolute top-2 right-2 flex h-8 w-8 items-center justify-center rounded-full bg-black/60 text-white hover:bg-danger transition-colors"
            aria-label="Remove image"
          >
            <X className="h-4 w-4" />
          </button>
        </div>
        <div className="mt-3 flex items-center justify-between">
          <Button variant="outline" size="sm" onClick={handleClick} disabled={disabled}>
            <Upload className="h-4 w-4 mr-2" />
            Change
          </Button>
          {error && <p className="text-sm text-danger">{error}</p>}
        </div>
        <input
          ref={fileInputRef}
          type="file"
          accept={acceptedTypes.join(',')}
          onChange={handleFileInputChange}
          className="hidden"
          disabled={disabled}
        />
      </div>
    );
  }

  return (
    <div
      onDragEnter={handleDrag}
      onDragLeave={handleDrag}
      onDragOver={handleDrag}
      onDrop={handleDrop}
      onClick={handleClick}
      className={cn(
        'relative rounded-2xl border-2 border-dashed p-8 text-center transition-all duration-300 cursor-pointer',
        'bg-background-elevated',
        isDragActive 
          ? 'border-primary bg-primary/5' 
          : 'border-border hover:border-primary/50',
        disabled && 'opacity-50 cursor-not-allowed'
      )}
      role="button"
      tabIndex={0}
      aria-label="Drop zone for image upload"
    >
      <input
        ref={fileInputRef}
        type="file"
        accept={acceptedTypes.join(',')}
        onChange={handleFileInputChange}
        className="hidden"
        disabled={disabled}
      />
      <div className="space-y-4">
        <div className={cn('mx-auto flex h-16 w-16 items-center justify-center rounded-full', isDragActive ? 'bg-primary/10' : 'bg-muted')}>
          <Upload className={cn('h-8 w-8', isDragActive ? 'text-primary' : 'text-muted-foreground')} />
        </div>
        <div>
          <h3 className="text-lg font-semibold">Drop image here</h3>
          <p className="text-sm text-muted-foreground mt-1">or click to browse</p>
          <p className="text-xs text-muted-foreground mt-2">
            JPEG, PNG, WebP up to {maxSizeMB}MB
          </p>
        </div>
        {error && <p className="text-sm text-danger" role="alert">{error}</p>}
      </div>
    </div>
  );
}