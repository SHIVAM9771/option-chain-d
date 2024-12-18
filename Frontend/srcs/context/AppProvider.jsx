import React, { createContext, useEffect, useRef } from "react";
import { useDispatch, useSelector } from "react-redux";
import { fetchLiveData, fetchExpiryDate, setExp } from "../context/dataSlice";

export const AppContext = createContext();

export const AppProvider = ({ children }) => {
  const dispatch = useDispatch();

  // User state from Redux
  const user = useSelector((state) => state.user.user);

  // Theme state from Redux
  const theme = useSelector((state) => state.theme.theme);
  const isReversed = useSelector((state) => state.theme.isReversed);
  const isHighlighting = useSelector((state) => state.theme.isHighlighting);

  // Data state from Redux
  const data = useSelector((state) => state.data.data);
  const exp = useSelector((state) => state.data.exp);
  const symbol = useSelector((state) => state.data.symbol);
  const expDate = useSelector((state) => state.data.expDate);
  const isOc = useSelector((state) => state.data.isOc);

  const intervalRef = useRef(null);

  // Fetch expiry dates on symbol change
  useEffect(() => {
    dispatch(fetchExpiryDate({ sid: symbol, exp }));
  }, [dispatch, symbol]); // Fetch expiry date when symbol changes

  useEffect(() => {
    if (data?.fut?.data?.explist) {
      dispatch(setExp(data.fut.data.explist[0] || 0));
    }
  }, [symbol]); // Run when explist is updated



  // Fetch live data every 3 seconds when `isOc` is true
  useEffect(() => {
    const fetchData = async () => {
      try {
        await dispatch(fetchLiveData({ sid: symbol, exp: exp }));
      } catch (error) {
        console.error("Error fetching live data:", error);
      }
    };

    if (isOc) {
      fetchData();
      intervalRef.current = setInterval(fetchData, 3000);
    }

    return () => {
      if (intervalRef.current) clearInterval(intervalRef.current);
    };
  }, [exp, expDate, dispatch]);

  return (
    <AppContext.Provider
      value={{
        user,
        theme,
        isReversed,
        isHighlighting,
        data,
        exp,
        symbol,
        expDate,
        isOc,
      }}
    >
      {children}
    </AppContext.Provider>
  );
};