import { useState } from 'react'
import UploadForm from './components/UploadForm'
import ItemList from './components/ItemList'
import './App.css'

function App() {
  const [refreshItems, setRefreshItems] = useState(false)

  const handleUploadSuccess = () => {
    setRefreshItems(true)
  }

  const handleRefreshComplete = () => {
    setRefreshItems(false)
  }

  return (
    <div className="app">
      <header className="app-header">
        <h1>🧠 Synapse</h1>
        <p>Your intelligent second brain</p>
      </header>
      
      <main className="app-main">
        <div className="upload-section">
          <UploadForm onSuccess={handleUploadSuccess} />
        </div>
        
        <div className="items-section">
          <ItemList 
            refresh={refreshItems} 
            onRefreshComplete={handleRefreshComplete}
          />
        </div>
      </main>
    </div>
  )
}

export default App
