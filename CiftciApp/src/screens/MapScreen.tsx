import React, { useState, useEffect } from 'react';
import { View, Text, StyleSheet, TouchableOpacity, TextInput, ActivityIndicator, Alert, Keyboard, StatusBar } from 'react-native';
import { Screen } from '../components/ui/Screen';
import { StackHeader } from '../components/ui/StackHeader';
import { WebView } from 'react-native-webview';
import { Search, Map as MapIcon, Navigation } from 'lucide-react-native';
import { colors, spacing, radius, typography, shadow } from '../theme';
import * as Location from 'expo-location';
import { getMapHtml, getUserProfile } from '../services/apiService';

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
    } catch (e) {
      // Profil çekilemezse varsayılan boş kalır
    }
  };

  const fetchMap = async (locationName: string) => {
    if (!locationName.trim()) return;

    Keyboard.dismiss();
    setLoading(true);
    try {
      const html = await getMapHtml(locationName);
      setMapHtml(html);
    } catch (error) {
      Alert.alert("Hata", "Harita yüklenirken bir sorun oluştu.");
    } finally {
      setLoading(false);
    }
  };

  // Konumumu Bul Fonksiyonu
  const handleCurrentLocation = async () => {
    setLoading(true);
    Keyboard.dismiss();
    try {
      let { status } = await Location.requestForegroundPermissionsAsync();
      if (status !== 'granted') {
        Alert.alert('İzin Reddedildi', 'Konumunuzu bulabilmek için izin vermeniz gerekiyor.');
        setLoading(false);
        return;
      }

      let location = await Location.getCurrentPositionAsync({});
      let address = await Location.reverseGeocodeAsync({
        latitude: location.coords.latitude,
        longitude: location.coords.longitude
      });

      if (address && address.length > 0) {
        const place = address[0];
        // Adres önceliği: İlçe -> Şehir -> Bölge
        const locationName = place.subregion || place.city || place.region;

        if (locationName) {
            setCity(locationName);
            fetchMap(locationName);
        } else {
            Alert.alert('Hata', 'Konum ismi tespit edilemedi.');
            setLoading(false);
        }
      }
    } catch (error) {
      Alert.alert('Hata', 'GPS konumu alınamadı.');
      setLoading(false);
    }
  };

  return (
    <Screen edges={['top', 'left', 'right']}>
      <StatusBar barStyle="dark-content" backgroundColor={colors.bg} />
      <StackHeader title="Tarla Haritası" onBack={() => navigation.goBack()} />

      {/* Arama Alanı */}
      <View style={styles.searchContainer}>
        <View style={styles.inputWrapper}>
          <TextInput
            style={styles.input}
            placeholder="Şehir/İlçe Ara..."
            value={city}
            onChangeText={setCity}
            placeholderTextColor={colors.textMuted}
          />
        </View>

        {/* Konumumu Bul Butonu (Mavi) */}
        <TouchableOpacity
          style={[styles.iconBtn, styles.locationBtn]}
          onPress={handleCurrentLocation}
          disabled={loading}
        >
          {loading ? <ActivityIndicator color="#fff" size="small" /> : <Navigation size={22} color="#fff" />}
        </TouchableOpacity>

        {/* Ara Butonu (Yeşil) */}
        <TouchableOpacity
          style={[styles.iconBtn, styles.searchBtn]}
          onPress={() => fetchMap(city)}
          disabled={loading}
        >
          <Search size={22} color="#fff" />
        </TouchableOpacity>
      </View>

      {/* Harita Alanı */}
      <View style={styles.mapContainer}>
        {mapHtml ? (
          <WebView
            originWhitelist={['*']}
            source={{ html: mapHtml }}
            style={styles.webview}
            startInLoadingState={true}
            renderLoading={() => (
                <View style={styles.loadingOverlay}>
                    <ActivityIndicator size="large" color={colors.primary} />
                    <Text style={styles.loadingText}>Uydu görüntüleri yükleniyor...</Text>
                </View>
            )}
          />
        ) : (
          <View style={styles.placeholder}>
            <View style={styles.iconCircle}>
                <MapIcon size={56} color={colors.primary} />
            </View>
            <Text style={styles.placeholderTitle}>Konum Seçin</Text>
            <Text style={styles.placeholderText}>
              Haritayı görüntülemek için bir yer arayın veya konumunuzu kullanın.
            </Text>
          </View>
        )}
      </View>
    </Screen>
  );
}

const styles = StyleSheet.create({
  searchContainer: {
    flexDirection: 'row',
    paddingHorizontal: spacing.lg,
    paddingBottom: spacing.md,
    paddingTop: 4,
    gap: 10,
    alignItems: 'center',
  },
  inputWrapper: {
    flex: 1,
    backgroundColor: colors.surface,
    borderRadius: radius.full,
    height: 48,
    justifyContent: 'center',
    borderWidth: 1,
    borderColor: colors.borderLight,
  },
  input: {
    paddingHorizontal: 20,
    fontSize: 15,
    color: colors.text,
    height: '100%',
  },
  iconBtn: {
    width: 48,
    height: 48,
    borderRadius: 24,
    justifyContent: 'center',
    alignItems: 'center',
    ...shadow.soft,
  },
  locationBtn: { backgroundColor: colors.primary },
  searchBtn: { backgroundColor: colors.accentDark },
  mapContainer: {
    flex: 1,
    marginHorizontal: spacing.lg,
    marginBottom: spacing.lg,
    backgroundColor: colors.surface,
    borderRadius: radius.xl,
    overflow: 'hidden',
    ...shadow.card,
  },
  webview: { flex: 1 },
  loadingOverlay: {
    ...StyleSheet.absoluteFillObject,
    backgroundColor: colors.surface,
    justifyContent: 'center',
    alignItems: 'center',
    zIndex: 10,
  },
  loadingText: { marginTop: 12, color: colors.textSecondary, fontWeight: '600' },
  placeholder: {
    flex: 1,
    justifyContent: 'center',
    alignItems: 'center',
    padding: 40,
    backgroundColor: colors.surface,
  },
  iconCircle: {
    width: 100,
    height: 100,
    borderRadius: 50,
    backgroundColor: colors.primarySoft,
    justifyContent: 'center',
    alignItems: 'center',
    marginBottom: 24,
  },
  placeholderTitle: { ...typography.h2, color: colors.text, marginBottom: 8 },
  placeholderText: { ...typography.body, color: colors.textSecondary, textAlign: 'center' },
});