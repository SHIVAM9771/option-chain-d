import { createSlice, createAsyncThunk } from '@reduxjs/toolkit';
import axios from 'axios';

const API_URL = 'http://16.16.204.22:10001';

const api = axios.create({
  baseURL: API_URL,
  headers: {
    'Accept': 'application/json',
    'Content-Type': 'application/json',
    'X-Requested-With': 'XMLHttpRequest'
  },
  withCredentials: true
});

api.interceptors.request.use(request => {
  request.headers['Access-Control-Allow-Origin'] = 'http://localhost:5173';
  request.headers['Access-Control-Allow-Credentials'] = 'true';
  
  console.log('Starting Request:', {
    url: request.url,
    method: request.method,
    data: request.data,
    headers: request.headers
  });
  return request;
}, error => {
  console.error('Request Error:', error);
  return Promise.reject(error);
});

api.interceptors.response.use(
  response => {
    console.log('Response:', response);
    return response;
  },
  error => {
    if (error.response) {
      console.error('Response Error:', {
        status: error.response.status,
        data: error.response.data,
        headers: error.response.headers
      });
    } else if (error.request) {
      console.error('Request Error:', error.request);
    } else {
      console.error('Error:', error.message);
    }
    return Promise.reject(error);
  }
);

// Helper function to handle API errors
const handleApiError = (error) => {
  if (error.response) {
    // Handle 401 errors by refreshing token
    if (error.response.status === 401) {
      return refreshTokenAndRetry(error);
    }
    return error.response.data?.message || 'Server error occurred';
  } else if (error.request) {
    return 'No response from server. Please check your internet connection.';
  } else {
    return error.message || 'An error occurred';
  }
};

// Function to refresh token and retry failed request
const refreshTokenAndRetry = async (error) => {
  try {
    const refreshToken = localStorage.getItem('refreshToken');
    if (!refreshToken) {
      throw new Error('No refresh token available');
    }

    // Get new access token
    const response = await api.post(`/refresh-token`, {
      refresh_token: refreshToken
    });

    // Update tokens
    const { access_token } = response.data;
    localStorage.setItem('token', access_token);

    // Update axios default header
    api.defaults.headers.common['Authorization'] = `Bearer ${access_token}`;

    // Retry the original request
    const config = error.config;
    config.headers['Authorization'] = `Bearer ${access_token}`;
    return api(config);
  } catch (error) {
    // If refresh fails, logout user
    store.dispatch(logout());
    throw new Error('Session expired. Please login again.');
  }
};

// Load initial state from localStorage
const loadInitialState = () => {
  try {
    const savedUser = localStorage.getItem('user');
    const savedToken = localStorage.getItem('token');
    const savedRefreshToken = localStorage.getItem('refreshToken');
    const savedTheme = localStorage.getItem('theme');
    const savedPreferences = localStorage.getItem('preferences');

    // Set axios default header if token exists
    if (savedToken) {
      api.defaults.headers.common['Authorization'] = `Bearer ${savedToken}`;
    }

    return {
      user: savedUser ? JSON.parse(savedUser) : null,
      token: savedToken || null,
      refreshToken: savedRefreshToken || null,
      theme: savedTheme || 'light',
      preferences: savedPreferences ? JSON.parse(savedPreferences) : {},
      isAuthenticated: !!savedUser && !!savedToken,
      error: null,
      loading: false
    };
  } catch (error) {
    console.error('Error loading auth state:', error);
    return {
      user: null,
      token: null,
      refreshToken: null,
      theme: 'light',
      preferences: {},
      isAuthenticated: false,
      error: null,
      loading: false
    };
  }
};

// Async actions
export const registerUser = createAsyncThunk(
  'auth/register',
  async (userData, { rejectWithValue }) => {
    try {
      const response = await api.post(`/register`, userData, {
        headers: {
          'Content-Type': 'application/json'
        },
        withCredentials: true
      });
      return response.data;
    } catch (error) {
      return rejectWithValue(handleApiError(error));
    }
  }
);

export const loginUser = createAsyncThunk(
  'auth/login',
  async (credentials, { rejectWithValue }) => {
    try {
      console.log('Attempting login with:', credentials);
      
      const response = await api.post(`/login`, credentials);
      console.log('Login response:', response.data);

      const { user, access_token, refresh_token } = response.data;

      // Store tokens and user data
      localStorage.setItem('token', access_token);
      localStorage.setItem('refreshToken', refresh_token);
      localStorage.setItem('user', JSON.stringify(user));
      localStorage.setItem('preferences', JSON.stringify(user.preferences || {}));

      // Set axios default header
      api.defaults.headers.common['Authorization'] = `Bearer ${access_token}`;

      return response.data;
    } catch (error) {
      console.error('Login error:', error.response?.data || error.message);
      if (error.response?.data?.error) {
        return rejectWithValue(error.response.data.error);
      }
      return rejectWithValue(error.message || 'Login failed. Please try again.');
    }
  }
);

export const logoutUser = createAsyncThunk(
  'auth/logout',
  async (_, { rejectWithValue }) => {
    try {
      await api.post(`/logout`);

      // Clear localStorage
      localStorage.removeItem('user');
      localStorage.removeItem('token');
      localStorage.removeItem('refreshToken');
      localStorage.removeItem('preferences');

      // Clear axios default header
      delete api.defaults.headers.common['Authorization'];

      return null;
    } catch (error) {
      return rejectWithValue(error.message);
    }
  }
);

export const updateProfile = createAsyncThunk(
  'auth/updateProfile',
  async (profileData, { getState, rejectWithValue }) => {
    try {
      const response = await api.put(`/profile`, profileData, {
        headers: {
          'Content-Type': 'application/json'
        },
        withCredentials: true
      });
      return response.data;
    } catch (error) {
      return rejectWithValue(handleApiError(error));
    }
  }
);

export const uploadProfileImage = createAsyncThunk(
  'auth/uploadProfileImage',
  async (imageFile, { rejectWithValue }) => {
    try {
      const formData = new FormData();
      formData.append('image', imageFile);

      const response = await api.post(`/profile/image`, formData, {
        headers: {
          'Content-Type': 'multipart/form-data',
        },
        withCredentials: true
      });
      return response.data;
    } catch (error) {
      return rejectWithValue(handleApiError(error));
    }
  }
);

const authSlice = createSlice({
  name: 'auth',
  initialState: loadInitialState(),
  reducers: {
    updateUserPreferences: (state, action) => {
      state.preferences = { ...state.preferences, ...action.payload };
      localStorage.setItem('preferences', JSON.stringify(state.preferences));
    },
    setTheme: (state, action) => {
      state.theme = action.payload;
      localStorage.setItem('theme', action.payload);
    },
    logout(state) {
      state.user = null;
      state.token = null;
      state.refreshToken = null;
      state.isAuthenticated = false;
      state.preferences = {};
      // Clear localStorage
      localStorage.removeItem('user');
      localStorage.removeItem('token');
      localStorage.removeItem('refreshToken');
      localStorage.removeItem('preferences');
    },
    clearError(state) {
      state.error = null;
    }
  },
  extraReducers: (builder) => {
    builder
      // Register cases
      .addCase(registerUser.pending, (state) => {
        state.loading = true;
        state.error = null;
      })
      .addCase(registerUser.fulfilled, (state, action) => {
        state.loading = false;
        state.user = action.payload.user;
        state.token = action.payload.token;
        state.refreshToken = action.payload.refresh_token;
        state.isAuthenticated = true;
        localStorage.setItem('user', JSON.stringify(action.payload.user));
        localStorage.setItem('token', action.payload.token);
        localStorage.setItem('refreshToken', action.payload.refresh_token);
      })
      .addCase(registerUser.rejected, (state, action) => {
        state.loading = false;
        state.error = action.payload;
      })
      // Login cases
      .addCase(loginUser.pending, (state) => {
        state.loading = true;
        state.error = null;
      })
      .addCase(loginUser.fulfilled, (state, action) => {
        state.loading = false;
        state.user = action.payload.user;
        state.token = action.payload.access_token;
        state.refreshToken = action.payload.refresh_token;
        state.isAuthenticated = true;
        state.preferences = action.payload.user.preferences || {};
      })
      .addCase(loginUser.rejected, (state, action) => {
        state.loading = false;
        state.error = action.payload;
      })
      // Logout cases
      .addCase(logoutUser.fulfilled, (state) => {
        state.user = null;
        state.token = null;
        state.refreshToken = null;
        state.isAuthenticated = false;
        state.preferences = {};
      })
      // Update profile cases
      .addCase(updateProfile.pending, (state) => {
        state.loading = true;
        state.error = null;
      })
      .addCase(updateProfile.fulfilled, (state, action) => {
        state.loading = false;
        state.user = action.payload.user;
      })
      .addCase(updateProfile.rejected, (state, action) => {
        state.loading = false;
        state.error = action.payload;
      })
      // Upload profile image cases
      .addCase(uploadProfileImage.pending, (state) => {
        state.loading = true;
        state.error = null;
      })
      .addCase(uploadProfileImage.fulfilled, (state, action) => {
        state.loading = false;
        state.user = {
          ...state.user,
          profile_image: action.payload.profile_image
        };
      })
      .addCase(uploadProfileImage.rejected, (state, action) => {
        state.loading = false;
        state.error = action.payload;
      });
  }
});

export const { logout, clearError, updateUserPreferences, setTheme } = authSlice.actions;
export default authSlice.reducer;
