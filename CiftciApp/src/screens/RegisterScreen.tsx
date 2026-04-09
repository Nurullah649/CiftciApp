import React, { useState } from 'react';
import {
  Alert,
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
import { ArrowLeft, UserPlus } from 'lucide-react-native';
import { registerUser } from '../services/apiService';
import { theme } from '../theme/theme';
import { AmbientBackdrop } from '../components/AmbientBackdrop';
import { AppButton } from '../components/AppButton';

export default function RegisterScreen({ navigation }: any) {
  const [formData, setFormData] = useState({
    firstName: '',
    lastName: '',
    email: '',
    password: '',
  });
  const [loading, setLoading] = useState(false);

  const handleRegister = async () => {
    if (!formData.email || !formData.password || !formData.firstName) {
      Alert.alert('Eksik bilgi', 'Ad, e-posta ve şifre gerekli.');
      return;
    }

    setLoading(true);
    try {
      await registerUser(formData);
      Alert.alert('Kayıt tamam', 'Giriş yapabilirsiniz.', [{ text: 'Tamam', onPress: () => navigation.navigate('Login') }]);
    } catch (error: any) {
      Alert.alert('Hata', error?.message || 'Kayıt başarısız.');
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
          <ScrollView contentContainerStyle={styles.scroll} showsVerticalScrollIndicator={false}>
            <TouchableOpacity onPress={() => navigation.goBack()} style={styles.backButton}>
              <ArrowLeft size={20} color={theme.ink} />
            </TouchableOpacity>

            <View style={styles.hero}>
              <Text style={styles.heroEyebrow}>YENİ HESAP</Text>
              <Text style={styles.heroTitle}>Sisteme birkaç adımda katılın.</Text>
              <Text style={styles.heroSub}>Temel bilgileri girin, kalan ayarlar uygulama içinde düzenlenebilir.</Text>
            </View>

            <View style={styles.card}>
              <View style={styles.iconWrap}>
                <UserPlus size={26} color={theme.accent} />
              </View>

              <View style={styles.row}>
                <View style={styles.col}>
                  <Text style={styles.label}>Ad</Text>
                  <TextInput
                    style={styles.input}
                    placeholder="Ali"
                    placeholderTextColor={theme.muted}
                    value={formData.firstName}
                    onChangeText={(t) => setFormData({ ...formData, firstName: t })}
                  />
                </View>
                <View style={styles.col}>
                  <Text style={styles.label}>Soyad</Text>
                  <TextInput
                    style={styles.input}
                    placeholder="Yılmaz"
                    placeholderTextColor={theme.muted}
                    value={formData.lastName}
                    onChangeText={(t) => setFormData({ ...formData, lastName: t })}
                  />
                </View>
              </View>

              <Text style={styles.label}>E-posta</Text>
              <TextInput
                style={styles.input}
                placeholder="ornek@email.com"
                placeholderTextColor={theme.muted}
                value={formData.email}
                onChangeText={(t) => setFormData({ ...formData, email: t })}
                autoCapitalize="none"
                keyboardType="email-address"
              />

              <Text style={styles.label}>Şifre</Text>
              <TextInput
                style={styles.input}
                placeholder="••••••"
                placeholderTextColor={theme.muted}
                secureTextEntry
                value={formData.password}
                onChangeText={(t) => setFormData({ ...formData, password: t })}
              />

              <AppButton
                label="Hesabı oluştur"
                onPress={handleRegister}
                loading={loading}
                style={styles.submitButton}
              />

              <TouchableOpacity onPress={() => navigation.navigate('Login')} style={styles.loginLink}>
                <Text style={styles.loginLinkText}>Zaten hesabım var</Text>
              </TouchableOpacity>
            </View>
          </ScrollView>
        </TouchableWithoutFeedback>
      </KeyboardAvoidingView>
    </SafeAreaView>
  );
}

const styles = StyleSheet.create({
  safe: { flex: 1, backgroundColor: theme.bg },
  scroll: { flexGrow: 1, padding: 20 },
  backButton: {
    width: 46,
    height: 46,
    borderRadius: 16,
    backgroundColor: theme.surface,
    borderWidth: 1,
    borderColor: theme.border,
    justifyContent: 'center',
    alignItems: 'center',
    marginBottom: 18,
  },
  hero: { marginBottom: 18 },
  heroEyebrow: { color: theme.muted, fontSize: 11, fontWeight: '900', letterSpacing: 1.2 },
  heroTitle: { color: theme.ink, fontSize: 32, lineHeight: 36, fontWeight: '900', marginTop: 10, maxWidth: 290 },
  heroSub: { color: theme.inkSoft, fontSize: 16, lineHeight: 24, marginTop: 10, maxWidth: 300 },
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
  iconWrap: {
    width: 58,
    height: 58,
    borderRadius: 18,
    backgroundColor: theme.accentSoft,
    justifyContent: 'center',
    alignItems: 'center',
    marginBottom: 8,
  },
  row: { flexDirection: 'row', gap: 12 },
  col: { flex: 1 },
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
  submitButton: { marginTop: 22 },
  loginLink: { alignItems: 'center', marginTop: 18 },
  loginLinkText: { color: theme.accent, fontWeight: '900', fontSize: 15 },
});
