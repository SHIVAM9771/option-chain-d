import React from "react";
import { useDispatch, useSelector } from "react-redux";
import { createSelector } from "reselect";
import { AuthProvider } from './AuthContext';

// Create a context for app-wide state management
export const AppContext = React.createContext();

// Create memoized selectors
const selectUser = (state) => state.auth.user;  
const selectToken = (state) => state.auth.token;
const selectIsAuthenticated = (state) => state.auth.isAuthenticated;
const selectTheme = (state) => state.theme.theme;
const selectIsReversed = (state) => state.theme.isReversed;
const selectIsHighlighting = (state) => state.theme.isHighlighting;

const selectAppState = createSelector(
  [
    selectUser,
    selectToken,
    selectIsAuthenticated,
    selectTheme,
    selectIsReversed,
    selectIsHighlighting,
  ],
  (
    user,
    token,
    isAuthenticated,
    theme,
    isReversed,
    isHighlighting,
  ) => ({
    user,
    token,
    isAuthenticated,
    theme,
    isReversed,
    isHighlighting,
  })
);

export const AppProvider = ({ children }) => {
  const {
    user,
    token,
    isAuthenticated,
    theme,
    isReversed,
    isHighlighting,
  } = useSelector(selectAppState);

  const value = {
    user,
    token,
    isAuthenticated,
    theme,
    isReversed,
    isHighlighting,
  };

  return (
    <AppContext.Provider value={value}>
      <AuthProvider>
        {children}
      </AuthProvider>
    </AppContext.Provider>
  );
};

export default AppProvider;
