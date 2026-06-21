import axios from 'axios';



const BASE_URL = 'http://localhost:8001';

export const registerUser = async (data) => {
  const response = await axios.post(`${BASE_URL}/register`, data);
  console.log('Registration response:', response.data);
  return response.data;
};


export const loginUser = async (data) => {
  const response = await axios.post(`${BASE_URL}/login`, data);
  return response.data;
};

export const getResponse = async (query, token) => {
  console.log(query)
  const response = await axios.post(`${BASE_URL}/chat/`,query,{
    headers: {
      Authorization: `Bearer ${token}`,
    },
  });
  return response.data.ai_response;
};


export const fetchSessions = async (token) => {
  const response = await axios.get(`${BASE_URL}/sessions/history`, {
    headers: { Authorization: `Bearer ${token}` },
  });

  if (response.status !== 200) {
    throw new Error('Failed to fetch sessions');
  }

  return response.data;
};

export const createSession = async (token) => {
  const response = await axios.post(`${BASE_URL}/sessions/initialize`,{}, {
    headers: { Authorization: `Bearer ${token}` },
  });

  if (response.status !== 201) {
    throw new Error('Failed to create session');
  }

  return response.data;
};

export const sessionHistory = async (session_id, token) => {
  try {
    const response = await axios.get(`${BASE_URL}/sessions/messages/${session_id}`, {
      headers: {
        Authorization: `Bearer ${token}`
      }
    });

    return response.data;
  } catch (error) {
    console.error(`Session fetch failed: ${error.response?.status} - ${error.response?.data?.detail || error.message}`);
    throw new Error('Failed to fetch session messages');
  }
};


export const deleteSession = async (session_id, token) => {
  try {
    const response = await axios.delete(`${BASE_URL}/sessions/${session_id}`, {
      headers: {
        Authorization: `Bearer ${token}`,
      },
    });

    if (response.status === 204) {
      return true;
    } else {
      throw new Error('Failed to delete session');
    }
  } catch (error) {
    console.error('Error deleting session:', error.response?.data || error.message);
    throw error;
  }
};