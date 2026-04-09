import React, { useRef, useState } from 'react';
import {
  ActivityIndicator,
  Alert,
  FlatList,
  KeyboardAvoidingView,
  Platform,
  SafeAreaView,
  StatusBar,
  StyleSheet,
  Text,
  TextInput,
  TouchableOpacity,
  View,
} from 'react-native';
import { History, MessageSquarePlus, Send } from 'lucide-react-native';
import * as Location from 'expo-location';
import { useSafeAreaInsets } from 'react-native-safe-area-context';
import { sendMessageToAI } from '../services/apiService';
import { ChatMessage } from '../types';
import { theme } from '../theme/theme';
import { AmbientBackdrop } from '../components/AmbientBackdrop';

const TAB_BAR_CLEARANCE = Platform.OS === 'ios' ? 94 : 84;
const QUICK_PROMPTS = [
  'Bugün sulama yapmalı mıyım?',
  'Domateste yaprak lekesi neden olur?',
  'Haftalık iş planı çıkar.',
];

export default function ChatScreen({ navigation }: any) {
  const insets = useSafeAreaInsets();
  const bottomExtra = TAB_BAR_CLEARANCE + Math.max(insets.bottom - 8, 0);
  const flatListRef = useRef<FlatList>(null);

  const initialMessage: ChatMessage = {
    id: '1',
    text: 'Merhaba. Tarla, sulama, gübreleme ve hastalık gözlemleri için buradayım. İstersen konumu da kullanarak daha net öneri verebilirim.',
    sender: 'ai',
  };

  const [messages, setMessages] = useState<ChatMessage[]>([initialMessage]);
  const [text, setText] = useState('');
  const [loading, setLoading] = useState(false);

  const renderStyledText = (value: string, user: boolean) => {
    const parts = value.split('**');
    return parts.map((part, index) =>
      index % 2 === 1 ? (
        <Text key={index} style={{ fontWeight: '900', color: user ? '#fff' : theme.accent }}>
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
      { text: 'Sıfırla', style: 'destructive', onPress: () => { setMessages([initialMessage]); setText(''); } },
    ]);
  };

  const handleSend = async (prefill?: string) => {
    const payload = (prefill ?? text).trim();
    if (!payload) return;

    const userMsg: ChatMessage = { id: Date.now().toString(), text: payload, sender: 'user' };
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

      await sendMessageToAI(payload, lat, lon, (streamText) => {
        setMessages((prev) => prev.map((msg) => (msg.id === aiMsgId ? { ...msg, text: streamText } : msg)));
      });
    } catch (e: any) {
      const err = e?.message || 'Bir hata oluştu.';
      setMessages((prev) =>
        prev.filter((m) => m.id !== aiMsgId).concat({ id: (Date.now() + 2).toString(), text: err, sender: 'ai' })
      );
    } finally {
      setLoading(false);
    }
  };

  return (
    <SafeAreaView style={styles.safe}>
      <StatusBar barStyle="dark-content" backgroundColor={theme.bg} />
      <AmbientBackdrop />

      <View style={styles.headerRow}>
        <View style={{ flex: 1 }}>
          <Text style={styles.headerEyebrow}>ZİRAAT ASİSTANI</Text>
          <Text style={styles.headerTitle}>Kısa yazın, net cevap alın.</Text>
        </View>
        <TouchableOpacity onPress={handleNewChat} style={styles.topButton}>
          <MessageSquarePlus size={18} color={theme.ink} />
        </TouchableOpacity>
        <TouchableOpacity onPress={() => navigation.navigate('ChatHistory')} style={styles.topButton}>
          <History size={18} color={theme.ink} />
        </TouchableOpacity>
      </View>

      <KeyboardAvoidingView style={{ flex: 1 }} behavior={Platform.OS === 'ios' ? 'padding' : 'height'}>
        <FlatList
          ref={flatListRef}
          data={messages}
          keyExtractor={(item) => item.id}
          onContentSizeChange={() => flatListRef.current?.scrollToEnd({ animated: true })}
          contentContainerStyle={styles.list}
          ListHeaderComponent={
            <View style={styles.promptCard}>
              <Text style={styles.promptTitle}>Hazır sorular</Text>
              <Text style={styles.promptSub}>Hızlı başlamak için birini seçebilirsiniz.</Text>
              <View style={styles.promptWrap}>
                {QUICK_PROMPTS.map((prompt) => (
                  <TouchableOpacity key={prompt} style={styles.promptChip} onPress={() => handleSend(prompt)} activeOpacity={0.88}>
                    <Text style={styles.promptChipText}>{prompt}</Text>
                  </TouchableOpacity>
                ))}
              </View>
            </View>
          }
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
              placeholder="Sorunuzu yazın..."
              placeholderTextColor={theme.muted}
              value={text}
              onChangeText={setText}
              multiline
            />
            <TouchableOpacity
              style={[styles.send, (!text.trim() || loading) && styles.sendDisabled]}
              onPress={() => handleSend()}
              disabled={loading || !text.trim()}
            >
              {loading ? <ActivityIndicator color="#fff" size="small" /> : <Send size={18} color="#fff" />}
            </TouchableOpacity>
          </View>
        </View>
      </KeyboardAvoidingView>
    </SafeAreaView>
  );
}

const styles = StyleSheet.create({
  safe: { flex: 1, backgroundColor: theme.bg },
  headerRow: {
    flexDirection: 'row',
    alignItems: 'center',
    gap: 10,
    paddingHorizontal: 20,
    paddingTop: 8,
    paddingBottom: 12,
  },
  headerEyebrow: { color: theme.muted, fontSize: 11, fontWeight: '900', letterSpacing: 1.2 },
  headerTitle: { color: theme.ink, fontSize: 28, lineHeight: 32, fontWeight: '900', marginTop: 8, maxWidth: 230 },
  topButton: {
    width: 42,
    height: 42,
    borderRadius: 14,
    backgroundColor: theme.surface,
    borderWidth: 1,
    borderColor: theme.border,
    justifyContent: 'center',
    alignItems: 'center',
  },
  list: { paddingHorizontal: 20, paddingTop: 6, paddingBottom: 24, flexGrow: 1 },
  promptCard: {
    backgroundColor: theme.surface,
    borderRadius: theme.radiusLg,
    padding: 16,
    borderWidth: 1,
    borderColor: theme.border,
    marginBottom: 14,
  },
  promptTitle: { color: theme.ink, fontSize: 17, fontWeight: '900' },
  promptSub: { color: theme.inkSoft, fontSize: 14, lineHeight: 20, marginTop: 6 },
  promptWrap: { flexDirection: 'row', flexWrap: 'wrap', gap: 8, marginTop: 12 },
  promptChip: {
    backgroundColor: theme.surfaceStrong,
    borderRadius: 999,
    paddingHorizontal: 12,
    paddingVertical: 10,
  },
  promptChipText: { color: theme.inkSecondary, fontSize: 13, fontWeight: '700' },
  row: { marginVertical: 5, width: '100%' },
  rowUser: { alignItems: 'flex-end' },
  rowAi: { alignItems: 'flex-start' },
  bubble: { maxWidth: '85%', paddingVertical: 13, paddingHorizontal: 16, borderRadius: 18 },
  bubbleUser: { backgroundColor: theme.accent, borderBottomRightRadius: 6 },
  bubbleAi: { backgroundColor: theme.surface, borderBottomLeftRadius: 6, borderWidth: 1, borderColor: theme.border },
  msg: { fontSize: 15, lineHeight: 23 },
  msgUser: { color: '#fff' },
  msgAi: { color: theme.ink },
  inputBar: { paddingHorizontal: 14, paddingTop: 10 },
  inputWrap: {
    flexDirection: 'row',
    alignItems: 'flex-end',
    backgroundColor: theme.surface,
    borderRadius: theme.radiusLg,
    borderWidth: 1,
    borderColor: theme.border,
    padding: 6,
  },
  input: {
    flex: 1,
    paddingHorizontal: 14,
    paddingVertical: 13,
    maxHeight: 120,
    fontSize: 16,
    color: theme.ink,
  },
  send: {
    width: 46,
    height: 46,
    borderRadius: 14,
    backgroundColor: theme.accent,
    justifyContent: 'center',
    alignItems: 'center',
  },
  sendDisabled: { opacity: 0.45 },
});
