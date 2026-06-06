import React, { useState, useCallback } from 'react';
import { View, Text, StyleSheet, FlatList, TouchableOpacity, ActivityIndicator, Alert, RefreshControl } from 'react-native';
import { Screen } from '../components/ui/Screen';
import { StackHeader } from '../components/ui/StackHeader';
import { Calendar, CheckCircle, Circle, Clock, ThumbsUp, Trash2 } from 'lucide-react-native';
import { colors, spacing, radius, typography, shadow } from '../theme';
import { useFocusEffect } from '@react-navigation/native';
import * as Notifications from 'expo-notifications';
import { getTasks, updateTaskStatus, deleteTask } from '../services/apiService';
import { Task } from '../types';

export default function ScheduleScreen({ navigation }: any) {
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

      // Bildirim mantığı (daha önce eklemiştik)
      const pendingCount = data.filter(t => t.status === 'pending').length;
      if (pendingCount > 0 && !loading && data.length > tasks.length) {
         sendRecommendationNotification(pendingCount);
      }

      setTasks(data);
    } catch (error) {
      console.error("Görevleri alma hatası:", error);
    } finally {
      setLoading(false);
      setRefreshing(false);
    }
  };

  const sendRecommendationNotification = async (count: number) => {
    try {
      await Notifications.scheduleNotificationAsync({
        content: {
          title: "Yeni Plan Önerisi! 🚜",
          body: `Asistanınız onayınızı bekleyen ${count} yeni görev oluşturdu.`,
          sound: true,
        },
        trigger: null,
      });
    } catch (e) {
      console.log("Bildirim gönderilemedi:", e);
    }
  };

  const handleDelete = (task: Task) => {
      Alert.alert(
          "Görevi Sil",
          "Bu görevi silmek istediğinize emin misiniz?",
          [
              { text: "Vazgeç", style: "cancel" },
              {
                  text: "Sil",
                  style: "destructive",
                  onPress: async () => {
                      // Optimistic Update
                      setTasks(prev => prev.filter(t => t.id !== task.id));
                      try {
                          await deleteTask(task.id);
                      } catch (error) {
                          Alert.alert("Hata", "Görev silinemedi.");
                          fetchTasks(); // Geri yükle
                      }
                  }
              }
          ]
      );
  };

  const handleStatusChange = async (task: Task) => {
    if (task.status === 'pending') {
        Alert.alert(
            "Görevi Onayla",
            "Bu görevi planınıza kalıcı olarak eklemek istiyor musunuz?",
            [
                { text: "İptal", style: "cancel" },
                {
                    text: "Onayla",
                    onPress: async () => {
                        await updateTask(task.id, 'approved');
                    }
                }
            ]
        );
    }
    else if (task.status === 'approved') {
        await updateTask(task.id, 'completed');
    }
    else if (task.status === 'completed') {
        await updateTask(task.id, 'approved');
    }
  };

  const updateTask = async (id: number, status: 'approved' | 'completed') => {
      setTasks(prev => prev.map(t => t.id === id ? { ...t, status } : t));
      try {
          await updateTaskStatus(id, status);
      } catch (error) {
          Alert.alert("Hata", "Durum güncellenemedi.");
          fetchTasks();
      }
  };

  const renderItem = ({ item }: { item: Task }) => {
    let iconColor = colors.textMuted;
    let IconComponent = Circle;
    let cardStyle = styles.card;
    let statusText = "";

    if (item.status === 'completed') {
        iconColor = colors.healthy;
        IconComponent = CheckCircle;
    } else if (item.status === 'approved') {
        iconColor = colors.primary;
        IconComponent = Clock;
    } else if (item.status === 'pending') {
        iconColor = colors.warning;
        IconComponent = ThumbsUp;
        cardStyle = {...styles.card, borderLeftWidth: 4, borderLeftColor: colors.warning};
        statusText = "Onay Bekliyor";
    }

    return (
      <TouchableOpacity style={cardStyle} onPress={() => handleStatusChange(item)}>
        <View style={styles.checkArea}>
          <IconComponent size={24} color={iconColor} />
        </View>
        <View style={{ flex: 1 }}>
          <Text style={[
              styles.title,
              item.status === 'completed' && styles.titleCompleted,
              item.status === 'pending' && styles.titlePending
          ]}>
            {item.title}
          </Text>

          <View style={styles.dateRow}>
            <Calendar size={14} color={colors.textMuted} />
            <Text style={styles.date}>{item.date_text}</Text>
            {item.status === 'pending' && (
                <View style={styles.pendingBadgeContainer}>
                    <Text style={styles.pendingBadge}>{statusText}</Text>
                </View>
            )}
          </View>
        </View>

        {/* SİLME BUTONU */}
        <TouchableOpacity style={styles.deleteBtn} onPress={() => handleDelete(item)}>
            <Trash2 size={20} color={colors.critical} />
        </TouchableOpacity>
      </TouchableOpacity>
    );
  };

  return (
    <Screen edges={['top', 'left', 'right']}>
      <StackHeader title="Planlanan Görevler" onBack={() => navigation.goBack()} />

      {loading ? (
          <View style={styles.center}>
              <ActivityIndicator size="large" color={colors.primary} />
          </View>
      ) : (
          <FlatList
            data={tasks}
            keyExtractor={item => item.id.toString()}
            contentContainerStyle={{ padding: spacing.lg, paddingBottom: 40 }}
            refreshControl={
                <RefreshControl refreshing={refreshing} onRefresh={() => {setRefreshing(true); fetchTasks();}} colors={[colors.primary]} />
            }
            renderItem={renderItem}
            ListEmptyComponent={
                <View style={styles.emptyState}>
                    <Clock size={48} color={colors.border} />
                    <Text style={styles.emptyText}>Henüz bir planınız yok.</Text>
                    <Text style={styles.emptySubText}>Asistanınızla konuşarak yeni görevler oluşturabilirsiniz.</Text>
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
  checkArea: { padding: 4 },
  title: { fontWeight: '700', color: colors.text, fontSize: 16 },
  titleCompleted: { textDecorationLine: 'line-through', color: colors.textMuted },
  titlePending: { color: colors.warning },
  dateRow: { flexDirection: 'row', alignItems: 'center', gap: 6, marginTop: 6 },
  date: { color: colors.textSecondary, fontSize: 13 },
  pendingBadgeContainer: { marginLeft: 'auto' },
  pendingBadge: {
    fontSize: 11,
    color: colors.warning,
    fontWeight: '700',
    backgroundColor: colors.accentSoft,
    paddingHorizontal: 8,
    paddingVertical: 2,
    borderRadius: 12,
  },
  deleteBtn: { padding: 8, marginLeft: 'auto' },
  emptyState: { alignItems: 'center', marginTop: 80, padding: 20 },
  emptyText: { ...typography.h3, color: colors.text, marginTop: 16 },
  emptySubText: { ...typography.caption, color: colors.textMuted, marginTop: 8, textAlign: 'center' },
});