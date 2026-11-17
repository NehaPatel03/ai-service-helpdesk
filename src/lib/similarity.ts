import crypto from 'crypto';
import { GoogleGenAI } from '@google/genai';
import { Ticket, SimilarIncident } from './types';
import { 
  getTicketById, 
  getAllTickets, 
  getTicketEmbedding, 
  saveTicketEmbedding 
} from './db';
import { isPostgresAvailable, pgGetTicketById, pgGetAllTickets } from './postgres';

// Vector dimension for mathematical TF-IDF semantic projection
const VECTOR_DIM = 128;

/**
 * Computes a hash of the ticket text to detect modifications
 */
export function computeTicketContentHash(title: string, description: string, category: string): string {
  const text = `${title.trim()}|||${category.trim()}|||${description.trim()}`;
  return crypto.createHash('sha256').update(text).digest('hex');
}

/**
 * Tokenizes text into normalized words and bigrams
 */
function tokenize(text: string): string[] {
  const clean = text
    .toLowerCase()
    .replace(/[^a-z0-9\s-]/g, ' ')
    .replace(/\s+/g, ' ')
    .trim();

  const words = clean.split(' ').filter(w => w.length > 2);
  const tokens = [...words];

  // Add bigrams for contextual awareness (e.g. 'vpn connection', 'password reset')
  for (let i = 0; i < words.length - 1; i++) {
    tokens.push(`${words[i]}_${words[i + 1]}`);
  }

  return tokens;
}

/**
 * Creates a deterministic high-dimensional TF-IDF feature vector
 */
function createDeterministicSemanticVector(text: string): number[] {
  const tokens = tokenize(text);
  const vector = new Array(VECTOR_DIM).fill(0);

  if (tokens.length === 0) return vector;

  // Domain-specific keyword boosts for IT Service Desk terminology
  const domainWeights: Record<string, number> = {
    vpn: 4.0,
    gateway: 3.5,
    anyconnect: 4.0,
    globalprotect: 4.0,
    timeout: 3.0,
    password: 3.5,
    auth: 3.5,
    authentication: 3.5,
    mfa: 4.0,
    token: 3.0,
    outlook: 4.0,
    email: 3.5,
    exchange: 3.5,
    database: 4.0,
    rds: 4.0,
    postgres: 4.0,
    mysql: 4.0,
    pool: 3.5,
    connections: 3.5,
    printer: 4.0,
    spooler: 4.0,
    zebra: 3.5,
    docker: 4.0,
    wsl: 4.0,
    memory: 3.0,
    leak: 3.5,
    freeze: 3.0,
    permission: 3.5,
    s3: 4.0,
    iam: 4.0,
    forbidden: 3.5,
    saml: 4.0,
    okta: 4.0,
    sso: 3.5,
    wifi: 3.5,
    network: 3.0
  };

  for (const token of tokens) {
    let hash = 0;
    for (let i = 0; i < token.length; i++) {
      hash = (hash << 5) - hash + token.charCodeAt(i);
      hash |= 0;
    }
    const idx = Math.abs(hash) % VECTOR_DIM;
    const baseWeight = domainWeights[token] || 1.0;
    vector[idx] += baseWeight;
  }

  // L2 normalize vector
  let norm = 0;
  for (let i = 0; i < VECTOR_DIM; i++) {
    norm += vector[i] * vector[i];
  }
  norm = Math.sqrt(norm);

  if (norm > 0) {
    for (let i = 0; i < VECTOR_DIM; i++) {
      vector[i] = vector[i] / norm;
    }
  }

  return vector;
}

/**
 * Computes cosine similarity between two numeric vectors (returns 0.0 to 1.0)
 */
export function computeCosineSimilarity(vecA: number[], vecB: number[]): number {
  if (!vecA || !vecB || vecA.length !== vecB.length || vecA.length === 0) {
    return 0;
  }

  let dotProduct = 0;
  let normA = 0;
  let normB = 0;

  for (let i = 0; i < vecA.length; i++) {
    dotProduct += vecA[i] * vecB[i];
    normA += vecA[i] * vecA[i];
    normB += vecB[i] * vecB[i];
  }

  const denominator = Math.sqrt(normA) * Math.sqrt(normB);
  if (denominator === 0) return 0;

  const score = dotProduct / denominator;
  return Math.max(0, Math.min(1, score));
}

/**
 * Generates an embedding for a ticket and caches it in SQLite
 */
export async function generateAndSaveEmbedding(ticket: Ticket): Promise<number[]> {
  const contentHash = computeTicketContentHash(ticket.title, ticket.description, ticket.category);
  const cached = getTicketEmbedding(ticket.id);

  if (cached && cached.contentHash === contentHash && cached.embedding.length > 0) {
    return cached.embedding;
  }

  const textToEmbed = `Title: ${ticket.title}. Category: ${ticket.category}. Description: ${ticket.description}`;
  const apiKey = process.env.GEMINI_API_KEY || process.env.GOOGLE_API_KEY;

  if (apiKey) {
    try {
      const ai = new GoogleGenAI({ apiKey });
      const response = await ai.models.embedContent({
        model: 'text-embedding-004',
        contents: textToEmbed,
      });

      const values = (response as any)?.embedding?.values;
      if (Array.isArray(values) && values.length > 0) {
        try {
          saveTicketEmbedding(ticket.id, values, contentHash);
        } catch {
          // Ignore foreign key failures on legacy SQLite cache for PostgreSQL tickets
        }
        return values;
      }
    } catch (err: any) {
      console.warn('Google GenAI embedding failed, using high-precision fallback vectorizer:', err?.message || err);
    }
  }

  // Fallback to high-precision semantic feature vector
  const fallbackVector = createDeterministicSemanticVector(textToEmbed);
  try {
    saveTicketEmbedding(ticket.id, fallbackVector, contentHash);
  } catch {
    // Ignore foreign key failures on legacy SQLite cache for PostgreSQL tickets
  }
  return fallbackVector;
}

/**
 * Identifies the top similar incidents for a given ticket
 */
export async function findSimilarIncidents(
  ticketId: number, 
  limit: number = 4, 
  threshold: number = 0.25
): Promise<SimilarIncident[]> {
  const usePg = await isPostgresAvailable();
  const currentTicket = usePg ? await pgGetTicketById(ticketId) : getTicketById(ticketId);
  if (!currentTicket) {
    return [];
  }

  const currentEmbedding = await generateAndSaveEmbedding(currentTicket);
  const allTickets = usePg ? await pgGetAllTickets() : getAllTickets();

  const otherTickets = allTickets.filter(t => t.id !== ticketId);
  const scoredList: SimilarIncident[] = [];

  for (const other of otherTickets) {
    const otherEmbedding = await generateAndSaveEmbedding(other);

    // Compute similarity
    let score = computeCosineSimilarity(currentEmbedding, otherEmbedding);

    // Boost score if categories match exactly
    if (other.category === currentTicket.category) {
      score = Math.min(1.0, score + 0.08);
    }

    // Convert to percentage (0 - 100)
    const percentage = Math.round(score * 100);

    if (score >= threshold) {
      scoredList.push({
        id: other.id,
        title: other.title,
        category: other.category,
        priority: other.priority,
        status: other.status,
        similarityScore: percentage,
        hasResolution: Boolean(other.resolution && other.resolution.trim().length > 0),
        resolution: other.resolution || null,
        created_at: other.created_at
      });
    }
  }

  // Sort descending by similarity score
  scoredList.sort((a, b) => b.similarityScore - a.similarityScore);

  return scoredList.slice(0, limit);
}
