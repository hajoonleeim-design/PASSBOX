// 사용자가 로그아웃 버튼으로 나간 직후인지 기억한다.
// 이 경우 보호 화면이 "로그인이 필요한 화면입니다" 안내와 복귀 주소를 로그인 화면에 붙이지 않아야 한다.
const WINDOW_MS = 3000
let loggedOutAt = 0

export function markLoggedOut(): void {
  loggedOutAt = Date.now()
}

export function wasJustLoggedOut(): boolean {
  return Date.now() - loggedOutAt < WINDOW_MS
}
