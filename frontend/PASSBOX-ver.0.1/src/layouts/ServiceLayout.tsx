// 로그인 후 서비스 화면에서 헤더·사이드바와 본문 영역을 함께 배치하는 레이아웃입니다.
import { Outlet } from 'react-router-dom'
import { useState } from 'react'
import { Header } from '../components/layout/Header'
import { Sidebar } from '../components/layout/Sidebar'

export function ServiceLayout() { const [isMenuOpen, setIsMenuOpen] = useState(false); return <div className="service-layout"><Header onMenuToggle={() => setIsMenuOpen((value) => !value)} /><Sidebar isOpen={isMenuOpen} onNavigate={() => setIsMenuOpen(false)} /><main className="main-content"><Outlet /></main></div> }
