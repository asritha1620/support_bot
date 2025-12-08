import axios from 'axios';

const API_BASE_URL = process.env.REACT_APP_API_URL || 'http://localhost:8000';

class ApiService {
  constructor() {
    this.api = axios.create({
      baseURL: API_BASE_URL,
      headers: {
        'Content-Type': 'application/json',
      },
    });
  }

  async checkHealth() {
    const response = await this.api.get('/health');
    return response.data;
  }

  async uploadFile(file, sessionId) {
    const formData = new FormData();
    formData.append('file', file);
    formData.append('session_id', sessionId);

    const response = await this.api.post('/upload', formData, {
      headers: {
        'Content-Type': 'multipart/form-data',
      },
    });
    return response.data;
  }

  async sendMessage(message, sessionId) {
    const response = await this.api.post('/chat', {
      message,
      session_id: sessionId,
    });
    return response.data;
  }

  async addResolution(resolutionData, sessionId) {
    const response = await this.api.post('/add-resolution', resolutionData);
    return response.data;
  }

  async submitFeedback(feedbackData) {
    const response = await this.api.post('/feedback', feedbackData);
    return response.data;
  }
}

const apiService = new ApiService();
export default apiService;