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

  // Signup function
  async function signup(email, password) {
    try {
      const response = await axios.post(`${import.meta.env.VITE_API_URL}/api/auth/register`, {
        email,
        password
      }, {
        withCredentials: true,
        headers: {
          'Content-Type': 'application/json'
        }
      });
      const { user, token } = response.data;
      setUser(user);
      setToken(token);
      // Set axios default header
      axios.defaults.headers.common['Authorization'] = `Bearer ${token}`;
      return response.data;
    } catch (error) {
      throw error.response?.data?.message || error.message;
    }
  }

  // Login function
  async function login(email, password) {
    try {
      const response = await axios.post(`${import.meta.env.VITE_API_URL}/api/auth/login`, {
        email,
        password
      }, {
        withCredentials: true,
        headers: {
          'Content-Type': 'application/json'
        }
      });
      const { user, token } = response.data;
      setUser(user);
      setToken(token);
      // Set axios default header
      axios.defaults.headers.common['Authorization'] = `Bearer ${token}`;
      return response.data;
    } catch (error) {
      throw error.response?.data?.message || error.message;
    }
  }

  // Logout function
  async function logout() {
    try {
      await axios.post(`${import.meta.env.VITE_API_URL}/api/auth/logout`, {}, {
        withCredentials: true,
        headers: {
          'Content-Type': 'application/json'
        }
      });
      setUser(null);
      setToken(null);
      // Remove axios default header
      delete axios.defaults.headers.common['Authorization'];
    } catch (error) {
      console.error('Logout error:', error);
      // Still clear the user state even if the API call fails
      setUser(null);
      setToken(null);
      delete axios.defaults.headers.common['Authorization'];
    }
  }

  // Google Sign In
  async function signInWithGoogle() {
    try {
      const provider = new GoogleAuthProvider();
      const result = await signInWithPopup(auth, provider);
      const idToken = await result.user.getIdToken();
      
      const response = await axios.post(`${import.meta.env.VITE_API_URL}/api/auth/google`, {
        idToken
      }, {
        withCredentials: true,
        headers: {
          'Content-Type': 'application/json'
        }
      });
      
      const { user, token } = response.data;
      setUser(user);
      setToken(token);
      // Set axios default header
      axios.defaults.headers.common['Authorization'] = `Bearer ${token}`;
      return response.data;
    } catch (error) {
      throw error.response?.data?.message || error.message;
    }
  }

  // Verify token on mount and token change
  useEffect(() => {
    const verifyToken = async () => {
      if (token) {
        try {
          const response = await axios.post(`${import.meta.env.VITE_API_URL}/api/auth/verify-token`, {
            token
          });
          setUser(response.data.user);
        } catch (error) {
          console.error('Token verification failed:', error);
          setUser(null);
          setToken(null);
          delete axios.defaults.headers.common['Authorization'];
        }
      }
      setLoading(false);
    };

    verifyToken();
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
