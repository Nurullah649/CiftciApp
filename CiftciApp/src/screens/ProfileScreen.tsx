import React, { useState, useEffect } from 'react';
import { View, Text, StyleSheet, TouchableOpacity, ScrollView, TextInput, Alert, ActivityIndicator } from 'react-native';
import { SafeAreaView } from 'react-native-safe-area-context';
import { ArrowLeft, User, LogOut, Save } from 'lucide-react-native';
import { getUserProfile, updateUserProfile, logoutUser, deleteMyAccount } from '../services/apiService';

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
      if (error instanceof Error && error.message.includes('Oturum')) {
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
      Alert.alert("Başarılı", "Profil bilgileriniz güncellendi.");
    } catch (error) {
      Alert.alert("Hata", "Güncelleme yapılamadı.");
    } finally {
      setSaving(false);
    }
  };

  // Güvenli Çıkış İşlemi
  const handleLogout = async () => {
    try {
      await logoutUser();
      navigation.reset({
        index: 0,
        routes: [{ name: 'Login' }],
      });
    } catch (e) {
      navigation.replace('Login');
    }
  };

  // Hesap Silme İşlemi
  const handleDeleteAccount = () => {
    Alert.alert(
      "Hesabı Sil",
      "Hesabınız ve tüm verileriniz kalıcı olarak silinecek. Bu işlem geri alınamaz!",
      [
        { text: "Vazgeç", style: "cancel" },
        {
          text: "Evet, Hesabımı Sil",
          style: "destructive",
          onPress: async () => {
            try {
              await deleteMyAccount();
              Alert.alert("Hesap Silindi", "Hesabınız başarıyla silindi.", [
                { text: "Tamam", onPress: () => handleLogout() }
              ]);
            } catch (error) {
              Alert.alert("Hata", "Hesap silinemedi. Lütfen tekrar deneyin.");
            }
          }
        }
      ]
    );
  };

  if (loading) {
    return <View style={styles.center}><ActivityIndicator size="large" color="#16a34a" /></View>;
  }

  return (
    <SafeAreaView style={styles.container} edges={['top']}>
      <View style={styles.header}>
        <TouchableOpacity onPress={() => navigation.goBack()} style={styles.backBtn}>
          <ArrowLeft size={24} color="#374151" />
        </TouchableOpacity>
        <Text style={styles.headerTitle}>Profilim</Text>
      </View>

      <ScrollView contentContainerStyle={{ padding: 20 }}>
        <View style={styles.avatarSection}>
          <View style={styles.avatarCircle}>
            <User size={40} color="#16a34a" />
          </View>
          <Text style={styles.name}>{formData.firstName || 'İsimsiz'} {formData.lastName || 'Çiftçi'}</Text>
          <Text style={styles.role}>Çiftçi</Text>
        </View>

        <View style={styles.section}>
          <Text style={styles.sectionTitle}>Kişisel Bilgiler</Text>
          <View style={styles.formCard}>
            <View style={styles.inputGroup}>
              <Text style={styles.label}>Ad</Text>
              <TextInput
                style={styles.input}
                value={formData.firstName}
                onChangeText={(t) => setFormData({ ...formData, firstName: t })}
                placeholder="Adınız"
                placeholderTextColor="#9ca3af"
              />
            </View>
            <View style={styles.inputGroup}>
              <Text style={styles.label}>Soyad</Text>
              <TextInput
                style={styles.input}
                value={formData.lastName}
                onChangeText={(t) => setFormData({ ...formData, lastName: t })}
                placeholder="Soyadınız"
                placeholderTextColor="#9ca3af"
              />
            </View>
            <View style={styles.inputGroup}>
              <Text style={styles.label}>Konum</Text>
              <TextInput
                style={styles.input}
                value={formData.location}
                onChangeText={(t) => setFormData({ ...formData, location: t })}
                placeholder="Örn: Selçuklu, Konya"
                placeholderTextColor="#9ca3af"
              />
            </View>
            <View style={styles.inputGroup}>
              <Text style={styles.label}>E-posta</Text>
              <TextInput
                style={[styles.input, { backgroundColor: '#f3f4f6', color: '#9ca3af' }]}
                value={formData.email}
                editable={false}
              />
            </View>
          </View>
        </View>

        <TouchableOpacity style={styles.saveBtn} onPress={handleSave} disabled={saving}>
          {saving ? <ActivityIndicator color="#fff" /> : <Save size={20} color="#fff" />}
          <Text style={styles.saveText}>{saving ? "Kaydediliyor..." : "Kaydet"}</Text>
        </TouchableOpacity>

        <TouchableOpacity style={styles.logoutBtn} onPress={handleLogout}>
          <LogOut size={20} color="#ef4444" />
          <Text style={styles.logoutText}>Çıkış Yap</Text>
        </TouchableOpacity>

        <TouchableOpacity style={styles.deleteAccountBtn} onPress={handleDeleteAccount}>
          <Text style={styles.deleteAccountText}>Hesabımı Sil</Text>
        </TouchableOpacity>
      </ScrollView>
    </SafeAreaView>
  );
}

const styles = StyleSheet.create({
  container: { flex: 1, backgroundColor: '#f9fafb' },
  center: { flex: 1, justifyContent: 'center', alignItems: 'center' },
  header: { flexDirection: 'row', alignItems: 'center', padding: 20, backgroundColor: '#fff', borderBottomWidth: 1, borderColor: '#f3f4f6' },
  backBtn: { marginRight: 16 },
  headerTitle: { fontSize: 20, fontWeight: 'bold', color: '#1f2937' },
  avatarSection: { alignItems: 'center', marginBottom: 32, marginTop: 10 },
  avatarCircle: { width: 100, height: 100, borderRadius: 50, backgroundColor: '#dcfce7', justifyContent: 'center', alignItems: 'center', marginBottom: 12, borderWidth: 4, borderColor: '#fff', shadowColor: "#000", shadowOpacity: 0.1, elevation: 5 },
  name: { fontSize: 22, fontWeight: 'bold', color: '#1f2937' },
  role: { fontSize: 14, color: '#6b7280' },
  section: { marginBottom: 24 },
  sectionTitle: { fontSize: 14, fontWeight: 'bold', color: '#6b7280', marginBottom: 12, marginLeft: 4, textTransform: 'uppercase' },
  formCard: { backgroundColor: '#fff', borderRadius: 16, padding: 16, elevation: 2 },
  inputGroup: { marginBottom: 16 },
  label: { fontSize: 12, color: '#6b7280', marginBottom: 6, fontWeight: '600' },
  input: { backgroundColor: '#f9fafb', borderWidth: 1, borderColor: '#e5e7eb', borderRadius: 10, padding: 12, fontSize: 16, color: '#1f2937' },
  saveBtn: { flexDirection: 'row', backgroundColor: '#16a34a', padding: 16, borderRadius: 16, justifyContent: 'center', alignItems: 'center', gap: 8, marginBottom: 12, elevation: 3 },
  saveText: { color: '#fff', fontWeight: 'bold', fontSize: 16 },
  logoutBtn: { flexDirection: 'row', backgroundColor: '#fef2f2', padding: 16, borderRadius: 16, justifyContent: 'center', alignItems: 'center', gap: 8, borderWidth: 1, borderColor: '#fee2e2' },
  logoutText: { color: '#ef4444', fontWeight: 'bold', fontSize: 16 },
  deleteAccountBtn: { padding: 16, alignItems: 'center', marginTop: 20, marginBottom: 40 },
  deleteAccountText: { color: '#9ca3af', fontSize: 14, textDecorationLine: 'underline' }
});
