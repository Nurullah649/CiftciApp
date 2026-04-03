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
  Leaf,
  CalendarRange,
  MapPin,
  Bell,
  User,
  Map,
  Sparkles,
} from 'lucide-react-native';
import { SafeAreaView } from 'react-native-safe-area-context';
import * as Location from 'expo-location';
import * as Notifications from 'expo-notifications';
import * as Device from 'expo-device';
import Constants from 'expo-constants';
import { getWeatherData, savePushToken } from '../services/apiService';
import { WeatherData } from '../types';
import { theme } from '../theme/theme';

const FALLBACK_LAT = 37.167;
const FALLBACK_LON = 38.793;
const TAB_PAD = 118;

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
        lightColor: theme.tabActive,
      });
    }
  };

  useEffect(() => {
    fetchDashboardData();
    registerDeviceForPushNotifications();
  }, []);

  const tip =
    weather && weather.temp > 28
      ? 'Sıcaklık yüksek: sulamayı sabah/akşam kaydırmak buharlaşmayı azaltır.'
      : weather && weather.temp < 6
        ? 'Soğuk hava: don riskine karşı hassas ürünleri kontrol edin.'
        : 'Koşullar genelde uygun; rutin saha kontrollerine devam.';

  return (
    <SafeAreaView style={styles.root} edges={['top', 'left', 'right']}>
      <StatusBar barStyle="light-content" backgroundColor={theme.forest} />
      <ScrollView
        contentContainerStyle={{ paddingBottom: TAB_PAD }}
        refreshControl={
          <RefreshControl
            refreshing={refreshing}
            onRefresh={() => {
              setRefreshing(true);
              fetchDashboardData();
            }}
            tintColor={theme.forestLight}
          />
        }
        showsVerticalScrollIndicator={false}
      >
        <View style={styles.hero}>
          <View style={styles.heroAccent} />
          <View style={styles.heroTop}>
            <View style={{ flex: 1 }}>
              <Text style={styles.kicker}>ÇİFTÇİ ASİSTAN</Text>
              <Text style={styles.heroTitle}>Bugün tarlada</Text>
              <Text style={styles.heroDate}>
                {new Date().toLocaleDateString('tr-TR', { weekday: 'long', day: 'numeric', month: 'long' })}
              </Text>
            </View>
            <View style={styles.heroActions}>
              <TouchableOpacity onPress={() => navigation.navigate('Notifications')} style={styles.iconGhost}>
                <Bell size={20} color="#fff" />
              </TouchableOpacity>
              <TouchableOpacity onPress={() => navigation.navigate('Profile')} style={styles.iconGhost}>
                <User size={20} color="#fff" />
              </TouchableOpacity>
            </View>
          </View>

          <View style={styles.weatherCard}>
            {loading ? (
              <ActivityIndicator size="large" color={theme.tabActive} style={{ padding: 24 }} />
            ) : (
              <>
                <View style={styles.weatherTop}>
                  <View style={{ flex: 1 }}>
                    <View style={styles.locPill}>
                      <MapPin size={14} color={theme.tabActive} style={{ marginRight: 6 }} />
                      <Text style={styles.locText} numberOfLines={1}>
                        {weather?.location || 'Konum'}
                      </Text>
                    </View>
                    <Text style={styles.temp}>{weather?.temp ?? '—'}°</Text>
                    <Text style={styles.cond}>{weather?.condition || '—'}</Text>
                  </View>
                  <CloudSun size={72} color={theme.tabActive} style={{ opacity: 0.95 }} />
                </View>
                <View style={styles.stats}>
                  <View style={styles.stat}>
                    <Droplets size={18} color={theme.tabActive} />
                    <Text style={styles.statLab}>Nem</Text>
                    <Text style={styles.statVal}>%{weather?.humidity ?? '—'}</Text>
                  </View>
                  <View style={styles.statLine} />
                  <View style={styles.stat}>
                    <Wind size={18} color={theme.tabActive} />
                    <Text style={styles.statLab}>Rüzgâr</Text>
                    <Text style={styles.statVal}>{weather?.wind ?? '—'} km/s</Text>
                  </View>
                </View>
              </>
            )}
          </View>
        </View>

        <View style={styles.body}>
          <View style={styles.sectionHead}>
            <Sparkles size={18} color={theme.accent} />
            <Text style={styles.sectionTitle}>Hızlı erişim</Text>
          </View>
          <View style={styles.quickRow}>
            <TouchableOpacity style={styles.quick} onPress={() => navigation.navigate('Analysis')} activeOpacity={0.92}>
              <View style={[styles.quickIco, { backgroundColor: theme.chipSage }]}>
                <Leaf size={26} color={theme.forestLight} />
              </View>
              <Text style={styles.quickTxt}>Bitki incelemesi</Text>
            </TouchableOpacity>
            <TouchableOpacity style={styles.quick} onPress={() => navigation.navigate('Schedule')} activeOpacity={0.92}>
              <View style={[styles.quickIco, { backgroundColor: theme.chipAmber }]}>
                <CalendarRange size={26} color={theme.accentDark} />
              </View>
              <Text style={styles.quickTxt}>İş takvimi</Text>
            </TouchableOpacity>
            <TouchableOpacity style={styles.quick} onPress={() => navigation.navigate('Map')} activeOpacity={0.92}>
              <View style={[styles.quickIco, { backgroundColor: theme.chipMist }]}>
                <Map size={26} color={theme.info} />
              </View>
              <Text style={styles.quickTxt}>Harita</Text>
            </TouchableOpacity>
          </View>

          <Text style={styles.hintTitle}>Günün notu</Text>
          <View style={styles.hintCard}>
            <View style={styles.hintBar} />
            <Text style={styles.hintBody}>{tip}</Text>
          </View>
        </View>
      </ScrollView>
    </SafeAreaView>
  );
}

const styles = StyleSheet.create({
  root: { flex: 1, backgroundColor: theme.bg },
  hero: {
    backgroundColor: theme.forest,
    paddingBottom: 26,
    borderBottomLeftRadius: 32,
    borderBottomRightRadius: 32,
    overflow: 'hidden',
  },
  heroAccent: {
    position: 'absolute',
    top: -80,
    right: -60,
    width: 200,
    height: 200,
    borderRadius: 100,
    backgroundColor: 'rgba(13,148,136,0.15)',
  },
  heroTop: {
    flexDirection: 'row',
    paddingHorizontal: 22,
    paddingTop: 6,
    paddingBottom: 20,
    alignItems: 'flex-start',
  },
  kicker: {
    color: theme.tabActive,
    fontSize: 11,
    fontWeight: '900',
    letterSpacing: 2,
  },
  heroTitle: { color: '#fff', fontSize: 30, fontWeight: '900', marginTop: 8 },
  heroDate: { color: 'rgba(255,255,255,0.72)', fontSize: 14, marginTop: 8, textTransform: 'capitalize' },
  heroActions: { flexDirection: 'row', gap: 10 },
  iconGhost: {
    width: 46,
    height: 46,
    borderRadius: 15,
    borderWidth: 1,
    borderColor: 'rgba(255,255,255,0.25)',
    backgroundColor: 'rgba(255,255,255,0.08)',
    justifyContent: 'center',
    alignItems: 'center',
  },
  weatherCard: {
    marginHorizontal: 18,
    backgroundColor: 'rgba(255,255,255,0.07)',
    borderRadius: theme.radiusLg,
    padding: 20,
    borderWidth: 1,
    borderColor: 'rgba(255,255,255,0.12)',
  },
  weatherTop: { flexDirection: 'row', justifyContent: 'space-between', alignItems: 'flex-start', marginBottom: 18 },
  locPill: {
    flexDirection: 'row',
    alignItems: 'center',
    alignSelf: 'flex-start',
    backgroundColor: 'rgba(0,0,0,0.22)',
    paddingHorizontal: 12,
    paddingVertical: 7,
    borderRadius: 20,
    maxWidth: '100%',
  },
  locText: { color: '#fff', fontSize: 12, fontWeight: '700', flex: 1 },
  temp: { color: '#fff', fontSize: 54, fontWeight: '900', marginTop: 6 },
  cond: { color: 'rgba(255,255,255,0.88)', fontSize: 15, marginTop: -4 },
  stats: {
    flexDirection: 'row',
    backgroundColor: 'rgba(0,0,0,0.2)',
    borderRadius: theme.radiusMd,
    paddingVertical: 14,
    alignItems: 'center',
  },
  stat: { flex: 1, flexDirection: 'row', alignItems: 'center', gap: 10, justifyContent: 'center' },
  statLab: { color: 'rgba(255,255,255,0.65)', fontSize: 12 },
  statVal: { color: '#fff', fontWeight: '800', fontSize: 15 },
  statLine: { width: 1, height: 28, backgroundColor: 'rgba(255,255,255,0.18)' },
  body: { paddingHorizontal: 20, paddingTop: 26 },
  sectionHead: { flexDirection: 'row', alignItems: 'center', gap: 8, marginBottom: 14 },
  sectionTitle: { fontSize: 18, fontWeight: '800', color: theme.ink },
  quickRow: { flexDirection: 'row', flexWrap: 'wrap', gap: 12 },
  quick: {
    width: '30.5%',
    flexGrow: 1,
    minWidth: 104,
    backgroundColor: theme.surface,
    borderRadius: theme.radiusMd,
    paddingVertical: 16,
    paddingHorizontal: 8,
    alignItems: 'center',
    borderWidth: 1,
    borderColor: theme.border,
    shadowColor: theme.shadow,
    shadowOffset: { width: 0, height: 4 },
    shadowOpacity: 1,
    shadowRadius: 14,
    elevation: 3,
  },
  quickIco: {
    width: 54,
    height: 54,
    borderRadius: 16,
    justifyContent: 'center',
    alignItems: 'center',
    marginBottom: 10,
  },
  quickTxt: { fontSize: 11, fontWeight: '800', color: theme.ink, textAlign: 'center' },
  hintTitle: { fontSize: 18, fontWeight: '800', color: theme.ink, marginTop: 28, marginBottom: 12 },
  hintCard: {
    flexDirection: 'row',
    backgroundColor: theme.surface,
    borderRadius: theme.radiusMd,
    borderWidth: 1,
    borderColor: theme.border,
    overflow: 'hidden',
  },
  hintBar: { width: 5, backgroundColor: theme.forestLight },
  hintBody: { flex: 1, padding: 18, color: theme.inkSecondary, fontSize: 14, lineHeight: 22 },
});
