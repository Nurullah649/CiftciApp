import React, { useState, useRef } from 'react';
import { View, Text, TextInput, TouchableOpacity, FlatList, StyleSheet, KeyboardAvoidingView, Platform, ActivityIndicator, StatusBar, Alert } from 'react-native';
import { Send, History, MessageSquarePlus } from 'lucide-react-native'; // Yeni ikon eklendi
import * as Location from 'expo-location';
import { SafeAreaView } from 'react-native-safe-area-context';
import { sendMessageToAI } from '../services/apiService';
import { ChatMessage } from '../types';

export default function ChatScreen({ navigation }: any) {
  // Başlangıç mesajını sabit bir değişkende tutalım, tekrar kullanacağız
  const INITIAL_MESSAGE: ChatMessage = {
    id: '1',
    text: "Merhaba! Ben Çiftçi Asistan. **Tarlanız**, **hava durumu** veya **bitki hastalıkları** hakkında bana her şeyi sorabilirsiniz.",
    sender: 'ai'
  };

  const [messages, setMessages] = useState<ChatMessage[]>([INITIAL_MESSAGE]);
  const [text, setText] = useState('');
  const [loading, setLoading] = useState(false);
  const flatListRef = useRef<FlatList>(null);

  // Metin içindeki **bold** işaretlerini işleyen fonksiyon
  const renderStyledText = (text: string) => {
    const parts = text.split('**');
    return parts.map((part, index) => {
      if (index % 2 === 1) {
        return (
          <Text key={index} style={{ fontWeight: 'bold' }}>
            {part}
          </Text>
        );
      }
      return <Text key={index}>{part}</Text>;
    });
  };

  // Yeni Sohbet Başlatma Fonksiyonu
  const handleNewChat = () => {
    Alert.alert(
      "Yeni Sohbet",
      "Mevcut konuşma temizlenecek ve yeni bir sayfa açılacak. Emin misiniz?",
      [
        { text: "Vazgeç", style: "cancel" },
        {
          text: "Evet, Temizle",
          onPress: () => {
            setMessages([INITIAL_MESSAGE]); // Mesajları sıfırla
            setText(''); // Yazı alanını temizle
          },
          style: 'destructive'
        }
      ]
    );
  };

  const handleSend = async () => {
    if (!text.trim()) return;

    const userMsg: ChatMessage = { id: Date.now().toString(), text: text, sender: 'user' };
    setMessages(prev => [...prev, userMsg]);
    setText('');
    setLoading(true);

    try {
      let lat = null;
      let lon = null;

      try {
        let { status } = await Location.requestForegroundPermissionsAsync();
        if (status === 'granted') {
          const locationPromise = Location.getCurrentPositionAsync({ accuracy: Location.Accuracy.Balanced });
          const timeoutPromise = new Promise((_, reject) => setTimeout(() => reject(new Error("Timeout")), 5000));
          const location: any = await Promise.race([locationPromise, timeoutPromise]);

          if (location && location.coords) {
            lat = location.coords.latitude;
            lon = location.coords.longitude;
          }
        }
      } catch (e) {
        console.log("Konum alınamadı, devam ediliyor:", e);
      }

      // 1. AI için boş bir mesaj oluştur
      const aiMsgId = (Date.now() + 1).toString();
      const aiMsg: ChatMessage = { id: aiMsgId, text: "...", sender: 'ai' };
      setMessages(prev => [...prev, aiMsg]);

      // 2. Stream başlat
      await sendMessageToAI(userMsg.text, lat, lon, (streamText) => {
        setMessages(prev =>
          prev.map(msg =>
            msg.id === aiMsgId ? { ...msg, text: streamText } : msg
          )
        );
      });

    } catch (e: any) {
      console.log("Sohbet Hatası:", e);
      let errorMessage = "Üzgünüm, bir hata oluştu.";

      if (e.message && (e.message.includes('zaman aşımı') || e.message.includes('timeout') || e.message.includes('Network request failed'))) {
        errorMessage = "Sunucu yanıtı gecikti. İşleminiz arka planda tamamlanmış olabilir. Lütfen **Sohbet Geçmişi** ekranını kontrol edin.";
      } else {
        errorMessage = "Sunucuyla bağlantı kurulamadı. Lütfen **internet bağlantınızı** kontrol edin.";
      }

      const errorMsgObj: ChatMessage = {
        id: (Date.now() + 2).toString(),
        text: errorMessage,
        sender: 'ai'
      };
      setMessages(prev => [...prev, errorMsgObj]);
    } finally {
      setLoading(false);
    }
  };

  return (
    <SafeAreaView style={styles.safeArea} edges={['top']}>
      <StatusBar barStyle="light-content" backgroundColor="#16a34a" />

      {/* Header */}
      <View style={styles.header}>
        <View style={styles.headerInfo}>
          <Text style={styles.headerTitle}>Çiftçi Asistan</Text>
          <Text style={styles.headerStatus}>• Çevrimiçi</Text>
        </View>

        {/* Buton Grubu */}
        <View style={styles.headerButtons}>
          {/* Yeni Sohbet Butonu */}
          <TouchableOpacity
            onPress={handleNewChat}
            style={styles.iconBtn}
          >
            <MessageSquarePlus size={24} color="#fff" />
          </TouchableOpacity>

          {/* Geçmiş Butonu */}
          <TouchableOpacity
            onPress={() => navigation.navigate('ChatHistory')}
            style={styles.iconBtn}
          >
            <History size={24} color="#fff" />
          </TouchableOpacity>
        </View>
      </View>

      <KeyboardAvoidingView
        style={styles.keyboardView}
        behavior={Platform.OS === 'ios' ? 'padding' : 'height'}
        keyboardVerticalOffset={Platform.OS === 'ios' ? 0 : 0}
      >
        <View style={styles.contentContainer}>
          <FlatList
            ref={flatListRef}
            data={messages}
            keyExtractor={item => item.id}
            onContentSizeChange={() => flatListRef.current?.scrollToEnd()}
            contentContainerStyle={styles.listContent}
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

          {/* Input Alanı */}
          <View style={styles.inputContainer}>
            <View style={styles.inputWrapper}>
              <TextInput
                style={styles.input}
                placeholder="Bir soru sorun..."
                value={text}
                onChangeText={setText}
                multiline
                placeholderTextColor="#9ca3af"
              />
              <TouchableOpacity
                style={[styles.sendBtn, (!text.trim() || loading) && styles.sendBtnDisabled]}
                onPress={handleSend}
                disabled={loading || !text.trim()}
              >
                {loading ? <ActivityIndicator color="#fff" size="small" /> : <Send size={20} color="#fff" />}
              </TouchableOpacity>
            </View>
          </View>
        </View>
      </KeyboardAvoidingView>
    </SafeAreaView>
  );
}

const styles = StyleSheet.create({
  safeArea: { flex: 1, backgroundColor: '#16a34a' },

  // Header
  header: {
    backgroundColor: '#16a34a',
    paddingVertical: 16,
    paddingHorizontal: 20,
    flexDirection: 'row',
    alignItems: 'center',
    justifyContent: 'space-between',
    elevation: 0,
    borderBottomWidth: 0,
  },
  headerInfo: { flex: 1 },
  headerTitle: { color: '#fff', fontSize: 20, fontWeight: 'bold' },
  headerStatus: { color: '#dcfce7', fontSize: 13, fontWeight: '500', marginTop: 2 },

  headerButtons: { flexDirection: 'row', gap: 12 },
  iconBtn: { padding: 8, backgroundColor: 'rgba(255,255,255,0.2)', borderRadius: 12 },

  // Genel Alan
  keyboardView: { flex: 1, backgroundColor: '#f3f4f6' },
  contentContainer: { flex: 1 },
  listContent: { padding: 16, paddingBottom: 24 },

  // Mesaj Satırları
  msgRow: { marginVertical: 4, width: '100%' },
  rowUser: { alignItems: 'flex-end' },
  rowAi: { alignItems: 'flex-start' },

  // Baloncuklar
  bubble: {
    maxWidth: '80%',
    paddingHorizontal: 16,
    paddingVertical: 12,
    borderRadius: 20,
  },
  bubbleUser: {
    backgroundColor: '#16a34a',
    borderBottomRightRadius: 4,
    shadowColor: "#16a34a",
    shadowOffset: { width: 0, height: 2 },
    shadowOpacity: 0.2,
    shadowRadius: 4,
    elevation: 2,
  },
  bubbleAi: {
    backgroundColor: '#ffffff',
    borderBottomLeftRadius: 4,
    shadowColor: "#000",
    shadowOffset: { width: 0, height: 1 },
    shadowOpacity: 0.05,
    shadowRadius: 2,
    elevation: 1,
  },

  // Metinler
  msgText: { fontSize: 16, lineHeight: 22 },
  textUser: { color: '#fff' },
  textAi: { color: '#1f2937' },

  // Input Alanı
  inputContainer: {
    padding: 16,
    backgroundColor: '#f3f4f6',
  },
  inputWrapper: {
    flexDirection: 'row',
    alignItems: 'flex-end',
    backgroundColor: '#fff',
    borderRadius: 28,
    padding: 6,
    shadowColor: "#000",
    shadowOffset: { width: 0, height: 2 },
    shadowOpacity: 0.05,
    shadowRadius: 8,
    elevation: 2,
  },
  input: {
    flex: 1,
    paddingHorizontal: 16,
    paddingTop: 12,
    paddingBottom: 12,
    maxHeight: 120,
    fontSize: 16,
    color: '#1f2937',
  },
  sendBtn: {
    width: 44,
    height: 44,
    backgroundColor: '#16a34a',
    borderRadius: 22,
    justifyContent: 'center',
    alignItems: 'center',
    marginBottom: 2,
    marginRight: 2
  },
  sendBtnDisabled: {
    backgroundColor: '#bdc3c7'
  }
});