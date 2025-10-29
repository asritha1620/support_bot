import React, { useState, useEffect } from 'react';
import {
  ThemeProvider,
  createTheme,
  CssBaseline,
  AppBar,
  Toolbar,
  Typography,
  Box,
  Alert,
  Snackbar
} from '@mui/material';
import { v4 as uuidv4 } from 'uuid';
import ChatInterface from './components/ChatInterface';
import ApiService from './services/ApiService';

const theme = createTheme({
  palette: {
    mode: 'light',
    primary: {
      main: '#1976d2',
    },
    secondary: {
      main: '#dc004e',
    },
    background: {
      default: '#f5f5f5',
    },
  },
  typography: {
    h4: {
      fontWeight: 600,
    },
  },
});

function App() {
  const [sessionId] = useState(() => uuidv4());
  const [fileInfo, setFileInfo] = useState(null);
  const [isLoading, setIsLoading] = useState(false);
  const [chatLoading, setChatLoading] = useState(false);
  const [chatHistory, setChatHistory] = useState([]);
  const [error, setError] = useState('');
  const [success, setSuccess] = useState('');
  const [hasDefaultData, setHasDefaultData] = useState(false);

  useEffect(() => {
    checkApiHealthAndDefaults();
  }, []);

  const checkApiHealthAndDefaults = async () => {
    try {
      const health = await ApiService.checkHealth();
      if (health.gemini_api === 'disconnected') {
        setError('Gemini API is not connected. Please check your API key.');
      }

      const defaultSession = await ApiService.getDefaultSession();
      if (defaultSession.available) {
        setHasDefaultData(true);
        setSuccess('Default support ticket data loaded! You can start chatting immediately.');
      }
    } catch (err) {
      setError('Cannot connect to the backend API. Please ensure the server is running.');
    }
  };

  const handleFileUpload = async (file) => {
    setIsLoading(true);
    setError('');
    try {
      const response = await ApiService.uploadFile(file, sessionId);
      
      // File was added to shared knowledge base, refresh shared session info
      const defaultSession = await ApiService.getDefaultSession();
      if (defaultSession.available) {
        // Update to show shared file info instead of personal
        setFileInfo(defaultSession.file_info);
        setHasDefaultData(true);
      }
      
      // Don't clear chat history since we're using shared knowledge base
      // setChatHistory([]); // Commented out
      
      setSuccess(`File '${file.name}' added to shared knowledge base! All users can now access this data.`);
    } catch (err) {
      setError(err.response?.data?.detail || 'Error uploading file');
    } finally {
      setIsLoading(false);
    }
  };

  const handleSendMessage = async (message) => {
    const userMessage = {
      id: uuidv4(),
      type: 'user',
      content: message,
      timestamp: new Date()
    };
    setChatHistory(prev => [...prev, userMessage]);
    setChatLoading(true);

    try {
      const response = await ApiService.sendMessage(message, sessionId);
      const botMessage = {
        id: uuidv4(),
        type: 'assistant',
        content: response.response,
        sources: response.sources || [],
        timestamp: new Date()
      };
      setChatHistory(prev => [...prev, botMessage]);
    } catch (err) {
      setError(err.response?.data?.detail || 'Error sending message');
      const errorMessage = {
        id: uuidv4(),
        type: 'error',
        content: 'Sorry, I encountered an error processing your message.',
        timestamp: new Date()
      };
      setChatHistory(prev => [...prev, errorMessage]);
    } finally {
      setChatLoading(false);
    }
  };

  const handleFeedback = async (messageId, feedback) => {
    try {
      await ApiService.submitFeedback(messageId, feedback, sessionId);
      setSuccess(`Thank you for your ${feedback} feedback!`);
    } catch (err) {
      setError('Error submitting feedback');
    }
  };

  return (
    <ThemeProvider theme={theme}>
      <CssBaseline />
      <Box sx={{ height: '100vh', width: '100%', display: 'flex', flexDirection: 'column' }}>
        {/* Header */}
        <AppBar position="static" elevation={1} sx={{ height: 48 }}>
          <Toolbar sx={{ height: 48, minHeight: 48 }}>
            <Typography variant="body1" component="div" sx={{ flexGrow: 1 }}>
              🤖 Support Ticket Assistant
            </Typography>
            <Typography variant="body2" color="inherit">
              AI-Powered Ticket Resolution
            </Typography>
          </Toolbar>
        </AppBar>

        {/* Main Chat Interface */}
        <Box sx={{ flex: 1, position: 'relative', overflow: 'hidden' }}>
          <ChatInterface
            chatHistory={chatHistory}
            onSendMessage={handleSendMessage}
            onFeedback={handleFeedback}
            onFileUpload={handleFileUpload}
            disabled={isLoading}
            hasDefaultData={hasDefaultData}
            fileInfo={fileInfo}
            loading={chatLoading}
          />
        </Box>

        {/* Notifications */}
        <Snackbar
          open={!!error}
          autoHideDuration={6000}
          onClose={() => setError('')}
        >
          <Alert severity="error" onClose={() => setError('')}>
            {error}
          </Alert>
        </Snackbar>

        <Snackbar
          open={!!success}
          autoHideDuration={4000}
          onClose={() => setSuccess('')}
        >
          <Alert severity="success" onClose={() => setSuccess('')}>
            {success}
          </Alert>
        </Snackbar>
      </Box>
    </ThemeProvider>
  );
}

export default App;