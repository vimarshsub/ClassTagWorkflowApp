import React, { useState } from 'react';
import './App.css';

function App() {
  const [username, setUsername] = useState('');
  const [password, setPassword] = useState('');
  const [announcements, setAnnouncements] = useState([]);
  const [isLoading, setIsLoading] = useState(false);
  const [error, setError] = useState(null);
  const [isLoggedIn, setIsLoggedIn] = useState(false);
  const [currentView, setCurrentView] = useState('initial'); // 'initial' or 'mainApp'

  const handleProceedToApp = () => {
    setCurrentView('mainApp');
  };

  const handleLogin = async (e) => {
    e.preventDefault();
    setIsLoading(true);
    setError(null);
    console.log("Attempting to login and fetch announcements with:", { username });

    try {
      const response = await fetch("https://dual-lorna-vimarshsub-a52bff93.koyeb.app/api/fetch-and-save-announcements", {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({ username, password }),
      });

      const data = await response.json();

      if (!response.ok) {
        const errorMessage = data && data.error ? data.error : `HTTP error! status: ${response.status}`;
        throw new Error(errorMessage);
      }
      
      setAnnouncements(data.edges && Array.isArray(data.edges) ? data.edges.map(edge => edge.node) : []);
      setIsLoggedIn(true);
      setError(null);
    } catch (err) {
      console.error("Login/Fetch error:", err);
      setError(err.message || "Failed to login or fetch announcements. Please check credentials and backend.");
      setAnnouncements([]);
      setIsLoggedIn(false);
    }
    setIsLoading(false);
  };

  if (currentView === 'initial') {
    return (
      <div className="App">
        <header className="App-header">
          <h1>Welcome to ClassTag Workflow</h1>
        </header>
        <main style={{ textAlign: 'center', marginTop: '50px' }}>
          <p>Click the button below to proceed to login and view announcements.</p>
          <button onClick={handleProceedToApp} style={{ padding: '10px 20px', fontSize: '16px' }}>
            Load Announcements
          </button>
        </main>
      </div>
    );
  }

  return (
    <div className="App">
      <header className="App-header">
        <h1>ClassTag Workflow Interface</h1>
      </header>
      <main>
        {!isLoggedIn ? (
          <form onSubmit={handleLogin}>
            <div>
              <label htmlFor="username">Username (Phone Number):</label>
              <input
                type="text"
                id="username"
                value={username}
                onChange={(e) => setUsername(e.target.value)}
                disabled={isLoading}
              />
            </div>
            <div>
              <label htmlFor="password">Password:</label>
              <input
                type="password"
                id="password"
                value={password}
                onChange={(e) => setPassword(e.target.value)}
                disabled={isLoading}
              />
            </div>
            <button type="submit" disabled={isLoading || !username || !password}>
              {isLoading ? 'Logging in...' : 'Login and Fetch Announcements'}
            </button>
            {error && <p className="error" style={{color: 'red'}}>{error}</p>}
          </form>
        ) : (
          <div>
            <p>Logged in as: {username}</p>
            <h2>Announcements</h2>
            {isLoading && <p>Loading announcements...</p>}
            {error && <p className="error" style={{color: 'red'}}>{error}</p>}
            {announcements.length > 0 ? (
              announcements.map(ann => (
                <div key={ann.id} style={{border: '1px solid #ccc', margin: '10px', padding: '10px'}}>
                  <h3>{ann.title || "No Title"}</h3>
                  <div dangerouslySetInnerHTML={{ __html: ann.message || "No Message" }} />
                  <p><small>Sent by: User ID {ann.user && ann.user.id ? ann.user.id : "N/A"} on {ann.createdAt ? new Date(ann.createdAt).toLocaleDateString() : "N/A"}</small></p>
                  <p><small>Documents: {ann.documentsCount}</small></p>
                </div>
              ))
            ) : (
              !isLoading && <p>No announcements found or returned.</p>
            )}
          </div>
        )}
      </main>
    </div>
  );
}

export default App;

