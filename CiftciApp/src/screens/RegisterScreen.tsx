import React, { useState } from 'react';
import {
  View,
  Text,
  TextInput,
  TouchableOpacity,
  StyleSheet,
  Alert,
  KeyboardAvoidingView,
  Platform,
  ScrollView,
  TouchableWithoutFeedback,
  Keyboard,
  StatusBar,
} from 'react-native';
import { ArrowLeft, UserPlus } from 'lucide-react-native';
import { Screen } from '../components/ui/Screen';
import { PrimaryButton, GhostButton } from '../components/ui/Buttons';
import { registerUser } from '../services/apiService';
import { colors, spacing, radius, typography, shadow } from '../theme';

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
      Alert.alert('Eksik Bilgi', 'Lütfen en az Ad, E-posta ve Şifre alanlarını doldurun.');
      return;
    }
    setLoading(true);
    try {
      await registerUser(formData);
      Alert.alert('Kayıt Başarılı', 'Hesabınız oluşturuldu.', [
        { text: 'Giriş Yap', onPress: () => navigation.navigate('Login') },
      ]);
    } catch (error: any) {
      Alert.alert('Hata', error.message || 'Kayıt işlemi başarısız.');
    } finally {
      setLoading(false);
    }
  };

  return (
    <Screen edges={['top', 'left', 'right', 'bottom']}>
      <StatusBar barStyle="dark-content" backgroundColor={colors.bg} />
      <KeyboardAvoidingView behavior={Platform.OS === 'ios' ? 'padding' : 'height'} style={{ flex: 1 }}>
        <TouchableWithoutFeedback onPress={Keyboard.dismiss}>
          <ScrollView contentContainerStyle={styles.scroll} keyboardShouldPersistTaps="handled">
            <TouchableOpacity onPress={() => navigation.goBack()} style={styles.backBtn}>
              <ArrowLeft size={22} color={colors.text} />
            </TouchableOpacity>

            <View style={styles.iconWrap}>
              <UserPlus size={36} color={colors.primary} />
            </View>
            <Text style={styles.title}>Hesap Oluştur</Text>
            <Text style={styles.subtitle}>Çiftçi Asistanına katılın</Text>

            <View style={styles.card}>
              <View style={styles.row}>
                <View style={styles.half}>
                  <Text style={styles.label}>Ad</Text>
                  <TextInput
                    style={styles.input}
                    placeholder="Ali"
                    placeholderTextColor={colors.textMuted}
                    value={formData.firstName}
                    onChangeText={(t) => setFormData({ ...formData, firstName: t })}
                  />
                </View>
                <View style={styles.half}>
                  <Text style={styles.label}>Soyad</Text>
                  <TextInput
                    style={styles.input}
                    placeholder="Yılmaz"
                    placeholderTextColor={colors.textMuted}
                    value={formData.lastName}
                    onChangeText={(t) => setFormData({ ...formData, lastName: t })}
                  />
                </View>
              </View>

              <Text style={styles.label}>E-posta</Text>
              <TextInput
                style={styles.input}
                placeholder="ornek@email.com"
                placeholderTextColor={colors.textMuted}
                value={formData.email}
                onChangeText={(t) => setFormData({ ...formData, email: t })}
                autoCapitalize="none"
                keyboardType="email-address"
              />

              <Text style={styles.label}>Şifre</Text>
              <TextInput
                style={styles.input}
                placeholder="••••••"
                placeholderTextColor={colors.textMuted}
                secureTextEntry
                value={formData.password}
                onChangeText={(t) => setFormData({ ...formData, password: t })}
              />

              <PrimaryButton label="Kayıt Ol" onPress={handleRegister} loading={loading} style={{ marginTop: spacing.md }} />
            </View>

            <View style={styles.loginRow}>
              <Text style={styles.loginMuted}>Zaten hesabınız var mı?</Text>
              <GhostButton
                label="Giriş Yap"
                onPress={() => navigation.navigate('Login')}
                textStyle={{ color: colors.primary, fontWeight: '800' }}
              />
            </View>
          </ScrollView>
        </TouchableWithoutFeedback>
      </KeyboardAvoidingView>
    </Screen>
  );
}

const styles = StyleSheet.create({
  scroll: { padding: spacing.lg, paddingBottom: 40 },
  backBtn: {
    width: 44,
    height: 44,
    borderRadius: 22,
    backgroundColor: colors.surface,
    alignItems: 'center',
    justifyContent: 'center',
    marginBottom: spacing.lg,
    borderWidth: 1,
    borderColor: colors.borderLight,
  },
  iconWrap: {
    width: 72,
    height: 72,
    borderRadius: 20,
    backgroundColor: colors.primarySoft,
    alignItems: 'center',
    justifyContent: 'center',
    alignSelf: 'center',
    marginBottom: spacing.md,
  },
  title: { ...typography.h1, color: colors.text, textAlign: 'center' },
  subtitle: { ...typography.caption, color: colors.textMuted, textAlign: 'center', marginBottom: spacing.lg },
  card: {
    backgroundColor: colors.surface,
    borderRadius: radius.xl,
    padding: spacing.lg,
    ...shadow.card,
  },
  row: { flexDirection: 'row', gap: 12 },
  half: { flex: 1 },
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
  loginRow: { alignItems: 'center', marginTop: spacing.lg },
  loginMuted: { color: colors.textMuted, fontSize: 14 },
});
