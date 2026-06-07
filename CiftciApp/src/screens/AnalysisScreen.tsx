import React, { useState } from 'react';
import {
  View,
  Text,
  StyleSheet,
  TouchableOpacity,
  Image,
  ScrollView,
  ActivityIndicator,
  Alert,
  Linking,
  StatusBar,
} from 'react-native';
import {
  Camera,
  Upload,
  X,
  CheckCircle,
  AlertOctagon,
  AlertTriangle,
  Microscope,
  ImageIcon,
} from 'lucide-react-native';
import * as ImagePicker from 'expo-image-picker';
import { Screen } from '../components/ui/Screen';
import { PrimaryButton, SecondaryButton } from '../components/ui/Buttons';
import { uploadImageForAnalysis } from '../services/apiService';
import { prepareAnalysisImage } from '../utils/prepareAnalysisImage';
import { AnalysisResult } from '../types';
import { colors, spacing, radius, typography, shadow, statusColor } from '../theme';

export default function AnalysisScreen() {
  const [image, setImage] = useState<string | null>(null);
  const [analyzing, setAnalyzing] = useState(false);
  const [result, setResult] = useState<AnalysisResult | null>(null);

  const pickImage = async (useCamera: boolean) => {
    const { status } = useCamera
      ? await ImagePicker.requestCameraPermissionsAsync()
      : await ImagePicker.requestMediaLibraryPermissionsAsync();
    if (status !== 'granted') {
      Alert.alert('İzin Gerekli', 'Kamera veya galeri izni verin.');
      return;
    }
    const picker = useCamera ? ImagePicker.launchCameraAsync : ImagePicker.launchImageLibraryAsync;
    const res = await picker({
      mediaTypes: ImagePicker.MediaTypeOptions.Images,
      allowsEditing: true,
      aspect: [4, 4],
      quality: 0.55,
    });
    if (!res.canceled) {
      try {
        const prepared = await prepareAnalysisImage(res.assets[0].uri);
        setImage(prepared);
      } catch {
        setImage(res.assets[0].uri);
      }
      setResult(null);
    }
  };

  const handleAnalyze = async () => {
    if (!image) return;
    setAnalyzing(true);
    try {
      const data = await uploadImageForAnalysis(image, { enrichWithBku: true });
      setResult(data);
    } catch (error: unknown) {
      Alert.alert('Hata', error instanceof Error ? error.message : 'Analiz başarısız.');
    } finally {
      setAnalyzing(false);
    }
  };

  const reset = () => {
    setImage(null);
    setResult(null);
  };

  const borderClr = result
    ? result.detected === false
      ? colors.textMuted
      : statusColor(result.status)
    : colors.primary;
  const showDiagnosis = result && result.detected !== false;

  return (
    <Screen>
      <StatusBar barStyle="dark-content" backgroundColor={colors.bg} />
      <ScrollView contentContainerStyle={styles.scroll} showsVerticalScrollIndicator={false}>
        <View style={styles.header}>
          <View style={styles.headerIcon}>
            <Microscope size={22} color={colors.textOnPrimary} />
          </View>
          <View>
            <Text style={styles.headerTitle}>Bitki Analizi</Text>
            <Text style={styles.headerSub}>Yaprak fotoğrafı ile hastalık teşhisi</Text>
          </View>
        </View>

        {!image ? (
          <View style={styles.dropZone}>
            <View style={styles.dropIcon}>
              <ImageIcon size={40} color={colors.primary} />
            </View>
            <Text style={styles.dropTitle}>Fotoğraf yükleyin</Text>
            <Text style={styles.dropSub}>
              Etkilenen yaprağın net, yakın ve iyi aydınlatılmış görüntüsü en iyi sonucu verir.
            </Text>
            <PrimaryButton
              label="Fotoğraf Çek"
              onPress={() => pickImage(true)}
              icon={<Camera size={20} color={colors.textOnPrimary} />}
              style={{ width: '100%', marginBottom: 12 }}
            />
            <SecondaryButton
              label="Galeriden Seç"
              onPress={() => pickImage(false)}
              icon={<Upload size={20} color={colors.primary} />}
              style={{ width: '100%' }}
            />
            <View style={styles.hints}>
              {['İyi ışık', 'Net odak', 'Tek yaprak'].map((h) => (
                <View key={h} style={styles.hintPill}>
                  <Text style={styles.hintText}>{h}</Text>
                </View>
              ))}
            </View>
          </View>
        ) : (
          <>
            <View style={styles.previewWrap}>
              <Image source={{ uri: image }} style={styles.preview} />
              {!analyzing && !result && (
                <TouchableOpacity style={styles.closeFab} onPress={reset}>
                  <X size={18} color={colors.textOnPrimary} />
                </TouchableOpacity>
              )}
              {analyzing && (
                <View style={styles.overlay}>
                  <ActivityIndicator size="large" color={colors.accent} />
                  <Text style={styles.overlayText}>Model inceliyor…</Text>
                  <Text style={styles.overlayHint}>İlk analiz 20–40 sn sürebilir</Text>
                </View>
              )}
            </View>

            {!result && !analyzing && (
              <PrimaryButton
                label="Analizi Başlat"
                onPress={handleAnalyze}
                icon={<Microscope size={20} color={colors.textOnPrimary} />}
              />
            )}

            {result && (
              <View style={[styles.resultCard, { borderTopColor: borderClr }]}>
                <View style={styles.resultHead}>
                  {result.detected === false ? (
                    <AlertOctagon size={36} color={colors.textMuted} />
                  ) : result.status === 'healthy' ? (
                    <CheckCircle size={36} color={colors.healthy} />
                  ) : result.status === 'warning' ? (
                    <AlertTriangle size={36} color={colors.warning} />
                  ) : (
                    <AlertOctagon size={36} color={colors.critical} />
                  )}
                  <View style={{ flex: 1, marginLeft: 14 }}>
                    <Text style={styles.diseaseName}>{result.diseaseName}</Text>
                    <Text style={styles.conf}>%{Math.round(result.confidence * 100)} güven</Text>
                    {result.detected === false ? (
                      <Text style={styles.crop}>
                        Eşik altı — net yaprak fotoğrafı ile tekrar deneyin
                      </Text>
                    ) : result.crop ? (
                      <Text style={styles.crop}>Kültür: {result.crop}</Text>
                    ) : null}
                  </View>
                </View>

                <View style={styles.block}>
                  <Text style={styles.blockTitle}>
                    {result.detected === false ? 'Ne yapmalısınız?' : 'Öneri'}
                  </Text>
                  <Text style={styles.blockBody}>{result.recommendation}</Text>
                </View>

                {showDiagnosis && result.activeIngredients && result.activeIngredients.length > 0 && (
                  <View style={[styles.block, styles.blockAccent]}>
                    <Text style={styles.blockTitle}>Etken maddeler (bilgi)</Text>
                    {result.activeIngredients.map((ing, i) => (
                      <Text key={i} style={styles.ingLine}>
                        • {ing.name}
                        {ing.role ? ` — ${ing.role}` : ''}
                      </Text>
                    ))}
                  </View>
                )}

                {showDiagnosis && result.bkuMrlEnrichment?.enabled && (
                  <View style={[styles.block, styles.blockBku]}>
                    <Text style={styles.blockTitle}>BKÜ — MRL özeti</Text>
                    {result.bkuMrlEnrichment.resolvedSubstances?.map((sub, idx) => (
                      <View key={idx} style={{ marginTop: 8 }}>
                        {sub.detailUrl ? (
                          <TouchableOpacity onPress={() => Linking.openURL(sub.detailUrl!)}>
                            <Text style={styles.link}>Resmi detay sayfası</Text>
                          </TouchableOpacity>
                        ) : null}
                        {sub.sampleRows?.slice(0, 6).map((row, j) => (
                          <Text key={j} style={styles.bkuLine}>
                            {row.mrlUrunAdi} — MRL {row.mrlOrani ?? '—'}
                          </Text>
                        ))}
                      </View>
                    ))}
                    {result.bkuMrlEnrichment.errors?.includes('bku_timeout') && (
                      <Text style={styles.muted}>BKÜ yanıt vermedi; tekrar deneyin.</Text>
                    )}
                  </View>
                )}

                {result.disclaimer ? <Text style={styles.disclaimer}>{result.disclaimer}</Text> : null}

                <SecondaryButton label="Yeni Analiz" onPress={reset} style={{ marginTop: 8 }} />
              </View>
            )}
          </>
        )}
      </ScrollView>
    </Screen>
  );
}

const styles = StyleSheet.create({
  scroll: { paddingHorizontal: spacing.lg, paddingBottom: 120 },
  header: { flexDirection: 'row', alignItems: 'center', gap: 14, paddingTop: spacing.md, marginBottom: spacing.lg },
  headerIcon: {
    width: 48,
    height: 48,
    borderRadius: 14,
    backgroundColor: colors.primary,
    alignItems: 'center',
    justifyContent: 'center',
  },
  headerTitle: { ...typography.h2, color: colors.primaryDark },
  headerSub: { ...typography.caption, color: colors.textMuted },
  dropZone: {
    backgroundColor: colors.surface,
    borderRadius: radius.xl,
    padding: spacing.xl,
    alignItems: 'center',
    borderWidth: 2,
    borderColor: colors.border,
    borderStyle: 'dashed',
    ...shadow.soft,
  },
  dropIcon: {
    width: 80,
    height: 80,
    borderRadius: 40,
    backgroundColor: colors.primarySoft,
    alignItems: 'center',
    justifyContent: 'center',
    marginBottom: spacing.md,
  },
  dropTitle: { ...typography.h2, color: colors.text },
  dropSub: { ...typography.caption, color: colors.textSecondary, textAlign: 'center', marginBottom: spacing.lg },
  hints: { flexDirection: 'row', gap: 8, marginTop: spacing.lg, flexWrap: 'wrap', justifyContent: 'center' },
  hintPill: { backgroundColor: colors.bg, paddingHorizontal: 12, paddingVertical: 6, borderRadius: radius.full },
  hintText: { fontSize: 12, fontWeight: '600', color: colors.textSecondary },
  previewWrap: {
    height: 320,
    borderRadius: radius.xl,
    overflow: 'hidden',
    backgroundColor: colors.bgDeep,
    marginBottom: spacing.md,
    ...shadow.card,
  },
  preview: { width: '100%', height: '100%' },
  closeFab: {
    position: 'absolute',
    top: 14,
    right: 14,
    backgroundColor: colors.overlay,
    padding: 10,
    borderRadius: 20,
  },
  overlay: {
    ...StyleSheet.absoluteFillObject,
    backgroundColor: colors.overlay,
    alignItems: 'center',
    justifyContent: 'center',
  },
  overlayText: { color: colors.textOnPrimary, fontWeight: '800', fontSize: 17, marginTop: 14 },
  overlayHint: { color: colors.accentSoft, fontSize: 13, marginTop: 6 },
  resultCard: {
    backgroundColor: colors.surface,
    borderRadius: radius.xl,
    padding: spacing.lg,
    borderTopWidth: 5,
    ...shadow.card,
  },
  resultHead: { flexDirection: 'row', alignItems: 'center', marginBottom: spacing.md },
  diseaseName: { ...typography.h2, color: colors.text },
  conf: { color: colors.textSecondary, fontWeight: '700', marginTop: 2 },
  crop: { color: colors.textMuted, fontSize: 13, marginTop: 4 },
  block: { backgroundColor: colors.bg, borderRadius: radius.md, padding: spacing.md, marginBottom: 12 },
  blockAccent: { backgroundColor: colors.accentSoft, borderWidth: 1, borderColor: colors.accent },
  blockBku: { backgroundColor: colors.primarySoft, borderWidth: 1, borderColor: colors.primaryLight },
  blockTitle: { fontWeight: '800', color: colors.text, marginBottom: 8, fontSize: 15 },
  blockBody: { color: colors.textSecondary, lineHeight: 22, fontSize: 15 },
  ingLine: { color: colors.text, fontSize: 14, marginTop: 6, lineHeight: 20 },
  link: { color: colors.primary, fontWeight: '700', marginBottom: 4 },
  bkuLine: { fontSize: 13, color: colors.textSecondary, marginTop: 4 },
  muted: { fontSize: 12, color: colors.textMuted, fontStyle: 'italic' },
  disclaimer: { fontSize: 11, color: colors.textMuted, fontStyle: 'italic', marginBottom: 12 },
});
