import React, { useState } from 'react';
import {
  Alert,
  Image,
  Keyboard,
  KeyboardAvoidingView,
  Platform,
  SafeAreaView,
  ScrollView,
  StatusBar,
  StyleSheet,
  Text,
  TextInput,
  TouchableOpacity,
  TouchableWithoutFeedback,
  View,
} from 'react-native';
import { Eye, EyeOff, ShieldCheck } from 'lucide-react-native';
import { loginUser } from '../services/apiService';
import { getApiBaseUrl } from '../config/apiBaseUrl';
import { theme } from '../theme/theme';
import { AmbientBackdrop } from '../components/AmbientBackdrop';
import { AppButton } from '../components/AppButton';

export default function LoginScreen({ navigation }: any) {
  const [email, setEmail] = useState('');
  const [password, setPassword] = useState('');
  const [loading, setLoading] = useState(false);
  const [showPassword, setShowPassword] = useState(false);

  const handleLogin = async () => {
    if (!email || !password) {
      Alert.alert('Eksik bilgi', 'E-posta ve şifre girin.');
      return;
    }

    setLoading(true);
    try {
      await loginUser(email, password);
      navigation.reset({ index: 0, routes: [{ name: 'Main' }] });
    } catch (error: any) {
      const net = error?.message === 'Network request failed';
      const base = getApiBaseUrl();
      const hint = __DEV__ ? ` API: ${base}` : '';
      Alert.alert(
        'Giriş yapılamadı',
        net ? `Sunucuya ulaşılamadı.${hint}` : error?.message || 'E-posta veya şifre hatalı olabilir.'
      );
    } finally {
      setLoading(false);
    }
  };

  return (
    <SafeAreaView style={styles.safe}>
      <StatusBar barStyle="dark-content" backgroundColor={theme.bg} />
      <AmbientBackdrop />
      <KeyboardAvoidingView behavior={Platform.OS === 'ios' ? 'padding' : 'height'} style={{ flex: 1 }}>
        <TouchableWithoutFeedback onPress={Keyboard.dismiss}>
          <ScrollView contentContainerStyle={styles.scroll} keyboardShouldPersistTaps="handled" showsVerticalScrollIndicator={false}>
            <View style={styles.hero}>
              <View style={styles.brandChip}>
                <Text style={styles.brandChipText}>ÇİFTÇİ APP</Text>
              </View>
              <Text style={styles.heroTitle}>Tarla yönetimini sadeleştirin.</Text>
              <Text style={styles.heroSub}>
                Hastalık analizi, görev planı ve ziraat asistanı tek bir akışta.
              </Text>
            </View>

            <View style={styles.card}>
              <View style={styles.cardHead}>
                <View style={styles.logoWrap}>
                  <Image source={require('../../assets/icon.png')} style={styles.logo} />
                </View>
                <View style={{ flex: 1 }}>
                  <Text style={styles.cardEyebrow}>GÜVENLİ GİRİŞ</Text>
                  <Text style={styles.cardTitle}>Hesabınıza devam edin</Text>
                </View>
              </View>

              <View style={styles.notice}>
                <ShieldCheck size={16} color={theme.success} />
                <Text style={styles.noticeText}>Cihaz, konum ve görev verileri hesabınızla eşlenir.</Text>
              </View>

              <Text style={styles.label}>E-posta</Text>
              <TextInput
                style={styles.input}
                placeholder="ornek@email.com"
                placeholderTextColor={theme.muted}
                value={email}
                onChangeText={setEmail}
                autoCapitalize="none"
                keyboardType="email-address"
                autoCorrect={false}
              />

              <Text style={styles.label}>Şifre</Text>
              <View style={styles.passwordRow}>
                <TextInput
                  style={styles.passwordInput}
                  placeholder="••••••••"
                  placeholderTextColor={theme.muted}
                  secureTextEntry={!showPassword}
                  value={password}
                  onChangeText={setPassword}
                  autoCapitalize="none"
                />
                <TouchableOpacity onPress={() => setShowPassword(!showPassword)} hitSlop={12}>
                  {showPassword ? <EyeOff size={20} color={theme.muted} /> : <Eye size={20} color={theme.muted} />}
                </TouchableOpacity>
              </View>

              <AppButton
                label="Giriş yap"
                onPress={handleLogin}
                loading={loading}
                style={styles.submitButton}
              />

              <View style={styles.footerRow}>
                <Text style={styles.footerText}>Hesabın yok mu? </Text>
                <TouchableOpacity onPress={() => navigation.navigate('Register')}>
                  <Text style={styles.footerLink}>Kayıt ol</Text>
                </TouchableOpacity>
              </View>
            </View>
          </ScrollView>
        </TouchableWithoutFeedback>
      </KeyboardAvoidingView>
    </SafeAreaView>
  );
}

const styles = StyleSheet.create({
  safe: { flex: 1, backgroundColor: theme.bg },
  scroll: { flexGrow: 1, padding: 20, justifyContent: 'center' },
  hero: { marginBottom: 18 },
  brandChip: {
    alignSelf: 'flex-start',
    backgroundColor: theme.accentSoft,
    borderRadius: 999,
    paddingHorizontal: 12,
    paddingVertical: 8,
  },
  brandChipText: { color: theme.accent, fontSize: 11, fontWeight: '900', letterSpacing: 1.1 },
  heroTitle: {
    color: theme.ink,
    fontSize: 34,
    lineHeight: 38,
    fontWeight: '900',
    marginTop: 16,
    maxWidth: 280,
  },
  heroSub: {
    color: theme.inkSoft,
    fontSize: 16,
    lineHeight: 24,
    marginTop: 12,
    maxWidth: 300,
  },
  card: {
    backgroundColor: theme.surface,
    borderRadius: theme.radiusXl,
    padding: 20,
    borderWidth: 1,
    borderColor: theme.border,
    shadowColor: theme.shadowStrong,
    shadowOffset: { width: 0, height: 12 },
    shadowOpacity: 1,
    shadowRadius: 24,
    elevation: 8,
  },
  cardHead: { flexDirection: 'row', alignItems: 'center', gap: 14, marginBottom: 16 },
  logoWrap: {
    width: 64,
    height: 64,
    borderRadius: 18,
    backgroundColor: theme.accentSoft,
    justifyContent: 'center',
    alignItems: 'center',
  },
  logo: { width: '54%', height: '54%', resizeMode: 'contain' },
  cardEyebrow: { color: theme.muted, fontSize: 11, fontWeight: '900', letterSpacing: 1.2 },
  cardTitle: { color: theme.ink, fontSize: 24, fontWeight: '900', marginTop: 6 },
  notice: {
    flexDirection: 'row',
    alignItems: 'center',
    gap: 8,
    backgroundColor: theme.surfaceStrong,
    borderRadius: theme.radiusMd,
    padding: 12,
    marginBottom: 6,
  },
  noticeText: { flex: 1, color: theme.inkSoft, fontSize: 13, lineHeight: 19 },
  label: {
    color: theme.inkSecondary,
    fontSize: 12,
    fontWeight: '900',
    marginTop: 14,
    marginBottom: 8,
    letterSpacing: 0.4,
  },
  input: {
    backgroundColor: theme.surfaceMuted,
    borderRadius: theme.radiusMd,
    borderWidth: 1,
    borderColor: theme.border,
    paddingHorizontal: 15,
    paddingVertical: 15,
    color: theme.ink,
    fontSize: 16,
  },
  passwordRow: {
    flexDirection: 'row',
    alignItems: 'center',
    backgroundColor: theme.surfaceMuted,
    borderRadius: theme.radiusMd,
    borderWidth: 1,
    borderColor: theme.border,
    paddingRight: 14,
  },
  passwordInput: {
    flex: 1,
    paddingHorizontal: 15,
    paddingVertical: 15,
    color: theme.ink,
    fontSize: 16,
  },
  submitButton: { marginTop: 20 },
  footerRow: { flexDirection: 'row', justifyContent: 'center', marginTop: 18 },
  footerText: { color: theme.muted, fontSize: 15 },
  footerLink: { color: theme.accent, fontSize: 15, fontWeight: '900' },
});
