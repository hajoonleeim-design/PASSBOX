import { createBrowserRouter, Navigate, RouterProvider } from 'react-router-dom'
import { AuthLayout } from '../layouts/AuthLayout'
import { ServiceLayout } from '../layouts/ServiceLayout'
import { LoginPage } from '../pages/auth/LoginPage'
import { LandingPage } from '../pages/marketing/LandingPage'
import { HomeShowroomPage } from '../pages/home/HomeShowroomPage'
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
import { ReviewQueuePage } from '../pages/reviews/ReviewQueuePage'
import { AccountPage } from '../pages/account/AccountPage'
import { ProtectedRoute } from './ProtectedRoute'

// URL과 화면 컴포넌트를 연결하는 라우터 설정입니다.
// '/'는 로그인 여부와 관계없이 누구나 보는 공개 랜딩페이지이고,
// 로그인한 사용자의 실제 작업 화면은 /home 아래(ProtectedRoute)에 있습니다.
const router = createBrowserRouter([
  { path: '/', element: <LandingPage /> },
  { element: <AuthLayout />, children: [{ path: '/login', element: <LoginPage /> }] },
  {
    element: <ProtectedRoute />,
    children: [{
      element: <ServiceLayout />,
      children: [
        { path: '/home', element: <HomeShowroomPage /> },
        { path: '/upload', element: <UploadPage /> },
        { path: '/analysis/recent', element: <AnalysisJobsPage /> },
        { path: '/analysis/:jobId', element: <AnalysisPage /> },
        { path: '/result/:requestId', element: <ResultPage /> },
        { path: '/chat', element: <ChatPage /> },
        { path: '/chat/:requestId', element: <ChatPage /> },
        { path: '/audit', element: <AuditPage /> },
        { path: '/audit/:requestId', element: <AuditPage /> },
        { path: '/admin/policy', element: <PolicyPage /> },
        { path: '/admin/policy/:policyId', element: <PolicyPage /> },
        { path: '/dashboard', element: <OperationsDashboardPage /> },
        { path: '/dashboard/:scenario', element: <OperationsDashboardPage /> },
        { path: '/support', element: <SupportPage /> },
        { path: '/support/:scenario', element: <SupportPage /> },
        { path: '/approvals', element: <ApprovalPage /> },
        { path: '/reviews', element: <ReviewQueuePage /> },
        { path: '/account', element: <AccountPage /> },
      ],
    }],
  },
  { path: '*', element: <Navigate to="/" replace /> },
])

export function AppRouter() { return <RouterProvider router={router} /> }
