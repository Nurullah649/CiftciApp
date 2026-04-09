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
  StatusBar,
} from 'react-native';
import { SafeAreaView } from 'react-native-safe-area-context';
import { Camera, Upload, X, CheckCircle, AlertOctagon, Info } from 'lucide-react-native';
import * as ImagePicker from 'expo-image-picker';
import { uploadImageForAnalysis } from '../services/apiService';
import { AnalysisResult } from '../types';
import { theme } from '../theme/theme';

const TAB_PAD = 118;

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
          quality: 0.72,
        })
      : await ImagePicker.launchImageLibraryAsync({
          mediaTypes: ImagePicker.MediaTypeOptions.Images,
          allowsEditing: true,
          aspect: [4, 4],
          quality: 0.72,
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

  return (
    <SafeAreaView style={styles.safe} edges={['top']}>
      <StatusBar barStyle="light-content" backgroundColor={theme.forest} />
      <View style={styles.head}>
        <Text style={styles.kicker}>TARLA</Text>
        <Text style={styles.title}>Fotoğraf analizi</Text>
        <Text style={styles.sub}>Etkilenen bitkiyi net ve aydınlık çekin; sonuç sunucudan gelir.</Text>
      </View>

      <ScrollView contentContainerStyle={[styles.scroll, { paddingBottom: TAB_PAD }]} showsVerticalScrollIndicator={false}>
        {!image ? (
          <View style={styles.drop}>
            <View style={styles.dropRing}>
              <Camera size={36} color={theme.forestLight} />
            </View>
            <Text style={styles.dropTitle}>Çek veya seç</Text>
            <Text style={styles.dropSub}>Yaprak veya dal yakın planı idealdir.</Text>

            <TouchableOpacity style={styles.btnPrimary} onPress={() => pickImage(true)} activeOpacity={0.9}>
              <Camera size={20} color="#fff" style={{ marginRight: 10 }} />
              <Text style={styles.btnPrimaryTxt}>Kamera</Text>
            </TouchableOpacity>
            <TouchableOpacity style={styles.btnGhost} onPress={() => pickImage(false)} activeOpacity={0.9}>
              <Upload size={20} color={theme.forestLight} style={{ marginRight: 10 }} />
              <Text style={styles.btnGhostTxt}>Galeri</Text>
            </TouchableOpacity>

            <View style={styles.hint}>
              <Info size={16} color={theme.forestLight} />
              <Text style={styles.hintText}>İyi ışık · gölgesiz kare</Text>
            </View>
          </View>
        ) : (
          <View>
            <View style={styles.previewBox}>
              <Image source={{ uri: image }} style={styles.preview} />
              {!analyzing && !result && (
                <TouchableOpacity style={styles.close} onPress={reset}>
                  <X size={20} color="#fff" />
                </TouchableOpacity>
              )}
              {analyzing && (
                <View style={styles.overlay}>
                  <ActivityIndicator size="large" color={theme.tabActive} />
                  <Text style={styles.overlayText}>İnceleniyor...</Text>
                </View>
              )}
            </View>

            {!result && !analyzing && (
              <TouchableOpacity style={styles.runBtn} onPress={handleAnalyze} activeOpacity={0.92}>
                <Text style={styles.runBtnText}>Analizi başlat</Text>
              </TouchableOpacity>
            )}

            {result && (
              <View style={[styles.result, result.status === 'healthy' ? styles.resultOk : styles.resultBad]}>
                <View style={styles.resultHead}>
                  {result.status === 'healthy' ? (
                    <CheckCircle size={32} color={theme.success} />
                  ) : (
                    <AlertOctagon size={32} color={theme.danger} />
                  )}
                  <View style={{ marginLeft: 14, flex: 1 }}>
                    <Text style={styles.resultName}>{result.diseaseName}</Text>
                    <Text style={styles.resultConf}>%{Math.round(result.confidence * 100)} güven</Text>
                  </View>
                </View>
                <View style={styles.rec}>
                  <Text style={styles.recTitle}>Öneri</Text>
                  <Text style={styles.recBody}>{result.recommendation}</Text>
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
                <TouchableOpacity style={styles.again} onPress={reset}>
                  <Text style={styles.againText}>Yeni fotoğraf</Text>
                </TouchableOpacity>
              </View>
            )}
          </View>
        )}
      </ScrollView>
    </SafeAreaView>
  );
}

const styles = StyleSheet.create({
  safe: { flex: 1, backgroundColor: theme.bg },
  head: {
    backgroundColor: theme.forest,
    paddingHorizontal: 22,
    paddingTop: 8,
    paddingBottom: 22,
    borderBottomLeftRadius: 28,
    borderBottomRightRadius: 28,
  },
  kicker: { color: theme.tabActive, fontSize: 10, fontWeight: '900', letterSpacing: 2 },
  title: { fontSize: 26, fontWeight: '900', color: '#fff', marginTop: 8 },
  sub: { fontSize: 14, color: 'rgba(255,255,255,0.75)', marginTop: 8, lineHeight: 20 },
  scroll: { padding: 20 },
  drop: {
    backgroundColor: theme.surface,
    borderRadius: theme.radiusLg,
    padding: 28,
    alignItems: 'center',
    borderWidth: 2,
    borderStyle: 'dashed',
    borderColor: theme.border,
  },
  dropRing: {
    width: 88,
    height: 88,
    borderRadius: 28,
    backgroundColor: theme.skyTint,
    justifyContent: 'center',
    alignItems: 'center',
    marginBottom: 16,
    borderWidth: 2,
    borderColor: theme.forestLight,
  },
  dropTitle: { fontSize: 21, fontWeight: '900', color: theme.ink },
  dropSub: { textAlign: 'center', color: theme.muted, marginTop: 8, marginBottom: 22, lineHeight: 20 },
  btnPrimary: {
    flexDirection: 'row',
    width: '100%',
    backgroundColor: theme.accent,
    padding: 16,
    borderRadius: theme.radiusMd,
    justifyContent: 'center',
    alignItems: 'center',
    marginBottom: 10,
  },
  btnPrimaryTxt: { color: '#fff', fontWeight: '900', fontSize: 16 },
  btnGhost: {
    flexDirection: 'row',
    width: '100%',
    backgroundColor: theme.bgElevated,
    padding: 16,
    borderRadius: theme.radiusMd,
    justifyContent: 'center',
    alignItems: 'center',
    borderWidth: 2,
    borderColor: theme.forestLight,
  },
  btnGhostTxt: { color: theme.forestLight, fontWeight: '800', fontSize: 16 },
  hint: { flexDirection: 'row', alignItems: 'center', gap: 8, marginTop: 22 },
  hintText: { color: theme.muted, fontSize: 13 },
  previewBox: {
    height: 300,
    borderRadius: theme.radiusLg,
    overflow: 'hidden',
    backgroundColor: theme.border,
    marginBottom: 18,
  },
  preview: { width: '100%', height: '100%' },
  close: {
    position: 'absolute',
    top: 14,
    right: 14,
    backgroundColor: 'rgba(0,0,0,0.55)',
    padding: 10,
    borderRadius: 22,
  },
  overlay: {
    ...StyleSheet.absoluteFillObject,
    backgroundColor: 'rgba(15,45,38,0.72)',
    justifyContent: 'center',
    alignItems: 'center',
  },
  overlayText: { color: '#fff', marginTop: 14, fontWeight: '700' },
  runBtn: {
    backgroundColor: theme.forest,
    padding: 17,
    borderRadius: theme.radiusMd,
    alignItems: 'center',
  },
  runBtnText: { color: '#fff', fontWeight: '900', fontSize: 16 },
  result: {
    backgroundColor: theme.surface,
    borderRadius: theme.radiusLg,
    padding: 20,
    borderWidth: 1,
    borderColor: theme.border,
  },
  resultOk: { borderLeftWidth: 5, borderLeftColor: theme.success },
  resultBad: { borderLeftWidth: 5, borderLeftColor: theme.danger },
  resultHead: { flexDirection: 'row', alignItems: 'center', marginBottom: 16 },
  resultName: { fontSize: 18, fontWeight: '900', color: theme.ink },
  resultConf: { color: theme.muted, marginTop: 2, fontWeight: '600' },
  rec: { backgroundColor: theme.bg, padding: 16, borderRadius: theme.radiusSm, marginBottom: 14 },
  recTitle: { fontWeight: '900', color: theme.ink, marginBottom: 6 },
  recBody: { color: theme.inkSecondary, lineHeight: 22 },
  tagsWrap: { marginBottom: 14 },
  tagsTitle: { fontWeight: '900', color: theme.ink, marginBottom: 10 },
  tagsRow: { flexDirection: 'row', flexWrap: 'wrap', gap: 8 },
  tag: {
    backgroundColor: theme.bg,
    borderWidth: 1,
    borderColor: theme.border,
    borderRadius: 999,
    paddingHorizontal: 12,
    paddingVertical: 8,
  },
  tagText: { color: theme.forestLight, fontWeight: '800', fontSize: 13 },
  again: { padding: 14, alignItems: 'center', borderRadius: theme.radiusSm, borderWidth: 1, borderColor: theme.border },
  againText: { fontWeight: '800', color: theme.forestLight },
});
