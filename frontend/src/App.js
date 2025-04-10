import React, { useState, useEffect } from 'react';
import './App.css';

function App() {
  const [stocks, setStocks] = useState({});
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState('');
  const API_URL = 'http://localhost:8000';

  useEffect(() => {
    fetch(`${API_URL}/api/stocks`)
      .then(response => response.json())
      .then(data => {
        setStocks(data);
        setLoading(false);
      })
      .catch(err => {
        console.error('Error:', err);
        setError('Chyba při načítání dat o akciích.');
        setLoading(false);
      });
  }, []);

  if (loading) {
    return <div className="App"><p>Načítání dat...</p></div>;
  }

  if (error) {
    return <div className="App"><p>{error}</p></div>;
  }

  return (
    <div className="App">
      <header className="App-header">
        <h1>Přehled akcií</h1>
      </header>
      <div className="table-container">
        <table>
          <thead>
            <tr>
              <th>Ticker</th>
              <th>Závěr poslední den</th>
              <th>Pokles 3 dny</th>
              <th>2+ poklesy za 5 dní</th>
              <th>Historie (datum: cena)</th>
            </tr>
          </thead>
          <tbody>
            {Object.entries(stocks).map(([ticker, data]) => (
              <tr key={ticker}>
                <td>{ticker}</td>
                {data.error ? (
                  <td colSpan="4" style={{ color: 'red' }}>{data.error}</td>
                ) : (
                  <>
                    <td>${data.latest_close.toFixed(2)}</td>
                    <td>{data.declined_last_3_days ? 'Ano' : 'Ne'}</td>
                    <td>{data.more_than_2_declines_last_5_days ? 'Ano' : 'Ne'}</td>
                    <td>
                      {data.history.map((entry, index) => (
                        <div key={index}>
                          {entry.date}: ${entry.close.toFixed(2)}
                        </div>
                      ))}
                    </td>
                  </>
                )}
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </div>
  );
}

export default App;
