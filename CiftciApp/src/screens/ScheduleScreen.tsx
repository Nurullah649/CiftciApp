import React, { useState, useCallback } from 'react';
import { View, Text, StyleSheet, FlatList, TouchableOpacity, ActivityIndicator, Alert, RefreshControl, StatusBar } from 'react-native';
import { SafeAreaView } from 'react-native-safe-area-context';
import { Calendar, CheckCircle, Circle, Clock, ThumbsUp, Trash2 } from 'lucide-react-native';
import { useFocusEffect } from '@react-navigation/native';
import * as Notifications from 'expo-notifications';
import { getTasks, updateTaskStatus, deleteTask } from '../services/apiService';
import { Task } from '../types';
import { theme } from '../theme/theme';

const TAB_PAD = 118;

export default function ScheduleScreen() {
  const [tasks, setTasks] = useState<Task[]>([]);
  const [loading, setLoading] = useState(true);
  const [refreshing, setRefreshing] = useState(false);

  useFocusEffect(
    useCallback(() => {
      fetchTasks();
    }, [])
  );

  const fetchTasks = async () => {
    try {
      const data = await getTasks();
      const pendingCount = data.filter((t) => t.status === 'pending').length;
      if (pendingCount > 0 && !loading && data.length > tasks.length) {
        sendRecommendationNotification(pendingCount);
      }
      setTasks(data);
    } catch (e) {
      console.error(e);
    } finally {
      setLoading(false);
      setRefreshing(false);
    }
  };

  const sendRecommendationNotification = async (count: number) => {
    try {
      await Notifications.scheduleNotificationAsync({
        content: {
          title: 'Yeni görev önerisi',
          body: `${count} kayıt onay bekliyor.`,
          sound: true,
        },
        trigger: null,
      });
    } catch {
      /* ignore */
    }
  };

  const handleDelete = (task: Task) => {
    Alert.alert('Sil', 'Bu görevi kaldırmak istiyor musunuz?', [
      { text: 'Vazgeç', style: 'cancel' },
      {
        text: 'Sil',
        style: 'destructive',
        onPress: async () => {
          setTasks((prev) => prev.filter((t) => t.id !== task.id));
          try {
            await deleteTask(task.id);
          } catch {
            Alert.alert('Hata', 'Silinemedi.');
            fetchTasks();
          }
        },
      },
    ]);
  };

  const handleStatusChange = async (task: Task) => {
    if (task.status === 'pending') {
      Alert.alert('Onayla', 'Takvime eklemek istiyor musunuz?', [
        { text: 'İptal', style: 'cancel' },
        { text: 'Onayla', onPress: async () => syncTaskStatus(task.id, 'approved') },
      ]);
    } else if (task.status === 'approved') {
      await syncTaskStatus(task.id, 'completed');
    } else if (task.status === 'completed') {
      await syncTaskStatus(task.id, 'approved');
    }
  };

  const syncTaskStatus = async (id: number, status: 'approved' | 'completed') => {
    setTasks((prev) => prev.map((t) => (t.id === id ? { ...t, status } : t)));
    try {
      await updateTaskStatus(id, status);
    } catch {
      Alert.alert('Hata', 'Güncellenemedi.');
      fetchTasks();
    }
  };

  const renderItem = ({ item }: { item: Task }) => {
    let iconColor = theme.border;
    let IconComponent = Circle;
    let statusText = '';
    const pending = item.status === 'pending';

    if (item.status === 'completed') {
      iconColor = theme.success;
      IconComponent = CheckCircle;
    } else if (item.status === 'approved') {
      iconColor = theme.info;
      IconComponent = Clock;
    } else if (pending) {
      iconColor = theme.accentDark;
      IconComponent = ThumbsUp;
      statusText = 'Onay bekliyor';
    }

    return (
      <TouchableOpacity
        style={[styles.card, pending && styles.cardPending]}
        onPress={() => handleStatusChange(item)}
        activeOpacity={0.88}
      >
        <View style={[styles.iconSlot, { backgroundColor: pending ? theme.chipAmber : theme.bg }]}>
          <IconComponent size={24} color={iconColor} />
        </View>
        <View style={{ flex: 1 }}>
          <Text style={[styles.taskTitle, item.status === 'completed' && styles.taskDone, pending && styles.taskPending]}>
            {item.title}
          </Text>
          <View style={styles.meta}>
            <Calendar size={14} color={theme.muted} />
            <Text style={styles.date}>{item.date_text}</Text>
            {pending && (
              <View style={styles.badgeWrap}>
                <Text style={styles.badge}>{statusText}</Text>
              </View>
            )}
          </View>
        </View>
        <TouchableOpacity style={styles.trash} onPress={() => handleDelete(item)}>
          <Trash2 size={20} color={theme.danger} />
        </TouchableOpacity>
      </TouchableOpacity>
    );
  };

  return (
    <SafeAreaView style={styles.container} edges={['top']}>
      <StatusBar barStyle="light-content" backgroundColor={theme.forest} />
      <View style={styles.header}>
        <Text style={styles.kicker}>TAKVİM</Text>
        <Text style={styles.headerTitle}>İş planı</Text>
        <Text style={styles.headerSub}>Asistan önerileri ve durumlarınız</Text>
      </View>

      {loading ? (
        <View style={styles.center}>
          <ActivityIndicator size="large" color={theme.forestLight} />
        </View>
      ) : (
        <FlatList
          data={tasks}
          keyExtractor={(item) => item.id.toString()}
          contentContainerStyle={{ padding: 20, paddingBottom: TAB_PAD }}
          refreshControl={
            <RefreshControl
              refreshing={refreshing}
              onRefresh={() => {
                setRefreshing(true);
                fetchTasks();
              }}
              tintColor={theme.forestLight}
            />
          }
          renderItem={renderItem}
          ListEmptyComponent={
            <View style={styles.empty}>
              <View style={styles.emptyRing}>
                <Clock size={40} color={theme.forestLight} />
              </View>
              <Text style={styles.emptyTitle}>Henüz görev yok</Text>
              <Text style={styles.emptySub}>Asistan ile [GÖREV: ...] formatında öneri alabilirsiniz.</Text>
            </View>
          }
        />
      )}
    </SafeAreaView>
  );
}

const styles = StyleSheet.create({
  container: { flex: 1, backgroundColor: theme.bg },
  center: { flex: 1, justifyContent: 'center', alignItems: 'center' },
  header: {
    backgroundColor: theme.forest,
    paddingHorizontal: 22,
    paddingTop: 8,
    paddingBottom: 20,
    borderBottomLeftRadius: 28,
    borderBottomRightRadius: 28,
  },
  kicker: { color: theme.tabActive, fontSize: 10, fontWeight: '900', letterSpacing: 2 },
  headerTitle: { fontSize: 28, fontWeight: '900', color: '#fff', marginTop: 8 },
  headerSub: { fontSize: 14, color: 'rgba(255,255,255,0.72)', marginTop: 6 },
  card: {
    flexDirection: 'row',
    backgroundColor: theme.surface,
    padding: 16,
    borderRadius: theme.radiusMd,
    marginBottom: 12,
    alignItems: 'center',
    gap: 14,
    borderWidth: 1,
    borderColor: theme.border,
    shadowColor: theme.shadow,
    shadowOffset: { width: 0, height: 2 },
    shadowOpacity: 1,
    shadowRadius: 10,
    elevation: 2,
  },
  cardPending: { borderLeftWidth: 4, borderLeftColor: theme.accent },
  iconSlot: {
    width: 48,
    height: 48,
    borderRadius: 14,
    justifyContent: 'center',
    alignItems: 'center',
  },
  taskTitle: { fontWeight: '800', color: theme.ink, fontSize: 16 },
  taskDone: { textDecorationLine: 'line-through', color: theme.muted },
  taskPending: { color: theme.accentDark },
  meta: { flexDirection: 'row', alignItems: 'center', gap: 6, marginTop: 6, flexWrap: 'wrap' },
  date: { color: theme.muted, fontSize: 13 },
  badgeWrap: { marginLeft: 'auto' },
  badge: {
    fontSize: 10,
    fontWeight: '900',
    color: theme.accentDark,
    backgroundColor: theme.chipAmber,
    paddingHorizontal: 8,
    paddingVertical: 4,
    borderRadius: 8,
    overflow: 'hidden',
  },
  trash: { padding: 8 },
  empty: { alignItems: 'center', marginTop: 56, padding: 20 },
  emptyRing: {
    width: 88,
    height: 88,
    borderRadius: 28,
    backgroundColor: theme.skyTint,
    justifyContent: 'center',
    alignItems: 'center',
    marginBottom: 16,
  },
  emptyTitle: { fontSize: 18, fontWeight: '900', color: theme.ink },
  emptySub: { color: theme.muted, textAlign: 'center', marginTop: 10, lineHeight: 20 },
});
