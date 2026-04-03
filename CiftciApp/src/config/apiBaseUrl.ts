import { Platform } from 'react-native';
import Constants from 'expo-constants';

const PRODUCTION_API = 'https://ciftciapp.nurullahkurnaz.com';

function devBaseUrl(): string {
  const host = Platform.OS === 'android' ? '10.0.2.2' : 'localhost';
  return `http://${host}:8000`;
}

/**
 * Öncelik:
 * 1) EXPO_PUBLIC_API_URL (fiziksel cihaz / özel sunucu)
 * 2) Geliştirme: yerel FastAPI (app/main.py, port 8000)
 * 3) Release: app.json extra.apiUrl
 * 4) Release yedeği: üretim domain
 */
export function getApiBaseUrl(): string {
  const fromEnv = process.env.EXPO_PUBLIC_API_URL?.trim();
  if (fromEnv) return fromEnv.replace(/\/$/, '');

  if (__DEV__) return devBaseUrl();

  const extra = Constants.expoConfig?.extra as { apiUrl?: string } | undefined;
  if (extra?.apiUrl?.trim()) return extra.apiUrl.trim().replace(/\/$/, '');

  return PRODUCTION_API;
}
