import React, { useState } from 'react';
import {
  Paper,
  Typography,
  Button,
  Box,
  CircularProgress,
  Alert
} from '@mui/material';
import {
  CloudUpload,
  Refresh
} from '@mui/icons-material';
import { useDropzone } from 'react-dropzone';

const FileUpload = ({ onFileUpload, isLoading, onReset }) => {
  const [dragError, setDragError] = useState('');

  const onDrop = (acceptedFiles, rejectedFiles) => {
    setDragError('');
    
    if (rejectedFiles.length > 0) {
      setDragError('Please upload only Excel (.xlsx, .xls) or PDF (.pdf) files');
      return;
    }

    if (acceptedFiles.length > 0) {
      onFileUpload(acceptedFiles[0]);
    }
  };

  const { getRootProps, getInputProps, isDragActive } = useDropzone({
    onDrop,
    accept: {
      'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet': ['.xlsx'],
      'application/vnd.ms-excel': ['.xls'],
      'application/pdf': ['.pdf']
    },
    multiple: false,
    disabled: isLoading
  });

  const handleReset = () => {
    setDragError('');
    onReset();
  };

  return (
    <Paper elevation={2} sx={{ p: 0.5 }}>
      <Typography variant="body1" gutterBottom>
        📁 Upload Ticket Data or Documentation
      </Typography>

      {/* File Upload */}
      <Box mb={3}>
        <Box
          {...getRootProps()}
          sx={{
            border: '2px dashed',
            borderColor: isDragActive ? 'primary.main' : 'grey.300',
            borderRadius: 1,
            p: 0.5,
            textAlign: 'center',
            cursor: isLoading ? 'not-allowed' : 'pointer',
            bgcolor: isDragActive ? 'action.hover' : 'background.paper',
            transition: 'all 0.2s ease',
            '&:hover': {
              borderColor: 'primary.main',
              bgcolor: 'action.hover'
            }
          }}
        >
          <input {...getInputProps()} />
          {isLoading ? (
            <Box>
              <CircularProgress size={24} sx={{ mb: 1 }} />
              <Typography variant="body2">Processing...</Typography>
            </Box>
          ) : (
            <Box>
              <CloudUpload sx={{ fontSize: 48, color: 'primary.main', mb: 1 }} />
              <Typography variant="body2" gutterBottom>
                {isDragActive
                  ? 'Drop the file here...'
                  : 'Drag & drop ticket data or documentation here, or click to select'
                }
              </Typography>
              <Typography variant="caption" color="text.secondary">
                Supports .xlsx, .xls, and .pdf files
              </Typography>
            </Box>
          )}
        </Box>

        {dragError && (
          <Alert severity="error" sx={{ mt: 2 }}>
            {dragError}
          </Alert>
        )}
      </Box>

      {/* Reset Button */}
      <Button
        startIcon={<Refresh />}
        onClick={handleReset}
        variant="outlined"
        color="secondary"
        size="small"
        fullWidth
      >
        Reset
      </Button>
    </Paper>
  );
};

export default FileUpload;
