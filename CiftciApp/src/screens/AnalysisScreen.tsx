import React, { useState } from 'react';
import { View, Text, StyleSheet, TouchableOpacity, Image, ScrollView, ActivityIndicator, Alert, Linking } from 'react-native';
import { Camera, Upload, X, CheckCircle, AlertOctagon, AlertTriangle, Info } from 'lucide-react-native';
import * as ImagePicker from 'expo-image-picker';
import { uploadImageForAnalysis } from '../services/apiService';
import { AnalysisResult } from '../types';

export default function AnalysisScreen() {
  const [image, setImage] = useState<string | null>(null);
  const [analyzing, setAnalyzing] = useState(false);
  const [result, setResult] = useState<AnalysisResult | null>(null);

  const pickImage = async (useCamera: boolean) => {
    // İzin İste
    const { status } = useCamera
      ? await ImagePicker.requestCameraPermissionsAsync()
      : await ImagePicker.requestMediaLibraryPermissionsAsync();

    if (status !== 'granted') {
      Alert.alert("İzin Gerekli", "Bu özelliği kullanmak için izin vermelisiniz.");
      return;
    }

    let result;
    if (useCamera) {
      result = await ImagePicker.launchCameraAsync({
        mediaTypes: ImagePicker.MediaTypeOptions.Images,
        allowsEditing: true,
        aspect: [4, 4],
        quality: 0.7,
      });
    } else {
      result = await ImagePicker.launchImageLibraryAsync({
        mediaTypes: ImagePicker.MediaTypeOptions.Images,
        allowsEditing: true,
        aspect: [4, 4],
        quality: 0.7,
      });
    }

    if (!result.canceled) {
      setImage(result.assets[0].uri);
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
      const msg = error instanceof Error ? error.message : 'Analiz sırasında bir sorun oluştu.';
      Alert.alert('Hata', msg);
    } finally {
      setAnalyzing(false);
    }
  };

  const reset = () => {
    setImage(null);
    setResult(null);
  };

  return (
    <ScrollView contentContainerStyle={styles.container}>
      {!image ? (
        <View style={styles.uploadArea}>
          <View style={styles.iconCircle}>
            <Camera size={48} color="#16a34a" />
          </View>
          <Text style={styles.title}>Bitki Analizi</Text>
          <Text style={styles.subtitle}>
            Hastalık teşhisi için bitkinin etkilenen bölgesinin net bir fotoğrafını yükleyin.
          </Text>

          <TouchableOpacity style={styles.btnPrimary} onPress={() => pickImage(true)}>
            <Camera size={20} color="#fff" style={{marginRight:8}} />
            <Text style={styles.btnText}>Fotoğraf Çek</Text>
          </TouchableOpacity>

          <TouchableOpacity style={styles.btnSecondary} onPress={() => pickImage(false)}>
            <Upload size={20} color="#16a34a" style={{marginRight:8}} />
            <Text style={[styles.btnText, {color: '#16a34a'}]}>Galeriden Seç</Text>
          </TouchableOpacity>

          <View style={styles.infoRow}>
            <Info size={16} color="#9ca3af" />
            <Text style={styles.infoText}>İyi Işık • Net Odak • Yakın Çekim</Text>
          </View>
        </View>
      ) : (
        <View style={styles.resultArea}>
          <View style={styles.imageContainer}>
            <Image source={{ uri: image }} style={styles.previewImage} />
            {!analyzing && !result && (
              <TouchableOpacity style={styles.closeBtn} onPress={reset}>
                <X size={20} color="#fff" />
              </TouchableOpacity>
            )}

            {analyzing && (
              <View style={styles.loadingOverlay}>
                <ActivityIndicator size="large" color="#fff" />
                <Text style={styles.loadingText}>Yapay Zeka İnceliyor...</Text>
              </View>
            )}
          </View>

          {!result && !analyzing && (
            <TouchableOpacity style={styles.analyzeBtn} onPress={handleAnalyze}>
              <Upload size={20} color="#fff" style={{marginRight:8}} />
              <Text style={styles.btnText}>Analizi Başlat</Text>
            </TouchableOpacity>
          )}

          {result && (
            <View style={[styles.card,
              result.status === 'healthy' ? styles.cardGreen :
              result.status === 'warning' ? styles.cardOrange : styles.cardRed]}>
              <View style={styles.cardHeader}>
                {result.status === 'healthy' ? (
                  <CheckCircle size={32} color="#22c55e" />
                ) : result.status === 'warning' ? (
                  <AlertTriangle size={32} color="#f59e0b" />
                ) : (
                  <AlertOctagon size={32} color="#ef4444" />
                )}
                <View style={{marginLeft: 12, flex: 1}}>
                  <Text style={styles.diseaseName}>{result.diseaseName}</Text>
                  <Text style={styles.confidence}>%{Math.round(result.confidence * 100)} güven</Text>
                  {result.crop ? (
                    <Text style={styles.cropHint}>Bitki: {result.crop}</Text>
                  ) : null}
                </View>
              </View>

              <View style={styles.recBox}>
                <Text style={styles.recTitle}>Öneri ve kültürel tedavi</Text>
                <Text style={styles.recText}>{result.recommendation}</Text>
              </View>

              {result.activeIngredients && result.activeIngredients.length > 0 ? (
                <View style={styles.ingBox}>
                  <Text style={styles.recTitle}>Etken madde / müdahale (bilgilendirme)</Text>
                  {result.activeIngredients.map((ing, i) => (
                    <View key={i} style={styles.ingRow}>
                      <Text style={styles.ingName}>• {ing.name}</Text>
                      {ing.role ? <Text style={styles.ingRole}>{ing.role}</Text> : null}
                      {ing.notes ? <Text style={styles.ingNotes}>{ing.notes}</Text> : null}
                    </View>
                  ))}
                </View>
              ) : result.status !== 'healthy' ? (
                <View style={styles.ingBox}>
                  <Text style={styles.ingMuted}>
                    Bu durum için özel etken madde satırı tanımlı değil veya doğrudan kimyasal önerisi yoktur; yukarıdaki kültürel önerilere bakın.
                  </Text>
                </View>
              ) : null}

              {result.bkuMrlEnrichment?.enabled ? (
                <View style={styles.bkuBox}>
                  <Text style={styles.recTitle}>BKÜ — MRL özeti (resmi veri tabanı)</Text>
                  <Text style={styles.bkuMuted}>
                    Kaynak:{' '}
                    {result.bkuMrlEnrichment.sourceHomepage ?? 'bku.tarimorman.gov.tr'}
                  </Text>
                  {!result.bkuMrlEnrichment.resolvedSubstances?.length &&
                  !result.bkuMrlEnrichment.lookupFailures?.length ? (
                    <Text style={styles.bkuMuted}>Bu sonuç için BKÜ haritasında eşleşen etken madde yok.</Text>
                  ) : null}
                  {result.bkuMrlEnrichment.resolvedSubstances?.map((sub, idx) => (
                    <View key={idx} style={styles.bkuSubBlock}>
                      {sub.detailUrl ? (
                        <TouchableOpacity onPress={() => Linking.openURL(sub.detailUrl!)}>
                          <Text style={styles.bkuLink}>Detay sayfası ({sub.detailId})</Text>
                        </TouchableOpacity>
                      ) : null}
                      {sub.sampleRows?.slice(0, 8).map((row, j) => (
                        <Text key={j} style={styles.bkuRow}>
                          • {row.mrlUrunAdi ?? ''} — MRL {row.mrlOrani ?? '—'} ({row.durumu ?? ''})
                        </Text>
                      ))}
                    </View>
                  ))}
                  {result.bkuMrlEnrichment.errors?.length ? (
                    <Text style={styles.bkuMuted}>
                      BKÜ isteği: {result.bkuMrlEnrichment.errors.join(' · ')}
                    </Text>
                  ) : null}
                  {result.bkuMrlEnrichment.lookupFailures &&
                  result.bkuMrlEnrichment.lookupFailures.length > 0 ? (
                    <Text style={styles.bkuMuted}>
                      Haritada olmayan etkenler:{' '}
                      {result.bkuMrlEnrichment.lookupFailures.map((f) => f.phrase).join(', ')}
                    </Text>
                  ) : null}
                  {result.bkuMrlEnrichment.disclaimerTr ? (
                    <Text style={styles.bkuDisclaimer}>{result.bkuMrlEnrichment.disclaimerTr}</Text>
                  ) : null}
                </View>
              ) : null}

              {result.narrativeSummary ? (
                <View style={styles.narrativeBox}>
                  <Text style={styles.recTitle}>Özet (AI)</Text>
                  <Text style={styles.recText}>{result.narrativeSummary}</Text>
                </View>
              ) : null}

              {result.disclaimer ? (
                <Text style={styles.disclaimer}>{result.disclaimer}</Text>
              ) : null}

              <TouchableOpacity style={styles.newBtn} onPress={reset}>
                <Text style={styles.newBtnText}>Yeni Analiz Yap</Text>
              </TouchableOpacity>
            </View>
          )}
        </View>
      )}
    </ScrollView>
  );
}

const styles = StyleSheet.create({
  container: { flexGrow: 1, backgroundColor: '#f9fafb', padding: 20 },
  uploadArea: { flex: 1, justifyContent: 'center', alignItems: 'center', backgroundColor: '#fff', borderRadius: 24, padding: 32, borderStyle: 'dashed', borderWidth: 2, borderColor: '#d1d5db' },
  iconCircle: { width: 90, height: 90, backgroundColor: '#f0fdf4', borderRadius: 45, justifyContent: 'center', alignItems: 'center', marginBottom: 24 },
  title: { fontSize: 24, fontWeight: 'bold', color: '#111', marginBottom: 8 },
  subtitle: { textAlign: 'center', color: '#6b7280', marginBottom: 32, lineHeight: 22 },
  btnPrimary: { flexDirection: 'row', backgroundColor: '#16a34a', width: '100%', padding: 16, borderRadius: 14, alignItems: 'center', justifyContent: 'center', marginBottom: 12, elevation: 2 },
  btnSecondary: { flexDirection: 'row', backgroundColor: '#fff', width: '100%', padding: 16, borderRadius: 14, alignItems: 'center', justifyContent: 'center', borderWidth: 1, borderColor: '#16a34a' },
  btnText: { color: '#fff', fontWeight: 'bold', fontSize: 16 },
  infoRow: { flexDirection: 'row', alignItems: 'center', marginTop: 32, gap: 8, opacity: 0.7 },
  infoText: { color: '#6b7280', fontSize: 13, fontWeight: '500' },

  resultArea: { flex: 1 },
  imageContainer: { height: 350, borderRadius: 24, overflow: 'hidden', marginBottom: 24, backgroundColor: '#e5e7eb', position: 'relative', elevation: 3 },
  previewImage: { width: '100%', height: '100%' },
  closeBtn: { position: 'absolute', top: 16, right: 16, backgroundColor: 'rgba(0,0,0,0.6)', padding: 8, borderRadius: 20 },
  loadingOverlay: { ...StyleSheet.absoluteFillObject, backgroundColor: 'rgba(0,0,0,0.7)', justifyContent: 'center', alignItems: 'center' },
  loadingText: { color: '#fff', marginTop: 16, fontWeight: 'bold', fontSize: 16 },
  analyzeBtn: { flexDirection: 'row', backgroundColor: '#16a34a', padding: 18, borderRadius: 16, justifyContent: 'center', alignItems: 'center', elevation: 3 },

  card: { backgroundColor: '#fff', borderRadius: 24, padding: 24, borderLeftWidth: 6, shadowColor: "#000", shadowOpacity: 0.1, shadowRadius: 10, elevation: 5 },
  cardGreen: { borderLeftColor: '#22c55e' },
  cardOrange: { borderLeftColor: '#f59e0b' },
  cardRed: { borderLeftColor: '#ef4444' },
  cardHeader: { flexDirection: 'row', alignItems: 'center', marginBottom: 20 },
  diseaseName: { fontSize: 20, fontWeight: 'bold', color: '#1f2937' },
  confidence: { color: '#6b7280', fontSize: 14, fontWeight: '600', marginTop: 2 },
  cropHint: { color: '#9ca3af', fontSize: 13, marginTop: 4 },
  recBox: { backgroundColor: '#f3f4f6', padding: 16, borderRadius: 16, marginBottom: 20 },
  recTitle: { fontWeight: 'bold', color: '#111', marginBottom: 8, fontSize: 15 },
  recText: { color: '#374151', lineHeight: 22, fontSize: 15 },
  ingBox: { backgroundColor: '#fffbeb', padding: 14, borderRadius: 14, marginBottom: 16, borderWidth: 1, borderColor: '#fde68a' },
  ingRow: { marginBottom: 12 },
  ingName: { fontWeight: '700', color: '#1f2937', fontSize: 15 },
  ingRole: { color: '#6b7280', fontSize: 13, marginTop: 2 },
  ingNotes: { color: '#4b5563', fontSize: 13, marginTop: 4, lineHeight: 18 },
  ingMuted: { color: '#6b7280', fontSize: 14, lineHeight: 20 },
  narrativeBox: { backgroundColor: '#eff6ff', padding: 14, borderRadius: 14, marginBottom: 16, borderWidth: 1, borderColor: '#bfdbfe' },
  bkuBox: { backgroundColor: '#f0fdf4', padding: 14, borderRadius: 14, marginBottom: 16, borderWidth: 1, borderColor: '#bbf7d0' },
  bkuSubBlock: { marginTop: 10 },
  bkuRow: { color: '#374151', fontSize: 13, lineHeight: 18, marginTop: 4 },
  bkuLink: { color: '#15803d', fontWeight: '700', fontSize: 14, marginBottom: 6 },
  bkuMuted: { color: '#6b7280', fontSize: 12, lineHeight: 18, marginTop: 6 },
  bkuDisclaimer: { fontSize: 11, color: '#6b7280', fontStyle: 'italic', marginTop: 8 },
  disclaimer: { fontSize: 11, color: '#6b7280', lineHeight: 16, marginBottom: 16, fontStyle: 'italic' },
  newBtn: { padding: 16, borderWidth: 1, borderColor: '#e5e7eb', borderRadius: 14, alignItems: 'center', backgroundColor: '#fafafa' },
  newBtnText: { color: '#4b5563', fontWeight: 'bold', fontSize: 15 }
});