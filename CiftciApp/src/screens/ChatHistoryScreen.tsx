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
  StatusBar
} from 'react-native';
import { Screen } from '../components/ui/Screen';
import { StackHeader } from '../components/ui/StackHeader';
import { Trash2, ChevronDown, ChevronUp, Calendar, MessageCircle } from 'lucide-react-native';
import { getChatHistory, clearChatHistory } from '../services/apiService';
import { colors, spacing, radius, typography, shadow } from '../theme';

// Android için animasyon aktivasyonu
if (Platform.OS === 'android' && UIManager.setLayoutAnimationEnabledExperimental) {
  UIManager.setLayoutAnimationEnabledExperimental(true);
}

// Mesaj Tipleri
interface HistoryItem {
  id: string;
  role: 'user' | 'ai';
  message: string;
  created_at: string;
}

// --- Alt Bileşen: Tarih Grubu Kartı ---
const DateGroup = ({ title, messages }: { title: string, messages: HistoryItem[] }) => {
  const [expanded, setExpanded] = useState(false);

  const toggleExpand = () => {
    LayoutAnimation.configureNext(LayoutAnimation.Presets.easeInEaseOut);
    setExpanded(!expanded);
  };

  return (
    <View style={styles.groupContainer}>
      {/* Tarih Başlığı (Tıklanabilir Kart) */}
      <TouchableOpacity
        onPress={toggleExpand}
        style={[styles.groupHeader, expanded && styles.groupHeaderActive]}
        activeOpacity={0.7}
      >
        <View style={styles.headerLeft}>
          <View style={[styles.iconBox, expanded ? styles.iconBoxActive : styles.iconBoxInactive]}>
             <Calendar size={20} color={expanded ? colors.textOnPrimary : colors.primary} />
          </View>
          <View>
             <Text style={styles.groupTitle}>{title}</Text>
             <Text style={styles.groupSubtitle}>{messages.length} Mesaj</Text>
          </View>
        </View>
        {expanded ? <ChevronUp size={20} color={colors.textSecondary} /> : <ChevronDown size={20} color={colors.textMuted} />}
      </TouchableOpacity>

      {/* Mesajlar Listesi (Sadece expanded ise görünür) */}
      {expanded && (
        <View style={styles.messagesList}>
          {messages.map((item, index) => {
            const isUser = item.role === 'user';
            return (
              <View key={item.id || index} style={[styles.msgRow, isUser ? styles.rowUser : styles.rowAi]}>
                <View style={[styles.bubble, isUser ? styles.bubbleUser : styles.bubbleAi]}>
                  <Text style={[styles.msgText, isUser ? styles.textUser : styles.textAi]}>
                    {item.message}
                  </Text>
                  <Text style={[styles.timeText, isUser ? styles.timeUser : styles.timeAi]}>
                    {new Date(item.created_at).toLocaleTimeString('tr-TR', { hour: '2-digit', minute:'2-digit' })}
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
      setHistory(data);
    } catch (error) {
      console.log("Geçmiş yüklenemedi:", error);
    } finally {
      setLoading(false);
    }
  };

  const handleClearHistory = () => {
    Alert.alert(
      "Geçmişi Temizle",
      "Tüm sohbet kayıtlarınız silinecek. Bu işlem geri alınamaz.",
      [
        { text: "Vazgeç", style: "cancel" },
        {
          text: "Evet, Sil",
          style: "destructive",
          onPress: async () => {
            setLoading(true);
            try {
              await clearChatHistory();
              setHistory([]); // Listeyi boşalt
            } catch (error) {
              Alert.alert("Hata", "Geçmiş temizlenemedi.");
            } finally {
              setLoading(false);
            }
          }
        }
      ]
    );
  };

  // Veriyi Tarihe Göre Grupla
  const groupedHistory = useMemo(() => {
    if (!history.length) return [];

    const grouped: { title: string; data: HistoryItem[] }[] = [];
    let currentTitle = "";
    let currentData: HistoryItem[] = [];

    history.forEach((item) => {
      const date = new Date(item.created_at);
      const today = new Date();
      const yesterday = new Date();
      yesterday.setDate(today.getDate() - 1);

      let title = date.toLocaleDateString('tr-TR', { day: 'numeric', month: 'long', year: 'numeric' });

      const isToday = date.getDate() === today.getDate() && date.getMonth() === today.getMonth() && date.getFullYear() === today.getFullYear();
      const isYesterday = date.getDate() === yesterday.getDate() && date.getMonth() === yesterday.getMonth() && date.getFullYear() === yesterday.getFullYear();

      if (isToday) title = "Bugün";
      else if (isYesterday) title = "Dün";

      if (title !== currentTitle) {
        if (currentTitle) {
          grouped.push({ title: currentTitle, data: currentData });
        }
        currentTitle = title;
        currentData = [item];
      } else {
        currentData.push(item);
      }
    });

    if (currentTitle) {
      grouped.push({ title: currentTitle, data: currentData });
    }

    return grouped;
  }, [history]);

  return (
    <Screen edges={['top', 'left', 'right']}>
      <StatusBar barStyle="dark-content" backgroundColor={colors.bg} />
      <StackHeader
        title="Sohbet Geçmişi"
        onBack={() => navigation.goBack()}
        right={
          history.length > 0 ? (
            <TouchableOpacity onPress={handleClearHistory} style={styles.clearBtn}>
              <Trash2 size={20} color={colors.critical} />
            </TouchableOpacity>
          ) : undefined
        }
      />

      {loading ? (
        <View style={styles.center}><ActivityIndicator size="large" color={colors.primary}/></View>
      ) : (
        <FlatList
          data={groupedHistory}
          keyExtractor={(item, index) => index.toString()}
          contentContainerStyle={{ padding: spacing.lg, paddingBottom: 40 }}
          renderItem={({ item }) => (
            <DateGroup title={item.title} messages={item.data} />
          )}
          ListEmptyComponent={
            <View style={styles.emptyContainer}>
              <View style={styles.emptyIconBox}>
                 <MessageCircle size={48} color={colors.textMuted} />
              </View>
              <Text style={styles.emptyTitle}>Henüz Sohbet Yok</Text>
              <Text style={styles.emptyText}>Asistanla yaptığınız konuşmalar burada tarihe göre gruplanarak saklanır.</Text>
            </View>
          }
        />
      )}
    </Screen>
  );
}

const styles = StyleSheet.create({
  center: { flex: 1, justifyContent: 'center', alignItems: 'center' },
  clearBtn: { padding: 8, backgroundColor: '#FEF2F2', borderRadius: radius.sm },
  groupContainer: {
    marginBottom: 16,
    backgroundColor: colors.surface,
    borderRadius: radius.lg,
    overflow: 'hidden',
    borderWidth: 1,
    borderColor: colors.borderLight,
    ...shadow.soft,
  },
  groupHeader: {
    flexDirection: 'row',
    alignItems: 'center',
    justifyContent: 'space-between',
    padding: 16,
    backgroundColor: colors.surface,
  },
  groupHeaderActive: { backgroundColor: colors.bg },
  headerLeft: { flexDirection: 'row', alignItems: 'center', gap: 12 },
  iconBox: {
    width: 40,
    height: 40,
    borderRadius: 20,
    justifyContent: 'center',
    alignItems: 'center',
  },
  iconBoxInactive: { backgroundColor: colors.primarySoft },
  iconBoxActive: { backgroundColor: colors.primary },
  groupTitle: { ...typography.h3, color: colors.text },
  groupSubtitle: { fontSize: 12, color: colors.textMuted, marginTop: 2 },
  messagesList: {
    padding: 16,
    paddingTop: 0,
    backgroundColor: colors.bg,
    borderTopWidth: 1,
    borderTopColor: colors.borderLight,
  },
  msgRow: { marginVertical: 6, width: '100%' },
  rowUser: { alignItems: 'flex-end' },
  rowAi: { alignItems: 'flex-start' },
  bubble: {
    maxWidth: '85%',
    padding: 12,
    borderRadius: 18,
    ...shadow.soft,
  },
  bubbleUser: {
    backgroundColor: colors.primary,
    borderBottomRightRadius: 2,
  },
  bubbleAi: {
    backgroundColor: colors.surface,
    borderBottomLeftRadius: 2,
    borderWidth: 1,
    borderColor: colors.borderLight,
  },
  msgText: { fontSize: 14, lineHeight: 20 },
  textUser: { color: colors.textOnPrimary },
  textAi: { color: colors.text },
  timeText: { fontSize: 10, marginTop: 4, alignSelf: 'flex-end' },
  timeUser: { color: 'rgba(255,255,255,0.8)' },
  timeAi: { color: colors.textMuted },
  emptyContainer: { alignItems: 'center', marginTop: 80, paddingHorizontal: 40 },
  emptyIconBox: {
    width: 100,
    height: 100,
    backgroundColor: colors.bgDeep,
    borderRadius: 50,
    justifyContent: 'center',
    alignItems: 'center',
    marginBottom: 24,
  },
  emptyTitle: { ...typography.h2, color: colors.text, marginBottom: 8 },
  emptyText: { ...typography.body, color: colors.textSecondary, textAlign: 'center' },
});