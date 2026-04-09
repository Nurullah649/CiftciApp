import React, { useEffect, useState } from 'react';
import { ActivityIndicator, Alert, SafeAreaView, ScrollView, StyleSheet, Text, TextInput, View } from 'react-native';
import { User } from 'lucide-react-native';
import { deleteMyAccount, getUserProfile, logoutUser, updateUserProfile } from '../services/apiService';
import { theme } from '../theme/theme';
import { StackHeader } from '../components/StackHeader';
import { AmbientBackdrop } from '../components/AmbientBackdrop';
import { AppButton } from '../components/AppButton';

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
    } catch (e: any) {
      if (e?.message?.includes('Oturum')) {
        handleLogout();
      }
    } finally {
      setLoading(false);
    }
  };

  const handleSave = async () => {
    setSaving(true);
    try {
      await updateUserProfile(formData);
      Alert.alert('Kaydedildi', 'Profiliniz güncellendi.');
    } catch {
      Alert.alert('Hata', 'Güncellenemedi.');
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
    Alert.alert('Hesabı sil', 'Tüm verileriniz sunucudan silinecek.', [
      { text: 'Vazgeç', style: 'cancel' },
      {
        text: 'Sil',
        style: 'destructive',
        onPress: async () => {
          try {
            await deleteMyAccount();
            Alert.alert('Tamam', 'Hesap silindi.', [{ text: 'OK', onPress: () => handleLogout() }]);
          } catch {
            Alert.alert('Hata', 'İşlem başarısız.');
          }
        },
      },
    ]);
  };

  if (loading) {
    return (
      <View style={styles.center}>
        <ActivityIndicator size="large" color={theme.accent} />
      </View>
    );
  }

  return (
    <SafeAreaView style={styles.safe}>
      <AmbientBackdrop />
      <StackHeader title="Profil" eyebrow="HESAP AYARLARI" onBack={() => navigation.goBack()} />

      <ScrollView contentContainerStyle={{ padding: 20, paddingBottom: 40 }} showsVerticalScrollIndicator={false}>
        <View style={styles.heroCard}>
          <View style={styles.avatar}>
            <User size={36} color={theme.accent} />
          </View>
          <Text style={styles.name}>
            {formData.firstName || 'Çiftçi'} {formData.lastName || ''}
          </Text>
          <Text style={styles.mail}>{formData.email}</Text>
        </View>

        <View style={styles.formCard}>
          <Text style={styles.sectionTitle}>Kişisel bilgiler</Text>

          <Text style={styles.label}>Ad</Text>
          <TextInput
            style={styles.input}
            value={formData.firstName}
            onChangeText={(t) => setFormData({ ...formData, firstName: t })}
            placeholder="Ad"
            placeholderTextColor={theme.muted}
          />

          <Text style={styles.label}>Soyad</Text>
          <TextInput
            style={styles.input}
            value={formData.lastName}
            onChangeText={(t) => setFormData({ ...formData, lastName: t })}
            placeholder="Soyad"
            placeholderTextColor={theme.muted}
          />

          <Text style={styles.label}>Konum</Text>
          <TextInput
            style={styles.input}
            value={formData.location}
            onChangeText={(t) => setFormData({ ...formData, location: t })}
            placeholder="İl / ilçe"
            placeholderTextColor={theme.muted}
          />

          <Text style={styles.label}>E-posta</Text>
          <TextInput style={[styles.input, styles.inputDisabled]} value={formData.email} editable={false} />
        </View>

        <AppButton label="Değişiklikleri kaydet" onPress={handleSave} loading={saving} style={styles.mainButton} />
        <AppButton label="Çıkış yap" onPress={handleLogout} variant="secondary" style={styles.secondaryButton} />
        <AppButton label="Hesabı kalıcı sil" onPress={handleDeleteAccount} variant="danger" />
      </ScrollView>
    </SafeAreaView>
  );
}

const styles = StyleSheet.create({
  safe: { flex: 1, backgroundColor: theme.bg },
  center: { flex: 1, justifyContent: 'center', alignItems: 'center', backgroundColor: theme.bg },
  heroCard: {
    backgroundColor: theme.surface,
    borderRadius: theme.radiusXl,
    padding: 20,
    borderWidth: 1,
    borderColor: theme.border,
    alignItems: 'center',
    marginBottom: 16,
  },
  avatar: {
    width: 88,
    height: 88,
    borderRadius: 28,
    backgroundColor: theme.accentSoft,
    justifyContent: 'center',
    alignItems: 'center',
    marginBottom: 16,
  },
  name: { color: theme.ink, fontSize: 24, fontWeight: '900' },
  mail: { color: theme.inkSoft, fontSize: 14, marginTop: 6 },
  formCard: {
    backgroundColor: theme.surface,
    borderRadius: theme.radiusXl,
    padding: 18,
    borderWidth: 1,
    borderColor: theme.border,
  },
  sectionTitle: { color: theme.ink, fontSize: 20, fontWeight: '900' },
  label: { color: theme.inkSecondary, fontSize: 12, fontWeight: '900', marginTop: 14, marginBottom: 8, letterSpacing: 0.4 },
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
  inputDisabled: { color: theme.muted },
  mainButton: { marginTop: 16 },
  secondaryButton: { marginTop: 10, marginBottom: 10 },
});
