import React, { useState, useCallback } from 'react';
import { View, Text, StyleSheet, FlatList, TouchableOpacity, ActivityIndicator, RefreshControl } from 'react-native';
import { Screen } from '../components/ui/Screen';
import { StackHeader } from '../components/ui/StackHeader';
import { Bell, Calendar, Clock } from 'lucide-react-native';
import { colors, spacing, radius, typography, shadow } from '../theme';
import { useFocusEffect } from '@react-navigation/native';
import * as Notifications from 'expo-notifications';
import { getTasks } from '../services/apiService';
import { Task } from '../types';

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

      // Şimdiki zaman
      const now = new Date();
      // 1 Hafta sonrası
      const nextWeek = new Date();
      nextWeek.setDate(now.getDate() + 7);

      // Filtreleme
      const filtered = allTasks.filter(t => {
        try {
            const taskDate = new Date(t.date_text.replace(' ', 'T'));
            return !isNaN(taskDate.getTime()) && taskDate >= now && taskDate <= nextWeek && (t.status === 'approved' || t.status === 'pending');
        } catch (e) {
            return false;
        }
      });

      // Sıralama
      filtered.sort((a, b) => {
          return new Date(a.date_text).getTime() - new Date(b.date_text).getTime();
      });

      setUpcomingTasks(filtered);
      scheduleReminders(filtered);

    } catch (error) {
      console.log("Bildirim yükleme hatası:", error);
    } finally {
      setLoading(false);
      setRefreshing(false);
    }
  };

  // --- DÜZELTİLEN KISIM BURASI ---
  const scheduleReminders = async (tasks: Task[]) => {
      await Notifications.cancelAllScheduledNotificationsAsync();

      for (const task of tasks) {
          try {
              const taskDate = new Date(task.date_text.replace(' ', 'T'));

              if (taskDate > new Date()) {
                  await Notifications.scheduleNotificationAsync({
                      content: {
                          title: "Göreviniz Var! 🚜",
                          body: `${task.title} zamanı geldi.`,
                          sound: true,
                          data: { taskId: task.id }
                      },
                      // ESKİ KOD (Hatalı olan):
                      // trigger: taskDate,

                      // YENİ KOD (Doğru olan):
                      trigger: {
                          type: 'date',
                          date: taskDate
                      },
                  });
              }
          } catch (e) {
              console.log("Bildirim kurulamadı:", task.title);
          }
      }
  };
  // --------------------------------

  const renderItem = ({ item }: { item: Task }) => (
    <View style={styles.card}>
      <View style={[styles.iconBox, { backgroundColor: item.status === 'approved' ? colors.primarySoft : colors.accentSoft }]}>
        {item.status === 'approved' ? (
            <Clock size={24} color={colors.primary} />
        ) : (
            <Bell size={24} color={colors.warning} />
        )}
      </View>
      <View style={{ flex: 1 }}>
        <View style={{ flexDirection: 'row', justifyContent: 'space-between', marginBottom: 4 }}>
          <Text style={styles.title}>{item.title}</Text>
          <Text style={styles.time}>{new Date(item.date_text).toLocaleTimeString('tr-TR', {hour: '2-digit', minute:'2-digit'})}</Text>
        </View>
        <View style={{flexDirection:'row', alignItems:'center', gap:4}}>
            <Calendar size={14} color={colors.textMuted} />
            <Text style={styles.desc}>
                {new Date(item.date_text).toLocaleDateString('tr-TR', { weekday: 'long', day: 'numeric', month: 'long' })}
            </Text>
        </View>
        <Text style={[styles.status, { color: item.status === 'approved' ? colors.primary : colors.warning }]}>
            {item.status === 'approved' ? 'Planlandı' : 'Onay Bekliyor'}
        </Text>
      </View>
    </View>
  );

  return (
    <Screen edges={['top', 'left', 'right']}>
      <StackHeader title="Yaklaşan Görevler" onBack={() => navigation.goBack()} />

      {loading ? (
        <View style={styles.center}><ActivityIndicator size="large" color={colors.primary}/></View>
      ) : (
        <FlatList
          data={upcomingTasks}
          keyExtractor={item => item.id.toString()}
          contentContainerStyle={{ padding: spacing.lg }}
          refreshControl={
             <RefreshControl refreshing={refreshing} onRefresh={() => {setRefreshing(true); loadNotifications();}} />
          }
          renderItem={renderItem}
          ListEmptyComponent={
            <View style={styles.emptyContainer}>
              <Bell size={40} color={colors.border} />
              <Text style={styles.emptyText}>Önümüzdeki 1 hafta için plan bulunmuyor.</Text>
            </View>
          }
        />
      )}
    </Screen>
  );
}

const styles = StyleSheet.create({
  center: { flex: 1, justifyContent: 'center', alignItems: 'center' },
  card: {
    flexDirection: 'row',
    backgroundColor: colors.surface,
    padding: 16,
    borderRadius: radius.lg,
    marginBottom: 12,
    alignItems: 'center',
    gap: 16,
    borderWidth: 1,
    borderColor: colors.borderLight,
    ...shadow.soft,
  },
  iconBox: { width: 48, height: 48, borderRadius: 24, justifyContent: 'center', alignItems: 'center' },
  title: { fontWeight: '700', color: colors.text, fontSize: 16, flex: 1 },
  desc: { color: colors.textSecondary, fontSize: 14 },
  time: { color: colors.primary, fontWeight: '700', fontSize: 12 },
  status: { fontSize: 12, marginTop: 4, fontWeight: '600' },
  emptyContainer: { alignItems: 'center', marginTop: 60, gap: 10 },
  emptyText: { ...typography.body, color: colors.textMuted, fontSize: 16 },
});