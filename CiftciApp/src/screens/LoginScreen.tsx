import React, { useState } from 'react';
import {
  View,
  Text,
  TextInput,
  StyleSheet,
  ActivityIndicator,
  Alert,
  KeyboardAvoidingView,
  Platform,
  ScrollView,
  TouchableWithoutFeedback,
  Keyboard,
  StatusBar,
  Image,
} from 'react-native';
import { Eye, EyeOff, Sprout } from 'lucide-react-native';
import { Screen } from '../components/ui/Screen';
import { PrimaryButton, GhostButton } from '../components/ui/Buttons';
import { loginUser } from '../services/apiService';
import { colors, spacing, radius, typography, shadow } from '../theme';

export default function LoginScreen({ navigation }: any) {
  const [email, setEmail] = useState('');
  const [password, setPassword] = useState('');
  const [loading, setLoading] = useState(false);
  const [showPassword, setShowPassword] = useState(false);

  const handleLogin = async () => {
    if (!email || !password) {
      Alert.alert('Uyarı', 'E-posta ve şifre giriniz.');
      return;
    }
    setLoading(true);
    try {
      await loginUser(email, password);
      navigation.reset({ index: 0, routes: [{ name: 'Main' }] });
    } catch (error: any) {
      const message =
        error.message === 'Network request failed'
          ? 'Sunucuya ulaşılamadı. İnternet bağlantınızı kontrol edin.'
          : 'Giriş yapılamadı. Bilgilerinizi kontrol edin.';
      Alert.alert('Giriş Başarısız', message);
    } finally {
      setLoading(false);
    }
  };

  return (
    <Screen edges={['top', 'left', 'right', 'bottom']} variant="cream">
      <StatusBar barStyle="light-content" backgroundColor={colors.primaryDark} />
      <KeyboardAvoidingView behavior={Platform.OS === 'ios' ? 'padding' : 'height'} style={{ flex: 1 }}>
        <TouchableWithoutFeedback onPress={Keyboard.dismiss}>
          <ScrollView contentContainerStyle={styles.scroll} keyboardShouldPersistTaps="handled">
            <View style={styles.hero}>
              <View style={styles.heroOrb1} />
              <View style={styles.heroOrb2} />
              <View style={styles.logoRing}>
                <Image source={require('../../assets/icon.png')} style={styles.logo} />
              </View>
              <Text style={styles.heroTitle}>Çiftçi AI</Text>
              <Text style={styles.heroSub}>Tarlanız için akıllı rehber</Text>
              <View style={styles.badge}>
                <Sprout size={14} color={colors.accent} />
                <Text style={styles.badgeText}>Teşhis · Hava · Asistan</Text>
              </View>
            </View>

            <View style={styles.card}>
              <Text style={styles.cardTitle}>Hoş geldiniz</Text>
              <Text style={styles.cardSub}>Hesabınıza giriş yapın</Text>

              <Text style={styles.label}>E-posta</Text>
              <TextInput
                style={styles.input}
                placeholder="ornek@email.com"
                placeholderTextColor={colors.textMuted}
                value={email}
                onChangeText={setEmail}
                autoCapitalize="none"
                keyboardType="email-address"
              />

              <Text style={styles.label}>Şifre</Text>
              <View style={styles.passWrap}>
                <TextInput
                  style={styles.passInput}
                  placeholder="••••••••"
                  placeholderTextColor={colors.textMuted}
                  secureTextEntry={!showPassword}
                  value={password}
                  onChangeText={setPassword}
                />
                <TouchableWithoutFeedback onPress={() => setShowPassword(!showPassword)}>
                  <View style={styles.eye}>
                    {showPassword ? <EyeOff size={20} color={colors.textMuted} /> : <Eye size={20} color={colors.textMuted} />}
                  </View>
                </TouchableWithoutFeedback>
              </View>

              <PrimaryButton label="Giriş Yap" onPress={handleLogin} loading={loading} style={{ marginTop: spacing.md }} />

              <View style={styles.registerRow}>
                <Text style={styles.registerMuted}>Hesabınız yok mu?</Text>
                <GhostButton
                  label="Kayıt olun"
                  onPress={() => navigation.navigate('Register')}
                  textStyle={{ color: colors.primary, fontWeight: '800' }}
                />
              </View>
            </View>
          </ScrollView>
        </TouchableWithoutFeedback>
      </KeyboardAvoidingView>
    </Screen>
  );
}

const styles = StyleSheet.create({
  scroll: { flexGrow: 1 },
  hero: {
    backgroundColor: colors.primaryDark,
    paddingTop: spacing.xl,
    paddingBottom: 56,
    alignItems: 'center',
    overflow: 'hidden',
  },
  heroOrb1: {
    position: 'absolute',
    width: 200,
    height: 200,
    borderRadius: 100,
    backgroundColor: colors.primary,
    opacity: 0.4,
    top: -60,
    right: -40,
  },
  heroOrb2: {
    position: 'absolute',
    width: 120,
    height: 120,
    borderRadius: 60,
    backgroundColor: colors.accent,
    opacity: 0.25,
    bottom: 20,
    left: -30,
  },
  logoRing: {
    width: 96,
    height: 96,
    borderRadius: 48,
    backgroundColor: colors.surface,
    alignItems: 'center',
    justifyContent: 'center',
    borderWidth: 3,
    borderColor: colors.accent,
    ...shadow.card,
  },
  logo: { width: '62%', height: '62%', resizeMode: 'contain' },
  heroTitle: { fontSize: 30, fontWeight: '800', color: colors.textOnPrimary, marginTop: spacing.md },
  heroSub: { fontSize: 15, color: colors.accentSoft, marginTop: 4 },
  badge: {
    flexDirection: 'row',
    alignItems: 'center',
    gap: 6,
    marginTop: spacing.md,
    backgroundColor: 'rgba(255,255,255,0.1)',
    paddingHorizontal: 14,
    paddingVertical: 8,
    borderRadius: radius.full,
  },
  badgeText: { color: colors.textOnDark, fontSize: 12, fontWeight: '600' },
  card: {
    flex: 1,
    marginTop: -28,
    marginHorizontal: spacing.lg,
    backgroundColor: colors.surface,
    borderRadius: radius.xl,
    padding: spacing.lg,
    ...shadow.card,
  },
  cardTitle: { ...typography.h1, fontSize: 24, color: colors.text },
  cardSub: { ...typography.caption, color: colors.textMuted, marginBottom: spacing.lg },
  label: { ...typography.label, color: colors.textSecondary, marginBottom: 8, marginTop: 12 },
  input: {
    backgroundColor: colors.bg,
    borderRadius: radius.md,
    padding: 16,
    fontSize: 16,
    color: colors.text,
    borderWidth: 1,
    borderColor: colors.borderLight,
  },
  passWrap: {
    flexDirection: 'row',
    alignItems: 'center',
    backgroundColor: colors.bg,
    borderRadius: radius.md,
    borderWidth: 1,
    borderColor: colors.borderLight,
    paddingRight: 12,
  },
  passInput: { flex: 1, padding: 16, fontSize: 16, color: colors.text },
  eye: { padding: 8 },
  registerRow: { alignItems: 'center', marginTop: spacing.lg },
  registerMuted: { color: colors.textMuted, fontSize: 14 },
});
