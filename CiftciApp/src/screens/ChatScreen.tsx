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
import { Send, History, MessageSquarePlus, Bot } from 'lucide-react-native';
import * as Location from 'expo-location';
import { SafeAreaView } from 'react-native-safe-area-context';
import { sendMessageToAI } from '../services/apiService';
import { ChatMessage } from '../types';
import { colors, spacing, radius, typography, shadow } from '../theme';

export default function ChatScreen({ navigation }: any) {
  const INITIAL_MESSAGE: ChatMessage = {
    id: '1',
    text: 'Merhaba! Ben Çiftçi Asistan. **Tarlanız**, **hava durumu** veya **bitki hastalıkları** hakkında bana her şeyi sorabilirsiniz.',
    sender: 'ai',
  };

  const [messages, setMessages] = useState<ChatMessage[]>([INITIAL_MESSAGE]);
  const [text, setText] = useState('');
  const [loading, setLoading] = useState(false);
  const flatListRef = useRef<FlatList>(null);

  const renderStyledText = (msg: string) => {
    const parts = msg.split('**');
    return parts.map((part, index) => (
      <Text key={index} style={index % 2 === 1 ? styles.bold : undefined}>
        {part}
      </Text>
    ));
  };

  const handleNewChat = () => {
    Alert.alert('Yeni Sohbet', 'Mevcut konuşma temizlenecek. Emin misiniz?', [
      { text: 'Vazgeç', style: 'cancel' },
      {
        text: 'Evet, Temizle',
        style: 'destructive',
        onPress: () => {
          setMessages([INITIAL_MESSAGE]);
          setText('');
        },
      },
    ]);
  };

  const handleSend = async () => {
    if (!text.trim()) return;
    const userMsg: ChatMessage = { id: Date.now().toString(), text: text, sender: 'user' };
    setMessages((prev) => [...prev, userMsg]);
    setText('');
    setLoading(true);

    try {
      let lat: number | null = null;
      let lon: number | null = null;
      try {
        const { status } = await Location.requestForegroundPermissionsAsync();
        if (status === 'granted') {
          const locationPromise = Location.getCurrentPositionAsync({ accuracy: Location.Accuracy.Balanced });
          const timeoutPromise = new Promise((_, reject) => setTimeout(() => reject(new Error('Timeout')), 5000));
          const location: any = await Promise.race([locationPromise, timeoutPromise]);
          if (location?.coords) {
            lat = location.coords.latitude;
            lon = location.coords.longitude;
          }
        }
      } catch (e) {
        console.log('Konum alınamadı:', e);
      }

      const aiMsgId = (Date.now() + 1).toString();
      setMessages((prev) => [...prev, { id: aiMsgId, text: '...', sender: 'ai' }]);

      await sendMessageToAI(userMsg.text, lat, lon, (streamText) => {
        setMessages((prev) =>
          prev.map((msg) => (msg.id === aiMsgId ? { ...msg, text: streamText } : msg)),
        );
      });
    } catch (e: any) {
      let errorMessage = 'Üzgünüm, bir hata oluştu.';
      if (
        e.message?.includes('zaman aşımı') ||
        e.message?.includes('timeout') ||
        e.message?.includes('Network request failed')
      ) {
        errorMessage =
          'Sunucu yanıtı gecikti. **Sohbet Geçmişi** ekranını kontrol edin.';
      } else {
        errorMessage = 'Sunucuya bağlanılamadı. **İnternet bağlantınızı** kontrol edin.';
      }
      setMessages((prev) => [
        ...prev,
        { id: (Date.now() + 2).toString(), text: errorMessage, sender: 'ai' },
      ]);
    } finally {
      setLoading(false);
    }
  };

  return (
    <SafeAreaView style={styles.safeArea} edges={['top']}>
      <StatusBar barStyle="light-content" backgroundColor={colors.primaryDark} />

      <View style={styles.header}>
        <View style={styles.headerAvatar}>
          <Bot size={22} color={colors.accent} />
        </View>
        <View style={styles.headerInfo}>
          <Text style={styles.headerTitle}>Çiftçi Asistan</Text>
          <Text style={styles.headerStatus}>Çevrimiçi</Text>
        </View>
        <View style={styles.headerButtons}>
          <TouchableOpacity onPress={handleNewChat} style={styles.iconBtn}>
            <MessageSquarePlus size={22} color={colors.textOnPrimary} />
          </TouchableOpacity>
          <TouchableOpacity onPress={() => navigation.navigate('ChatHistory')} style={styles.iconBtn}>
            <History size={22} color={colors.textOnPrimary} />
          </TouchableOpacity>
        </View>
      </View>

      <KeyboardAvoidingView
        style={styles.keyboardView}
        behavior={Platform.OS === 'ios' ? 'padding' : 'height'}
      >
        <FlatList
          ref={flatListRef}
          data={messages}
          keyExtractor={(item) => item.id}
          onContentSizeChange={() => flatListRef.current?.scrollToEnd()}
          contentContainerStyle={styles.listContent}
          style={{ flex: 1 }}
          renderItem={({ item }) => {
            const isUser = item.sender === 'user';
            return (
              <View style={[styles.msgRow, isUser ? styles.rowUser : styles.rowAi]}>
                <View style={[styles.bubble, isUser ? styles.bubbleUser : styles.bubbleAi]}>
                  <Text style={[styles.msgText, isUser ? styles.textUser : styles.textAi]}>
                    {renderStyledText(item.text)}
                  </Text>
                </View>
              </View>
            );
          }}
        />

        <View style={styles.inputContainer}>
          <View style={styles.inputWrapper}>
            <TextInput
              style={styles.input}
              placeholder="Bir soru sorun..."
              value={text}
              onChangeText={setText}
              multiline
              placeholderTextColor={colors.textMuted}
            />
            <TouchableOpacity
              style={[styles.sendBtn, (!text.trim() || loading) && styles.sendBtnDisabled]}
              onPress={handleSend}
              disabled={loading || !text.trim()}
            >
              {loading ? (
                <ActivityIndicator color={colors.textOnPrimary} size="small" />
              ) : (
                <Send size={20} color={colors.textOnPrimary} />
              )}
            </TouchableOpacity>
          </View>
        </View>
      </KeyboardAvoidingView>
    </SafeAreaView>
  );
}

const styles = StyleSheet.create({
  safeArea: { flex: 1, backgroundColor: colors.primaryDark },
  header: {
    flexDirection: 'row',
    alignItems: 'center',
    paddingVertical: 14,
    paddingHorizontal: spacing.md,
    backgroundColor: colors.primaryDark,
    gap: 12,
  },
  headerAvatar: {
    width: 44,
    height: 44,
    borderRadius: 14,
    backgroundColor: 'rgba(255,255,255,0.12)',
    alignItems: 'center',
    justifyContent: 'center',
  },
  headerInfo: { flex: 1 },
  headerTitle: { color: colors.textOnPrimary, ...typography.h2, fontSize: 18 },
  headerStatus: { color: colors.accentSoft, fontSize: 12, fontWeight: '600', marginTop: 2 },
  headerButtons: { flexDirection: 'row', gap: 8 },
  iconBtn: {
    padding: 10,
    backgroundColor: 'rgba(255,255,255,0.15)',
    borderRadius: radius.sm,
  },
  keyboardView: { flex: 1, backgroundColor: colors.bg },
  listContent: { padding: spacing.md, paddingBottom: spacing.md },
  msgRow: { marginVertical: 4, width: '100%' },
  rowUser: { alignItems: 'flex-end' },
  rowAi: { alignItems: 'flex-start' },
  bubble: {
    maxWidth: '82%',
    paddingHorizontal: 16,
    paddingVertical: 12,
    borderRadius: 20,
  },
  bubbleUser: {
    backgroundColor: colors.primary,
    borderBottomRightRadius: 4,
    ...shadow.soft,
  },
  bubbleAi: {
    backgroundColor: colors.surface,
    borderBottomLeftRadius: 4,
    borderWidth: 1,
    borderColor: colors.borderLight,
  },
  msgText: { fontSize: 16, lineHeight: 22 },
  bold: { fontWeight: '800' },
  textUser: { color: colors.textOnPrimary },
  textAi: { color: colors.text },
  inputContainer: { padding: spacing.md, backgroundColor: colors.bg },
  inputWrapper: {
    flexDirection: 'row',
    alignItems: 'flex-end',
    backgroundColor: colors.surface,
    borderRadius: radius.full,
    padding: 6,
    borderWidth: 1,
    borderColor: colors.borderLight,
    ...shadow.soft,
  },
  input: {
    flex: 1,
    paddingHorizontal: 16,
    paddingVertical: 12,
    maxHeight: 120,
    fontSize: 16,
    color: colors.text,
  },
  sendBtn: {
    width: 44,
    height: 44,
    backgroundColor: colors.primary,
    borderRadius: 22,
    justifyContent: 'center',
    alignItems: 'center',
    marginRight: 2,
    marginBottom: 2,
  },
  sendBtnDisabled: { backgroundColor: colors.textMuted },
});
