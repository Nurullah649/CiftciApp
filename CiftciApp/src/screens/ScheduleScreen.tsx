import React, { useCallback, useState } from 'react';
import { ActivityIndicator, Alert, FlatList, RefreshControl, SafeAreaView, StatusBar, StyleSheet, Text, TouchableOpacity, View } from 'react-native';
import { Calendar, CheckCircle, Clock, ThumbsUp, Trash2 } from 'lucide-react-native';
import { useFocusEffect } from '@react-navigation/native';
import * as Notifications from 'expo-notifications';
import { getTasks, updateTaskStatus, deleteTask } from '../services/apiService';
import { Task } from '../types';
import { theme } from '../theme/theme';
import { AmbientBackdrop } from '../components/AmbientBackdrop';

const TAB_PAD = 120;

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

  const summary = {
    pending: tasks.filter((task) => task.status === 'pending').length,
    approved: tasks.filter((task) => task.status === 'approved').length,
    completed: tasks.filter((task) => task.status === 'completed').length,
  };

  const renderItem = ({ item }: { item: Task }) => {
    const meta =
      item.status === 'completed'
        ? { Icon: CheckCircle, color: theme.success, chipBg: theme.successSoft, chipText: 'Tamamlandı' }
        : item.status === 'approved'
          ? { Icon: Clock, color: theme.info, chipBg: theme.infoSoft, chipText: 'Planlandı' }
          : { Icon: ThumbsUp, color: theme.gold, chipBg: theme.chipAmber, chipText: 'Onay bekliyor' };

    return (
      <TouchableOpacity style={styles.taskCard} onPress={() => handleStatusChange(item)} activeOpacity={0.88}>
        <View style={[styles.taskIconWrap, { backgroundColor: meta.chipBg }]}>
          <meta.Icon size={20} color={meta.color} />
        </View>
        <View style={{ flex: 1 }}>
          <Text style={[styles.taskTitle, item.status === 'completed' && styles.taskDone]}>{item.title}</Text>
          <View style={styles.taskMeta}>
            <Calendar size={14} color={theme.muted} />
            <Text style={styles.taskDate}>{item.date_text}</Text>
          </View>
          <View style={[styles.statusChip, { backgroundColor: meta.chipBg }]}>
            <Text style={[styles.statusChipText, { color: meta.color }]}>{meta.chipText}</Text>
          </View>
        </View>
        <TouchableOpacity style={styles.deleteButton} onPress={() => handleDelete(item)}>
          <Trash2 size={18} color={theme.danger} />
        </TouchableOpacity>
      </TouchableOpacity>
    );
  };

  return (
    <SafeAreaView style={styles.safe}>
      <StatusBar barStyle="dark-content" backgroundColor={theme.bg} />
      <AmbientBackdrop />

      <FlatList
        data={loading ? [] : tasks}
        keyExtractor={(item) => item.id.toString()}
        contentContainerStyle={{ padding: 20, paddingBottom: TAB_PAD }}
        refreshControl={
          <RefreshControl
            refreshing={refreshing}
            onRefresh={() => {
              setRefreshing(true);
              fetchTasks();
            }}
            tintColor={theme.accent}
          />
        }
        ListHeaderComponent={
          <>
            <View style={styles.header}>
              <Text style={styles.headerEyebrow}>TAKVİM</Text>
              <Text style={styles.headerTitle}>Görevleri tek listede yönetin.</Text>
            </View>

            <View style={styles.summaryRow}>
              <View style={styles.summaryCard}>
                <Text style={styles.summaryValue}>{summary.pending}</Text>
                <Text style={styles.summaryLabel}>Bekleyen</Text>
              </View>
              <View style={styles.summaryCard}>
                <Text style={styles.summaryValue}>{summary.approved}</Text>
                <Text style={styles.summaryLabel}>Planlı</Text>
              </View>
              <View style={styles.summaryCard}>
                <Text style={styles.summaryValue}>{summary.completed}</Text>
                <Text style={styles.summaryLabel}>Biten</Text>
              </View>
            </View>

            {loading && (
              <View style={styles.center}>
                <ActivityIndicator size="large" color={theme.accent} />
              </View>
            )}
          </>
        }
        renderItem={renderItem}
        ListEmptyComponent={
          !loading ? (
            <View style={styles.empty}>
              <Clock size={34} color={theme.accent} />
              <Text style={styles.emptyTitle}>Henüz görev yok</Text>
              <Text style={styles.emptyText}>Asistan görev önerdiğinde burada listelenecek.</Text>
            </View>
          ) : null
        }
      />
    </SafeAreaView>
  );
}

const styles = StyleSheet.create({
  safe: { flex: 1, backgroundColor: theme.bg },
  header: { marginBottom: 16 },
  headerEyebrow: { color: theme.muted, fontSize: 11, fontWeight: '900', letterSpacing: 1.2 },
  headerTitle: { color: theme.ink, fontSize: 30, lineHeight: 34, fontWeight: '900', marginTop: 10, maxWidth: 260 },
  summaryRow: { flexDirection: 'row', gap: 10, marginBottom: 18 },
  summaryCard: {
    flex: 1,
    backgroundColor: theme.surface,
    borderRadius: theme.radiusLg,
    padding: 14,
    borderWidth: 1,
    borderColor: theme.border,
  },
  summaryValue: { color: theme.ink, fontSize: 28, fontWeight: '900' },
  summaryLabel: { color: theme.muted, fontSize: 13, marginTop: 6 },
  center: { paddingVertical: 30 },
  taskCard: {
    flexDirection: 'row',
    alignItems: 'flex-start',
    gap: 12,
    backgroundColor: theme.surface,
    borderRadius: theme.radiusLg,
    padding: 16,
    borderWidth: 1,
    borderColor: theme.border,
    marginBottom: 12,
  },
  taskIconWrap: {
    width: 42,
    height: 42,
    borderRadius: 14,
    justifyContent: 'center',
    alignItems: 'center',
  },
  taskTitle: { color: theme.ink, fontSize: 16, lineHeight: 21, fontWeight: '900' },
  taskDone: { textDecorationLine: 'line-through', color: theme.muted },
  taskMeta: { flexDirection: 'row', alignItems: 'center', gap: 6, marginTop: 8 },
  taskDate: { color: theme.inkSoft, fontSize: 13 },
  statusChip: {
    alignSelf: 'flex-start',
    borderRadius: 999,
    paddingHorizontal: 10,
    paddingVertical: 7,
    marginTop: 10,
  },
  statusChipText: { fontSize: 12, fontWeight: '900' },
  deleteButton: {
    width: 36,
    height: 36,
    borderRadius: 12,
    backgroundColor: theme.dangerSoft,
    justifyContent: 'center',
    alignItems: 'center',
  },
  empty: {
    backgroundColor: theme.surface,
    borderRadius: theme.radiusXl,
    padding: 24,
    alignItems: 'center',
    borderWidth: 1,
    borderColor: theme.border,
  },
  emptyTitle: { color: theme.ink, fontSize: 20, fontWeight: '900', marginTop: 14 },
  emptyText: { color: theme.inkSoft, fontSize: 14, lineHeight: 20, marginTop: 8, textAlign: 'center' },
});
