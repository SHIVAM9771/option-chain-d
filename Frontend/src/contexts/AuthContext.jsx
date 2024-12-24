import React, { createContext, useContext, useState, useEffect } from 'react';
import { 
  createUserWithEmailAndPassword, 
  signInWithEmailAndPassword, 
  signOut, 
  sendPasswordResetEmail,
  updatePassword,
  updateEmail,
  updateProfile
} from 'firebase/auth';
import { auth } from '../config/firebase';
import axios from 'axios';

const AuthContext = createContext();

export function useAuth() {
  return useContext(AuthContext);
}

export function AuthProvider({ children }) {
  const [currentUser, setCurrentUser] = useState(null);
  const [loading, setLoading] = useState(true);

  const signup = async (email, password, username) => {
    try {
      const userCredential = await createUserWithEmailAndPassword(auth, email, password);
      await updateProfile(userCredential.user, { displayName: username });
      const idToken = await userCredential.user.getIdToken();
      
      // Register with our backend
      const response = await axios.post(`${import.meta.env.VITE_API_URL}/api/auth/login`, {
        idToken
      });
      
      setCurrentUser({
        ...response.data.user,
        token: response.data.token
      });
      
      return response.data;
    } catch (error) {
      throw error;
    }
  };

  const login = async (email, password) => {
    try {
      const userCredential = await signInWithEmailAndPassword(auth, email, password);
      const idToken = await userCredential.user.getIdToken();
      
      // Login with our backend
      const response = await axios.post(`${import.meta.env.VITE_API_URL}/api/auth/login`, {
        idToken
      });
      
      setCurrentUser({
        ...response.data.user,
        token: response.data.token
      });
      
      return response.data;
    } catch (error) {
      throw error;
    }
  };

  const logout = async () => {
    await signOut(auth);
    setCurrentUser(null);
  };

  const resetPassword = (email) => {
    return sendPasswordResetEmail(auth, email);
  };

  const updateUserEmail = async (email) => {
    try {
      await updateEmail(auth.currentUser, email);
      const idToken = await auth.currentUser.getIdToken(true);
      
      // Update profile in our backend
      const response = await axios.put(
        `${import.meta.env.VITE_API_URL}/api/auth/user/profile`,
        { email },
        {
          headers: {
            Authorization: `Bearer ${idToken}`
          }
        }
      );
      
      setCurrentUser({
        ...response.data,
        token: idToken
      });
    } catch (error) {
      throw error;
    }
  };

  const updateUserPassword = async (newPassword) => {
    try {
      await updatePassword(auth.currentUser, newPassword);
      const idToken = await auth.currentUser.getIdToken(true);
      setCurrentUser(prev => ({
        ...prev,
        token: idToken
      }));
    } catch (error) {
      throw error;
    }
  };

  const updateUserProfile = async (updates) => {
    try {
      if (updates.displayName) {
        await updateProfile(auth.currentUser, { displayName: updates.displayName });
      }
      
      const idToken = await auth.currentUser.getIdToken();
      
      // Update profile in our backend
      const response = await axios.put(
        `${import.meta.env.VITE_API_URL}/api/auth/user/profile`,
        {
          username: updates.displayName
        },
        {
          headers: {
            Authorization: `Bearer ${idToken}`
          }
        }
      );
      
      setCurrentUser({
        ...response.data,
        token: idToken
      });
    } catch (error) {
      throw error;
    }
  };

  useEffect(() => {
    const unsubscribe = auth.onAuthStateChanged(async (user) => {
      if (user) {
        try {
          const idToken = await user.getIdToken();
          const response = await axios.post(`${import.meta.env.VITE_API_URL}/api/auth/verify-token`, {
            idToken
          });
          
          setCurrentUser({
            ...response.data,
            token: idToken
          });
        } catch (error) {
          console.error('Error verifying token:', error);
          setCurrentUser(null);
        }
      } else {
        setCurrentUser(null);
      }
      setLoading(false);
    });

    return unsubscribe;
  }, []);

  const value = {
    currentUser,
    signup,
    login,
    logout,
    resetPassword,
    updateUserEmail,
    updateUserPassword,
    updateUserProfile
  };

  return (
    <AuthContext.Provider value={value}>
      {!loading && children}
    </AuthContext.Provider>
  );
}
