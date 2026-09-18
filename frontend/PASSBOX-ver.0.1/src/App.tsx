import { AuthProvider } from './stores/AuthContext'
import { AppRouter } from './router'

// 모든 화면이 로그인 정보(AuthContext)를 사용할 수 있도록 감싼 최상위 컴포넌트입니다.
export default function App() { return <AuthProvider><AppRouter /></AuthProvider> }
