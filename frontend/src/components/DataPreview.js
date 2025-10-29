import React from 'react';
import {
  Paper,
  Typography,
  Box,
  Chip,
  List,
  ListItem,
  ListItemText,
  Divider
} from '@mui/material';
import {
  TableChart,
  ViewColumn,
  Numbers
} from '@mui/icons-material';

const DataPreview = ({ fileInfo }) => {
  if (!fileInfo) return null;

  return (
    <Paper elevation={2} sx={{ p: 0.5 }}>
      <Typography variant="body1" gutterBottom>
        📊 Data Preview
      </Typography>

      <Box mb={2}>
        <Typography variant="subtitle2" gutterBottom>
          {fileInfo.filename}
        </Typography>
        
        <Box display="flex" gap={1} flexWrap="wrap" mb={2}>
          <Chip
            icon={<TableChart />}
            label={`${fileInfo.rows} rows`}
            size="small"
            color="primary"
            variant="outlined"
          />
          <Chip
            icon={<ViewColumn />}
            label={`${fileInfo.columns} columns`}
            size="small"
            color="secondary"
            variant="outlined"
          />
        </Box>
      </Box>

      <Divider sx={{ my: 2 }} />

      <Typography variant="subtitle2" gutterBottom>
        <Numbers sx={{ mr: 1, verticalAlign: 'middle' }} />
        Columns
      </Typography>
      
      <Box
        sx={{
          maxHeight: 100,
          overflow: 'auto',
          border: '1px solid',
          borderColor: 'divider',
          borderRadius: 1,
          scrollbarWidth: 'none',
          '&::-webkit-scrollbar': {
            display: 'none'
          }
        }}
      >
        <List dense>
          {fileInfo.column_names.map((column, index) => (
            <ListItem key={index} divider={index < fileInfo.column_names.length - 1}>
              <ListItemText
                primary={column}
                primaryTypographyProps={{
                  variant: 'body2',
                  fontFamily: 'monospace'
                }}
              />
            </ListItem>
          ))}
        </List>
      </Box>

      <Box mt={2}>
        <Typography variant="caption" color="text.secondary">
          Ready to answer questions about your data!
        </Typography>
      </Box>
    </Paper>
  );
};

export default DataPreview;