import React, { useState, useEffect } from 'react';
import { View, Text, StyleSheet, TouchableOpacity, ScrollView, TextInput, Alert, ActivityIndicator } from 'react-native';
import { SafeAreaView } from 'react-native-safe-area-context';
import { User, LogOut, Save } from 'lucide-react-native';
import { getUserProfile, updateUserProfile, logoutUser, deleteMyAccount } from '../services/apiService';
import { theme } from '../theme/theme';
import { StackHeader } from '../components/StackHeader';

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
        <ActivityIndicator size="large" color={theme.forestLight} />
      </View>
    );
  }

  return (
    <SafeAreaView style={styles.safe} edges={['top']}>
      <StackHeader title="Profil" onBack={() => navigation.goBack()} />

      <ScrollView contentContainerStyle={{ padding: 20, paddingBottom: 40 }} showsVerticalScrollIndicator={false}>
        <View style={styles.hero}>
          <View style={styles.avatar}>
            <User size={40} color={theme.forest} />
          </View>
          <Text style={styles.name}>
            {formData.firstName || 'Çiftçi'} {formData.lastName || ''}
          </Text>
          <Text style={styles.role}>Hesap bilgileriniz</Text>
        </View>

        <Text style={styles.sectionLabel}>Kişisel</Text>
        <View style={styles.card}>
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

        <TouchableOpacity style={styles.save} onPress={handleSave} disabled={saving} activeOpacity={0.9}>
          {saving ? <ActivityIndicator color="#fff" /> : <Save size={20} color="#fff" />}
          <Text style={styles.saveText}>{saving ? 'Kaydediliyor...' : 'Kaydet'}</Text>
        </TouchableOpacity>

        <TouchableOpacity style={styles.logout} onPress={handleLogout} activeOpacity={0.9}>
          <LogOut size={20} color={theme.danger} />
          <Text style={styles.logoutText}>Çıkış yap</Text>
        </TouchableOpacity>

        <TouchableOpacity onPress={handleDeleteAccount} style={styles.del}>
          <Text style={styles.delText}>Hesabı kalıcı sil</Text>
        </TouchableOpacity>
      </ScrollView>
    </SafeAreaView>
  );
}

const styles = StyleSheet.create({
  safe: { flex: 1, backgroundColor: theme.bg },
  center: { flex: 1, justifyContent: 'center', alignItems: 'center', backgroundColor: theme.bg },
  hero: { alignItems: 'center', marginBottom: 26, marginTop: 8 },
  avatar: {
    width: 96,
    height: 96,
    borderRadius: 30,
    backgroundColor: theme.skyTint,
    justifyContent: 'center',
    alignItems: 'center',
    marginBottom: 14,
    borderWidth: 3,
    borderColor: theme.forestLight,
  },
  name: { fontSize: 22, fontWeight: '900', color: theme.ink },
  role: { fontSize: 14, color: theme.muted, marginTop: 4 },
  sectionLabel: {
    fontSize: 11,
    fontWeight: '900',
    color: theme.muted,
    marginBottom: 10,
    marginLeft: 4,
    letterSpacing: 1,
  },
  card: {
    backgroundColor: theme.surface,
    borderRadius: theme.radiusMd,
    padding: 16,
    borderWidth: 1,
    borderColor: theme.border,
    marginBottom: 16,
  },
  label: { fontSize: 12, fontWeight: '800', color: theme.inkSecondary, marginBottom: 6, marginTop: 10 },
  input: {
    backgroundColor: theme.bg,
    borderRadius: theme.radiusSm,
    padding: 14,
    fontSize: 16,
    color: theme.ink,
    borderWidth: 1,
    borderColor: theme.border,
  },
  inputDisabled: { color: theme.muted },
  save: {
    flexDirection: 'row',
    backgroundColor: theme.accent,
    padding: 16,
    borderRadius: theme.radiusMd,
    justifyContent: 'center',
    alignItems: 'center',
    gap: 10,
    marginBottom: 12,
  },
  saveText: { color: '#fff', fontWeight: '900', fontSize: 16 },
  logout: {
    flexDirection: 'row',
    backgroundColor: theme.surface,
    padding: 16,
    borderRadius: theme.radiusMd,
    justifyContent: 'center',
    alignItems: 'center',
    gap: 10,
    borderWidth: 1,
    borderColor: theme.border,
  },
  logoutText: { color: theme.danger, fontWeight: '900', fontSize: 16 },
  del: { alignItems: 'center', marginTop: 24 },
  delText: { color: theme.muted, textDecorationLine: 'underline', fontSize: 14 },
});
