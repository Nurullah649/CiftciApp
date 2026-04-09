import * as SecureStore from 'expo-secure-store';
import { manipulateAsync, SaveFormat } from 'expo-image-manipulator';
import { Platform } from 'react-native';
import { AnalysisResult, WeatherData, Task } from '../types';
import { getApiBaseUrl } from '../config/apiBaseUrl';

const API_BASE_URL = getApiBaseUrl();
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

const getAuthHeaders = async () => {
  const token = await getToken();
  return {
    'Content-Type': 'application/json',
    'Authorization': `Bearer ${token}`
  };
};

const handleApiError = async (response: Response, endpointName: string) => {
  if (!response.ok) {
    if (response.status === 401) {
      await removeToken();
      throw new Error('Oturum süresi doldu.');
    }
    const text = await response.text();
    let msg = `Sunucu hatası (${response.status})`;
    try {
      const json = JSON.parse(text);
      if (typeof json?.detail === 'string') msg = json.detail;
      else if (Array.isArray(json?.detail)) msg = json.detail.map((d: { msg?: string }) => d?.msg).filter(Boolean).join(' ') || msg;
    } catch {
      /* gövde JSON değil */
    }
    throw new Error(msg);
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

// --- PROFİL (Endpointler backend ile uyumlu hale getirildi: /me) ---
export const getUserProfile = async () => {
  const headers = await getAuthHeaders();
  const response = await fetch(`${API_BASE_URL}/auth/me`, { headers });
  return await handleApiError(response, 'GetProfile');
};

export const updateUserProfile = async (data: { firstName: string, lastName: string, location: string }) => {
  const headers = await getAuthHeaders();
  const response = await fetch(`${API_BASE_URL}/auth/me`, {
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

// --- GÖREV YÖNETİMİ ---
export const getTasks = async (): Promise<Task[]> => {
  const headers = await getAuthHeaders();
  try {
    const response = await fetch(`${API_BASE_URL}/tasks`, { headers });
    return await handleApiError(response, 'GetTasks');
  } catch (error) {
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

// --- SOHBET VE AI (Geliştirilmiş Streaming) ---
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
    const headers = {
      'Content-Type': 'application/json',
      'Authorization': `Bearer ${token}`
    };
    const response = await fetch(`${API_BASE_URL}/ask`, {
      method: 'POST',
      headers,
      body: JSON.stringify({ question, lat: lat || null, lon: lon || null })
    });
    if (!response.ok) throw new Error(`Hata: ${response.status}`);
    return await response.text();
  }

  return new Promise((resolve, reject) => {
    const xhr = new XMLHttpRequest();
    xhr.open('POST', `${API_BASE_URL}/ask`);
    xhr.setRequestHeader('Content-Type', 'application/json');
    xhr.setRequestHeader('Authorization', `Bearer ${token}`);

    // Sunucu hızı düşük olduğu için timeout süresini 10 dakika yapıyoruz
    xhr.timeout = 600000;

    xhr.onprogress = () => {
      // Sunucu 200 OK dönmeden progress başlamaz
      if (xhr.status === 200) {
        onProgress(xhr.responseText);
      }
    };

    xhr.onload = () => {
      if (xhr.status >= 200 && xhr.status < 300) {
        resolve(xhr.responseText);
      } else {
        // Sunucu bazen 200 OK dönmeden hata dönebilir (örn: 500, 401)
        try {
            const errorData = JSON.parse(xhr.responseText);
            reject(new Error(errorData.detail || `Hata: ${xhr.status}`));
        } catch {
            reject(new Error(`Sunucu hatası: ${xhr.status}`));
        }
      }
    };

    xhr.ontimeout = () => reject(new Error("Sunucu yanıt süresi doldu (Timeout)."));
    xhr.onerror = () => reject(new Error("Sunucuyla bağlantı kurulamadı."));

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
    return { temp: 0, condition: 'Veri Yok', humidity: 0, wind: 0, location: 'Hata' };
  }
};

export const uploadImageForAnalysis = async (imageUri: string): Promise<AnalysisResult> => {
  const token = await getToken();

  const buildErrorResult = (diseaseName: string, recommendation: string): AnalysisResult => ({
    id: Date.now().toString(),
    imageUri,
    timestamp: new Date().toISOString(),
    diseaseName,
    confidence: 0,
    recommendation,
    status: 'warning'
  });

  const prepareImageForUpload = async (sourceUri: string, aggressive = false) => {
    const resizeWidth = aggressive ? 1200 : 1600;
    const compress = aggressive ? 0.35 : 0.55;

    try {
      const manipulated = await manipulateAsync(
        sourceUri,
        [{ resize: { width: resizeWidth } }],
        {
          compress,
          format: SaveFormat.JPEG,
        }
      );
      return manipulated.uri;
    } catch {
      return sourceUri;
    }
  };

  const postAnalysisImage = async (uri: string) => {
    const formData = new FormData();
    formData.append('file', {
      uri,
      name: 'photo.jpg',
      type: 'image/jpeg',
    } as any);

    return fetch(`${API_BASE_URL}/tools/analyze-plant`, {
      method: 'POST',
      headers: { 'Authorization': `Bearer ${token}` },
      body: formData,
    });
  };

  try {
    let preparedUri = await prepareImageForUpload(imageUri);
    let response = await postAnalysisImage(preparedUri);

    if (response.status === 413) {
      preparedUri = await prepareImageForUpload(imageUri, true);
      response = await postAnalysisImage(preparedUri);
    }

    if (!response.ok) {
      let message = response.status === 413
        ? 'Fotoğraf boyutu çok büyük. Uygulama sıkıştırmayı denedi ama sunucu yine reddetti. Daha yakın ve daha küçük bir kare deneyin.'
        : `Analiz hatası (${response.status})`;
      try {
        const errorData = await response.json();
        if (typeof errorData?.detail === 'string') {
          message = errorData.detail;
        }
      } catch {
        /* sunucu JSON dönmemiş olabilir */
      }
      return buildErrorResult('Analiz Basarisiz', message);
    }

    const data = await response.json();
    return {
      ...data,
      imageUri: data?.imageUri || imageUri,
    };
  } catch (error) {
    const message = error instanceof Error ? error.message : 'Sunucuya bağlanılamadı.';
    return buildErrorResult('Baglanti Hatasi', message);
  }
};

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

export const getMapHtml = async (city: string) => {
  const response = await fetch(`${API_BASE_URL}/tools/generate-map`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ city }),
  });
  if (!response.ok) throw new Error("Harita oluşturulamadı.");
  return await response.text();
};
