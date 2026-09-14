import { StrictMode } from 'react'
import { createRoot } from 'react-dom/client'
import './theme.css'
import App from './App.jsx'
import { SesionProvider } from './hooks/useSesion.jsx'

createRoot(document.getElementById('root')).render(
  <StrictMode>
    <SesionProvider>
      <App />
    </SesionProvider>
  </StrictMode>,
)
