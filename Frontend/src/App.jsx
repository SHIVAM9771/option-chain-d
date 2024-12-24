import React, { Suspense } from 'react';
import { BrowserRouter as Router, Routes, Route, Navigate } from 'react-router-dom';
import { useSelector } from 'react-redux';
import Login from './components/auth/Login';
import Register from './components/auth/Register';
import Profile from './components/auth/Profile';
import OptionChain from './pages/OptionChain';
import Dashboard from './pages/Dashboard';
import ErrorBoundary from './ErrorBoundary';
import Blog from './pages/Blog';
import About from './pages/About';
import ProfitLossCalculator from './pages/Tca';
import ContactUs from './pages/Contact';
import Spinner from './components/Spinner';
import Home from './pages/Home';
import PositionSizing from './pages/PositionSizing';
import NotFound from './pages/NotFound';
import MainLayout from './layouts/MainLayout';

// Protected Route component
const ProtectedRoute = ({ children }) => {
  const { isAuthenticated } = useSelector((state) => state.auth);
  return isAuthenticated ? children : <Navigate to="/" />;
};

function App() {
  const theme = useSelector((state) => state.theme.theme);
  const { isAuthenticated } = useSelector((state) => state.auth);

  return (
    <Router>
      <div className={`min-h-screen ${theme === 'dark' ? 'bg-gray-900' : 'bg-gray-100'}`}>
        <ErrorBoundary>
          <Suspense fallback={<div>Loading...</div>}>
            <Routes>
              {/* Public Routes */}
              <Route path="/" element={
                isAuthenticated ? <Navigate to="/dashboard" /> : <Login />
              } />
              <Route path="/register" element={<Register />} />
              <Route path="/contact" element={<ContactUs />} />
              
              {/* Protected Routes */}
              <Route element={<ProtectedRoute><MainLayout /></ProtectedRoute>}>
                <Route path="/dashboard" element={<Dashboard />} />
                <Route path="/option-chain" element={<OptionChain />} />
                <Route path="/risk-analysis" element={<ProfitLossCalculator />} />
                <Route path="/position-sizing" element={<PositionSizing />} />
                <Route path="/blog" element={<Blog />} />
                <Route path="/profile" element={<Profile />} />
                <Route path="/about" element={<About />} />
                <Route path="/login" element={<Login />} />
              </Route>
              
              {/* 404 Route */}
              <Route path="*" element={<NotFound />} />
            </Routes>
          </Suspense>
        </ErrorBoundary>
      </div>
    </Router>
  );
}

export default App;
