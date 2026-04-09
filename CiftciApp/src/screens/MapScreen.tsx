import React, { useEffect, useState } from 'react';
import { ActivityIndicator, Alert, Keyboard, SafeAreaView, StyleSheet, Text, TextInput, TouchableOpacity, View } from 'react-native';
import { SafeAreaView as SafeArea } from 'react-native-safe-area-context';
import { WebView } from 'react-native-webview';
import { Map as MapIcon, Navigation, Search } from 'lucide-react-native';
import * as Location from 'expo-location';
import { getMapHtml, getUserProfile } from '../services/apiService';
import { theme } from '../theme/theme';
import { StackHeader } from '../components/StackHeader';
import { AmbientBackdrop } from '../components/AmbientBackdrop';

export default function MapScreen({ navigation }: any) {
  const [city, setCity] = useState('');
  const [mapHtml, setMapHtml] = useState<string | null>(null);
  const [loading, setLoading] = useState(false);

  useEffect(() => {
    loadDefaultLocation();
  }, []);

  const loadDefaultLocation = async () => {
    try {
      const profile = await getUserProfile();
      if (profile.location) {
        setCity(profile.location);
        fetchMap(profile.location);
      }
    } catch {
      /* ignore */
    }
  };

  const fetchMap = async (locationName: string) => {
    if (!locationName.trim()) return;
    Keyboard.dismiss();
    setLoading(true);
    try {
      const html = await getMapHtml(locationName);
      setMapHtml(html);
    } catch {
      Alert.alert('Hata', 'Harita yüklenemedi.');
    } finally {
      setLoading(false);
    }
  };

  const handleCurrentLocation = async () => {
    setLoading(true);
    Keyboard.dismiss();
    try {
      const { status } = await Location.requestForegroundPermissionsAsync();
      if (status !== 'granted') {
        Alert.alert('İzin', 'Konum için izin gerekli.');
        setLoading(false);
        return;
      }

      const location = await Location.getCurrentPositionAsync({});
      const address = await Location.reverseGeocodeAsync({
        latitude: location.coords.latitude,
        longitude: location.coords.longitude,
      });

      if (address && address.length > 0) {
        const place = address[0];
        const locationName = place.subregion || place.city || place.region;
        if (locationName) {
          setCity(locationName);
          fetchMap(locationName);
        } else {
          Alert.alert('Hata', 'Konum adı bulunamadı.');
          setLoading(false);
        }
      }
    } catch {
      Alert.alert('Hata', 'GPS alınamadı.');
      setLoading(false);
    }
  };

  return (
    <SafeArea style={styles.safe} edges={['top']}>
      <AmbientBackdrop />
      <StackHeader title="Harita" eyebrow="PARSEL GÖRÜNÜMÜ" onBack={() => navigation.goBack()} />

      <View style={styles.content}>
        <View style={styles.searchCard}>
          <Text style={styles.searchTitle}>Konum seçin</Text>
          <Text style={styles.searchSub}>İl, ilçe veya mevcut profil konumu ile haritayı açabilirsiniz.</Text>

          <View style={styles.searchRow}>
            <View style={styles.inputWrap}>
              <TextInput
                style={styles.input}
                placeholder="İl / ilçe ara..."
                value={city}
                onChangeText={setCity}
                placeholderTextColor={theme.muted}
                onSubmitEditing={() => fetchMap(city)}
              />
            </View>
            <TouchableOpacity style={[styles.btn, styles.btnGps]} onPress={handleCurrentLocation} disabled={loading}>
              {loading ? <ActivityIndicator color="#fff" size="small" /> : <Navigation size={20} color="#fff" />}
            </TouchableOpacity>
            <TouchableOpacity style={[styles.btn, styles.btnSearch]} onPress={() => fetchMap(city)} disabled={loading}>
              <Search size={20} color="#fff" />
            </TouchableOpacity>
          </View>
        </View>

        <View style={styles.mapBox}>
          {mapHtml ? (
            <WebView
              originWhitelist={['*']}
              source={{ html: mapHtml }}
              style={styles.webview}
              startInLoadingState
              renderLoading={() => (
                <View style={styles.loadingOverlay}>
                  <ActivityIndicator size="large" color={theme.accent} />
                  <Text style={styles.loadingText}>Harita açılıyor...</Text>
                </View>
              )}
            />
          ) : (
            <View style={styles.placeholder}>
              <View style={styles.iconCircle}>
                <MapIcon size={42} color={theme.accent} />
              </View>
              <Text style={styles.placeholderTitle}>Harita hazır bekliyor</Text>
              <Text style={styles.placeholderText}>Yukarıdan bir bölge seçin veya GPS ile konum alın.</Text>
            </View>
          )}
        </View>
      </View>
    </SafeArea>
  );
}

const styles = StyleSheet.create({
  safe: { flex: 1, backgroundColor: theme.bg },
  content: { flex: 1, paddingHorizontal: 20, paddingBottom: 20 },
  searchCard: {
    backgroundColor: theme.surface,
    borderRadius: theme.radiusLg,
    padding: 16,
    borderWidth: 1,
    borderColor: theme.border,
    marginBottom: 14,
  },
  searchTitle: { color: theme.ink, fontSize: 20, fontWeight: '900' },
  searchSub: { color: theme.inkSoft, fontSize: 14, lineHeight: 20, marginTop: 8 },
  searchRow: { flexDirection: 'row', gap: 10, alignItems: 'center', marginTop: 14 },
  inputWrap: {
    flex: 1,
    backgroundColor: theme.surfaceMuted,
    borderRadius: theme.radiusMd,
    borderWidth: 1,
    borderColor: theme.border,
    height: 52,
    justifyContent: 'center',
  },
  input: { paddingHorizontal: 15, color: theme.ink, fontSize: 16, height: '100%' },
  btn: {
    width: 52,
    height: 52,
    borderRadius: theme.radiusMd,
    justifyContent: 'center',
    alignItems: 'center',
  },
  btnGps: { backgroundColor: theme.info },
  btnSearch: { backgroundColor: theme.accent },
  mapBox: {
    flex: 1,
    backgroundColor: theme.surface,
    borderRadius: theme.radiusXl,
    overflow: 'hidden',
    borderWidth: 1,
    borderColor: theme.border,
  },
  webview: { flex: 1 },
  loadingOverlay: {
    ...StyleSheet.absoluteFillObject,
    backgroundColor: theme.surface,
    justifyContent: 'center',
    alignItems: 'center',
    zIndex: 10,
  },
  loadingText: { marginTop: 12, color: theme.muted, fontWeight: '600' },
  placeholder: { flex: 1, justifyContent: 'center', alignItems: 'center', padding: 30 },
  iconCircle: {
    width: 88,
    height: 88,
    borderRadius: 28,
    backgroundColor: theme.accentSoft,
    justifyContent: 'center',
    alignItems: 'center',
    marginBottom: 16,
  },
  placeholderTitle: { color: theme.ink, fontSize: 22, fontWeight: '900' },
  placeholderText: { color: theme.inkSoft, fontSize: 14, lineHeight: 20, textAlign: 'center', marginTop: 8, maxWidth: 250 },
});
