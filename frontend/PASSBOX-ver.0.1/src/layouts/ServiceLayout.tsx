// 로그인 후 서비스 화면에서 헤더·사이드바와 본문 영역을 함께 배치하는 레이아웃입니다.
import { Outlet } from 'react-router-dom'
import { useState } from 'react'
import { Header } from '../components/layout/Header'
import { Sidebar } from '../components/layout/Sidebar'

export function ServiceLayout() {
  const [isMenuOpen, setIsMenuOpen] = useState(false)
  const [isSidebarCollapsed, setIsSidebarCollapsed] = useState(false)

  const toggleMenu = () => {
    setIsMenuOpen((value) => !value)
    setIsSidebarCollapsed((value) => !value)
  }

  const closeMenu = () => {
    setIsMenuOpen(false)
    setIsSidebarCollapsed(false)
  }

  return <div className={`service-layout ${isSidebarCollapsed ? 'service-layout--sidebar-collapsed' : ''}`}>
    <Header isMenuOpen={isMenuOpen} onMenuToggle={toggleMenu} />
    <Sidebar isOpen={isMenuOpen} isCollapsed={isSidebarCollapsed} onNavigate={closeMenu} />
    {isMenuOpen && <button type="button" className="sidebar-backdrop" aria-label="메뉴 닫기" onClick={closeMenu} />}
    <main className="main-content"><Outlet /></main>
  </div>
}
