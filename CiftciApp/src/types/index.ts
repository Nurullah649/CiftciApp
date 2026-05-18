export interface BkuMrlSampleRow {
  mrlUrunAdi?: string;
  mrlOrani?: string;
  durumu?: string;
  tarih?: string;
  aciklama?: string | null;
}

export interface BkuResolvedSubstance {
  detailId?: number;
  detailUrl?: string;
  matchedFromIngredients?: string[];
  matchedTokens?: string[];
  recordsFiltered?: number;
  sampleRows?: BkuMrlSampleRow[];
}

export interface BkuMrlEnrichment {
  enabled?: boolean;
  sourceHomepage?: string;
  resolvedSubstances?: BkuResolvedSubstance[];
  lookupFailures?: Array<{ phrase: string; normalizedPieces?: string[]; reason?: string }>;
  disclaimerTr?: string;
  infoTr?: string;
  errors?: string[] | null;
}

export interface ActiveIngredient {
  name: string;
  role?: string;
  notes?: string;
}

export interface AnalysisResult {
  id: string;
  imageUri: string;
  timestamp: string;
  diseaseName: string;
  confidence: number;
  recommendation: string;
  status: 'healthy' | 'warning' | 'critical';
  /** API'den (backend birleşik yanıt) */
  crop?: string;
  classKey?: string;
  activeIngredients?: ActiveIngredient[];
  disclaimer?: string;
  narrativeSummary?: string | null;
  modelLoaded?: boolean;
  bkuMrlEnrichment?: BkuMrlEnrichment;
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