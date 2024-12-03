import React, { useState } from 'react';

function App() {
  const [url, setUrl] = useState('');
  const [loading, setLoading] = useState(false);

  const handleUrlSubmit = (e) => {
    e.preventDefault();
    if (url) {
      setLoading(true);
      // 使用代理URL
      window.location.href = `http://localhost:5000/proxy?url=${encodeURIComponent(url)}`;
    }
  };

  return (
    <div className="container">
      <div className="url-input-section">
        <form onSubmit={handleUrlSubmit}>
          <input
            type="url"
            value={url}
            onChange={(e) => setUrl(e.target.value)}
            placeholder="请输入网页URL"
            required
          />
          <button type="submit">访问</button>
        </form>
      </div>
      {loading && <div className="loading">正在加载页面...</div>}
    </div>
  );
}

export default App; 