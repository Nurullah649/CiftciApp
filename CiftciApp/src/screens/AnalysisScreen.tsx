import React, { useMemo, useState } from 'react';
import {
  Alert,
  Image,
  SafeAreaView,
  ScrollView,
  StatusBar,
  StyleSheet,
  Text,
  TouchableOpacity,
  View,
} from 'react-native';
import { Camera, CheckCircle, Info, Upload, X } from 'lucide-react-native';
import * as ImagePicker from 'expo-image-picker';
import { uploadImageForAnalysis } from '../services/apiService';
import { AnalysisResult } from '../types';
import { theme } from '../theme/theme';
import { AmbientBackdrop } from '../components/AmbientBackdrop';
import { AppButton } from '../components/AppButton';

const TAB_PAD = 126;

export default function AnalysisScreen() {
  const [image, setImage] = useState<string | null>(null);
  const [analyzing, setAnalyzing] = useState(false);
  const [result, setResult] = useState<AnalysisResult | null>(null);

  const pickImage = async (useCamera: boolean) => {
    const { status } = useCamera
      ? await ImagePicker.requestCameraPermissionsAsync()
      : await ImagePicker.requestMediaLibraryPermissionsAsync();

    if (status !== 'granted') {
      Alert.alert('İzin', 'Fotoğraf için izin gerekli.');
      return;
    }

    const res = useCamera
      ? await ImagePicker.launchCameraAsync({
          mediaTypes: ImagePicker.MediaTypeOptions.Images,
          allowsEditing: true,
          aspect: [4, 4],
          quality: 0.55,
        })
      : await ImagePicker.launchImageLibraryAsync({
          mediaTypes: ImagePicker.MediaTypeOptions.Images,
          allowsEditing: true,
          aspect: [4, 4],
          quality: 0.55,
        });

    if (!res.canceled) {
      setImage(res.assets[0].uri);
      setResult(null);
    }
  };

  const handleAnalyze = async () => {
    if (!image) return;
    setAnalyzing(true);
    try {
      const data = await uploadImageForAnalysis(image);
      setResult(data);
    } catch {
      Alert.alert('Hata', 'Analiz tamamlanamadı.');
    } finally {
      setAnalyzing(false);
    }
  };

  const reset = () => {
    setImage(null);
    setResult(null);
  };

  const statusMeta = useMemo(() => {
    if (!result) return null;
    if (result.status === 'healthy') {
      return { label: 'Sağlıklı görünüm', bg: theme.successSoft, fg: theme.success };
    }
    if (result.status === 'critical') {
      return { label: 'Öncelikli kontrol', bg: theme.dangerSoft, fg: theme.danger };
    }
    return { label: 'İzleme önerilir', bg: theme.chipAmber, fg: theme.gold };
  }, [result]);

  return (
    <SafeAreaView style={styles.safe}>
      <StatusBar barStyle="dark-content" backgroundColor={theme.bg} />
      <AmbientBackdrop />

      <ScrollView contentContainerStyle={[styles.scroll, { paddingBottom: TAB_PAD }]} showsVerticalScrollIndicator={false}>
        <View style={styles.header}>
          <Text style={styles.headerEyebrow}>BİTKİ TARAMASI</Text>
          <Text style={styles.headerTitle}>Fotoğrafı yükleyin, teşhisi alın.</Text>
          <Text style={styles.headerSub}>
            Uygulama yüklemeden önce fotoğrafı sıkıştırır. Bu sayede 413 boyut hatası büyük ölçüde engellenir.
          </Text>
        </View>

        <View style={styles.card}>
          {!image ? (
            <>
              <View style={styles.placeholder}>
                <Camera size={34} color={theme.accent} />
              </View>
              <Text style={styles.cardTitle}>Yakın plan ve net odak kullanın</Text>
              <Text style={styles.cardSub}>Tek yaprak, iyi ışık ve gereksiz arka plan olmadan çekilen fotoğraflar daha iyi sonuç verir.</Text>

              <AppButton
                label="Kamera ile çek"
                onPress={() => pickImage(true)}
                leftIcon={<Camera size={18} color="#fff" />}
                style={styles.primaryAction}
              />
              <AppButton
                label="Galeriden seç"
                onPress={() => pickImage(false)}
                variant="secondary"
                leftIcon={<Upload size={18} color={theme.ink} />}
                style={styles.secondaryAction}
              />

              <View style={styles.tip}>
                <Info size={16} color={theme.accent} />
                <Text style={styles.tipText}>Büyük fotoğraflar analiz öncesi otomatik küçültülür.</Text>
              </View>
            </>
          ) : (
            <>
              <View style={styles.imageWrap}>
                <Image source={{ uri: image }} style={styles.previewImage} />
                {!analyzing && (
                  <TouchableOpacity style={styles.close} onPress={reset}>
                    <X size={18} color="#fff" />
                  </TouchableOpacity>
                )}
              </View>

              <AppButton
                label={analyzing ? 'Analiz ediliyor...' : 'Analizi başlat'}
                onPress={handleAnalyze}
                loading={analyzing}
                style={styles.primaryAction}
              />
            </>
          )}
        </View>

        {result && (
          <View style={styles.resultCard}>
            <View style={styles.resultHead}>
              <View style={{ flex: 1 }}>
                <Text style={styles.resultEyebrow}>SONUÇ</Text>
                <Text style={styles.resultTitle}>{result.diseaseName}</Text>
              </View>
              <View style={[styles.statusChip, { backgroundColor: statusMeta?.bg }]}>
                <Text style={[styles.statusChipText, { color: statusMeta?.fg }]}>{statusMeta?.label}</Text>
              </View>
            </View>

            <View style={styles.resultInfo}>
              <View style={styles.confidenceBox}>
                <CheckCircle size={20} color={theme.accent} />
                <Text style={styles.confidenceLabel}>Güven</Text>
                <Text style={styles.confidenceValue}>%{Math.round(result.confidence * 100)}</Text>
              </View>
              <View style={styles.summaryBox}>
                <Text style={styles.summaryTitle}>Öneri</Text>
                <Text style={styles.summaryText}>{result.recommendation}</Text>
              </View>
            </View>

            {!!result.treatmentTitles?.length && (
              <View style={styles.tagsWrap}>
                <Text style={styles.tagsTitle}>Tedavi başlıkları</Text>
                <View style={styles.tagsRow}>
                  {result.treatmentTitles.map((title) => (
                    <View key={title} style={styles.tag}>
                      <Text style={styles.tagText}>{title}</Text>
                    </View>
                  ))}
                </View>
              </View>
            )}

            <AppButton label="Yeni fotoğraf seç" onPress={reset} variant="secondary" style={styles.secondaryAction} />
          </View>
        )}
      </ScrollView>
    </SafeAreaView>
  );
}

const styles = StyleSheet.create({
  safe: { flex: 1, backgroundColor: theme.bg },
  scroll: { padding: 20 },
  header: { marginBottom: 16 },
  headerEyebrow: { color: theme.muted, fontSize: 11, fontWeight: '900', letterSpacing: 1.2 },
  headerTitle: { color: theme.ink, fontSize: 30, lineHeight: 34, fontWeight: '900', marginTop: 10, maxWidth: 260 },
  headerSub: { color: theme.inkSoft, fontSize: 15, lineHeight: 22, marginTop: 10, maxWidth: 310 },
  card: {
    backgroundColor: theme.surface,
    borderRadius: theme.radiusXl,
    padding: 18,
    borderWidth: 1,
    borderColor: theme.border,
  },
  placeholder: {
    width: 72,
    height: 72,
    borderRadius: 24,
    backgroundColor: theme.accentSoft,
    justifyContent: 'center',
    alignItems: 'center',
    marginBottom: 16,
  },
  cardTitle: { color: theme.ink, fontSize: 22, lineHeight: 28, fontWeight: '900' },
  cardSub: { color: theme.inkSoft, fontSize: 15, lineHeight: 22, marginTop: 10, marginBottom: 18 },
  primaryAction: { marginTop: 0 },
  secondaryAction: { marginTop: 10 },
  tip: {
    flexDirection: 'row',
    alignItems: 'center',
    gap: 8,
    backgroundColor: theme.surfaceStrong,
    borderRadius: theme.radiusMd,
    padding: 12,
    marginTop: 14,
  },
  tipText: { flex: 1, color: theme.inkSoft, fontSize: 13, lineHeight: 19 },
  imageWrap: {
    height: 320,
    borderRadius: theme.radiusLg,
    overflow: 'hidden',
    backgroundColor: theme.bgMuted,
    marginBottom: 16,
  },
  previewImage: { width: '100%', height: '100%' },
  close: {
    position: 'absolute',
    top: 12,
    right: 12,
    width: 34,
    height: 34,
    borderRadius: 12,
    backgroundColor: 'rgba(0,0,0,0.45)',
    justifyContent: 'center',
    alignItems: 'center',
  },
  resultCard: {
    backgroundColor: theme.surface,
    borderRadius: theme.radiusXl,
    padding: 18,
    borderWidth: 1,
    borderColor: theme.border,
    marginTop: 16,
  },
  resultHead: { flexDirection: 'row', gap: 12, alignItems: 'flex-start' },
  resultEyebrow: { color: theme.muted, fontSize: 11, fontWeight: '900', letterSpacing: 1.2 },
  resultTitle: { color: theme.ink, fontSize: 24, lineHeight: 30, fontWeight: '900', marginTop: 8 },
  statusChip: { borderRadius: 999, paddingHorizontal: 12, paddingVertical: 8 },
  statusChipText: { fontSize: 12, fontWeight: '900' },
  resultInfo: { flexDirection: 'row', gap: 12, marginTop: 16 },
  confidenceBox: {
    width: 110,
    backgroundColor: theme.surfaceStrong,
    borderRadius: theme.radiusLg,
    padding: 14,
  },
  confidenceLabel: { color: theme.muted, fontSize: 12, marginTop: 10 },
  confidenceValue: { color: theme.ink, fontSize: 28, fontWeight: '900', marginTop: 6 },
  summaryBox: { flex: 1, backgroundColor: theme.surfaceMuted, borderRadius: theme.radiusLg, padding: 14 },
  summaryTitle: { color: theme.ink, fontSize: 15, fontWeight: '900', marginBottom: 8 },
  summaryText: { color: theme.inkSoft, fontSize: 14, lineHeight: 21 },
  tagsWrap: { marginTop: 16 },
  tagsTitle: { color: theme.ink, fontSize: 14, fontWeight: '900', marginBottom: 10 },
  tagsRow: { flexDirection: 'row', flexWrap: 'wrap', gap: 8 },
  tag: {
    backgroundColor: theme.accentSoft,
    borderRadius: 999,
    paddingHorizontal: 12,
    paddingVertical: 8,
  },
  tagText: { color: theme.accent, fontSize: 13, fontWeight: '800' },
});
