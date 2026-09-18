import { StrictMode } from 'react'
import { createRoot } from 'react-dom/client'
import './index.css'
import App from './App.tsx'

// React 앱을 HTML의 #root 요소에 연결하는 시작 지점입니다.
// StrictMode는 개발 중 의도치 않은 부작용을 더 빨리 찾도록 도와줍니다.
createRoot(document.getElementById('root')!).render(
  <StrictMode>
    <App />
  </StrictMode>,
)
