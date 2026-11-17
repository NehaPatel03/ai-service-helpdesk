import { Pool } from 'pg';
import { Ticket, TicketStatus, TicketPriority, TicketCategory, KnowledgeArticle, DashboardStats } from './types';

declare global {
  // eslint-disable-next-line no-var
  var _pg_pool: Pool | undefined;
}

const pgUrl = process.env.DATABASE_URL || 'postgresql://postgres:postgres@localhost:5432/support_desk';

export function getPgPool(): Pool {
  if (!globalThis._pg_pool) {
    globalThis._pg_pool = new Pool({
      connectionString: pgUrl,
      connectionTimeoutMillis: 3000,
      idleTimeoutMillis: 10000,
      max: 10
    });

    globalThis._pg_pool.on('error', (err) => {
      console.warn('PostgreSQL client pool idle error:', err.message);
    });
  }
  return globalThis._pg_pool;
}

export async function isPostgresAvailable(): Promise<boolean> {
  try {
    const pool = getPgPool();
    const res = await pool.query('SELECT 1;');
    return (res.rowCount ?? 0) > 0;
  } catch {
    return false;
  }
}

export async function pgGetAllTickets(filters?: {
  status?: string;
  priority?: string;
  category?: string;
  search?: string;
}): Promise<Ticket[]> {
  const pool = getPgPool();
  let query = 'SELECT * FROM tickets WHERE 1=1';
  const values: any[] = [];
  let paramIdx = 1;

  if (filters?.status && filters.status !== 'All') {
    query += ` AND status = $${paramIdx++}`;
    values.push(filters.status);
  }
  if (filters?.priority && filters.priority !== 'All') {
    query += ` AND priority = $${paramIdx++}`;
    values.push(filters.priority);
  }
  if (filters?.category && filters.category !== 'All') {
    query += ` AND category = $${paramIdx++}`;
    values.push(filters.category);
  }
  if (filters?.search) {
    query += ` AND (title ILIKE $${paramIdx} OR description ILIKE $${paramIdx})`;
    values.push(`%${filters.search}%`);
    paramIdx++;
  }

  query += ' ORDER BY id DESC;';
  const res = await pool.query(query, values);
  return res.rows.map(mapPgTicketRow);
}

export async function pgGetTicketById(id: number): Promise<Ticket | null> {
  const pool = getPgPool();
  const res = await pool.query('SELECT * FROM tickets WHERE id = $1;', [id]);
  if (res.rows.length === 0) return null;
  return mapPgTicketRow(res.rows[0]);
}

export async function pgCreateTicket(data: {
  title: string;
  description: string;
  priority?: TicketPriority;
  category?: TicketCategory;
}): Promise<Ticket> {
  const pool = getPgPool();
  const priority = data.priority || 'Medium';
  const category = data.category || 'Other';

  const res = await pool.query(`
    INSERT INTO tickets (title, description, priority, category, status, source)
    VALUES ($1, $2, $3, $4, 'Open', 'manual')
    RETURNING *;
  `, [data.title, data.description, priority, category]);

  return mapPgTicketRow(res.rows[0]);
}

export async function pgUpdateTicket(
  id: number,
  fields: Partial<Ticket>
): Promise<Ticket | null> {
  const pool = getPgPool();
  const setClauses: string[] = [];
  const values: any[] = [];
  let paramIdx = 1;

  const allowedCols: (keyof Ticket)[] = [
    'title', 'description', 'priority', 'category', 'status',
    'resolution', 'ai_summary', 'ai_cause', 'ai_solution',
    'ai_suggested_category', 'ai_suggested_priority'
  ];

  for (const col of allowedCols) {
    if (fields[col] !== undefined) {
      setClauses.push(`${col} = $${paramIdx++}`);
      values.push(fields[col]);
    }
  }

  if (setClauses.length === 0) {
    return pgGetTicketById(id);
  }

  setClauses.push('updated_at = CURRENT_TIMESTAMP');
  values.push(id);

  const query = `
    UPDATE tickets
    SET ${setClauses.join(', ')}
    WHERE id = $${paramIdx}
    RETURNING *;
  `;

  const res = await pool.query(query, values);
  if (res.rows.length === 0) return null;
  return mapPgTicketRow(res.rows[0]);
}

function mapPgTicketRow(row: any): Ticket {
  return {
    id: row.id,
    title: row.title,
    description: row.description,
    priority: row.priority as TicketPriority,
    category: row.category as TicketCategory,
    status: row.status as TicketStatus,
    resolution: row.resolution,
    ai_summary: row.ai_summary,
    ai_cause: row.ai_cause,
    ai_solution: row.ai_solution,
    ai_suggested_category: row.ai_suggested_category,
    ai_suggested_priority: row.ai_suggested_priority,
    source: row.source,
    external_id: row.external_id,
    created_at: row.created_at ? new Date(row.created_at).toISOString() : new Date().toISOString(),
    updated_at: row.updated_at ? new Date(row.updated_at).toISOString() : new Date().toISOString()
  };
}
