import React, { useEffect, useState } from 'react';
import {
  ActivityIndicator,
  Platform,
  RefreshControl,
  ScrollView,
  StatusBar,
  StyleSheet,
  Text,
  TouchableOpacity,
  View,
} from 'react-native';
import {
  Bell,
  Bot,
  CalendarRange,
  CloudSun,
  Droplets,
  Leaf,
  Map,
  MapPin,
  User,
  Wind,
} from 'lucide-react-native';
import { SafeAreaView } from 'react-native-safe-area-context';
import * as Device from 'expo-device';
import * as Location from 'expo-location';
import * as Notifications from 'expo-notifications';
import Constants from 'expo-constants';
import { getWeatherData, savePushToken } from '../services/apiService';
import { WeatherData } from '../types';
import { theme } from '../theme/theme';
import { AmbientBackdrop } from '../components/AmbientBackdrop';

const FALLBACK_LAT = 37.167;
const FALLBACK_LON = 38.793;
const TAB_PAD = 120;

export default function DashboardScreen({ navigation }: any) {
  const [weather, setWeather] = useState<WeatherData | null>(null);
  const [loading, setLoading] = useState(true);
  const [refreshing, setRefreshing] = useState(false);

  const fetchDashboardData = async () => {
    try {
      let lat = FALLBACK_LAT;
      let lon = FALLBACK_LON;
      const { status } = await Location.requestForegroundPermissionsAsync();
      if (status === 'granted') {
        const loc = await Location.getCurrentPositionAsync({ accuracy: Location.Accuracy.Balanced });
        lat = loc.coords.latitude;
        lon = loc.coords.longitude;
      }
      const data = await getWeatherData(lat, lon);
      setWeather(data);
    } catch (e) {
      console.error('Dashboard:', e);
    } finally {
      setLoading(false);
      setRefreshing(false);
    }
  };

  const registerDeviceForPushNotifications = async () => {
    if (!Device.isDevice) return;
    try {
      const { status: existingStatus } = await Notifications.getPermissionsAsync();
      let finalStatus = existingStatus;
      if (existingStatus !== 'granted') {
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
      console.log('Push token:', e);
    }
    if (Platform.OS === 'android') {
      await Notifications.setNotificationChannelAsync('default', {
        name: 'default',
        importance: Notifications.AndroidImportance.MAX,
        vibrationPattern: [0, 250, 250, 250],
        lightColor: theme.accent,
      });
    }
  };

  useEffect(() => {
    fetchDashboardData();
    registerDeviceForPushNotifications();
  }, []);

  const note =
    weather && weather.temp > 28
      ? 'Sıcaklık yüksek. Sulamayı günün serin saatlerine kaydırmak verimlidir.'
      : weather && weather.temp < 6
        ? 'Düşük sıcaklık var. Hassas bitkilerde don stresi ihtimalini kontrol edin.'
        : 'Hava dengeli görünüyor. Bugün rutin saha kontrolü yeterli olabilir.';

  const quickLinks = [
    { key: 'analysis', title: 'Bitki analizi', text: 'Fotoğrafla inceleme başlat', icon: Leaf, screen: 'Analysis' },
    { key: 'chat', title: 'Asistan', text: 'Tarla sorularını yaz', icon: Bot, screen: 'Chat' },
    { key: 'schedule', title: 'Takvim', text: 'Görevleri yönet', icon: CalendarRange, screen: 'Schedule' },
    { key: 'map', title: 'Harita', text: 'Parsel görünümü aç', icon: Map, screen: 'Map' },
  ];

  return (
    <SafeAreaView style={styles.root} edges={['top', 'left', 'right']}>
      <StatusBar barStyle="dark-content" backgroundColor={theme.bg} />
      <AmbientBackdrop />

      <ScrollView
        contentContainerStyle={{ padding: 20, paddingBottom: TAB_PAD }}
        refreshControl={
          <RefreshControl
            refreshing={refreshing}
            onRefresh={() => {
              setRefreshing(true);
              fetchDashboardData();
            }}
            tintColor={theme.accent}
          />
        }
        showsVerticalScrollIndicator={false}
      >
        <View style={styles.topRow}>
          <View>
            <Text style={styles.topEyebrow}>OPERASYON MERKEZİ</Text>
            <Text style={styles.topTitle}>Bugün tarlada ne oluyor?</Text>
          </View>
          <View style={styles.topActions}>
            <TouchableOpacity onPress={() => navigation.navigate('Notifications')} style={styles.iconButton}>
              <Bell size={18} color={theme.ink} />
            </TouchableOpacity>
            <TouchableOpacity onPress={() => navigation.navigate('Profile')} style={styles.iconButton}>
              <User size={18} color={theme.ink} />
            </TouchableOpacity>
          </View>
        </View>

        <View style={styles.weatherCard}>
          {loading ? (
            <View style={styles.weatherLoading}>
              <ActivityIndicator size="large" color={theme.accent} />
            </View>
          ) : (
            <>
              <View style={styles.weatherTop}>
                <View style={{ flex: 1 }}>
                  <View style={styles.locationChip}>
                    <MapPin size={14} color={theme.accent} />
                    <Text style={styles.locationText} numberOfLines={1}>
                      {weather?.location || 'Konum alınamadı'}
                    </Text>
                  </View>
                  <Text style={styles.temperature}>{weather?.temp ?? '—'}°</Text>
                  <Text style={styles.condition}>{weather?.condition || 'Veri yok'}</Text>
                </View>
                <View style={styles.weatherIconWrap}>
                  <CloudSun size={34} color={theme.accent} />
                </View>
              </View>

              <View style={styles.metricRow}>
                <View style={styles.metricCard}>
                  <Droplets size={18} color={theme.accent} />
                  <Text style={styles.metricLabel}>Nem</Text>
                  <Text style={styles.metricValue}>%{weather?.humidity ?? '—'}</Text>
                </View>
                <View style={styles.metricCard}>
                  <Wind size={18} color={theme.accent} />
                  <Text style={styles.metricLabel}>Rüzgar</Text>
                  <Text style={styles.metricValue}>{weather?.wind ?? '—'} km/s</Text>
                </View>
              </View>
            </>
          )}
        </View>

        <View style={styles.section}>
          <Text style={styles.sectionTitle}>Hızlı işlemler</Text>
          <View style={styles.quickGrid}>
            {quickLinks.map((item) => {
              const Icon = item.icon;
              return (
                <TouchableOpacity
                  key={item.key}
                  style={styles.quickCard}
                  onPress={() => navigation.navigate(item.screen)}
                  activeOpacity={0.88}
                >
                  <View style={styles.quickIcon}>
                    <Icon size={20} color={theme.accent} />
                  </View>
                  <Text style={styles.quickTitle}>{item.title}</Text>
                  <Text style={styles.quickText}>{item.text}</Text>
                </TouchableOpacity>
              );
            })}
          </View>
        </View>

        <View style={styles.noteCard}>
          <Text style={styles.noteEyebrow}>GÜNÜN NOTU</Text>
          <Text style={styles.noteTitle}>Bugünkü saha önerisi</Text>
          <Text style={styles.noteBody}>{note}</Text>
        </View>
      </ScrollView>
    </SafeAreaView>
  );
}

const styles = StyleSheet.create({
  root: { flex: 1, backgroundColor: theme.bg },
  topRow: { flexDirection: 'row', justifyContent: 'space-between', alignItems: 'flex-start', marginBottom: 18 },
  topEyebrow: { color: theme.muted, fontSize: 11, fontWeight: '900', letterSpacing: 1.2 },
  topTitle: { color: theme.ink, fontSize: 30, lineHeight: 34, fontWeight: '900', marginTop: 10, maxWidth: 240 },
  topActions: { flexDirection: 'row', gap: 10 },
  iconButton: {
    width: 44,
    height: 44,
    borderRadius: 16,
    backgroundColor: theme.surface,
    borderWidth: 1,
    borderColor: theme.border,
    justifyContent: 'center',
    alignItems: 'center',
  },
  weatherCard: {
    backgroundColor: theme.surface,
    borderRadius: theme.radiusXl,
    padding: 18,
    borderWidth: 1,
    borderColor: theme.border,
    marginBottom: 18,
  },
  weatherLoading: { paddingVertical: 46 },
  weatherTop: { flexDirection: 'row', alignItems: 'center', gap: 16 },
  locationChip: {
    alignSelf: 'flex-start',
    flexDirection: 'row',
    alignItems: 'center',
    gap: 6,
    paddingHorizontal: 12,
    paddingVertical: 8,
    borderRadius: 999,
    backgroundColor: theme.accentSoft,
  },
  locationText: { color: theme.accent, fontSize: 13, fontWeight: '700', maxWidth: 190 },
  temperature: { color: theme.ink, fontSize: 48, fontWeight: '900', marginTop: 14 },
  condition: { color: theme.inkSoft, fontSize: 16, marginTop: 4 },
  weatherIconWrap: {
    width: 68,
    height: 68,
    borderRadius: 22,
    backgroundColor: theme.surfaceStrong,
    justifyContent: 'center',
    alignItems: 'center',
  },
  metricRow: { flexDirection: 'row', gap: 12, marginTop: 18 },
  metricCard: {
    flex: 1,
    backgroundColor: theme.surfaceMuted,
    borderRadius: theme.radiusLg,
    padding: 14,
  },
  metricLabel: { color: theme.muted, fontSize: 12, marginTop: 10 },
  metricValue: { color: theme.ink, fontSize: 18, fontWeight: '900', marginTop: 6 },
  section: { marginBottom: 18 },
  sectionTitle: { color: theme.ink, fontSize: 22, fontWeight: '900', marginBottom: 12 },
  quickGrid: { flexDirection: 'row', flexWrap: 'wrap', gap: 12 },
  quickCard: {
    width: '48%',
    backgroundColor: theme.surface,
    borderRadius: theme.radiusLg,
    padding: 16,
    borderWidth: 1,
    borderColor: theme.border,
  },
  quickIcon: {
    width: 44,
    height: 44,
    borderRadius: 14,
    backgroundColor: theme.accentSoft,
    justifyContent: 'center',
    alignItems: 'center',
    marginBottom: 14,
  },
  quickTitle: { color: theme.ink, fontSize: 17, fontWeight: '900' },
  quickText: { color: theme.inkSoft, fontSize: 13, lineHeight: 19, marginTop: 8 },
  noteCard: {
    backgroundColor: theme.surface,
    borderRadius: theme.radiusXl,
    padding: 18,
    borderWidth: 1,
    borderColor: theme.border,
  },
  noteEyebrow: { color: theme.muted, fontSize: 11, fontWeight: '900', letterSpacing: 1.2 },
  noteTitle: { color: theme.ink, fontSize: 22, fontWeight: '900', marginTop: 10 },
  noteBody: { color: theme.inkSoft, fontSize: 15, lineHeight: 23, marginTop: 10 },
});
