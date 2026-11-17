import { Pool } from 'pg';
import dns from 'dns';
import { Ticket, TicketStatus, TicketPriority, TicketCategory, KnowledgeArticle, DashboardStats } from './types';

declare global {
  // eslint-disable-next-line no-var
  var _pg_pool: Pool | undefined;
  // eslint-disable-next-line no-var
  var _pg_pool_promise: Promise<Pool> | undefined;
}

const rawDbUrl = process.env.DATABASE_URL || 'postgresql://postgres:postgres@localhost:5432/support_desk';

/**
 * Resolves a hostname via Google Public DNS (8.8.8.8) to handle environments
 * where the local router/ISP DNS refuses cloud subdomains.
 */
async function resolveHostIp(hostname: string): Promise<string> {
  if (hostname === 'localhost' || hostname === '127.0.0.1' || /^[\d.]+$/.test(hostname)) {
    return hostname;
  }
  return new Promise((resolve) => {
    try {
      const resolver = new dns.Resolver();
      resolver.setServers(['8.8.8.8', '1.1.1.1']);
      resolver.resolve4(hostname, (err, addrs) => {
        if (err || !addrs || addrs.length === 0) {
          resolve(hostname);
        } else {
          resolve(addrs[0]);
        }
      });
    } catch {
      resolve(hostname);
    }
  });
}

export async function getPgPool(): Promise<Pool> {
  if (globalThis._pg_pool) {
    return globalThis._pg_pool;
  }

  if (!globalThis._pg_pool_promise) {
    globalThis._pg_pool_promise = (async () => {
      try {
        const parsed = new URL(rawDbUrl);
        const hostname = parsed.hostname;
        const resolvedIp = await resolveHostIp(hostname);
        const port = parseInt(parsed.port || '5432', 10);
        const username = parsed.username;
        const password = decodeURIComponent(parsed.password || '');
        const database = parsed.pathname.replace(/^\//, '');
        const isSsl = rawDbUrl.includes('sslmode=') || !['localhost', '127.0.0.1'].includes(hostname);

        const pool = new Pool({
          host: resolvedIp,
          port,
          user: username,
          password,
          database,
          ssl: isSsl ? {
            rejectUnauthorized: false,
            servername: hostname // SNI header required by Neon/cloud proxies
          } : undefined,
          connectionTimeoutMillis: 5000,
          idleTimeoutMillis: 10000,
          max: 10
        });

        pool.on('error', (err) => {
          console.warn('PostgreSQL pool background error:', err.message);
        });

        globalThis._pg_pool = pool;
        return pool;
      } catch (err: any) {
        console.error('Failed to create PostgreSQL pool:', err.message);
        throw err;
      }
    })();
  }

  return globalThis._pg_pool_promise;
}

export async function isPostgresAvailable(): Promise<boolean> {
  try {
    const pool = await getPgPool();
    const res = await pool.query('SELECT 1;');
    return (res.rowCount ?? 0) > 0;
  } catch (err: any) {
    console.warn('PostgreSQL health check failed:', err.message);
    return false;
  }
}

export async function pgGetAllTickets(filters?: {
  status?: string;
  priority?: string;
  category?: string;
  search?: string;
}): Promise<Ticket[]> {
  const pool = await getPgPool();
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
  const pool = await getPgPool();
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
  const pool = await getPgPool();
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
  const pool = await getPgPool();
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

export async function pgDeleteTicket(id: number): Promise<boolean> {
  const pool = await getPgPool();
  const res = await pool.query('DELETE FROM tickets WHERE id = $1;', [id]);
  return (res.rowCount ?? 0) > 0;
}

export async function pgGetDashboardStats(): Promise<any> {
  const pool = await getPgPool();
  const totalRes = await pool.query('SELECT COUNT(*) as count FROM tickets');
  const openRes = await pool.query("SELECT COUNT(*) as count FROM tickets WHERE status = 'Open'");
  const inProgRes = await pool.query("SELECT COUNT(*) as count FROM tickets WHERE status = 'In Progress'");
  const resolvedRes = await pool.query("SELECT COUNT(*) as count FROM tickets WHERE status = 'Resolved'");
  const closedRes = await pool.query("SELECT COUNT(*) as count FROM tickets WHERE status = 'Closed'");
  const recentRes = await pool.query('SELECT * FROM tickets ORDER BY id DESC LIMIT 6');
  const priorityRes = await pool.query('SELECT priority, COUNT(*) as count FROM tickets GROUP BY priority');
  const categoryRes = await pool.query('SELECT category, COUNT(*) as count FROM tickets GROUP BY category');

  return {
    totalTickets: parseInt(totalRes.rows[0].count, 10),
    openTickets: parseInt(openRes.rows[0].count, 10),
    inProgressTickets: parseInt(inProgRes.rows[0].count, 10),
    resolvedTickets: parseInt(resolvedRes.rows[0].count, 10),
    closedTickets: parseInt(closedRes.rows[0].count, 10),
    recentTickets: recentRes.rows.map(mapPgTicketRow),
    priorityBreakdown: priorityRes.rows.map(r => ({ priority: r.priority, count: parseInt(r.count, 10) })),
    categoryBreakdown: categoryRes.rows.map(r => ({ category: r.category, count: parseInt(r.count, 10) }))
  };
}

export async function pgGetAllKBArticles(): Promise<KnowledgeArticle[]> {
  const pool = await getPgPool();
  const res = await pool.query('SELECT id, title, body as content, category, created_at FROM kb_articles ORDER BY id ASC;');
  return res.rows.map(r => ({
    id: r.id,
    title: r.title,
    category: r.category as TicketCategory,
    summary: r.content.slice(0, 150) + '...',
    content: r.content,
    tags: [],
    created_at: r.created_at ? new Date(r.created_at).toISOString() : new Date().toISOString()
  }));
}

export async function pgGetRelevantKBArticles(
  title: string,
  description: string,
  category?: string,
  limit: number = 3
): Promise<KnowledgeArticle[]> {
  const pool = await getPgPool();
  const query = `${title} ${description}`.trim();
  
  try {
    let sql = `
      SELECT id, title, body as content, category, created_at
      FROM kb_articles
      WHERE (title ILIKE $1 OR body ILIKE $1
    `;
    const params: any[] = [`%${query.split(' ')[0]}%`];
    
    if (category) {
      sql += ` OR category ILIKE $2) ORDER BY CASE WHEN category ILIKE $2 THEN 0 ELSE 1 END, id ASC LIMIT $3;`;
      params.push(`%${category}%`, limit);
    } else {
      sql += `) ORDER BY id ASC LIMIT $2;`;
      params.push(limit);
    }

    const res = await pool.query(sql, params);
    if (res.rows.length > 0) {
      return res.rows.map(r => ({
        id: r.id,
        title: r.title,
        category: r.category as TicketCategory,
        summary: r.content.slice(0, 150) + '...',
        content: r.content,
        tags: [],
        created_at: r.created_at ? new Date(r.created_at).toISOString() : new Date().toISOString()
      }));
    }
  } catch (err) {
    console.warn('Postgres KB search fallback to basic query:', err);
  }

  // Fallback to top KB articles
  const fallbackRes = await pool.query('SELECT id, title, body as content, category, created_at FROM kb_articles ORDER BY id ASC LIMIT $1;', [limit]);
  return fallbackRes.rows.map(r => ({
    id: r.id,
    title: r.title,
    category: r.category as TicketCategory,
    summary: r.content.slice(0, 150) + '...',
    content: r.content,
    tags: [],
    created_at: r.created_at ? new Date(r.created_at).toISOString() : new Date().toISOString()
  }));
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
