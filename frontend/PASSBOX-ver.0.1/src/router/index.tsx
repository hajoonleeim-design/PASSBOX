import { createBrowserRouter, Navigate, RouterProvider } from 'react-router-dom'
import { AuthLayout } from '../layouts/AuthLayout'
import { ServiceLayout } from '../layouts/ServiceLayout'
import { LoginPage } from '../pages/auth/LoginPage'
import { HomePageRedesign } from '../pages/home/HomePageRedesign'
import { UploadPage } from '../pages/upload/UploadPage'
import { ChatPage } from '../pages/chat/ChatPage'
import { AnalysisPage } from '../pages/analysis/AnalysisPage'
import { AnalysisJobsPage } from '../pages/analysis/AnalysisJobsPage'
import { ResultPage } from '../pages/result/ResultPage'
import { AuditPage } from '../pages/audit/AuditPage'
import { PolicyPage } from '../pages/policy/PolicyPage'
import { OperationsDashboardPage } from '../pages/dashboard/OperationsDashboardPage'
import { SupportPage } from '../pages/support/SupportPage'
import { ApprovalPage } from '../pages/approvals/ApprovalPage'
import { AccountPage } from '../pages/account/AccountPage'
import { ProtectedRoute } from './ProtectedRoute'

// URL과 화면 컴포넌트를 연결하는 라우터 설정입니다.
// 쇼룸(HomePageRedesign)은 접근성을 위해 최상위 '/'로 제공되며,
// 보안 콘솔 내부 기능들은 ProtectedRoute를 거치도록 구성됩니다.
const router = createBrowserRouter([
  { element: <AuthLayout />, children: [{ path: '/login', element: <LoginPage /> }] },
  { path: '/', element: <HomePageRedesign /> },
  {
    element: <ProtectedRoute />,
    children: [{
      element: <ServiceLayout />,
      children: [
        { path: '/upload', element: <UploadPage /> },
        { path: '/analysis/recent', element: <AnalysisJobsPage /> },
        { path: '/analysis/:jobId', element: <AnalysisPage /> },
        { path: '/result/:requestId', element: <ResultPage /> },
        { path: '/chat', element: <ChatPage /> },
        { path: '/chat/:requestId', element: <ChatPage /> },
        { path: '/audit/:requestId', element: <AuditPage /> },
        { path: '/admin/policy', element: <PolicyPage /> },
        { path: '/admin/policy/:policyId', element: <PolicyPage /> },
        { path: '/dashboard', element: <OperationsDashboardPage /> },
        { path: '/dashboard/:scenario', element: <OperationsDashboardPage /> },
        { path: '/support', element: <SupportPage /> },
        { path: '/support/:scenario', element: <SupportPage /> },
        { path: '/approvals', element: <ApprovalPage /> },
        { path: '/account', element: <AccountPage /> },
      ],
    }],
  },
  { path: '*', element: <Navigate to="/" replace /> },
])

export function AppRouter() { return <RouterProvider router={router} /> }
