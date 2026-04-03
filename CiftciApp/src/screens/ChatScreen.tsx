import React, { useState, useRef } from 'react';
import {
  View,
  Text,
  TextInput,
  TouchableOpacity,
  FlatList,
  StyleSheet,
  KeyboardAvoidingView,
  Platform,
  ActivityIndicator,
  StatusBar,
  Alert,
} from 'react-native';
import { Send, History, MessageSquarePlus } from 'lucide-react-native';
import * as Location from 'expo-location';
import { SafeAreaView, useSafeAreaInsets } from 'react-native-safe-area-context';
import { sendMessageToAI } from '../services/apiService';
import { ChatMessage } from '../types';
import { theme } from '../theme/theme';

const TAB_BAR_CLEARANCE = Platform.OS === 'ios' ? 92 : 82;

export default function ChatScreen({ navigation }: any) {
  const insets = useSafeAreaInsets();
  const bottomExtra = TAB_BAR_CLEARANCE + Math.max(insets.bottom - 8, 0);

  const INITIAL_MESSAGE: ChatMessage = {
    id: '1',
    text: 'Merhaba! **Çiftçi asistan** burada. Sulama, gübreleme, hava veya takvim önerileri için yazın. Yanıtlar sunucudaki modelden gelir.',
    sender: 'ai',
  };

  const [messages, setMessages] = useState<ChatMessage[]>([INITIAL_MESSAGE]);
  const [text, setText] = useState('');
  const [loading, setLoading] = useState(false);
  const flatListRef = useRef<FlatList>(null);

  const renderStyledText = (t: string, user: boolean) => {
    const parts = t.split('**');
    return parts.map((part, index) =>
      index % 2 === 1 ? (
        <Text key={index} style={{ fontWeight: '900', color: user ? '#fff' : theme.forestLight }}>
          {part}
        </Text>
      ) : (
        <Text key={index}>{part}</Text>
      )
    );
  };

  const handleNewChat = () => {
    Alert.alert('Yeni sohbet', 'Bu ekrandaki mesajlar sıfırlanır (sunucu geçmişi silinmez).', [
      { text: 'Vazgeç', style: 'cancel' },
      { text: 'Sıfırla', style: 'destructive', onPress: () => { setMessages([INITIAL_MESSAGE]); setText(''); } },
    ]);
  };

  const handleSend = async () => {
    if (!text.trim()) return;

    const userMsg: ChatMessage = { id: Date.now().toString(), text: text.trim(), sender: 'user' };
    setMessages((prev) => [...prev, userMsg]);
    setText('');
    setLoading(true);

    const aiMsgId = (Date.now() + 1).toString();

    try {
      let lat: number | null = null;
      let lon: number | null = null;
      try {
        const { status } = await Location.requestForegroundPermissionsAsync();
        if (status === 'granted') {
          const locationPromise = Location.getCurrentPositionAsync({ accuracy: Location.Accuracy.Balanced });
          const timeoutPromise = new Promise<never>((_, reject) => setTimeout(() => reject(new Error('Timeout')), 5000));
          const location: any = await Promise.race([locationPromise, timeoutPromise]);
          if (location?.coords) {
            lat = location.coords.latitude;
            lon = location.coords.longitude;
          }
        }
      } catch {
        /* konum opsiyonel */
      }

      const aiMsg: ChatMessage = { id: aiMsgId, text: '...', sender: 'ai' };
      setMessages((prev) => [...prev, aiMsg]);

      await sendMessageToAI(userMsg.text, lat, lon, (streamText) => {
        setMessages((prev) => prev.map((msg) => (msg.id === aiMsgId ? { ...msg, text: streamText } : msg)));
      });
    } catch (e: any) {
      const err = e?.message || 'Bir hata oluştu.';
      setMessages((prev) =>
        prev
          .filter((m) => m.id !== aiMsgId)
          .concat({ id: (Date.now() + 2).toString(), text: err, sender: 'ai' })
      );
    } finally {
      setLoading(false);
    }
  };

  return (
    <SafeAreaView style={styles.safe} edges={['top']}>
      <StatusBar barStyle="light-content" backgroundColor={theme.forest} />
      <View style={styles.header}>
        <View style={{ flex: 1 }}>
          <Text style={styles.kicker}>ASİSTAN</Text>
          <Text style={styles.headerTitle}>Canlı sohbet</Text>
          <Text style={styles.headerSub}>Akışlı yanıt</Text>
        </View>
        <TouchableOpacity onPress={handleNewChat} style={styles.hBtn}>
          <MessageSquarePlus size={22} color="#fff" />
        </TouchableOpacity>
        <TouchableOpacity onPress={() => navigation.navigate('ChatHistory')} style={styles.hBtn}>
          <History size={22} color="#fff" />
        </TouchableOpacity>
      </View>

      <KeyboardAvoidingView style={{ flex: 1 }} behavior={Platform.OS === 'ios' ? 'padding' : 'height'} keyboardVerticalOffset={0}>
        <FlatList
          ref={flatListRef}
          data={messages}
          keyExtractor={(item) => item.id}
          onContentSizeChange={() => flatListRef.current?.scrollToEnd()}
          contentContainerStyle={styles.list}
          renderItem={({ item }) => {
            const user = item.sender === 'user';
            return (
              <View style={[styles.row, user ? styles.rowUser : styles.rowAi]}>
                <View style={[styles.bubble, user ? styles.bubbleUser : styles.bubbleAi]}>
                  <Text style={[styles.msg, user ? styles.msgUser : styles.msgAi]}>{renderStyledText(item.text, user)}</Text>
                </View>
              </View>
            );
          }}
        />

        <View style={[styles.inputBar, { paddingBottom: 12 + bottomExtra }]}>
          <View style={styles.inputWrap}>
            <TextInput
              style={styles.input}
              placeholder="Mesajınızı yazın..."
              placeholderTextColor={theme.muted}
              value={text}
              onChangeText={setText}
              multiline
            />
            <TouchableOpacity
              style={[styles.send, (!text.trim() || loading) && { opacity: 0.4 }]}
              onPress={handleSend}
              disabled={loading || !text.trim()}
            >
              {loading ? <ActivityIndicator color="#fff" size="small" /> : <Send size={20} color="#fff" />}
            </TouchableOpacity>
          </View>
        </View>
      </KeyboardAvoidingView>
    </SafeAreaView>
  );
}

const styles = StyleSheet.create({
  safe: { flex: 1, backgroundColor: theme.forest },
  header: {
    flexDirection: 'row',
    alignItems: 'center',
    paddingHorizontal: 20,
    paddingTop: 6,
    paddingBottom: 18,
    borderBottomLeftRadius: 24,
    borderBottomRightRadius: 24,
    backgroundColor: theme.forest,
  },
  kicker: { color: theme.tabActive, fontSize: 10, fontWeight: '900', letterSpacing: 2 },
  headerTitle: { color: '#fff', fontSize: 22, fontWeight: '900', marginTop: 6 },
  headerSub: { color: 'rgba(255,255,255,0.65)', fontSize: 12, marginTop: 2 },
  hBtn: {
    padding: 11,
    backgroundColor: 'rgba(255,255,255,0.1)',
    borderRadius: 14,
    marginLeft: 8,
    borderWidth: 1,
    borderColor: 'rgba(255,255,255,0.12)',
  },
  list: { padding: 16, paddingBottom: 20, backgroundColor: theme.bg, flexGrow: 1 },
  row: { marginVertical: 5, width: '100%' },
  rowUser: { alignItems: 'flex-end' },
  rowAi: { alignItems: 'flex-start' },
  bubble: { maxWidth: '84%', paddingVertical: 12, paddingHorizontal: 16, borderRadius: 18 },
  bubbleUser: { backgroundColor: theme.forestLight, borderBottomRightRadius: 4 },
  bubbleAi: {
    backgroundColor: theme.surface,
    borderBottomLeftRadius: 4,
    borderWidth: 1,
    borderColor: theme.border,
  },
  msg: { fontSize: 16, lineHeight: 23 },
  msgUser: { color: '#fff' },
  msgAi: { color: theme.ink },
  inputBar: { paddingHorizontal: 14, paddingTop: 10, backgroundColor: theme.bg, borderTopWidth: 1, borderTopColor: theme.border },
  inputWrap: {
    flexDirection: 'row',
    alignItems: 'flex-end',
    backgroundColor: theme.surface,
    borderRadius: 22,
    borderWidth: 1,
    borderColor: theme.border,
    paddingLeft: 4,
    paddingRight: 4,
    paddingVertical: 4,
  },
  input: { flex: 1, paddingHorizontal: 14, paddingVertical: 12, maxHeight: 120, fontSize: 16, color: theme.ink },
  send: {
    width: 46,
    height: 46,
    borderRadius: 23,
    backgroundColor: theme.accent,
    justifyContent: 'center',
    alignItems: 'center',
  },
});
