import React, { useState, useEffect } from 'react';
import './App.css';

function App() {
  const [message, setMessage] = useState('Loading...');

  const API_URL = 'http://localhost:8000';

  useEffect(() => {
    fetch(`${API_URL}/api/hello`)
      .then(response => response.json())
      .then(data => setMessage(data.message))
      .catch(error => {
        console.error('Error:', error);
        setMessage('Error loading message');
      });
  }, []);

  return (
    <div className="App">
      <header className="App-header">
        <h1>Hello Docker World</h1>
        <p>{message}</p>
      </header>
    </div>
  );
}

export default App;