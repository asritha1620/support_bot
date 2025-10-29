import React, { useState, useRef, useEffect } from 'react';
import {
  Paper,
  Typography,
  Box,
  TextField,
  Button,
  List,
  ListItem,
  Avatar,
  IconButton,
  Chip,
  Collapse,
  Alert,
  Dialog,
  DialogTitle,
  DialogContent,
  DialogActions,
  FormControl,
  InputLabel,
  Select,
  MenuItem,
  CircularProgress
} from '@mui/material';
import {
  Send,
  Person,
  SmartToy,
  ThumbUp,
  ThumbDown,
  ExpandMore,
  ExpandLess,
  Error,
  AttachFile,
  Add
} from '@mui/icons-material';

const ChatMessage = ({ message, onFeedback }) => {
  const [showSources, setShowSources] = useState(false);
  const [feedbackGiven, setFeedbackGiven] = useState(null);

  const handleFeedback = (feedback) => {
    onFeedback(message.id, feedback);
    setFeedbackGiven(feedback);
  };

  const formatTime = (timestamp) => {
    return new Date(timestamp).toLocaleTimeString([], {
      hour: '2-digit',
      minute: '2-digit'
    });
  };

  return (
    <ListItem
      sx={{
        display: 'flex',
        flexDirection: 'column',
        alignItems: message.type === 'user' ? 'flex-end' : 'flex-start',
        p: 1
      }}
    >
      <Box
        sx={{
          display: 'flex',
          alignItems: 'flex-start',
          gap: 1,
          maxWidth: '90%',
          flexDirection: message.type === 'user' ? 'row-reverse' : 'row'
        }}
      >
        <Avatar
          sx={{
            bgcolor: message.type === 'user' ? 'primary.main' :
                    message.type === 'error' ? 'error.main' : 'secondary.main',
            width: 24,
            height: 24
          }}
        >
          {message.type === 'user' ? <Person /> :
           message.type === 'error' ? <Error /> : <SmartToy />}
        </Avatar>

        <Paper
          elevation={1}
          sx={{
            p: 0.5,
            bgcolor: message.type === 'user' ? 'primary.light' :
                    message.type === 'error' ? 'error.light' : 'grey.100',
            color: message.type === 'user' ? 'primary.contrastText' : 'text.primary'
          }}
        >
          <Typography variant="body2" sx={{ whiteSpace: 'pre-wrap' }}>
            {message.content}
          </Typography>

          <Typography variant="caption" sx={{ display: 'block', mt: 1, opacity: 0.7 }}>
            {formatTime(message.timestamp)}
          </Typography>

          {message.type === 'assistant' && message.sources && message.sources.length > 0 && (
            <Box mt={1}>
              <Button
                size="small"
                onClick={() => setShowSources(!showSources)}
                endIcon={showSources ? <ExpandLess /> : <ExpandMore />}
                sx={{ p: 0, minWidth: 'auto' }}
              >
                <Typography variant="caption">
                  Sources ({message.sources.length})
                </Typography>
              </Button>

              <Collapse in={showSources}>
                <Box mt={1}>
                  {message.sources.map((source, index) => (
                    <Chip
                      key={index}
                      label={`Row ${source.metadata.row_index || 'N/A'}`}
                      size="small"
                      variant="outlined"
                      sx={{ mr: 0.5, mb: 0.5 }}
                    />
                  ))}
                </Box>
              </Collapse>
            </Box>
          )}

          {message.type === 'assistant' && (
            <Box mt={1} display="flex" gap={1}>
              <IconButton
                size="small"
                onClick={() => handleFeedback('positive')}
                color={feedbackGiven === 'positive' ? 'success' : 'default'}
                disabled={feedbackGiven !== null}
              >
                <ThumbUp fontSize="small" />
              </IconButton>
              <IconButton
                size="small"
                onClick={() => handleFeedback('negative')}
                color={feedbackGiven === 'negative' ? 'error' : 'default'}
                disabled={feedbackGiven !== null}
              >
                <ThumbDown fontSize="small" />
              </IconButton>
              {feedbackGiven && (
                <Typography variant="caption" sx={{ alignSelf: 'center', ml: 1 }}>
                  Thank you for your feedback!
                </Typography>
              )}
            </Box>
          )}
        </Paper>
      </Box>
    </ListItem>
  );
};

const ChatInterface = ({
  chatHistory,
  onSendMessage,
  onFeedback,
  disabled,
  onFileUpload,
  hasDefaultData,
  fileInfo,
  loading = false
}) => {
  const [message, setMessage] = useState('');
  const [addResolutionOpen, setAddResolutionOpen] = useState(false);
  const [resolutionData, setResolutionData] = useState({
    error_code: '',
    module: '',
    description: '',
    resolution: '',
    ticket_level: 'L2'
  });
  const messagesEndRef = useRef(null);

  useEffect(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  }, [chatHistory]);

  const handleSend = () => {
    if (message.trim() && !disabled) {
      onSendMessage(message.trim());
      setMessage('');
    }
  };

  const handleKeyPress = (e) => {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault();
      handleSend();
    }
  };

  const handleFileSelect = (event) => {
    const file = event.target.files[0];
    if (file) {
      onFileUpload(file);
    }
    event.target.value = '';
  };

  const handleAddResolution = () => {
    setAddResolutionOpen(true);
  };

  const handleCloseResolutionDialog = () => {
    setAddResolutionOpen(false);
    setResolutionData({
      error_code: '',
      module: '',
      description: '',
      resolution: '',
      ticket_level: 'L2'
    });
  };

  const handleResolutionDataChange = (field, value) => {
    setResolutionData(prev => ({
      ...prev,
      [field]: value
    }));
  };

  const handleSubmitResolution = async () => {
    // Validate required fields
    if (!resolutionData.description.trim() || !resolutionData.resolution.trim()) {
      alert('Please fill in the description and resolution fields.');
      return;
    }

    try {
      const response = await fetch('http://localhost:8000/add-resolution?session_id=default_support_tickets', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify(resolutionData)
      });

      if (response.ok) {
        alert('Resolution added successfully to the shared knowledge base! All users can now access this resolution.');
        handleCloseResolutionDialog();
        // Note: Chat history is preserved, no page reload needed
      } else {
        const error = await response.json();
        alert(`Failed to add resolution: ${error.detail || 'Please try again.'}`);
      }
    } catch (error) {
      console.error('Error adding resolution:', error);
      alert('Error adding resolution. Please check the console for details.');
    }
  };

  const exampleQuestions = [
    "What is the summary of these support tickets?",
    "What are the most common ticket categories?",
    "what are the common error codes in shipment?"
  ];

  return (
    <Box sx={{ height: '100vh', width: '100%', display: 'flex', flexDirection: 'column' }}>
      {/* Header */}
      <Box sx={{ p: 1, borderBottom: 1, borderColor: 'divider', bgcolor: 'background.paper', flexShrink: 0 }}>
        <Box display="flex" justifyContent="space-between" alignItems="center">
          <Box>
            <Typography variant="body1">
               Chat with your tickets
            </Typography>
            {fileInfo && (
              <Typography variant="caption" color="text.secondary">
                Shared: {fileInfo.filename} ({fileInfo.rows} tickets)
              </Typography>
            )}
            {!fileInfo && hasDefaultData && (
              <Typography variant="caption" color="text.secondary">
                Using shared support ticket data
              </Typography>
            )}
          </Box>
          <Button
            variant="outlined"
            size="small"
            startIcon={<Add />}
            onClick={handleAddResolution}
            disabled={!hasDefaultData && !fileInfo}
          >
            Add Resolution
          </Button>
        </Box>
      </Box>

      {/* Recommended Questions */}
      {chatHistory.length === 0 && (
        <Box sx={{ p: 2, bgcolor: 'background.default', flexShrink: 0 }}>
          {disabled && !hasDefaultData ? (
            <Alert severity="info">
              Please upload ticket data to add to the shared knowledge base!
            </Alert>
          ) : (
            <>
              <Typography variant="h6" color="text.secondary" gutterBottom>
                Welcome to Support Ticket Assistant! 🤖
              </Typography>
              <Typography variant="body2" color="text.secondary" gutterBottom sx={{ mb: 2 }}>
                Upload Excel files to add to the shared knowledge base, or try asking one of these questions:
              </Typography>
              <Box>
                {exampleQuestions.map((question, index) => (
                  <Chip
                    key={index}
                    label={question}
                    variant="outlined"
                    size="medium"
                    clickable
                    onClick={() => !disabled && onSendMessage(question)}
                    sx={{ m: 0.5, fontSize: '0.875rem' }}
                  />
                ))}
              </Box>
            </>
          )}
        </Box>
      )}

      {/* Chat Messages */}
      <Box
        sx={{
          flex: 1,
          overflowY: 'auto',
          bgcolor: 'background.default',
          paddingBottom: '100px', // space for input box
          scrollbarWidth: 'none',
          '&::-webkit-scrollbar': {
            display: 'none'
          }
        }}
      >
        {chatHistory.length > 0 && (
          <List sx={{ p: 0 }}>
            {chatHistory.map((msg, index) => (
              <ChatMessage key={msg.id || index} message={msg} onFeedback={onFeedback} />
            ))}
            
            {/* Loading indicator */}
            {loading && (
              <ListItem
                sx={{
                  display: 'flex',
                  alignItems: 'flex-start',
                  gap: 1,
                  p: 1
                }}
              >
                <Avatar
                  sx={{
                    bgcolor: 'secondary.main',
                    width: 24,
                    height: 24
                  }}
                >
                  <SmartToy />
                </Avatar>
                <Paper
                  elevation={1}
                  sx={{
                    p: 1,
                    bgcolor: 'grey.100',
                    display: 'flex',
                    alignItems: 'center',
                    gap: 1
                  }}
                >
                  <CircularProgress size={16} />
                  <Typography variant="body2" color="text.secondary">
                    Loading...
                  </Typography>
                </Paper>
              </ListItem>
            )}
            
            <div ref={messagesEndRef} />
          </List>
        )}
      </Box>

      {/* Input Box - Fixed at Bottom */}
      <Box
        sx={{
          position: 'fixed',
          bottom: 0,
          left: 0,
          width: '100%',
          bgcolor: 'background.paper',
          borderTop: '1px solid #ddd',
          p: 1,
          boxShadow: '0 -2px 8px rgba(0,0,0,0.1)'
        }}
      >
        <Box display="flex" gap={1} alignItems="flex-end">
          <Button
            variant="outlined"
            size="small"
            startIcon={<Add />}
            onClick={handleAddResolution}
            disabled={!hasDefaultData && !fileInfo}
            sx={{ mr: 1 }}
          >
            Add Resolution
          </Button>
          
          <TextField
            fullWidth
            multiline
            maxRows={3}
            placeholder={loading ? "Waiting for response..." : (disabled && !hasDefaultData ? "Upload ticket data to add to shared knowledge base..." : "Ask a question about the shared tickets...")}
            value={message}
            onChange={(e) => setMessage(e.target.value)}
            onKeyPress={handleKeyPress}
            disabled={(disabled && !hasDefaultData) || loading}
            size="small"
          />

          <input
            accept=".xlsx,.xls"
            style={{ display: 'none' }}
            id="file-upload-input"
            type="file"
            onChange={handleFileSelect}
          />
          <label htmlFor="file-upload-input">
            <IconButton component="span" size="small" title="Upload new ticket data">
              <AttachFile />
            </IconButton>
          </label>

          <Button
            variant="contained"
            endIcon={<Send />}
            onClick={handleSend}
            disabled={(disabled && !hasDefaultData) || !message.trim() || loading}
            sx={{ minWidth: 'auto', px: 2 }}
          >
            Send
          </Button>
        </Box>
      </Box>

      {/* Add Resolution Dialog */}
      <Dialog open={addResolutionOpen} onClose={handleCloseResolutionDialog} maxWidth="md" fullWidth>
        <DialogTitle>Add New Resolution</DialogTitle>
        <DialogContent>
          <Box sx={{ pt: 2, display: 'flex', flexDirection: 'column', gap: 2 }}>
            <TextField
              label="Error Code (optional)"
              value={resolutionData.error_code}
              onChange={(e) => handleResolutionDataChange('error_code', e.target.value)}
              placeholder="e.g., SHIP404, SHP-ERR-3344"
              fullWidth
            />
            
            <FormControl fullWidth>
              <InputLabel>Module</InputLabel>
              <Select
                value={resolutionData.module}
                onChange={(e) => handleResolutionDataChange('module', e.target.value)}
                label="Module"
              >
                <MenuItem value="shipping">Shipping</MenuItem>
                <MenuItem value="logistics">Logistics</MenuItem>
                <MenuItem value="payment">Payment</MenuItem>
                <MenuItem value="order">Order</MenuItem>
                <MenuItem value="inventory">Inventory</MenuItem>
                <MenuItem value="customer">Customer</MenuItem>
                <MenuItem value="api">API</MenuItem>
                <MenuItem value="database">Database</MenuItem>
                <MenuItem value="other">Other</MenuItem>
              </Select>
            </FormControl>

            <FormControl fullWidth>
              <InputLabel>Ticket Level</InputLabel>
              <Select
                value={resolutionData.ticket_level}
                onChange={(e) => handleResolutionDataChange('ticket_level', e.target.value)}
                label="Ticket Level"
              >
                <MenuItem value="L1">L1</MenuItem>
                <MenuItem value="L2">L2</MenuItem>
                <MenuItem value="L3">L3</MenuItem>
              </Select>
            </FormControl>

            <TextField
              label="Issue Description"
              value={resolutionData.description}
              onChange={(e) => handleResolutionDataChange('description', e.target.value)}
              multiline
              rows={3}
              placeholder="Describe the issue or error that occurred"
              fullWidth
              required
            />

            <TextField
              label="Resolution Steps"
              value={resolutionData.resolution}
              onChange={(e) => handleResolutionDataChange('resolution', e.target.value)}
              multiline
              rows={4}
              placeholder="Describe the steps taken to resolve this issue"
              fullWidth
              required
            />
          </Box>
        </DialogContent>
        <DialogActions>
          <Button onClick={handleCloseResolutionDialog}>Cancel</Button>
          <Button onClick={handleSubmitResolution} variant="contained">
            Add Resolution
          </Button>
        </DialogActions>
      </Dialog>
    </Box>
  );
};

export default ChatInterface;