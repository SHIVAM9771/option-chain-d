import { createContext, useContext, useState, useEffect } from 'react';
import {
  signInWithEmailAndPassword,
  signOut,
  onAuthStateChanged,
  GoogleAuthProvider,
  signInWithPopup,
} from 'firebase/auth';
import { auth } from '../config/firebase';
import { api } from '../api/axiosConfig';

// Get the API URL from environment variables or use a default
const API_URL = import.meta.env.VITE_API_URL || 'http://16.16.204.22:10001';

// Create axios instance with default config
// const api = axios.create({
//   baseURL: API_URL,
//   headers: {
//     'Content-Type': 'application/json',
//     'Accept': 'application/json'
//   },
//   timeout: 10000, // 10 second timeout
//   withCredentials: true // Enable credentials
// });

// Add request interceptor for debugging
// api.interceptors.request.use(request => {
//   console.log('Starting Request:', {
//     url: request.url,
//     method: request.method,
//     headers: request.headers,
//     data: request.data,
//     baseURL: request.baseURL
//   });
//   return request;
// }, error => {
//   console.error('Request Error:', error);
//   return Promise.reject(error);
// });

// Add response interceptor for debugging
// api.interceptors.response.use(
//   response => {
//     console.log('Response:', response);
//     return response;
//   },
//   error => {
//     console.error('Response Error:', {
//       message: error.message,
//       response: error.response?.data,
//       status: error.response?.status,
//       config: {
//         url: error.config?.url,
//         baseURL: error.config?.baseURL,
//         method: error.config?.method
//       }
//     });
//     return Promise.reject(error);
//   }
// );

const AuthContext = createContext(null);

export function useAuth() {
  const context = useContext(AuthContext);
  if (!context) {
    throw new Error('useAuth must be used within an AuthProvider');
  }
  return context;
}

export function AuthProvider({ children }) {
  const [user, setUser] = useState(null);
  const [loading, setLoading] = useState(true);
  const [token, setToken] = useState(null);

  // Update axios authorization header when token changes
  useEffect(() => {
    if (token) {
      api.defaults.headers.common['Authorization'] = `Bearer ${token}`;
    } else {
      delete api.defaults.headers.common['Authorization'];
    }
  }, [token]);

  // Signup function
  async function signup(email, password) {
    try {
      const response = await api.post('/api/auth/register', {
        email,
        password
      });
      const { user, token } = response.data;
      setUser(user);
      setToken(token);
      return response.data;
    } catch (error) {
      console.error('Signup error:', error);
      if (error.response?.data?.error) {
        throw new Error(error.response.data.error);
      }
      if (error.code === 'ERR_NETWORK') {
        throw new Error(`Unable to connect to server at ${API_URL}. Please check if the server is running.`);
      }
      throw new Error('Failed to create account. Please try again.');
    }
  }

  // Login function
  async function login(email, password) {
    try {
      console.log('Attempting login with:', { email, apiUrl: API_URL });
      
      // First try to check if the server is accessible
      try {
        await api.options('/api/auth/login');
      } catch (error) {
        console.error('Server check failed:', error);
        throw new Error(`Server at ${API_URL} is not accessible. Please check if the server is running.`);
      }
      
      const response = await api.post('/api/auth/login', {
        email,
        password
      });
      
      console.log('Login response:', response.data);
      const { user, token } = response.data;
      setUser(user);
      setToken(token);
      return response.data;
    } catch (error) {
      console.error('Login error:', error);
      if (error.response?.data?.error) {
        throw new Error(error.response.data.error);
      }
      if (error.code === 'ERR_NETWORK') {
        throw new Error(`Unable to connect to server at ${API_URL}. Please check if the server is running.`);
      }
      throw new Error('Invalid email or password.');
    }
  }

  // Logout function
  async function logout() {
    try {
      if (token) {
        await api.post('/api/auth/logout');
      }
    } catch (error) {
      console.error('Logout error:', error);
    } finally {
      setUser(null);
      setToken(null);
    }
  }

  // Google Sign In
  async function signInWithGoogle() {
    try {
      const provider = new GoogleAuthProvider();
      const result = await signInWithPopup(auth, provider);
      const idToken = await result.user.getIdToken();
      
      const response = await api.post('/api/auth/google', {
        idToken
      });
      
      const { user, token } = response.data;
      setUser(user);
      setToken(token);
      return response.data;
    } catch (error) {
      console.error('Google sign in error:', error);
      if (error.response?.data?.error) {
        throw new Error(error.response.data.error);
      }
      if (error.code === 'ERR_NETWORK') {
        throw new Error(`Unable to connect to server at ${API_URL}. Please check if the server is running.`);
      }
      throw new Error('Google sign in failed. Please try again.');
    }
  }

  // Check auth state on mount
  useEffect(() => {
    const checkAuth = async () => {
      try {
        if (token) {
          const response = await api.post('/api/auth/verify-token', { token });
          setUser(response.data.user);
        }
      } catch (error) {
        console.error('Token verification failed:', error);
        setUser(null);
        setToken(null);
      } finally {
        setLoading(false);
      }
    };

    checkAuth();
  }, [token]);

  const value = {
    user,
    token,
    signup,
    login,
    logout,
    signInWithGoogle,
  };

  return (
    <AuthContext.Provider value={value}>
      {!loading && children}
    </AuthContext.Provider>
  );
}

export default AuthContext;
