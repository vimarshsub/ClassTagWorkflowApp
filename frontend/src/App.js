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
  const [testDocuments, setTestDocuments] = useState([]);
  const [testLoading, setTestLoading] = useState(false);
  const [testError, setTestError] = useState(null);
  const [testMessage, setTestMessage] = useState('');

  const handleProceedToApp = () => {
    setCurrentView('mainApp');
  };

  const handleLogin = async (e) => {
    e.preventDefault();
    setIsLoading(true);
    setError(null);
    console.log("Attempting to login and fetch announcements with:", { username });

    try {
      console.log("=== FRONTEND DEBUG LOGS ===");
      console.log("1. Sending request to backend with credentials:", { username, password: "***" });
      const response = await fetch("http://localhost:5001/api/fetch-and-save-announcements", {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          'Accept': 'application/json',
          'Origin': 'http://localhost:3000'
        },
        body: JSON.stringify({ 
          username: username,
          password: password
        }),
      });

      console.log("2. Response status:", response.status);
      const data = await response.json();
      console.log("3. Raw response data:", data);
      console.log("4. Response data type:", typeof data);
      console.log("5. Response data keys:", Object.keys(data));

      if (!response.ok) {
        const errorMessage = data && data.error ? data.error : `HTTP error! status: ${response.status}`;
        throw new Error(errorMessage);
      }
      
      // Handle the response format from the backend
      if (data.announcements && Array.isArray(data.announcements)) {
        console.log("6. Found announcements array with length:", data.announcements.length);
        console.log("7. First announcement:", data.announcements[0]);
        setAnnouncements(data.announcements);
      } else if (data.edges && Array.isArray(data.edges)) {
        console.log("6. Found edges array with length:", data.edges.length);
        const announcements = data.edges.map(edge => edge.node);
        console.log("7. Processed announcements:", announcements);
        setAnnouncements(announcements);
      } else if (data.message) {
        console.log("6. No announcements found:", data.message);
        setAnnouncements([]);
      } else {
        console.log("6. Unexpected response format:", data);
        setAnnouncements([]);
      }
      console.log("=== END OF FRONTEND DEBUG LOGS ===");
      setIsLoggedIn(true);
      setError(null);
    } catch (err) {
      console.error("=== ERROR IN FRONTEND ===");
      console.error("Error details:", err);
      console.error("Error message:", err.message);
      console.error("=== END OF ERROR LOGS ===");
      setError(err.message || "Failed to login or fetch announcements. Please check credentials and backend.");
      setAnnouncements([]);
      setIsLoggedIn(false);
    }
    setIsLoading(false);
  };

  const handleTestDocuments = async () => {
    try {
      setTestLoading(true);
      setTestError(null);
      console.log('Starting document fetch test...');
      console.log('Using credentials:', { username, password });
      
      // Find the first announcement that has documents
      const announcementWithDocs = announcements.find(ann => ann.documentsCount > 0);
      
      if (!announcementWithDocs) {
        console.error('No announcements with documents found');
        setTestError('No announcements with documents found');
        return;
      }
      
      console.log('Selected announcement:', announcementWithDocs);
      const announcementId = announcementWithDocs.dbId;
      console.log('Selected announcement ID:', announcementId);
      
      console.log('Sending request to:', 'http://localhost:5001/api/test-fetch-documents');
      console.log('Request payload:', { 
        username, 
        password,
        announcementId 
      });
      
      const response = await fetch('http://localhost:5001/api/test-fetch-documents', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          'Accept': 'application/json',
        },
        body: JSON.stringify({ 
          username, 
          password,
          announcementId 
        })
      });

      console.log('Response status:', response.status);
      console.log('Response headers:', Object.fromEntries(response.headers.entries()));
      
      const responseText = await response.text();
      console.log('Raw response text:', responseText);
      
      if (!response.ok) {
        console.error('Error response:', responseText);
        throw new Error(`HTTP error! status: ${response.status}, message: ${responseText}`);
      }

      let data;
      try {
        data = JSON.parse(responseText);
        console.log('Parsed response data:', data);
      } catch (parseError) {
        console.error('Failed to parse response as JSON:', parseError);
        throw new Error(`Invalid JSON response: ${responseText}`);
      }
      
      if (data.error) {
        throw new Error(data.error);
      }

      setTestDocuments(data.documents || []);
      setTestMessage(data.message || 'No message received');
    } catch (error) {
      console.error('Error fetching documents:', error);
      console.error('Error stack:', error.stack);
      setTestError(error.message);
      setTestDocuments([]);
    } finally {
      setTestLoading(false);
    }
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
                name="username"
                autoComplete="tel"
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
                name="password"
                autoComplete="current-password"
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
            <div style={{marginBottom: '20px', padding: '10px', border: '1px solid #ccc'}}>
              <h3>Test Document Fetch</h3>
              <button 
                onClick={handleTestDocuments} 
                disabled={testLoading}
                style={{padding: '10px 20px', fontSize: '16px'}}
              >
                {testLoading ? 'Testing Document Fetch...' : 'Test Document Fetch'}
              </button>
              {testError && <p className="error" style={{color: 'red'}}>{testError}</p>}
              {testDocuments.length > 0 && (
                <div style={{marginTop: '10px'}}>
                  <h4>Test Documents Results:</h4>
                  <ul>
                    {testDocuments.map(doc => (
                      <li key={doc.id}>
                        {doc.fileFilename} ({doc.contentType})
                        <br/>
                        <a href={doc.fileUrl} target="_blank" rel="noopener noreferrer">
                          View Document
                        </a>
                      </li>
                    ))}
                  </ul>
                </div>
              )}
            </div>
            <h2>Announcements</h2>
            {isLoading && <p>Loading announcements...</p>}
            {error && <p className="error" style={{color: 'red'}}>{error}</p>}
            {announcements.length > 0 ? (
              announcements.map(ann => (
                <div key={ann.id} style={{border: '1px solid #ccc', margin: '10px', padding: '10px'}}>
                  <h3>{ann.title || "No Title"}</h3>
                  <div dangerouslySetInnerHTML={{ __html: ann.message || "No Message" }} />
                  <p><small>Sent by: User ID {ann.user && ann.user.id ? ann.user.id : "N/A"} on {ann.createdAt ? new Date(ann.createdAt).toLocaleDateString() : "N/A"}</small></p>
                  <p><small>Announcement ID: {ann.dbId || "N/A"}</small></p>
                  <p><small>Documents Count: {ann.documentsCount || 0}</small></p>
                  {ann.documents && ann.documents.length > 0 ? (
                    <div style={{marginTop: '10px', padding: '10px', backgroundColor: '#f0f0f0'}}>
                      <h4>📎 Attached Documents ({ann.documents.length}):</h4>
                      <ul style={{listStyle: 'none', padding: 0}}>
                        {ann.documents.map(doc => (
                          <li key={doc.id} style={{margin: '5px 0'}}>
                            <a href={doc.fileUrl} target="_blank" rel="noopener noreferrer" style={{color: 'blue', textDecoration: 'underline'}}>
                              📄 {doc.fileFilename} ({doc.contentType})
                            </a>
                          </li>
                        ))}
                      </ul>
                    </div>
                  ) : (
                    <p style={{color: '#666'}}>No documents attached</p>
                  )}
                  <div style={{marginTop: '10px', fontSize: '12px', color: '#666'}}>
                    <p>Debug Info:</p>
                    <pre style={{whiteSpace: 'pre-wrap', wordBreak: 'break-all'}}>
                      {JSON.stringify(ann, null, 2)}
                    </pre>
                  </div>
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

