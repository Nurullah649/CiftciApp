import React, { useEffect, useState, useMemo } from 'react';
import {
  View,
  Text,
  StyleSheet,
  TouchableOpacity,
  ActivityIndicator,
  Alert,
  FlatList,
  LayoutAnimation,
  Platform,
  UIManager,
} from 'react-native';
import { SafeAreaView } from 'react-native-safe-area-context';
import { Trash2, ChevronDown, ChevronUp, Calendar, MessageCircle } from 'lucide-react-native';
import { getChatHistory, clearChatHistory } from '../services/apiService';
import { theme } from '../theme/theme';
import { StackHeader } from '../components/StackHeader';

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
      <TouchableOpacity onPress={toggleExpand} style={[styles.groupHead, expanded && styles.groupHeadOn]} activeOpacity={0.75}>
        <View style={styles.groupHeadLeft}>
          <View style={[styles.calIcon, expanded && styles.calIconOn]}>
            <Calendar size={20} color={expanded ? '#fff' : theme.forestLight} />
          </View>
          <View>
            <Text style={styles.groupTitle}>{title}</Text>
            <Text style={styles.groupSub}>{messages.length} mesaj</Text>
          </View>
        </View>
        {expanded ? <ChevronUp size={20} color={theme.muted} /> : <ChevronDown size={20} color={theme.border} />}
      </TouchableOpacity>

      {expanded && (
        <View style={styles.msgBlock}>
          {messages.map((item, index) => {
            const isUser = item.role === 'user';
            return (
              <View key={String(item.id ?? index)} style={[styles.msgRow, isUser ? styles.rowUser : styles.rowAi]}>
                <View style={[styles.bubble, isUser ? styles.bubbleUser : styles.bubbleAi]}>
                  <Text style={[styles.msgText, isUser ? styles.textUser : styles.textAi]}>{item.message}</Text>
                  <Text style={[styles.time, isUser ? styles.timeUser : styles.timeAi]}>
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
      const isToday =
        date.getDate() === today.getDate() && date.getMonth() === today.getMonth() && date.getFullYear() === today.getFullYear();
      const isYesterday =
        date.getDate() === yesterday.getDate() &&
        date.getMonth() === yesterday.getMonth() &&
        date.getFullYear() === yesterday.getFullYear();
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
      <TouchableOpacity onPress={handleClear} style={styles.trashBtn}>
        <Trash2 size={20} color={theme.danger} />
      </TouchableOpacity>
    ) : undefined;

  return (
    <SafeAreaView style={styles.safe} edges={['top']}>
      <StackHeader title="Sohbet geçmişi" onBack={() => navigation.goBack()} right={headerRight} />

      {loading ? (
        <View style={styles.center}>
          <ActivityIndicator size="large" color={theme.forestLight} />
        </View>
      ) : (
        <FlatList
          data={grouped}
          keyExtractor={(_, i) => String(i)}
          contentContainerStyle={{ padding: 20, paddingBottom: 40 }}
          renderItem={({ item }) => <DateGroup title={item.title} messages={item.data} />}
          ListEmptyComponent={
            <View style={styles.empty}>
              <View style={styles.emptyIcon}>
                <MessageCircle size={44} color={theme.forestLight} />
              </View>
              <Text style={styles.emptyTitle}>Kayıt yok</Text>
              <Text style={styles.emptySub}>Asistan ile konuştukça mesajlar burada listelenir.</Text>
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
  trashBtn: { padding: 10, backgroundColor: 'rgba(190,18,60,0.12)', borderRadius: 12 },
  group: {
    marginBottom: 14,
    backgroundColor: theme.surface,
    borderRadius: theme.radiusMd,
    overflow: 'hidden',
    borderWidth: 1,
    borderColor: theme.border,
  },
  groupHead: {
    flexDirection: 'row',
    alignItems: 'center',
    justifyContent: 'space-between',
    padding: 16,
  },
  groupHeadOn: { backgroundColor: theme.skyTint },
  groupHeadLeft: { flexDirection: 'row', alignItems: 'center', gap: 12 },
  calIcon: {
    width: 44,
    height: 44,
    borderRadius: 14,
    backgroundColor: theme.bg,
    justifyContent: 'center',
    alignItems: 'center',
    borderWidth: 1,
    borderColor: theme.border,
  },
  calIconOn: { backgroundColor: theme.forest, borderColor: theme.forest },
  groupTitle: { fontSize: 16, fontWeight: '900', color: theme.ink },
  groupSub: { fontSize: 12, color: theme.muted, marginTop: 2 },
  msgBlock: { padding: 14, paddingTop: 0, backgroundColor: theme.bg, borderTopWidth: 1, borderTopColor: theme.border },
  msgRow: { marginVertical: 6, width: '100%' },
  rowUser: { alignItems: 'flex-end' },
  rowAi: { alignItems: 'flex-start' },
  bubble: { maxWidth: '86%', padding: 12, borderRadius: 16 },
  bubbleUser: { backgroundColor: theme.forestLight, borderBottomRightRadius: 4 },
  bubbleAi: { backgroundColor: theme.surface, borderBottomLeftRadius: 4, borderWidth: 1, borderColor: theme.border },
  msgText: { fontSize: 14, lineHeight: 20 },
  textUser: { color: '#fff' },
  textAi: { color: theme.ink },
  time: { fontSize: 10, marginTop: 4, alignSelf: 'flex-end' },
  timeUser: { color: 'rgba(255,255,255,0.9)' },
  timeAi: { color: theme.muted },
  empty: { alignItems: 'center', marginTop: 64, paddingHorizontal: 36 },
  emptyIcon: {
    width: 96,
    height: 96,
    borderRadius: 28,
    backgroundColor: theme.skyTint,
    justifyContent: 'center',
    alignItems: 'center',
    marginBottom: 18,
    borderWidth: 1,
    borderColor: theme.border,
  },
  emptyTitle: { fontSize: 20, fontWeight: '900', color: theme.ink, marginBottom: 8 },
  emptySub: { fontSize: 15, color: theme.muted, textAlign: 'center', lineHeight: 22 },
});
