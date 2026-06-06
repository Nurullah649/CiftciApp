import React from 'react';
import { View, TouchableOpacity, Text, StyleSheet, Platform } from 'react-native';
import { BottomTabBarProps } from '@react-navigation/bottom-tabs';
import { Home, ScanLine, MessageCircle, Sprout } from 'lucide-react-native';
import { colors, radius, shadow, typography } from '../../theme';

const TABS = [
  { name: 'Dashboard', label: 'Ana Sayfa', Icon: Home },
  { name: 'Analysis', label: 'Analiz', Icon: ScanLine, center: true },
  { name: 'Chat', label: 'Asistan', Icon: MessageCircle },
] as const;

export function MainTabBar({ state, navigation }: BottomTabBarProps) {
  return (
    <View style={styles.bar}>
      {TABS.map((tab) => {
        const routeIndex = state.routes.findIndex((r) => r.name === tab.name);
        const focused = state.index === routeIndex;
        const { Icon } = tab;

        if (tab.center) {
          return (
            <TouchableOpacity
              key={tab.name}
              style={styles.fabWrap}
              onPress={() => navigation.navigate(tab.name)}
              activeOpacity={0.9}
            >
              <View style={[styles.fab, focused && styles.fabFocused]}>
                <ScanLine size={28} color={colors.textOnPrimary} strokeWidth={2.2} />
              </View>
              <Text style={[styles.fabLabel, focused && styles.labelFocused]}>{tab.label}</Text>
            </TouchableOpacity>
          );
        }

        return (
          <TouchableOpacity
            key={tab.name}
            style={styles.tab}
            onPress={() => navigation.navigate(tab.name)}
            activeOpacity={0.7}
          >
            <View style={[styles.iconWrap, focused && styles.iconWrapActive]}>
              <Icon size={22} color={focused ? colors.primary : colors.textMuted} />
            </View>
            <Text style={[styles.label, focused && styles.labelFocused]}>{tab.label}</Text>
          </TouchableOpacity>
        );
      })}
    </View>
  );
}

/** Splash branding */
export function SplashBrand() {
  return (
    <View style={splash.wrap}>
      <View style={splash.logo}>
        <Sprout size={40} color={colors.accent} />
      </View>
      <Text style={splash.title}>Çiftçi AI</Text>
      <Text style={splash.sub}>Akıllı tarım asistanınız</Text>
    </View>
  );
}

const styles = StyleSheet.create({
  bar: {
    flexDirection: 'row',
    alignItems: 'flex-end',
    justifyContent: 'space-around',
    backgroundColor: colors.surface,
    borderTopWidth: 1,
    borderTopColor: colors.borderLight,
    paddingTop: 10,
    paddingBottom: Platform.OS === 'ios' ? 28 : 14,
    paddingHorizontal: 8,
    ...shadow.tab,
  },
  tab: { flex: 1, alignItems: 'center', paddingBottom: 4 },
  iconWrap: {
    width: 44,
    height: 36,
    borderRadius: radius.sm,
    alignItems: 'center',
    justifyContent: 'center',
  },
  iconWrapActive: { backgroundColor: colors.primarySoft },
  label: { ...typography.caption, fontSize: 11, color: colors.textMuted, marginTop: 4 },
  labelFocused: { color: colors.primary, fontWeight: '700' },
  fabWrap: { flex: 1, alignItems: 'center', marginTop: -28 },
  fab: {
    width: 60,
    height: 60,
    borderRadius: 30,
    backgroundColor: colors.primary,
    alignItems: 'center',
    justifyContent: 'center',
    borderWidth: 4,
    borderColor: colors.surface,
    ...shadow.card,
  },
  fabFocused: { backgroundColor: colors.primaryDark },
  fabLabel: { ...typography.caption, fontSize: 11, color: colors.textMuted, marginTop: 6 },
});

const splash = StyleSheet.create({
  wrap: { alignItems: 'center' },
  logo: {
    width: 88,
    height: 88,
    borderRadius: 44,
    backgroundColor: colors.primaryDark,
    alignItems: 'center',
    justifyContent: 'center',
    marginBottom: 20,
    borderWidth: 3,
    borderColor: colors.accent,
  },
  title: { fontSize: 28, fontWeight: '800', color: colors.primaryDark, letterSpacing: -0.5 },
  sub: { fontSize: 15, color: colors.textSecondary, marginTop: 6 },
});
