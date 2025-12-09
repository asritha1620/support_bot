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
  CircularProgress
} from '@mui/material';
import {
  Send,
  Person,
  SmartToy,
  ExpandMore,
  ExpandLess,
  Error,
  AttachFile,
  Add,
  ThumbUp,
  ThumbDown,
  Clear
} from '@mui/icons-material';
import ApiService from '../services/ApiService';

const ChatMessage = ({ message, onFeedback }) => {
  const [showSources, setShowSources] = useState(false);
  const [feedbackGiven, setFeedbackGiven] = useState(false);
  const [feedbackMessage, setFeedbackMessage] = useState('');

  const formatTime = (timestamp) => {
    return new Date(timestamp).toLocaleTimeString([], {
      hour: '2-digit',
      minute: '2-digit'
    });
  };

  const handleFeedback = (type) => {
    setFeedbackGiven(true);
    
    // Set appropriate feedback message
    if (type === 'positive') {
      setFeedbackMessage('Thanks for the feedback! 😊');
    } else {
      setFeedbackMessage('Thanks for your feedback! 📝');
    }
    
    onFeedback(type, message);
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

        <Box sx={{ maxWidth: '100%' }}>
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
                        label={source.metadata.source || 'Unknown source'}
                        size="small"
                        variant="outlined"
                        sx={{ mr: 0.5, mb: 0.5 }}
                      />
                    ))}
                  </Box>
                </Collapse>
              </Box>
            )}
          </Paper>

          {/* Feedback buttons for assistant messages */}
          {message.type === 'assistant' && !feedbackGiven && (
            <Box sx={{ display: 'flex', gap: 0.5, mt: 0.5, justifyContent: message.type === 'user' ? 'flex-end' : 'flex-start' }}>
              <IconButton
                size="small"
                onClick={() => handleFeedback('positive')}
                sx={{ p: 0.5 }}
                title="Good response"
              >
                <ThumbUp fontSize="small" color="action" />
              </IconButton>
              <IconButton
                size="small"
                onClick={() => handleFeedback('negative')}
                sx={{ p: 0.5 }}
                title="Needs improvement"
              >
                <ThumbDown fontSize="small" color="action" />
              </IconButton>
            </Box>
          )}

          {/* Feedback confirmation */}
          {message.type === 'assistant' && feedbackGiven && (
            <Typography variant="caption" sx={{ mt: 0.5, opacity: 0.7, display: 'block', textAlign: message.type === 'user' ? 'right' : 'left' }}>
              {feedbackMessage}
            </Typography>
          )}
        </Box>
      </Box>
    </ListItem>
  );
};

const ChatInterface = ({
  chatHistory,
  onSendMessage,
  disabled,
  onFileUpload,
  hasDefaultData,
  fileInfo,
  loading = false,
  onClearChat
}) => {
  const [message, setMessage] = useState('');
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
      const response = await fetch('http://localhost:8000/add-resolution', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify(resolutionData)
      });

      if (response.ok) {
        alert('Resolution added successfully to the shared knowledge base! All users can now access this resolution.');
        handleCloseResolutionDialog();
      } else {
        const error = await response.json();
        alert(`Failed to add resolution: ${error.detail || 'Please try again.'}`);
      }
    } catch (error) {
      console.error('Error adding resolution:', error);
      alert('Error adding resolution. Please check the console for details.');
    }
  };

  const handleFeedback = (type, message) => {
    // Send feedback directly without dialog
    ApiService.submitFeedback({ 
      type, 
      messageId: message.id,
      suggestions: type === 'negative' ? 'User indicated response needs improvement' : ''
    });
  };

  const handleFeedbackSubmit = async () => {
    await ApiService.submitFeedback({
      type: feedbackData.type,
      messageId: feedbackData.message.id,
      suggestions: feedbackData.suggestions
    });
    setFeedbackDialogOpen(false);
    setFeedbackData({ type: '', message: null, suggestions: '' });
  };

  const exampleQuestions = [
    "What are the most common shipping errors this month?",
    "Can you show me tickets related to payment failures?"
  ];

  return (
    <Box sx={{ height: '100vh', width: '100%', display: 'flex', flexDirection: 'column' }}>
      {/* Header */}
      <Box sx={{ p: 1, borderBottom: 1, borderColor: 'divider', bgcolor: 'background.paper', flexShrink: 0 }}>
        <Box display="flex" justifyContent="space-between" alignItems="center">
          <Box>
            <Typography variant="body1">
               Chat with your Bot!
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
                Welcome to Support Ticket Assistant!
              </Typography>
              <Typography variant="body2" color="text.secondary" gutterBottom sx={{ mb: 2 }}>
                Upload Excel files to add to the shared knowledge base, or try asking your questions like these:
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
              <ChatMessage key={msg.id || index} message={msg} onFeedback={handleFeedback} />
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
            startIcon={<Clear />}
            onClick={onClearChat}
            disabled={chatHistory.length === 0}
            sx={{ mr: 1 }}
          >
            Clear Chat
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

    </Box>
  );
};

export default ChatInterface;
