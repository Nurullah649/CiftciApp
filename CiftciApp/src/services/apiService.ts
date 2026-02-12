import * as SecureStore from 'expo-secure-store';
import { Platform } from 'react-native';
import { AnalysisResult, WeatherData, Task } from '../types';

// GÜVENLİK NOTU: Sunucu IP adresini buraya girin.
const API_BASE_URL = "https://ciftciapp.nurullahkurnaz.com:8000";

const TOKEN_KEY = 'auth_token';

// --- GÜVENLİ DEPOLAMA YARDIMCILARI ---
async function saveToken(token: string) {
  if (Platform.OS === 'web') {
    localStorage.setItem(TOKEN_KEY, token);
  } else {
    await SecureStore.setItemAsync(TOKEN_KEY, token);
  }
}

async function getToken(): Promise<string | null> {
  if (Platform.OS === 'web') {
    return localStorage.getItem(TOKEN_KEY);
  }
  return await SecureStore.getItemAsync(TOKEN_KEY);
}

// Auto-login kontrolü için export
export async function isLoggedIn(): Promise<boolean> {
  const token = await getToken();
  return token !== null && token.length > 0;
}

export async function removeToken() {
  if (Platform.OS === 'web') {
    localStorage.removeItem(TOKEN_KEY);
  } else {
    await SecureStore.deleteItemAsync(TOKEN_KEY);
  }
}

// --- YARDIMCI: HEADER OLUŞTURMA ---
const getAuthHeaders = async () => {
  const token = await getToken();
  return {
    'Content-Type': 'application/json',
    'Authorization': `Bearer ${token}`
  };
};

// --- HATA YÖNETİMİ ---
const handleApiError = async (response: Response, endpointName: string) => {
  if (!response.ok) {
    console.log(`API Hatası (${endpointName}):`, response.status);
    if (response.status === 401) {
      await removeToken();
      throw new Error('Oturum süresi doldu.');
    }
    const text = await response.text();
    try {
      const json = JSON.parse(text);
      throw new Error(json.detail || `Sunucu hatası: ${response.status}`);
    } catch (e) {
      throw new Error(`Sunucu hatası (${response.status})`);
    }
  }
  return response.json();
};

// --- KİMLİK DOĞRULAMA ---
export const loginUser = async (email: string, password: string) => {
  const response = await fetch(`${API_BASE_URL}/auth/login`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ email, password }),
  });
  const data = await handleApiError(response, 'Login');
  if (data.access_token) {
    await saveToken(data.access_token);
  }
  return data;
};

export const registerUser = async (data: { email: string; password: string; firstName?: string; lastName?: string }) => {
  const response = await fetch(`${API_BASE_URL}/auth/register`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({
      email: data.email,
      password: data.password,
      first_name: data.firstName,
      last_name: data.lastName
    }),
  });
  return await handleApiError(response, 'Register');
};

export const logoutUser = async () => {
  await removeToken();
};

export const deleteMyAccount = async () => {
  const headers = await getAuthHeaders();
  const response = await fetch(`${API_BASE_URL}/auth/me`, {
    method: 'DELETE',
    headers
  });
  return await handleApiError(response, 'DeleteAccount');
};

// --- PROFİL ---
export const getUserProfile = async () => {
  const headers = await getAuthHeaders();
  const response = await fetch(`${API_BASE_URL}/auth/profile`, { headers });
  return await handleApiError(response, 'GetProfile');
};

export const updateUserProfile = async (data: { firstName: string, lastName: string, location: string }) => {
  const headers = await getAuthHeaders();
  const response = await fetch(`${API_BASE_URL}/auth/profile`, {
    method: 'PUT',
    headers,
    body: JSON.stringify({
      first_name: data.firstName,
      last_name: data.lastName,
      location: data.location
    }),
  });
  return await handleApiError(response, 'UpdateProfile');
};

// --- GÖREV (PLAN) YÖNETİMİ ---
export const getTasks = async (): Promise<Task[]> => {
  const headers = await getAuthHeaders();
  try {
    const response = await fetch(`${API_BASE_URL}/tasks`, { headers });
    return await handleApiError(response, 'GetTasks');
  } catch (error) {
    console.log("Görev çekme hatası:", error);
    return [];
  }
};

export const updateTaskStatus = async (taskId: number, status: 'approved' | 'completed') => {
  const headers = await getAuthHeaders();
  const response = await fetch(`${API_BASE_URL}/tasks/${taskId}`, {
    method: 'PUT',
    headers,
    body: JSON.stringify({ status })
  });
  return await handleApiError(response, 'UpdateTask');
};

export const deleteTask = async (taskId: number) => {
  const headers = await getAuthHeaders();
  const response = await fetch(`${API_BASE_URL}/tasks/${taskId}`, {
    method: 'DELETE',
    headers
  });
  return await handleApiError(response, 'DeleteTask');
};

// --- SOHBET VE AI ---
export const getChatHistory = async () => {
  const headers = await getAuthHeaders();
  const response = await fetch(`${API_BASE_URL}/chat/history`, { headers });
  return await handleApiError(response, 'ChatHistory');
};

export const clearChatHistory = async () => {
  const headers = await getAuthHeaders();
  const response = await fetch(`${API_BASE_URL}/chat/history`, {
    method: 'DELETE',
    headers
  });
  return await handleApiError(response, 'ClearChatHistory');
};

export const sendMessageToAI = async (
  question: string,
  lat?: number | null,
  lon?: number | null,
  onProgress?: (text: string) => void
): Promise<string> => {
  const token = await getToken();

  if (!onProgress) {
    // Eski yöntem (stream yoksa)
    const headers = {
      'Content-Type': 'application/json',
      'Authorization': `Bearer ${token}`
    };
    const response = await fetch(`${API_BASE_URL}/ask`, {
      method: 'POST',
      headers,
      body: JSON.stringify({
        question,
        lat: lat || null,
        lon: lon || null
      })
    });

    if (!response.ok) {
      throw new Error(`API Hatası: ${response.status}`);
    }
    return await response.text();
  }

  // Streaming (XMLHttpRequest ile)
  return new Promise((resolve, reject) => {
    const xhr = new XMLHttpRequest();
    xhr.open('POST', `${API_BASE_URL}/ask`);
    xhr.setRequestHeader('Content-Type', 'application/json');
    xhr.setRequestHeader('Authorization', `Bearer ${token}`);

    // Stream işleme
    xhr.onprogress = () => {
      // responseText tüm içeriği tutar (accumulated)
      onProgress(xhr.responseText);
    };

    xhr.onload = () => {
      if (xhr.status >= 200 && xhr.status < 300) {
        resolve(xhr.responseText);
      } else {
        reject(new Error(`API Hatası: ${xhr.status}`));
      }
    };

    xhr.onerror = () => {
      reject(new Error("Sunucuyla bağlantı kurulamadı."));
    };

    xhr.send(JSON.stringify({
      question,
      lat: lat || null,
      lon: lon || null
    }));
  });
};

export const getWeatherData = async (lat: number, lon: number): Promise<WeatherData> => {
  try {
    const headers = await getAuthHeaders();
    const response = await fetch(`${API_BASE_URL}/weather?lat=${lat}&lon=${lon}`, { headers });
    if (!response.ok) throw new Error("Hava durumu alınamadı");
    return await response.json();
  } catch (error) {
    return {
      temp: 0,
      condition: 'Veri Yok',
      humidity: 0,
      wind: 0,
      location: 'Hata'
    };
  }
};

export const uploadImageForAnalysis = async (imageUri: string): Promise<AnalysisResult> => {
  const token = await getToken();
  const formData = new FormData();
  formData.append('file', {
    uri: imageUri,
    name: 'photo.jpg',
    type: 'image/jpeg',
  } as any);

  try {
    const response = await fetch(`${API_BASE_URL}/tools/analyze-plant`, {
      method: 'POST',
      headers: {
        'Authorization': `Bearer ${token}`,
      },
      body: formData,
    });

    if (!response.ok) {
      // Eğer backend henüz hazır değilse, demo sonuç dön
      if (response.status === 404 || response.status === 405) {
        console.log('Analiz endpoint henüz hazır değil, demo sonuç dönülüyor.');
        return {
          id: Date.now().toString(),
          imageUri,
          timestamp: new Date().toISOString(),
          diseaseName: "Sağlıklı Bitki",
          confidence: 0.98,
          recommendation: "Bitkiniz sağlıklı görünüyor. (Demo mod - Backend analiz servisi yapılandırılmamış)",
          status: 'healthy'
        };
      }
      throw new Error(`Analiz hatası: ${response.status}`);
    }

    return await response.json();
  } catch (error: any) {
    // Network hataları için graceful fallback
    if (error.message?.includes('Network') || error.message?.includes('fetch')) {
      return {
        id: Date.now().toString(),
        imageUri,
        timestamp: new Date().toISOString(),
        diseaseName: "Bağlantı Hatası",
        confidence: 0,
        recommendation: "Sunucuya bağlanılamadı. Lütfen internet bağlantınızı kontrol edin.",
        status: 'warning'
      };
    }
    throw error;
  }
};

// --- BİLDİRİM (PUSH TOKEN) ---
export const savePushToken = async (pushToken: string) => {
  const headers = await getAuthHeaders();
  try {
    const response = await fetch(`${API_BASE_URL}/auth/save-push-token`, {
      method: 'POST',
      headers,
      body: JSON.stringify({ token: pushToken }),
    });
    return await handleApiError(response, 'SavePushToken');
  } catch (error) {
    console.log("Token sunucuya kaydedilemedi:", error);
  }
};

// --- HARİTA SERVİSİ ---
export const getMapHtml = async (city: string) => {
  const response = await fetch(`${API_BASE_URL}/tools/generate-map`, {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json'
    },
    body: JSON.stringify({ city }),
  });

  if (!response.ok) {
    throw new Error("Harita oluşturulamadı.");
  }
  return await response.text();
};