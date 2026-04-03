import React, { useState, useEffect } from 'react';
import { View, Text, StyleSheet, TouchableOpacity, TextInput, ActivityIndicator, Alert, Keyboard } from 'react-native';
import { SafeAreaView } from 'react-native-safe-area-context';
import { WebView } from 'react-native-webview';
import { Search, Map as MapIcon, Navigation } from 'lucide-react-native';
import * as Location from 'expo-location';
import { getMapHtml, getUserProfile } from '../services/apiService';
import { theme } from '../theme/theme';
import { StackHeader } from '../components/StackHeader';

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
    <SafeAreaView style={styles.container} edges={['top']}>
      <StackHeader title="Parsel haritası" onBack={() => navigation.goBack()} />

      <View style={styles.searchBlock}>
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
          {loading ? <ActivityIndicator color="#fff" size="small" /> : <Navigation size={22} color="#fff" />}
        </TouchableOpacity>
        <TouchableOpacity style={[styles.btn, styles.btnSearch]} onPress={() => fetchMap(city)} disabled={loading}>
          <Search size={22} color="#fff" />
        </TouchableOpacity>
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
                <ActivityIndicator size="large" color={theme.forestLight} />
                <Text style={styles.loadingText}>Harita açılıyor...</Text>
              </View>
            )}
          />
        ) : (
          <View style={styles.placeholder}>
            <View style={styles.iconCircle}>
              <MapIcon size={48} color={theme.forestLight} />
            </View>
            <Text style={styles.placeholderTitle}>Konum seçin</Text>
            <Text style={styles.placeholderText}>Arama veya GPS ile bölgenizi yükleyin. OSM karosu kullanılır.</Text>
          </View>
        )}
      </View>
    </SafeAreaView>
  );
}

const styles = StyleSheet.create({
  container: { flex: 1, backgroundColor: theme.bg },
  searchBlock: {
    flexDirection: 'row',
    paddingHorizontal: 20,
    paddingTop: 16,
    paddingBottom: 14,
    gap: 10,
    alignItems: 'center',
  },
  inputWrap: {
    flex: 1,
    backgroundColor: theme.surface,
    borderRadius: theme.radiusMd,
    height: 50,
    justifyContent: 'center',
    borderWidth: 1,
    borderColor: theme.border,
  },
  input: { paddingHorizontal: 16, fontSize: 16, color: theme.ink, height: '100%' },
  btn: {
    width: 50,
    height: 50,
    borderRadius: theme.radiusSm,
    justifyContent: 'center',
    alignItems: 'center',
  },
  btnGps: { backgroundColor: theme.info },
  btnSearch: { backgroundColor: theme.forestLight },
  mapBox: {
    flex: 1,
    marginHorizontal: 20,
    marginBottom: 20,
    backgroundColor: theme.surface,
    borderRadius: theme.radiusLg,
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
  placeholder: { flex: 1, justifyContent: 'center', alignItems: 'center', padding: 40 },
  iconCircle: {
    width: 100,
    height: 100,
    borderRadius: 32,
    backgroundColor: theme.skyTint,
    justifyContent: 'center',
    alignItems: 'center',
    marginBottom: 18,
    borderWidth: 2,
    borderColor: theme.forestLight,
  },
  placeholderTitle: { fontSize: 20, fontWeight: '900', color: theme.ink, marginBottom: 8 },
  placeholderText: { fontSize: 15, color: theme.muted, textAlign: 'center', lineHeight: 22 },
});
