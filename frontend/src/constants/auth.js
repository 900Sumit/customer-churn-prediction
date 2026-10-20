const appOrigin = (import.meta.env.VITE_APP_URL || 'http://localhost:5173').replace(/\/$/, '')

export const authUrls = {
  origin: appOrigin,
  landing: `${appOrigin}/`,
  signIn: `${appOrigin}/sign-in`,
  signUp: `${appOrigin}/sign-up`,
  dashboard: `${appOrigin}/dashboard`,
}
