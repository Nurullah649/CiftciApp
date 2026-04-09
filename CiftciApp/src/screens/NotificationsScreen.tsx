import React, { useCallback, useState } from 'react';
import { ActivityIndicator, FlatList, RefreshControl, SafeAreaView, StyleSheet, Text, View } from 'react-native';
import { Bell, Calendar, Clock } from 'lucide-react-native';
import { useFocusEffect } from '@react-navigation/native';
import * as Notifications from 'expo-notifications';
import { getTasks } from '../services/apiService';
import { Task } from '../types';
import { theme } from '../theme/theme';
import { StackHeader } from '../components/StackHeader';
import { AmbientBackdrop } from '../components/AmbientBackdrop';

export default function NotificationsScreen({ navigation }: any) {
  const [upcomingTasks, setUpcomingTasks] = useState<Task[]>([]);
  const [loading, setLoading] = useState(true);
  const [refreshing, setRefreshing] = useState(false);

  useFocusEffect(
    useCallback(() => {
      loadNotifications();
    }, [])
  );

  const loadNotifications = async () => {
    try {
      const allTasks = await getTasks();
      const now = new Date();
      const nextWeek = new Date();
      nextWeek.setDate(now.getDate() + 7);

      const filtered = allTasks.filter((t) => {
        try {
          const taskDate = new Date(t.date_text.replace(' ', 'T'));
          return !isNaN(taskDate.getTime()) && taskDate >= now && taskDate <= nextWeek && (t.status === 'approved' || t.status === 'pending');
        } catch {
          return false;
        }
      });

      filtered.sort((a, b) => new Date(a.date_text).getTime() - new Date(b.date_text).getTime());
      setUpcomingTasks(filtered);
      await scheduleReminders(filtered);
    } catch {
      /* ignore */
    } finally {
      setLoading(false);
      setRefreshing(false);
    }
  };

  const scheduleReminders = async (tasks: Task[]) => {
    await Notifications.cancelAllScheduledNotificationsAsync();
    for (const task of tasks) {
      try {
        const taskDate = new Date(task.date_text.replace(' ', 'T'));
        if (taskDate > new Date()) {
          await Notifications.scheduleNotificationAsync({
            content: {
              title: 'Yaklaşan görev',
              body: task.title,
              sound: true,
              data: { taskId: task.id },
            },
            trigger: { type: Notifications.SchedulableTriggerInputTypes.DATE, date: taskDate },
          });
        }
      } catch {
        /* ignore */
      }
    }
  };

  const renderItem = ({ item }: { item: Task }) => (
    <View style={styles.card}>
      <View style={[styles.iconBox, item.status === 'approved' ? styles.iconPlan : styles.iconWait]}>
        {item.status === 'approved' ? <Clock size={20} color={theme.info} /> : <Bell size={20} color={theme.gold} />}
      </View>
      <View style={{ flex: 1 }}>
        <Text style={styles.cardTitle}>{item.title}</Text>
        <View style={styles.cardMeta}>
          <Calendar size={14} color={theme.muted} />
          <Text style={styles.date}>{new Date(item.date_text).toLocaleDateString('tr-TR', { weekday: 'long', day: 'numeric', month: 'long' })}</Text>
        </View>
        <Text style={[styles.status, { color: item.status === 'approved' ? theme.info : theme.gold }]}>
          {item.status === 'approved' ? 'Planlandı' : 'Onay bekliyor'}
        </Text>
      </View>
    </View>
  );

  return (
    <SafeAreaView style={styles.safe}>
      <AmbientBackdrop />
      <StackHeader title="Bildirimler" eyebrow="YAKLAŞAN GÖREVLER" onBack={() => navigation.goBack()} />

      {loading ? (
        <View style={styles.center}>
          <ActivityIndicator size="large" color={theme.accent} />
        </View>
      ) : (
        <FlatList
          data={upcomingTasks}
          keyExtractor={(item) => item.id.toString()}
          contentContainerStyle={{ padding: 20, paddingBottom: 28 }}
          refreshControl={
            <RefreshControl
              refreshing={refreshing}
              onRefresh={() => {
                setRefreshing(true);
                loadNotifications();
              }}
              tintColor={theme.accent}
            />
          }
          ListHeaderComponent={
            <View style={styles.summaryCard}>
              <Text style={styles.summaryValue}>{upcomingTasks.length}</Text>
              <Text style={styles.summaryText}>Önümüzdeki 7 gün içinde planlanan veya onay bekleyen kayıt</Text>
            </View>
          }
          renderItem={renderItem}
          ListEmptyComponent={
            <View style={styles.empty}>
              <Bell size={34} color={theme.accent} />
              <Text style={styles.emptyTitle}>Yaklaşan görev yok</Text>
              <Text style={styles.emptyText}>Önümüzdeki hafta için planlanan kayıt görünmüyor.</Text>
            </View>
          }
        />
      )}
    </SafeAreaView>
  );
}

const styles = StyleSheet.create({
  safe: { flex: 1, backgroundColor: theme.bg },
  center: { flex: 1, justifyContent: 'center', alignItems: 'center' },
  summaryCard: {
    backgroundColor: theme.surface,
    borderRadius: theme.radiusLg,
    padding: 18,
    borderWidth: 1,
    borderColor: theme.border,
    marginBottom: 14,
  },
  summaryValue: { color: theme.ink, fontSize: 30, fontWeight: '900' },
  summaryText: { color: theme.inkSoft, fontSize: 14, lineHeight: 20, marginTop: 8 },
  card: {
    flexDirection: 'row',
    gap: 12,
    backgroundColor: theme.surface,
    borderRadius: theme.radiusLg,
    padding: 16,
    borderWidth: 1,
    borderColor: theme.border,
    marginBottom: 12,
  },
  iconBox: { width: 42, height: 42, borderRadius: 14, justifyContent: 'center', alignItems: 'center' },
  iconPlan: { backgroundColor: theme.infoSoft },
  iconWait: { backgroundColor: theme.chipAmber },
  cardTitle: { color: theme.ink, fontSize: 16, lineHeight: 21, fontWeight: '900' },
  cardMeta: { flexDirection: 'row', alignItems: 'center', gap: 6, marginTop: 8 },
  date: { color: theme.inkSoft, fontSize: 13 },
  status: { fontSize: 12, fontWeight: '900', marginTop: 10 },
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
