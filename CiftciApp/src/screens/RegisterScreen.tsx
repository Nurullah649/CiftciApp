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
} from 'react-native';
import { UserPlus, ArrowLeft } from 'lucide-react-native';
import { registerUser } from '../services/apiService';
import { theme } from '../theme/theme';

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
      <StatusBar barStyle="light-content" backgroundColor={theme.forest} />
      <KeyboardAvoidingView behavior={Platform.OS === 'ios' ? 'padding' : 'height'} style={{ flex: 1 }}>
        <TouchableWithoutFeedback onPress={Keyboard.dismiss}>
          <ScrollView contentContainerStyle={styles.scroll} showsVerticalScrollIndicator={false}>
            <View style={styles.curve}>
              <TouchableOpacity onPress={() => navigation.goBack()} style={styles.back}>
                <ArrowLeft size={22} color="#fff" />
              </TouchableOpacity>
              <Text style={styles.kicker}>HESAP</Text>
              <View style={styles.heroIcon}>
                <UserPlus size={32} color={theme.forest} />
              </View>
              <Text style={styles.heroTitle}>Kayıt ol</Text>
              <Text style={styles.heroSub}>Birkaç alanla başlayın</Text>
            </View>

            <View style={styles.sheet}>
              <View style={styles.row}>
                <View style={{ flex: 1, marginRight: 8 }}>
                  <Text style={styles.label}>Ad</Text>
                  <TextInput
                    style={styles.input}
                    placeholder="Ali"
                    placeholderTextColor={theme.muted}
                    value={formData.firstName}
                    onChangeText={(t) => setFormData({ ...formData, firstName: t })}
                  />
                </View>
                <View style={{ flex: 1, marginLeft: 8 }}>
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

              <TouchableOpacity style={[styles.cta, loading && { opacity: 0.75 }]} onPress={handleRegister} disabled={loading}>
                {loading ? <ActivityIndicator color="#fff" /> : <Text style={styles.ctaText}>Hesap oluştur</Text>}
              </TouchableOpacity>

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
  scroll: { flexGrow: 1, paddingBottom: 36 },
  curve: {
    backgroundColor: theme.forest,
    borderBottomLeftRadius: 36,
    borderBottomRightRadius: 36,
    paddingHorizontal: 22,
    paddingTop: 4,
    paddingBottom: 96,
  },
  back: { alignSelf: 'flex-start', padding: 10, marginBottom: 4 },
  kicker: { color: theme.tabActive, fontSize: 10, fontWeight: '900', letterSpacing: 2 },
  heroIcon: {
    width: 64,
    height: 64,
    borderRadius: 20,
    backgroundColor: theme.tabActive,
    justifyContent: 'center',
    alignItems: 'center',
    marginTop: 12,
    marginBottom: 14,
  },
  heroTitle: { fontSize: 30, fontWeight: '900', color: '#fff' },
  heroSub: { fontSize: 15, color: 'rgba(255,255,255,0.78)', marginTop: 8 },
  sheet: {
    marginTop: -68,
    marginHorizontal: 20,
    backgroundColor: theme.surface,
    borderRadius: theme.radiusLg,
    padding: 20,
    borderWidth: 1,
    borderColor: theme.border,
    shadowColor: theme.shadow,
    shadowOffset: { width: 0, height: 12 },
    shadowOpacity: 1,
    shadowRadius: 24,
    elevation: 8,
  },
  row: { flexDirection: 'row', marginBottom: 4 },
  label: { fontSize: 12, fontWeight: '800', color: theme.inkSecondary, marginBottom: 6, marginTop: 10 },
  input: {
    backgroundColor: theme.bg,
    borderRadius: theme.radiusMd,
    padding: 14,
    fontSize: 16,
    color: theme.ink,
    borderWidth: 1,
    borderColor: theme.border,
  },
  cta: {
    backgroundColor: theme.accent,
    paddingVertical: 16,
    borderRadius: theme.radiusMd,
    alignItems: 'center',
    marginTop: 20,
  },
  ctaText: { color: '#fff', fontSize: 17, fontWeight: '900' },
  loginLink: { alignItems: 'center', marginTop: 18 },
  loginLinkText: { color: theme.forestLight, fontWeight: '900', fontSize: 15 },
});
