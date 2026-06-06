import React, { useEffect, useState } from 'react';
import {
  View,
  Text,
  StyleSheet,
  ScrollView,
  TouchableOpacity,
  ActivityIndicator,
  RefreshControl,
  Platform,
  StatusBar,
} from 'react-native';
import {
  CloudSun,
  Droplets,
  Wind,
  ScanLine,
  Calendar,
  MapPin,
  Bell,
  User,
  Map,
  Sparkles,
  ChevronRight,
  Leaf,
} from 'lucide-react-native';
import * as Location from 'expo-location';
import * as Notifications from 'expo-notifications';
import * as Device from 'expo-device';
import Constants from 'expo-constants';
import { Screen } from '../components/ui/Screen';
import { getWeatherData, savePushToken } from '../services/apiService';
import { WeatherData } from '../types';
import { colors, spacing, radius, typography, shadow } from '../theme';

function greeting(): string {
  const h = new Date().getHours();
  if (h < 12) return 'Günaydın';
  if (h < 18) return 'İyi günler';
  return 'İyi akşamlar';
}

export default function DashboardScreen({ navigation }: any) {
  const [weather, setWeather] = useState<WeatherData | null>(null);
  const [loading, setLoading] = useState(true);
  const [refreshing, setRefreshing] = useState(false);

  const fetchDashboardData = async () => {
    try {
      const { status } = await Location.requestForegroundPermissionsAsync();
      if (status !== 'granted') return;
      const location = await Location.getCurrentPositionAsync({
        accuracy: Location.Accuracy.Balanced,
      });
      const data = await getWeatherData(location.coords.latitude, location.coords.longitude);
      setWeather(data);
    } catch (e) {
      console.error('Dashboard:', e);
    } finally {
      setLoading(false);
      setRefreshing(false);
    }
  };

  const registerPush = async () => {
    if (!Device.isDevice) return;
    try {
      const { status: existing } = await Notifications.getPermissionsAsync();
      let finalStatus = existing;
      if (existing !== 'granted') {
        const { status } = await Notifications.requestPermissionsAsync();
        finalStatus = status;
      }
      if (finalStatus !== 'granted') return;
      const projectId =
        Constants.expoConfig?.extra?.eas?.projectId ??
        Constants.easConfig?.projectId ??
        'f18467ff-fc40-4c69-9e71-e47056d31b33';
      const tokenData = await Notifications.getExpoPushTokenAsync({ projectId });
      await savePushToken(tokenData.data);
    } catch (e) {
      console.log('Push:', e);
    }
    if (Platform.OS === 'android') {
      await Notifications.setNotificationChannelAsync('default', {
        name: 'Çiftçi AI',
        importance: Notifications.AndroidImportance.MAX,
      });
    }
  };

  useEffect(() => {
    fetchDashboardData();
    registerPush();
  }, []);

  const tip =
    weather && weather.temp > 28
      ? 'Sıcaklık yüksek. Sulama aralığını gözden geçirin.'
      : weather && weather.temp < 5
        ? 'Don riski. Hassas bitkileri koruyun.'
        : 'Koşullar normal. Düzenli saha kontrolü önerilir.';

  return (
    <Screen>
      <StatusBar barStyle="dark-content" backgroundColor={colors.bg} />
      <ScrollView
        showsVerticalScrollIndicator={false}
        contentContainerStyle={styles.scroll}
        refreshControl={
          <RefreshControl refreshing={refreshing} onRefresh={() => { setRefreshing(true); fetchDashboardData(); }} colors={[colors.primary]} />
        }
      >
        <View style={styles.topRow}>
          <View>
            <Text style={styles.greet}>{greeting()}</Text>
            <Text style={styles.brand}>Çiftçi AI</Text>
            <Text style={styles.date}>
              {new Date().toLocaleDateString('tr-TR', { weekday: 'long', day: 'numeric', month: 'long' })}
            </Text>
          </View>
          <View style={styles.topActions}>
            <TouchableOpacity style={styles.iconBtn} onPress={() => navigation.navigate('Notifications')}>
              <Bell size={20} color={colors.text} />
            </TouchableOpacity>
            <TouchableOpacity style={styles.iconBtn} onPress={() => navigation.navigate('Profile')}>
              <User size={20} color={colors.text} />
            </TouchableOpacity>
          </View>
        </View>

        <View style={styles.weatherHero}>
          <View style={styles.weatherGlow} />
          {loading ? (
            <ActivityIndicator color={colors.accent} size="large" style={{ padding: 40 }} />
          ) : (
            <>
              <View style={styles.weatherRow}>
                <View style={{ flex: 1 }}>
                  <View style={styles.locPill}>
                    <MapPin size={12} color={colors.accentSoft} />
                    <Text style={styles.locText}>{weather?.location || 'Konum alınıyor…'}</Text>
                  </View>
                  <Text style={styles.temp}>{weather?.temp ?? '—'}°</Text>
                  <Text style={styles.cond}>{weather?.condition || '—'}</Text>
                </View>
                <CloudSun size={72} color={colors.accent} strokeWidth={1.5} />
              </View>
              <View style={styles.stats}>
                <View style={styles.stat}>
                  <Droplets size={18} color={colors.accentSoft} />
                  <Text style={styles.statVal}>%{weather?.humidity ?? '—'}</Text>
                  <Text style={styles.statLbl}>Nem</Text>
                </View>
                <View style={styles.statDivider} />
                <View style={styles.stat}>
                  <Wind size={18} color={colors.accentSoft} />
                  <Text style={styles.statVal}>{weather?.wind ?? '—'}</Text>
                  <Text style={styles.statLbl}>km/s rüzgâr</Text>
                </View>
              </View>
            </>
          )}
        </View>

        <TouchableOpacity
          style={styles.heroCta}
          onPress={() => navigation.navigate('Analysis')}
          activeOpacity={0.92}
        >
          <View style={styles.heroCtaIcon}>
            <ScanLine size={28} color={colors.textOnPrimary} />
          </View>
          <View style={{ flex: 1 }}>
            <Text style={styles.heroCtaTitle}>Yaprak Teşhisi</Text>
            <Text style={styles.heroCtaSub}>Fotoğraf çek → AI hastalık analizi</Text>
          </View>
          <ChevronRight size={22} color={colors.accentSoft} />
        </TouchableOpacity>

        <Text style={styles.sectionLabel}>ARAÇLAR</Text>
        <View style={styles.toolsRow}>
          <TouchableOpacity style={styles.toolCard} onPress={() => navigation.navigate('Schedule')}>
            <View style={[styles.toolIcon, { backgroundColor: colors.accentSoft }]}>
              <Calendar size={22} color={colors.accentDark} />
            </View>
            <Text style={styles.toolText}>Planlama</Text>
          </TouchableOpacity>
          <TouchableOpacity style={styles.toolCard} onPress={() => navigation.navigate('Map')}>
            <View style={[styles.toolIcon, { backgroundColor: colors.primarySoft }]}>
              <Map size={22} color={colors.primary} />
            </View>
            <Text style={styles.toolText}>Harita</Text>
          </TouchableOpacity>
          <TouchableOpacity style={styles.toolCard} onPress={() => navigation.navigate('Chat')}>
            <View style={[styles.toolIcon, { backgroundColor: '#E8F4F8' }]}>
              <Sparkles size={22} color={colors.primaryDark} />
            </View>
            <Text style={styles.toolText}>Asistan</Text>
          </TouchableOpacity>
        </View>

        <View style={styles.tipCard}>
          <View style={styles.tipIcon}>
            <Leaf size={22} color={colors.primary} />
          </View>
          <View style={{ flex: 1 }}>
            <Text style={styles.tipTitle}>Saha notu</Text>
            <Text style={styles.tipBody}>{tip}</Text>
          </View>
        </View>
      </ScrollView>
    </Screen>
  );
}

const styles = StyleSheet.create({
  scroll: { paddingBottom: 110, paddingHorizontal: spacing.lg },
  topRow: {
    flexDirection: 'row',
    justifyContent: 'space-between',
    alignItems: 'flex-start',
    paddingTop: spacing.md,
    marginBottom: spacing.lg,
  },
  greet: { ...typography.caption, color: colors.textSecondary, textTransform: 'uppercase' },
  brand: { ...typography.hero, fontSize: 28, color: colors.primaryDark, marginTop: 2 },
  date: { ...typography.caption, color: colors.textMuted, marginTop: 4, textTransform: 'capitalize' },
  topActions: { flexDirection: 'row', gap: 10 },
  iconBtn: {
    width: 44,
    height: 44,
    borderRadius: 22,
    backgroundColor: colors.surface,
    alignItems: 'center',
    justifyContent: 'center',
    borderWidth: 1,
    borderColor: colors.borderLight,
    ...shadow.soft,
  },
  weatherHero: {
    backgroundColor: colors.primaryDark,
    borderRadius: radius.xl,
    padding: spacing.lg,
    overflow: 'hidden',
    marginBottom: spacing.md,
    ...shadow.card,
  },
  weatherGlow: {
    position: 'absolute',
    top: -40,
    right: -40,
    width: 140,
    height: 140,
    borderRadius: 70,
    backgroundColor: colors.primaryLight,
    opacity: 0.35,
  },
  weatherRow: { flexDirection: 'row', alignItems: 'flex-start' },
  locPill: {
    flexDirection: 'row',
    alignItems: 'center',
    gap: 6,
    backgroundColor: 'rgba(255,255,255,0.12)',
    paddingHorizontal: 12,
    paddingVertical: 6,
    borderRadius: radius.full,
    alignSelf: 'flex-start',
    marginBottom: 10,
  },
  locText: { color: colors.textOnDark, fontSize: 12, fontWeight: '600' },
  temp: { fontSize: 52, fontWeight: '800', color: colors.textOnPrimary, letterSpacing: -2 },
  cond: { color: colors.accentSoft, fontSize: 16, fontWeight: '600', marginTop: -4 },
  stats: {
    flexDirection: 'row',
    marginTop: spacing.lg,
    backgroundColor: 'rgba(0,0,0,0.15)',
    borderRadius: radius.lg,
    padding: spacing.md,
  },
  stat: { flex: 1, alignItems: 'center', gap: 4 },
  statVal: { color: colors.textOnPrimary, fontWeight: '800', fontSize: 16 },
  statLbl: { color: colors.accentSoft, fontSize: 11, fontWeight: '600' },
  statDivider: { width: 1, backgroundColor: 'rgba(255,255,255,0.2)' },
  heroCta: {
    flexDirection: 'row',
    alignItems: 'center',
    backgroundColor: colors.primary,
    borderRadius: radius.lg,
    padding: spacing.md,
    marginBottom: spacing.lg,
    gap: spacing.md,
    ...shadow.card,
  },
  heroCtaIcon: {
    width: 52,
    height: 52,
    borderRadius: 16,
    backgroundColor: 'rgba(255,255,255,0.15)',
    alignItems: 'center',
    justifyContent: 'center',
  },
  heroCtaTitle: { color: colors.textOnPrimary, fontSize: 18, fontWeight: '800' },
  heroCtaSub: { color: colors.primarySoft, fontSize: 13, marginTop: 2, fontWeight: '500' },
  sectionLabel: { ...typography.label, color: colors.textMuted, marginBottom: spacing.sm },
  toolsRow: { flexDirection: 'row', gap: 12, marginBottom: spacing.lg },
  toolCard: {
    flex: 1,
    backgroundColor: colors.surface,
    borderRadius: radius.lg,
    paddingVertical: spacing.md,
    alignItems: 'center',
    borderWidth: 1,
    borderColor: colors.borderLight,
    ...shadow.soft,
  },
  toolIcon: {
    width: 48,
    height: 48,
    borderRadius: 24,
    alignItems: 'center',
    justifyContent: 'center',
    marginBottom: 10,
  },
  toolText: { fontWeight: '700', color: colors.text, fontSize: 12 },
  tipCard: {
    flexDirection: 'row',
    backgroundColor: colors.surface,
    borderRadius: radius.lg,
    padding: spacing.md,
    gap: spacing.md,
    borderLeftWidth: 4,
    borderLeftColor: colors.accent,
    ...shadow.soft,
  },
  tipIcon: {
    width: 44,
    height: 44,
    borderRadius: 12,
    backgroundColor: colors.primarySoft,
    alignItems: 'center',
    justifyContent: 'center',
  },
  tipTitle: { ...typography.h3, color: colors.primaryDark },
  tipBody: { ...typography.caption, color: colors.textSecondary, marginTop: 4 },
});
