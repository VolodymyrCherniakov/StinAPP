import React, { useState, useEffect } from 'react';
import './App.css';

const API_URL = 'http://localhost:8000';

function App() {
  const [stocks, setStocks] = useState({});
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState('');
const [message, setMessage] = useState('');
  const [newTicker, setNewTicker] = useState('');
const [adding, setAdding] = useState(false);

const handleAddTicker = () => {
  if (!newTicker) return;
  setAdding(true);
  setMessage('');
  fetch(`${API_URL}/api/stocks/add_and_check`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ ticker: newTicker })
  })
    .then(async res => {
      const data = await res.json();
      if (!res.ok || data[newTicker]?.error) {
        setMessage(data[newTicker]?.error || 'Ticker nebyl nalezen.');
      } else {
        setStocks(prev => ({ ...prev, ...data }));
      }
      setNewTicker('');
    })
    .catch(err => {
      console.error('Chyba při přidávání tickeru:', err);
      setMessage('Chyba spojení s API.');
    })
    .finally(() => setAdding(false));
};

const handleRemoveTicker = (ticker) => {
  fetch(`${API_URL}/api/stocks/remove`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ ticker })
  })
    .then(res => res.json())
    .then(data => {
      if (data.removed) {
        setStocks(prev => {
          const updated = { ...prev };
          delete updated[ticker];
          return updated;
        });
      } else {
        alert(data.error || 'Chyba při odebírání tickeru');
      }
    })
    .catch(err => {
      console.error('Chyba při odebírání tickeru:', err);
      alert('Chyba spojení s API.');
    });
};


const sendRecommendations = async () => {
  try {
    const response = await fetch('http://localhost:8000/api/stocks/recommend', {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json'
      }
    });

    if (!response.ok) {
      throw new Error('Chyba při odesílání doporučení');
    }

    const result = await response.json();
    console.log('Odesláno:', result.odeslano);
    alert(`Doporučení odesláno pro: ${result.odeslano.join(', ')}`);
  } catch (error) {
    console.error(error);
    alert('Nepodařilo se odeslat doporučení');
  }
};


  useEffect(() => {
      setLoading(false); // označíme jako načteno, ale bez dotazu
    }, []);

  if (loading) return <div className="App"><p>🔄 Načítání dat...</p></div>;
  if (error) return <div className="App"><p>❌ {error}</p></div>;

  return (
    <div className="App">
      <header className="App-header">
        <h1>📈 Přehled akcií</h1>
      </header>
        <div style={{ marginBottom: '20px' }}>
          <input
            type="text"
            placeholder="Zadejte ticker (např. AAPL)"
            value={newTicker}
            onChange={(e) => setNewTicker(e.target.value.toUpperCase())}
            disabled={adding}
          />
          <button onClick={handleAddTicker} disabled={adding || !newTicker}>
            {adding ? 'Přidávám...' : 'Přidat a zkontrolovat'}
          </button>
          {message && (
            <div style={{ color: 'red', marginTop: 10 }}>{message}</div>
          )}
        </div>
      <div className="table-container">
        <table>
          <thead>
  <tr>
    <th>Ticker</th>
    <th>Společnost</th>
    <th>Závěr poslední den</th>
    <th>Pokles 3 dny</th>
    <th>2+ poklesy za 5 dní</th>
    <th>Historie</th>
    <th>Akce</th> {/* nový sloupec */}
  </tr>
    </thead>
    <tbody>
      {Object.entries(stocks).map(([ticker, data]) => (
        <tr key={ticker}>
          <td>{ticker}</td>
          <td>{data?.company_name || 'Neznámá'}</td>
          <td>${data.latest_close?.toFixed(2)}</td>
          <td>{data.declined_last_3_days ? '✅ Ano' : '❌ Ne'}</td>
          <td>{data.more_than_2_declines_last_5_days ? '✅ Ano' : '❌ Ne'}</td>
          <td>
            <ul style={{ paddingLeft: 10 }}>
              {data.history.map((entry, index) => (
                <li key={index}>
                  {entry.date}: ${entry.close?.toFixed(2)}
                </li>
              ))}
            </ul>
          </td>
          <td>
            <button onClick={() => handleRemoveTicker(ticker)}>🗑️ Odebrat</button>
          </td>
        </tr>
      ))}
    </tbody>
        </table>
        <div style={{ marginTop: '20px' }}>
          <button onClick={sendRecommendations}>
            Odeslat doporučení
          </button>
        </div>
      </div>
    </div>
  );
}

export default App;
