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
  const [recommendError, setRecommendError] = useState('');
  const [recommendMessage, setRecommendMessage] = useState('');

  const [newsUrl, setNewsUrl] = useState('');
  const [minRating, setMinRating] = useState(-5);
  const [newsData, setNewsData] = useState([]);
  const [newsError, setNewsError] = useState('');
  const [newsLoading, setNewsLoading] = useState(false);

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
    setRecommendError('');
    setRecommendMessage('');
    try {
      const response = await fetch(API_URL + '/api/stocks/recommend', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json'
        }
      });

      if (!response.ok) {
        throw new Error('Chyba při odesílání doporučení');
      }

      const result = await response.json();

      if (!result.odeslano || result.odeslano.length === 0) {
        setRecommendError('Žádné doporučení nebylo odesláno – seznam je prázdný.');
      } else {
        setRecommendMessage(`Doporučení odesláno pro: ${result.odeslano.join(', ')}`);
      }

    } catch (error) {
      console.error(error);
      setRecommendError('Nepodařilo se odeslat doporučení.');
    }
  };

  const handleSendNews = async () => {
    setNewsLoading(true);
    setNewsError('');
    setNewsData([]);

    try {
      const res = await fetch('/api/news', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          api_url: 'https://news-production-257a.up.railway.app/news/recommend',
          min_rating_for_sell: minRating
        })
      });

      const data = await res.json();

      if (!res.ok) {
        setNewsError(data.error || 'Chyba při zpracování zpráv');
      } else {
        setNewsData(data.data || []);
      }
    } catch (e) {
      console.error('Chyba při odesílání zpráv:', e);
      setNewsError('Nepodařilo se odeslat zprávy.');
    } finally {
      setNewsLoading(false);
    }
  };

  useEffect(() => {
    fetch(`${API_URL}/api/stocks`)
      .then(res => res.json())
      .then(data => {
        setStocks(data);
      })
      .catch(err => {
        console.error('Chyba při načítání dat:', err);
        setError('Nepodařilo se načíst akciová data.');
      })
      .finally(() => {
        setLoading(false);
      });
  }, []);

  if (loading) return <div className="App"><p>🔄 Načítání dat...</p></div>;
  if (error) return <div className="App"><p>❌ {error}</p></div>;

  return (
    <>
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
                <th>Více než 2 poklesy za 5 dní</th>
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
            {recommendError && (
              <div style={{ color: 'red', marginTop: 10 }}>{recommendError}</div>
            )}
            {recommendMessage && (
              <div style={{ color: 'green', marginTop: 10 }}>{recommendMessage}</div>
            )}
          </div>
        </div>
        <div style={{ marginBottom: '1rem' }}>
        <label htmlFor="minRating">Minimální rating pro SELL:</label>
          <input
            type="number"
            id="minRating"
            value={minRating}
            onChange={(e) => {
              let value = parseInt(e.target.value);
              // Omezíme hodnotu mezi -10 a 10
              if (value < -10) value = -10;
              if (value > 10) value = 10;
              setMinRating(value);
            }}
            style={{ marginLeft: '0.5rem', width: '60px' }}
            min="-10"
            max="10"
          />
        </div>
        <button style={{ marginTop: 10 }} onClick={handleSendNews} disabled={newsLoading}>
          {newsLoading ? 'Zpracovávám...' : 'Odeslat a vyhodnotit zprávy'}
        </button>
        {newsError && <div style={{ color: 'red', marginTop: 10 }}>{newsError}</div>}

        {newsData.length > 0 && (
          <div style={{ marginTop: 20 }}>
            <h3>📋 Výsledky zpracovaných zpráv</h3>
            <table style={{ width: '100%', marginTop: 10 }}>
              <thead>
                <tr>
                  <th>Společnost</th>
                  <th>Datum</th>
                  <th>Hodnocení</th>
                  <th>SELL</th>
                </tr>
              </thead>
              <tbody>
                {newsData.map((item, idx) => (
                  <tr key={idx}>
                    <td>{item.name}</td>
                    <td>{item.date}</td>
                    <td>{item.rating}</td>
                    <td>{item.sell === 1 ? '✅ Ano' : '❌ Ne'}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </div>
    </>
  );
}

export default App;
