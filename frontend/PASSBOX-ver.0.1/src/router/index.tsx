import { createBrowserRouter, Navigate, RouterProvider } from 'react-router-dom'
import { AuthLayout } from '../layouts/AuthLayout'
import { ServiceLayout } from '../layouts/ServiceLayout'
import { LoginPage } from '../pages/auth/LoginPage'
import { HomePage } from '../pages/home/HomePage'
import { UploadPage } from '../pages/upload/UploadPage'
import { ChatPage } from '../pages/chat/ChatPage'
import { AnalysisPage } from '../pages/analysis/AnalysisPage'
import { ResultPage } from '../pages/result/ResultPage'
import { AuditPage } from '../pages/audit/AuditPage'
import { PolicyPage } from '../pages/policy/PolicyPage'
import { OperationsDashboardPage } from '../pages/dashboard/OperationsDashboardPage'
import { SupportPage } from '../pages/support/SupportPage'
import { ApprovalPage } from '../pages/approvals/ApprovalPage'
import { ProtectedRoute } from './ProtectedRoute'

// URL과 화면 컴포넌트를 연결하는 표입니다.
// ProtectedRoute 아래의 화면은 로그인한 사용자만 들어갈 수 있습니다.
const router = createBrowserRouter([
  { element: <AuthLayout />, children: [{ path: '/login', element: <LoginPage /> }] },
  {
    element: <ProtectedRoute />,
    children: [{
      element: <ServiceLayout />,
      children: [
        { path: '/', element: <HomePage /> },
        { path: '/upload', element: <UploadPage /> },
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
      ],
    }],
  },
  { path: '*', element: <Navigate to="/" replace /> },
])

// 위에서 만든 라우터를 React 앱에 실제로 적용합니다.
export function AppRouter() { return <RouterProvider router={router} /> }
