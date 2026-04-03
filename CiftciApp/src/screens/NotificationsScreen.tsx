import React, { useState, useCallback } from 'react';
import { View, Text, StyleSheet, FlatList, TouchableOpacity, ActivityIndicator, RefreshControl } from 'react-native';
import { SafeAreaView } from 'react-native-safe-area-context';
import { Bell, Calendar, Clock } from 'lucide-react-native';
import { useFocusEffect } from '@react-navigation/native';
import * as Notifications from 'expo-notifications';
import { getTasks } from '../services/apiService';
import { Task } from '../types';
import { theme } from '../theme/theme';
import { StackHeader } from '../components/StackHeader';

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
          return (
            !isNaN(taskDate.getTime()) &&
            taskDate >= now &&
            taskDate <= nextWeek &&
            (t.status === 'approved' || t.status === 'pending')
          );
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
        {item.status === 'approved' ? <Clock size={22} color={theme.info} /> : <Bell size={22} color={theme.accentDark} />}
      </View>
      <View style={{ flex: 1 }}>
        <View style={styles.cardTop}>
          <Text style={styles.cardTitle}>{item.title}</Text>
          <Text style={styles.time}>
            {new Date(item.date_text).toLocaleTimeString('tr-TR', { hour: '2-digit', minute: '2-digit' })}
          </Text>
        </View>
        <View style={styles.cardMeta}>
          <Calendar size={14} color={theme.muted} />
          <Text style={styles.date}>
            {new Date(item.date_text).toLocaleDateString('tr-TR', { weekday: 'long', day: 'numeric', month: 'long' })}
          </Text>
        </View>
        <Text style={[styles.status, { color: item.status === 'approved' ? theme.info : theme.accentDark }]}>
          {item.status === 'approved' ? 'Planlandı' : 'Onay bekliyor'}
        </Text>
      </View>
    </View>
  );

  return (
    <SafeAreaView style={styles.safe} edges={['top']}>
      <StackHeader title="Yaklaşanlar" onBack={() => navigation.goBack()} />

      {loading ? (
        <View style={styles.center}>
          <ActivityIndicator size="large" color={theme.forestLight} />
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
              tintColor={theme.forestLight}
            />
          }
          renderItem={renderItem}
          ListEmptyComponent={
            <View style={styles.empty}>
              <View style={styles.emptyRing}>
                <Bell size={36} color={theme.forestLight} />
              </View>
              <Text style={styles.emptyText}>Önümüzdeki hafta için kayıt yok.</Text>
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
  card: {
    flexDirection: 'row',
    backgroundColor: theme.surface,
    padding: 16,
    borderRadius: theme.radiusMd,
    marginBottom: 12,
    gap: 14,
    alignItems: 'center',
    borderWidth: 1,
    borderColor: theme.border,
    shadowColor: theme.shadow,
    shadowOffset: { width: 0, height: 2 },
    shadowOpacity: 1,
    shadowRadius: 8,
    elevation: 2,
  },
  iconBox: { width: 50, height: 50, borderRadius: 16, justifyContent: 'center', alignItems: 'center' },
  iconPlan: { backgroundColor: theme.chipMist },
  iconWait: { backgroundColor: theme.chipAmber },
  cardTop: { flexDirection: 'row', justifyContent: 'space-between', marginBottom: 4 },
  cardTitle: { fontWeight: '800', color: theme.ink, fontSize: 16, flex: 1, paddingRight: 8 },
  time: { color: theme.forestLight, fontWeight: '900', fontSize: 12 },
  cardMeta: { flexDirection: 'row', alignItems: 'center', gap: 6 },
  date: { color: theme.muted, fontSize: 14 },
  status: { fontSize: 12, marginTop: 6, fontWeight: '800' },
  empty: { alignItems: 'center', marginTop: 48, gap: 14 },
  emptyRing: {
    width: 88,
    height: 88,
    borderRadius: 28,
    backgroundColor: theme.skyTint,
    justifyContent: 'center',
    alignItems: 'center',
  },
  emptyText: { color: theme.muted, fontSize: 16, textAlign: 'center', paddingHorizontal: 24 },
});
