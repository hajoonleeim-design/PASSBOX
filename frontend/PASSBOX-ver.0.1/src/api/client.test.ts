import { afterEach, describe, expect, it } from 'vitest'
import { getAccessToken, getApiErrorCode, setAccessToken } from './client'

afterEach(() => {
  setAccessToken(null)
})

describe('getApiErrorCode', () => {
  it('서버가 code를 주면 그대로 쓴다', () => {
    expect(getApiErrorCode({ code: 'POLICY_BLOCKED' })).toBe('POLICY_BLOCKED')
  })

  it('401은 UNAUTHORIZED로 매핑한다', () => {
    expect(getApiErrorCode({ status: 401 })).toBe('UNAUTHORIZED')
  })

  it('403은 FORBIDDEN으로 매핑한다', () => {
    expect(getApiErrorCode({ status: 403 })).toBe('FORBIDDEN')
  })

  it('404는 NOT_FOUND로 매핑한다', () => {
    expect(getApiErrorCode({ status: 404 })).toBe('NOT_FOUND')
  })

  it('그 외 status는 HTTP_ 접두어로 매핑한다', () => {
    expect(getApiErrorCode({ status: 500 })).toBe('HTTP_500')
  })

  it('status도 code도 없으면 undefined를 준다', () => {
    expect(getApiErrorCode({})).toBeUndefined()
    expect(getApiErrorCode(null)).toBeUndefined()
    expect(getApiErrorCode('not an object')).toBeUndefined()
  })
})

describe('access token storage', () => {
  it('토큰을 설정하면 sessionStorage에 저장되고 다시 읽힌다', () => {
    setAccessToken('token-123')
    expect(getAccessToken()).toBe('token-123')
    expect(window.sessionStorage.getItem('passbox_access_token')).toBe('token-123')
  })

  it('null을 설정하면 sessionStorage에서 제거된다', () => {
    setAccessToken('token-123')
    setAccessToken(null)
    expect(getAccessToken()).toBeNull()
    expect(window.sessionStorage.getItem('passbox_access_token')).toBeNull()
  })
})
