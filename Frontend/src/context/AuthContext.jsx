import { createContext, useContext, useState, useEffect } from 'react';
import {
  signInWithEmailAndPassword,
  signOut,
  onAuthStateChanged,
  GoogleAuthProvider,
  signInWithPopup,
} from 'firebase/auth';
import { auth } from '../config/firebase';
import axios from 'axios';

// Create axios instance with default config
const api = axios.create({
  baseURL: import.meta.env.VITE_API_URL,
  headers: {
    'Content-Type': 'application/json',
  },
  withCredentials: false // Set to false since we're allowing all origins
});

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
      throw error.response?.data?.error || error.message;
    }
  }

  // Login function
  async function login(email, password) {
    try {
      const response = await api.post('/api/auth/login', {
        email,
        password
      });
      const { user, token } = response.data;
      setUser(user);
      setToken(token);
      return response.data;
    } catch (error) {
      console.error('Login error:', error);
      throw error.response?.data?.error || error.message;
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
      throw error.response?.data?.error || error.message;
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
