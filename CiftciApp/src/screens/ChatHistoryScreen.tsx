import React, { useEffect, useMemo, useState } from 'react';
import {
  ActivityIndicator,
  Alert,
  FlatList,
  LayoutAnimation,
  Platform,
  SafeAreaView,
  StyleSheet,
  Text,
  TouchableOpacity,
  UIManager,
  View,
} from 'react-native';
import { Calendar, ChevronDown, ChevronUp, MessageCircle, Trash2 } from 'lucide-react-native';
import { clearChatHistory, getChatHistory } from '../services/apiService';
import { theme } from '../theme/theme';
import { StackHeader } from '../components/StackHeader';
import { AmbientBackdrop } from '../components/AmbientBackdrop';

if (Platform.OS === 'android' && UIManager.setLayoutAnimationEnabledExperimental) {
  UIManager.setLayoutAnimationEnabledExperimental(true);
}

interface HistoryItem {
  id: number | string;
  role: 'user' | 'ai';
  message: string;
  created_at: string;
}

const DateGroup = ({ title, messages }: { title: string; messages: HistoryItem[] }) => {
  const [expanded, setExpanded] = useState(false);

  const toggleExpand = () => {
    LayoutAnimation.configureNext(LayoutAnimation.Presets.easeInEaseOut);
    setExpanded(!expanded);
  };

  return (
    <View style={styles.group}>
      <TouchableOpacity onPress={toggleExpand} style={styles.groupHead} activeOpacity={0.78}>
        <View style={styles.groupLeft}>
          <View style={styles.groupIcon}>
            <Calendar size={18} color={theme.accent} />
          </View>
          <View>
            <Text style={styles.groupTitle}>{title}</Text>
            <Text style={styles.groupSub}>{messages.length} mesaj</Text>
          </View>
        </View>
        {expanded ? <ChevronUp size={18} color={theme.muted} /> : <ChevronDown size={18} color={theme.muted} />}
      </TouchableOpacity>

      {expanded && (
        <View style={styles.messageBlock}>
          {messages.map((item, index) => {
            const isUser = item.role === 'user';
            return (
              <View key={String(item.id ?? index)} style={[styles.messageRow, isUser ? styles.rowUser : styles.rowAi]}>
                <View style={[styles.messageBubble, isUser ? styles.userBubble : styles.aiBubble]}>
                  <Text style={[styles.messageText, isUser ? styles.userText : styles.aiText]}>{item.message}</Text>
                  <Text style={[styles.messageTime, isUser ? styles.userTime : styles.aiTime]}>
                    {new Date(item.created_at).toLocaleTimeString('tr-TR', { hour: '2-digit', minute: '2-digit' })}
                  </Text>
                </View>
              </View>
            );
          })}
        </View>
      )}
    </View>
  );
};

export default function ChatHistoryScreen({ navigation }: any) {
  const [history, setHistory] = useState<HistoryItem[]>([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    loadHistory();
  }, []);

  const loadHistory = async () => {
    try {
      const data = await getChatHistory();
      const arr: HistoryItem[] = Array.isArray(data) ? data : [];
      arr.sort((a, b) => new Date(a.created_at).getTime() - new Date(b.created_at).getTime());
      setHistory(arr);
    } catch {
      setHistory([]);
    } finally {
      setLoading(false);
    }
  };

  const handleClear = () => {
    Alert.alert('Geçmişi sil', 'Sunucudaki sohbet kayıtları silinecek.', [
      { text: 'Vazgeç', style: 'cancel' },
      {
        text: 'Sil',
        style: 'destructive',
        onPress: async () => {
          setLoading(true);
          try {
            await clearChatHistory();
            setHistory([]);
          } catch {
            Alert.alert('Hata', 'Temizlenemedi.');
          } finally {
            setLoading(false);
          }
        },
      },
    ]);
  };

  const grouped = useMemo(() => {
    if (!history.length) return [];
    const out: { title: string; data: HistoryItem[] }[] = [];
    let curTitle = '';
    let cur: HistoryItem[] = [];

    history.forEach((item) => {
      const date = new Date(item.created_at);
      const today = new Date();
      const yesterday = new Date();
      yesterday.setDate(today.getDate() - 1);

      let title = date.toLocaleDateString('tr-TR', { day: 'numeric', month: 'long', year: 'numeric' });
      const isToday = date.toDateString() === today.toDateString();
      const isYesterday = date.toDateString() === yesterday.toDateString();

      if (isToday) title = 'Bugün';
      else if (isYesterday) title = 'Dün';

      if (title !== curTitle) {
        if (curTitle) out.push({ title: curTitle, data: cur });
        curTitle = title;
        cur = [item];
      } else {
        cur.push(item);
      }
    });

    if (curTitle) out.push({ title: curTitle, data: cur });
    return out;
  }, [history]);

  const headerRight =
    history.length > 0 ? (
      <TouchableOpacity onPress={handleClear} style={styles.clearButton}>
        <Trash2 size={18} color={theme.danger} />
      </TouchableOpacity>
    ) : undefined;

  return (
    <SafeAreaView style={styles.safe}>
      <AmbientBackdrop />
      <StackHeader title="Sohbet geçmişi" eyebrow="KAYITLAR" onBack={() => navigation.goBack()} right={headerRight} />

      {loading ? (
        <View style={styles.center}>
          <ActivityIndicator size="large" color={theme.accent} />
        </View>
      ) : (
        <FlatList
          data={grouped}
          keyExtractor={(_, i) => String(i)}
          contentContainerStyle={{ padding: 20, paddingBottom: 40 }}
          ListHeaderComponent={
            <View style={styles.summaryCard}>
              <Text style={styles.summaryValue}>{history.length}</Text>
              <Text style={styles.summaryText}>Toplam mesaj kaydı</Text>
            </View>
          }
          renderItem={({ item }) => <DateGroup title={item.title} messages={item.data} />}
          ListEmptyComponent={
            <View style={styles.empty}>
              <MessageCircle size={34} color={theme.accent} />
              <Text style={styles.emptyTitle}>Kayıt yok</Text>
              <Text style={styles.emptyText}>Asistan ile konuştukça geçmiş burada görünecek.</Text>
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
  clearButton: {
    width: 40,
    height: 40,
    borderRadius: 14,
    backgroundColor: theme.dangerSoft,
    justifyContent: 'center',
    alignItems: 'center',
  },
  summaryCard: {
    backgroundColor: theme.surface,
    borderRadius: theme.radiusLg,
    padding: 18,
    borderWidth: 1,
    borderColor: theme.border,
    marginBottom: 14,
  },
  summaryValue: { color: theme.ink, fontSize: 30, fontWeight: '900' },
  summaryText: { color: theme.inkSoft, fontSize: 14, marginTop: 8 },
  group: {
    backgroundColor: theme.surface,
    borderRadius: theme.radiusLg,
    borderWidth: 1,
    borderColor: theme.border,
    marginBottom: 12,
    overflow: 'hidden',
  },
  groupHead: { flexDirection: 'row', justifyContent: 'space-between', alignItems: 'center', padding: 16 },
  groupLeft: { flexDirection: 'row', alignItems: 'center', gap: 12 },
  groupIcon: {
    width: 40,
    height: 40,
    borderRadius: 14,
    backgroundColor: theme.accentSoft,
    justifyContent: 'center',
    alignItems: 'center',
  },
  groupTitle: { color: theme.ink, fontSize: 16, fontWeight: '900' },
  groupSub: { color: theme.muted, fontSize: 12, marginTop: 4 },
  messageBlock: {
    backgroundColor: theme.surfaceMuted,
    borderTopWidth: 1,
    borderTopColor: theme.border,
    padding: 14,
  },
  messageRow: { marginVertical: 5, width: '100%' },
  rowUser: { alignItems: 'flex-end' },
  rowAi: { alignItems: 'flex-start' },
  messageBubble: { maxWidth: '85%', padding: 12, borderRadius: 16 },
  userBubble: { backgroundColor: theme.accent, borderBottomRightRadius: 6 },
  aiBubble: { backgroundColor: theme.surface, borderBottomLeftRadius: 6, borderWidth: 1, borderColor: theme.border },
  messageText: { fontSize: 14, lineHeight: 20 },
  userText: { color: '#fff' },
  aiText: { color: theme.ink },
  messageTime: { fontSize: 10, marginTop: 4, alignSelf: 'flex-end' },
  userTime: { color: 'rgba(255,255,255,0.8)' },
  aiTime: { color: theme.muted },
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
