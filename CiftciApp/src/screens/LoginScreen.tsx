import React, { useState } from 'react';
import {
  View,
  Text,
  TextInput,
  TouchableOpacity,
  StyleSheet,
  ActivityIndicator,
  Alert,
  SafeAreaView,
  KeyboardAvoidingView,
  Platform,
  ScrollView,
  TouchableWithoutFeedback,
  Keyboard,
  StatusBar,
  Image,
} from 'react-native';
import { Eye, EyeOff } from 'lucide-react-native';
import { loginUser } from '../services/apiService';
import { getApiBaseUrl } from '../config/apiBaseUrl';
import { theme } from '../theme/theme';

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
      <StatusBar barStyle="light-content" backgroundColor={theme.forest} />
      <KeyboardAvoidingView behavior={Platform.OS === 'ios' ? 'padding' : 'height'} style={{ flex: 1 }}>
        <TouchableWithoutFeedback onPress={Keyboard.dismiss}>
          <ScrollView contentContainerStyle={styles.scroll} keyboardShouldPersistTaps="handled" showsVerticalScrollIndicator={false}>
            <View style={styles.hero}>
              <View style={styles.heroGlow} />
              <Text style={styles.brand}>ÇİFTÇİ</Text>
              <Text style={styles.heroLine}>Asistan</Text>
              <Text style={styles.heroSub}>Hava, tarla ve takvim — tek yerde</Text>
            </View>

            <View style={styles.sheet}>
              <View style={styles.logoWrap}>
                <Image source={require('../../assets/icon.png')} style={styles.logo} />
              </View>
              <Text style={styles.title}>Giriş</Text>
              <Text style={styles.sub}>Hesabınla devam et</Text>

              <View style={styles.form}>
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
                <View style={styles.passRow}>
                  <TextInput
                    style={styles.passInput}
                    placeholder="••••••••"
                    placeholderTextColor={theme.muted}
                    secureTextEntry={!showPassword}
                    value={password}
                    onChangeText={setPassword}
                    autoCapitalize="none"
                  />
                  <TouchableOpacity onPress={() => setShowPassword(!showPassword)} hitSlop={12}>
                    {showPassword ? <EyeOff size={22} color={theme.muted} /> : <Eye size={22} color={theme.muted} />}
                  </TouchableOpacity>
                </View>

                <TouchableOpacity style={[styles.cta, loading && { opacity: 0.75 }]} onPress={handleLogin} disabled={loading}>
                  {loading ? <ActivityIndicator color="#fff" /> : <Text style={styles.ctaText}>Giriş yap</Text>}
                </TouchableOpacity>
              </View>

              <View style={styles.footerRow}>
                <Text style={styles.footerMuted}>Hesabın yok mu? </Text>
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
  scroll: { flexGrow: 1, paddingBottom: 40 },
  hero: {
    minHeight: 220,
    backgroundColor: theme.forest,
    paddingHorizontal: 28,
    paddingTop: 28,
    paddingBottom: 56,
    borderBottomLeftRadius: 36,
    borderBottomRightRadius: 36,
    justifyContent: 'flex-end',
  },
  heroGlow: {
    position: 'absolute',
    top: 20,
    right: -40,
    width: 160,
    height: 160,
    borderRadius: 80,
    backgroundColor: 'rgba(13,148,136,0.2)',
  },
  brand: { color: theme.tabActive, fontSize: 12, fontWeight: '900', letterSpacing: 4 },
  heroLine: { color: '#fff', fontSize: 34, fontWeight: '900', marginTop: 8 },
  heroSub: { color: 'rgba(255,255,255,0.75)', fontSize: 15, marginTop: 10, maxWidth: 280 },
  sheet: {
    marginTop: -44,
    marginHorizontal: 20,
    backgroundColor: theme.surface,
    borderRadius: theme.radiusLg,
    paddingHorizontal: 22,
    paddingTop: 26,
    paddingBottom: 28,
    borderWidth: 1,
    borderColor: theme.border,
    shadowColor: theme.shadow,
    shadowOffset: { width: 0, height: 14 },
    shadowOpacity: 1,
    shadowRadius: 28,
    elevation: 10,
  },
  logoWrap: {
    alignSelf: 'center',
    width: 76,
    height: 76,
    borderRadius: 22,
    backgroundColor: theme.skyTint,
    justifyContent: 'center',
    alignItems: 'center',
    marginBottom: 16,
    borderWidth: 2,
    borderColor: theme.forestLight,
  },
  logo: { width: '55%', height: '55%', resizeMode: 'contain' },
  title: { fontSize: 26, fontWeight: '900', color: theme.ink, textAlign: 'center' },
  sub: { fontSize: 15, color: theme.muted, textAlign: 'center', marginTop: 6, marginBottom: 4 },
  form: { gap: 2 },
  label: { fontSize: 12, fontWeight: '800', color: theme.inkSecondary, marginBottom: 4, marginTop: 12 },
  input: {
    backgroundColor: theme.bg,
    borderRadius: theme.radiusMd,
    padding: 15,
    fontSize: 16,
    color: theme.ink,
    borderWidth: 1,
    borderColor: theme.border,
  },
  passRow: {
    flexDirection: 'row',
    alignItems: 'center',
    backgroundColor: theme.bg,
    borderRadius: theme.radiusMd,
    borderWidth: 1,
    borderColor: theme.border,
    paddingRight: 12,
  },
  passInput: { flex: 1, padding: 15, fontSize: 16, color: theme.ink },
  cta: {
    backgroundColor: theme.accent,
    paddingVertical: 16,
    borderRadius: theme.radiusMd,
    alignItems: 'center',
    marginTop: 22,
  },
  ctaText: { color: '#fff', fontSize: 17, fontWeight: '900' },
  footerRow: { flexDirection: 'row', justifyContent: 'center', marginTop: 22 },
  footerMuted: { color: theme.muted, fontSize: 15 },
  footerLink: { color: theme.forestLight, fontSize: 15, fontWeight: '900' },
});
