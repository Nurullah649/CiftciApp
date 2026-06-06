import React, { useState, useEffect } from 'react';
import {
  View,
  Text,
  StyleSheet,
  TouchableOpacity,
  ScrollView,
  TextInput,
  Alert,
  ActivityIndicator,
} from 'react-native';
import { User, LogOut, Save } from 'lucide-react-native';
import { Screen } from '../components/ui/Screen';
import { StackHeader } from '../components/ui/StackHeader';
import { PrimaryButton } from '../components/ui/Buttons';
import { getUserProfile, updateUserProfile, logoutUser, deleteMyAccount } from '../services/apiService';
import { colors, spacing, radius, typography, shadow } from '../theme';

export default function ProfileScreen({ navigation }: any) {
  const [loading, setLoading] = useState(true);
  const [saving, setSaving] = useState(false);
  const [formData, setFormData] = useState({
    firstName: '',
    lastName: '',
    email: '',
    location: '',
  });

  useEffect(() => {
    loadProfile();
  }, []);

  const loadProfile = async () => {
    try {
      const data = await getUserProfile();
      setFormData({
        firstName: data.first_name || '',
        lastName: data.last_name || '',
        email: data.email || '',
        location: data.location || '',
      });
    } catch (error) {
      if (error instanceof Error && error.message.includes('Oturum')) handleLogout();
    } finally {
      setLoading(false);
    }
  };

  const handleSave = async () => {
    setSaving(true);
    try {
      await updateUserProfile(formData);
      Alert.alert('Başarılı', 'Profil bilgileriniz güncellendi.');
    } catch {
      Alert.alert('Hata', 'Güncelleme yapılamadı.');
    } finally {
      setSaving(false);
    }
  };

  const handleLogout = async () => {
    try {
      await logoutUser();
      navigation.reset({ index: 0, routes: [{ name: 'Login' }] });
    } catch {
      navigation.replace('Login');
    }
  };

  const handleDeleteAccount = () => {
    Alert.alert('Hesabı Sil', 'Hesabınız kalıcı olarak silinecek. Bu işlem geri alınamaz!', [
      { text: 'Vazgeç', style: 'cancel' },
      {
        text: 'Evet, Sil',
        style: 'destructive',
        onPress: async () => {
          try {
            await deleteMyAccount();
            Alert.alert('Hesap Silindi', 'Hesabınız silindi.', [
              { text: 'Tamam', onPress: () => handleLogout() },
            ]);
          } catch {
            Alert.alert('Hata', 'Hesap silinemedi.');
          }
        },
      },
    ]);
  };

  if (loading) {
    return (
      <Screen style={styles.center}>
        <ActivityIndicator size="large" color={colors.primary} />
      </Screen>
    );
  }

  return (
    <Screen edges={['top', 'left', 'right']}>
      <StackHeader title="Profilim" onBack={() => navigation.goBack()} />
      <ScrollView contentContainerStyle={styles.scroll}>
        <View style={styles.avatarSection}>
          <View style={styles.avatarCircle}>
            <User size={40} color={colors.primary} />
          </View>
          <Text style={styles.name}>
            {formData.firstName || 'İsimsiz'} {formData.lastName || 'Çiftçi'}
          </Text>
          <Text style={styles.role}>Çiftçi</Text>
        </View>

        <Text style={styles.sectionLabel}>KİŞİSEL BİLGİLER</Text>
        <View style={styles.formCard}>
          <Text style={styles.label}>Ad</Text>
          <TextInput
            style={styles.input}
            value={formData.firstName}
            onChangeText={(t) => setFormData({ ...formData, firstName: t })}
            placeholder="Adınız"
            placeholderTextColor={colors.textMuted}
          />
          <Text style={styles.label}>Soyad</Text>
          <TextInput
            style={styles.input}
            value={formData.lastName}
            onChangeText={(t) => setFormData({ ...formData, lastName: t })}
            placeholder="Soyadınız"
            placeholderTextColor={colors.textMuted}
          />
          <Text style={styles.label}>Konum</Text>
          <TextInput
            style={styles.input}
            value={formData.location}
            onChangeText={(t) => setFormData({ ...formData, location: t })}
            placeholder="Örn: Selçuklu, Konya"
            placeholderTextColor={colors.textMuted}
          />
          <Text style={styles.label}>E-posta</Text>
          <TextInput style={[styles.input, styles.inputDisabled]} value={formData.email} editable={false} />
        </View>

        <PrimaryButton
          label={saving ? 'Kaydediliyor...' : 'Kaydet'}
          onPress={handleSave}
          loading={saving}
          icon={!saving ? <Save size={20} color={colors.textOnPrimary} /> : undefined}
        />

        <TouchableOpacity style={styles.logoutBtn} onPress={handleLogout}>
          <LogOut size={20} color={colors.critical} />
          <Text style={styles.logoutText}>Çıkış Yap</Text>
        </TouchableOpacity>

        <TouchableOpacity style={styles.deleteBtn} onPress={handleDeleteAccount}>
          <Text style={styles.deleteText}>Hesabımı Sil</Text>
        </TouchableOpacity>
      </ScrollView>
    </Screen>
  );
}

const styles = StyleSheet.create({
  center: { justifyContent: 'center', alignItems: 'center' },
  scroll: { padding: spacing.lg, paddingBottom: 40 },
  avatarSection: { alignItems: 'center', marginBottom: spacing.lg },
  avatarCircle: {
    width: 96,
    height: 96,
    borderRadius: 48,
    backgroundColor: colors.primarySoft,
    alignItems: 'center',
    justifyContent: 'center',
    borderWidth: 4,
    borderColor: colors.surface,
    ...shadow.card,
  },
  name: { ...typography.h2, color: colors.text, marginTop: 12 },
  role: { ...typography.caption, color: colors.textMuted },
  sectionLabel: { ...typography.label, color: colors.textMuted, marginBottom: spacing.sm },
  formCard: {
    backgroundColor: colors.surface,
    borderRadius: radius.lg,
    padding: spacing.md,
    marginBottom: spacing.md,
    ...shadow.soft,
  },
  label: { ...typography.label, color: colors.textSecondary, marginBottom: 6, marginTop: 10 },
  input: {
    backgroundColor: colors.bg,
    borderWidth: 1,
    borderColor: colors.borderLight,
    borderRadius: radius.sm,
    padding: 14,
    fontSize: 16,
    color: colors.text,
  },
  inputDisabled: { color: colors.textMuted },
  logoutBtn: {
    flexDirection: 'row',
    backgroundColor: '#FEF2F2',
    padding: 16,
    borderRadius: radius.md,
    justifyContent: 'center',
    alignItems: 'center',
    gap: 8,
    marginTop: 12,
    borderWidth: 1,
    borderColor: '#FECACA',
  },
  logoutText: { color: colors.critical, fontWeight: '700', fontSize: 16 },
  deleteBtn: { padding: 16, alignItems: 'center', marginTop: 16 },
  deleteText: { color: colors.textMuted, fontSize: 14, textDecorationLine: 'underline' },
});
