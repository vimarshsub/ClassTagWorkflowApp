import React, { useState } from 'react';
import './App.css';

function App() {
  const [username, setUsername] = useState('');
  const [password, setPassword] = useState('');
  const [announcements, setAnnouncements] = useState([]);
  const [isLoading, setIsLoading] = useState(false);
  const [error, setError] = useState(null);
  const [isLoggedIn, setIsLoggedIn] = useState(false);

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
        // If data.error exists, use it, otherwise use a generic HTTP error
        const errorMessage = data && data.error ? data.error : `HTTP error! status: ${response.status}`;
        throw new Error(errorMessage);
      }
      
      // Assuming 'data' from backend is the announcements_content object which has an 'edges' array
      // Each edge has a 'node' which is the actual announcement
      setAnnouncements(data.edges && Array.isArray(data.edges) ? data.edges.map(edge => edge.node) : []);
      setIsLoggedIn(true);
      setError(null); // Clear any previous errors
    } catch (err) {
      console.error("Login/Fetch error:", err);
      setError(err.message || "Failed to login or fetch announcements. Please check credentials and backend.");
      setAnnouncements([]); // Clear announcements on error
      setIsLoggedIn(false);
    }
    setIsLoading(false);
  };

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

