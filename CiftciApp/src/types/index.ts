export interface AnalysisResult {
  id: string;
  imageUri: string;
  timestamp: string;
  diseaseName: string;
  confidence: number;
  recommendation: string;
  treatmentTitles?: string[];
  status: 'healthy' | 'warning' | 'critical';
}

export interface ChatMessage {
  id: string;
  text: string;
  sender: 'user' | 'ai';
}

export interface WeatherData {
  temp: number;
  condition: string;
  humidity: number;
  wind: number;
  location: string;
}

// YENİ: Görev Tipi
export interface Task {
  id: number;
  title: string;
  date_text: string;
  status: 'pending' | 'approved' | 'completed';
  created_at?: string;
}
