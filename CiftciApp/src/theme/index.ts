/** Çiftçi AI — tasarım sistemi (tarla + agritech) */
export const colors = {
  bg: '#F4EFE4',
  bgDeep: '#E8E0D0',
  surface: '#FFFFFF',
  surfaceMuted: '#FAF7F2',

  primary: '#2D6A4F',
  primaryDark: '#1B4332',
  primaryLight: '#40916C',
  primarySoft: '#D8F3DC',

  accent: '#D4A373',
  accentDark: '#BC8A5F',
  accentSoft: '#FAEDCD',

  text: '#1B2E1F',
  textSecondary: '#5C6B5E',
  textMuted: '#8A968C',
  textOnPrimary: '#FFFFFF',
  textOnDark: '#F4EFE4',

  border: '#E2D9C8',
  borderLight: '#EDE6D6',

  healthy: '#40916C',
  warning: '#E9A319',
  critical: '#BC4749',

  chatUser: '#2D6A4F',
  chatAi: '#FFFFFF',
  overlay: 'rgba(27, 67, 50, 0.85)',
};

export const spacing = {
  xs: 4,
  sm: 8,
  md: 16,
  lg: 24,
  xl: 32,
  xxl: 48,
};

export const radius = {
  sm: 12,
  md: 18,
  lg: 24,
  xl: 32,
  full: 999,
};

export const typography = {
  hero: { fontSize: 32, fontWeight: '800' as const, letterSpacing: -1 },
  h1: { fontSize: 26, fontWeight: '800' as const, letterSpacing: -0.5 },
  h2: { fontSize: 20, fontWeight: '700' as const },
  h3: { fontSize: 17, fontWeight: '700' as const },
  body: { fontSize: 16, fontWeight: '500' as const, lineHeight: 24 },
  caption: { fontSize: 13, fontWeight: '500' as const, lineHeight: 18 },
  label: { fontSize: 12, fontWeight: '700' as const, letterSpacing: 0.8 },
};

export const shadow = {
  card: {
    shadowColor: '#1B4332',
    shadowOffset: { width: 0, height: 8 },
    shadowOpacity: 0.08,
    shadowRadius: 20,
    elevation: 4,
  },
  soft: {
    shadowColor: '#000',
    shadowOffset: { width: 0, height: 2 },
    shadowOpacity: 0.06,
    shadowRadius: 8,
    elevation: 2,
  },
  tab: {
    shadowColor: '#1B4332',
    shadowOffset: { width: 0, height: -4 },
    shadowOpacity: 0.06,
    shadowRadius: 12,
    elevation: 12,
  },
};

export function statusColor(status?: string): string {
  if (status === 'healthy') return colors.healthy;
  if (status === 'critical') return colors.critical;
  if (status === 'unknown') return colors.textMuted;
  return colors.warning;
}
