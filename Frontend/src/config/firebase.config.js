// Import the functions you need from the SDKs you need
import { initializeApp } from "firebase/app";

// Your web app's Firebase configuration
// For Firebase JS SDK v7.20.0 and later, measurementId is optional
const firebaseConfig = {
  apiKey: "AIzaSyAoeZHm-azcBvHdEFEfnKYibK6bYHyXqLU",
  authDomain: "stockify-6e2b1.firebaseapp.com",
  projectId: "stockify-6e2b1",
  storageBucket: "stockify-6e2b1.firebasestorage.app",
  messagingSenderId: "1051195772160",
  appId: "1:1051195772160:web:b2b7ea0d56cf988baf37e5",
  measurementId: "G-WFZQQV6LY6"
};

// Initialize Firebase
const app = initializeApp(firebaseConfig);

export { app };
export default firebaseConfig;
