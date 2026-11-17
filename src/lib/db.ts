import Database from 'better-sqlite3';
import path from 'path';
import fs from 'fs';
import { Ticket, KnowledgeArticle, TicketPriority, TicketCategory, TicketStatus, TicketChatMessage } from './types';

declare global {
  // eslint-disable-next-line no-var
  var _sqlite_db: Database.Database | undefined;
}

function getDatabase(): Database.Database {
  if (globalThis._sqlite_db) {
    return globalThis._sqlite_db;
  }

  const dbDir = path.join(process.cwd(), 'data');
  if (!fs.existsSync(dbDir)) {
    fs.mkdirSync(dbDir, { recursive: true });
  }

  const dbPath = path.join(dbDir, 'support_desk.db');
  
  // Set 15s timeout to prevent lock contention across workers
  const db = new Database(dbPath, { timeout: 15000 });
  db.pragma('journal_mode = WAL');
  db.pragma('busy_timeout = 15000');

  // Initialize schema if not exists
  db.exec(`
    CREATE TABLE IF NOT EXISTS tickets (
      id INTEGER PRIMARY KEY AUTOINCREMENT,
      title TEXT NOT NULL,
      description TEXT NOT NULL,
      priority TEXT NOT NULL DEFAULT 'Medium',
      category TEXT NOT NULL DEFAULT 'Other',
      status TEXT NOT NULL DEFAULT 'Open',
      resolution TEXT,
      ai_summary TEXT,
      ai_cause TEXT,
      ai_solution TEXT,
      ai_suggested_category TEXT,
      ai_suggested_priority TEXT,
      source TEXT DEFAULT 'manual',
      external_id TEXT,
      created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
      updated_at DATETIME DEFAULT CURRENT_TIMESTAMP
    );

    CREATE TABLE IF NOT EXISTS knowledge_base (
      id INTEGER PRIMARY KEY AUTOINCREMENT,
      title TEXT NOT NULL,
      category TEXT NOT NULL,
      summary TEXT NOT NULL,
      content TEXT NOT NULL,
      tags TEXT NOT NULL,
      created_at DATETIME DEFAULT CURRENT_TIMESTAMP
    );

    CREATE TABLE IF NOT EXISTS ticket_embeddings (
      ticket_id INTEGER PRIMARY KEY,
      embedding_json TEXT NOT NULL,
      content_hash TEXT NOT NULL,
      updated_at DATETIME DEFAULT CURRENT_TIMESTAMP,
      FOREIGN KEY (ticket_id) REFERENCES tickets(id) ON DELETE CASCADE
    );

    CREATE TABLE IF NOT EXISTS ticket_messages (
      id INTEGER PRIMARY KEY AUTOINCREMENT,
      ticket_id INTEGER NOT NULL,
      sender TEXT NOT NULL,
      message TEXT NOT NULL,
      is_fallback BOOLEAN DEFAULT 0,
      created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
      FOREIGN KEY (ticket_id) REFERENCES tickets(id) ON DELETE CASCADE
    );

    CREATE INDEX IF NOT EXISTS idx_ticket_messages_ticket ON ticket_messages(ticket_id);
  `);

  // Safe incremental migrations for existing databases
  try {
    const tableInfo = db.prepare("PRAGMA table_info(tickets)").all() as Array<{ name: string }>;
    const columnNames = tableInfo.map(col => col.name);
    if (!columnNames.includes('source')) {
      db.exec("ALTER TABLE tickets ADD COLUMN source TEXT DEFAULT 'manual'");
    }
    if (!columnNames.includes('external_id')) {
      db.exec("ALTER TABLE tickets ADD COLUMN external_id TEXT");
      db.exec("CREATE INDEX IF NOT EXISTS idx_tickets_external_id ON tickets(external_id)");
    }
  } catch (migErr) {
    console.error('Migration warning (tickets columns):', migErr);
  }

  seedInitialData(db);

  globalThis._sqlite_db = db;
  return db;
}

// Seed initial support data if empty
function seedInitialData(db: Database.Database) {
  try {
    const kbCount = db.prepare('SELECT COUNT(*) as count FROM knowledge_base').get() as { count: number };
    
    if (kbCount.count === 0) {
      const insertKB = db.prepare(`
        INSERT INTO knowledge_base (title, category, summary, content, tags)
        VALUES (?, ?, ?, ?, ?)
      `);

      const initialArticles = [
        {
          title: 'GlobalProtect / AnyConnect VPN Connection Timeout & Auth Failures',
          category: 'Network',
          summary: 'Resolve corporate VPN gateway timeouts, certificate mismatches, and MFA push notification failures.',
          content: `### Troubleshooting Corporate VPN Issues 🌐
1. **Verify Internet & DNS**: Ensure local internet is reachable (ping 8.8.8.8). Flush local DNS cache using \`ipconfig /flushdns\`.
2. **Clear VPN Credentials**: Open VPN Client settings -> Preferences -> Clear Saved Credentials.
3. **MFA Session Sync**: Open your Authenticator app, check for stale push notifications or enter the 6-digit TOTP code manually.
4. **Gateway Switch**: Switch server gateway to the regional secondary gateway (e.g., vpn-east.corp.com or vpn-west.corp.com).
5. **Driver Reset**: In Device Manager -> Network Adapters, right-click the virtual VPN adapter (TAP/TUN) and select 'Disable', then 'Enable'.`,
          tags: JSON.stringify(['vpn', 'network', 'timeout', 'mfa', 'connection', 'globalprotect', 'anyconnect'])
        },
        {
          title: 'Outlook 365 Constant Password Loop & Modern Auth Glitch',
          category: 'Email & Communication',
          summary: 'Fix Microsoft Outlook continuously prompting for password or stuck in a login loop due to stale Windows Credential Manager tokens.',
          content: `### Resolving Outlook Password Prompts ✉️
1. **Close Outlook & Office Apps**: Terminate Outlook and Teams completely.
2. **Clear Windows Credentials**:
   - Open Start -> Search **Credential Manager** -> **Windows Credentials**.
   - Under 'Generic Credentials', locate all entries starting with \`MicrosoftOffice16\`, \`MS.Outlook\`, or \`ADAL\`.
   - Click 'Remove' on each of these cached tokens.
3. **Re-authenticate Modern Auth**:
   - Reopen Outlook. Enter company SSO credentials and approve MFA push.
4. **Delete Identity Cache Registry (if needed)**:
   - Clear cache key in \`HKEY_CURRENT_USER\\Software\\Microsoft\\Office\\16.0\\Common\\Identity\`.`,
          tags: JSON.stringify(['outlook', 'email', 'password', 'sso', 'mfa', 'office365', 'credentials'])
        },
        {
          title: 'Database Connection Pool Exhaustion (500 Internal Server Error)',
          category: 'Cloud & Infrastructure',
          summary: 'Diagnose and remediate connection pool exhaustion, locked queries, and max_connections limits in PostgreSQL/MySQL.',
          content: `### Resolving Database Pool Exhaustion 🗄️
1. **Inspect Active Connections**:
   - PostgreSQL: \`SELECT count(*), state FROM pg_stat_activity GROUP BY state;\`
   - MySQL: \`SHOW PROCESSLIST;\`
2. **Identify Long-Running or Locked Queries**:
   - PostgreSQL: \`SELECT pid, now() - pg_stat_activity.query_start AS duration, query, state FROM pg_stat_activity WHERE state != 'idle' ORDER BY 2 DESC LIMIT 10;\`
3. **Terminate Zombie Connections**:
   - Terminate offending PID: \`SELECT pg_terminate_backend(PID);\`
4. **Adjust Pool Configuration**:
   - Verify connection pool max limits in backend configuration (\`pool_size\`, \`max_overflow\`).
   - Implement connection pooling proxy (PgBouncer or ProxySQL).`,
          tags: JSON.stringify(['database', 'postgres', 'mysql', '500-error', 'connection-pool', 'timeout', 'infrastructure'])
        },
        {
          title: 'Office Network Printer Showing Offline on Windows & macOS',
          category: 'Hardware',
          summary: 'Step-by-step guide to bring networked office printers back online, clear print spooler queues, and reset IP mappings.',
          content: `### Network Printer Offline Troubleshooting 🖨️
1. **Verify Physical Device & IP**:
   - Confirm printer LCD is awake and connected to the corporate WiFi/Ethernet subnet.
   - Ping printer IP address from terminal: \`ping 192.168.1.150\`.
2. **Restart Print Spooler (Windows)**:
   - Open PowerShell as Admin and run:
     \`net stop spooler\`
     \`Remove-Item -Path "C:\\Windows\\System32\\spool\\PRINTERS\\*" -Force\`
     \`net start spooler\`
3. **Disable SNMP Status on Port**:
   - Printer Properties -> Ports -> Configure Port -> Uncheck **SNMP Status Enabled**.
4. **Mac OS Reset**:
   - System Settings -> Printers & Scanners -> Right-click printer list -> 'Reset Printing System'.`,
          tags: JSON.stringify(['printer', 'hardware', 'offline', 'spooler', 'paper', 'network'])
        },
        {
          title: '403 Forbidden / AWS IAM S3 Access Denied Remediation',
          category: 'Access & Security',
          summary: 'Troubleshoot AWS S3 403 Forbidden errors, IAM bucket policy restrictions, and KMS encryption key permissions.',
          content: `### AWS S3 403 Forbidden Fix 🔒
1. **Check IAM Policy Permissions**:
   - Ensure the requesting IAM Role/User has \`s3:GetObject\`, \`s3:PutObject\`, and \`s3:ListBucket\` permissions for \`arn:aws:s3:::bucket-name/*\`.
2. **Review Bucket Policy & Block Public Access**:
   - Check if explicit Deny exists in the S3 Bucket Policy for IP ranges or VPC endpoints.
3. **Verify KMS Key Decryption Permissions**:
   - If the bucket uses AWS KMS (SSE-KMS), the user's role must also have \`kms:Decrypt\` on the specific KMS Key ARN.
4. **Check Object ACL vs Bucket Ownership**:
   - Ensure Object Ownership is set to **Bucket Owner Enforced** to prevent unreadable cross-account objects.`,
          tags: JSON.stringify(['aws', 's3', '403-forbidden', 'access', 'security', 'iam', 'cloud', 'permissions'])
        },
        {
          title: 'High CPU & Memory Usage by Docker Desktop / WSL2',
          category: 'Software',
          summary: 'Resolve Docker Desktop runaway resource consumption and limit Vmmem memory consumption on Windows/Mac.',
          content: `### Taming Docker & WSL2 Memory Usage 💻
1. **Configure WSL2 Memory Limit (.wslconfig)**:
   - Create or edit \`C:\\Users\\<YourUser>\\.wslconfig\`:
     \`\`\`ini
     [wsl2]
     memory=6GB
     processors=4
     swap=2GB
     \`\`\`
2. **Restart WSL2**:
   - Run in PowerShell: \`wsl --shutdown\`
3. **Prune Stale Docker Objects**:
   - Run: \`docker system prune -a --volumes\`
4. **Limit Container Resource Constraints**:
   - Add \`mem_limit: 1g\` and \`cpus: 1.0\` to \`docker-compose.yml\` services.`,
          tags: JSON.stringify(['docker', 'wsl2', 'memory', 'cpu', 'software', 'performance', 'slow'])
        }
      ];

      for (const article of initialArticles) {
        insertKB.run(article.title, article.category, article.summary, article.content, article.tags);
      }
    }

    const ticketCount = db.prepare('SELECT COUNT(*) as count FROM tickets').get() as { count: number };
    
    if (ticketCount.count === 0) {
      const insertTicket = db.prepare(`
        INSERT INTO tickets (title, description, priority, category, status, resolution, ai_summary, ai_cause, ai_solution, created_at)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, datetime('now', ?))
      `);

      const initialTickets = [
        {
          title: 'Cannot connect to GlobalProtect VPN after returning from PTO',
          description: 'I came back from vacation today and when I try to log into the corporate VPN using GlobalProtect, it sits on "Connecting" for 2 minutes and then fails with "Gateway timeout / Authentication error". My WiFi is working fine for other websites.',
          priority: 'High',
          category: 'Network',
          status: 'Open',
          resolution: null,
          ai_summary: 'User experiencing connection timeout and auth failure on GlobalProtect VPN after absence.',
          ai_cause: 'Expired VPN cached credentials or unsynchronized MFA session token after returning from PTO.',
          ai_solution: '1. Clear saved credentials in GlobalProtect settings.\n2. Open Microsoft Authenticator to re-sync MFA.\n3. Switch to secondary VPN gateway if timeout persists.',
          timeOffset: '-2 hours'
        },
        {
          title: 'Outlook keeps repeatedly prompting for password every 10 minutes',
          description: 'Ever since I changed my Windows domain password yesterday, Microsoft Outlook keeps popping up a login box asking for password. Even when I type the new password and check "Remember my credentials", the popup comes back shortly.',
          priority: 'Medium',
          category: 'Email & Communication',
          status: 'Open',
          resolution: null,
          ai_summary: 'Outlook in a continuous password prompt loop following domain password change.',
          ai_cause: 'Stale cached credentials in Windows Credential Manager conflicting with Modern Authentication tokens.',
          ai_solution: '1. Close Outlook.\n2. Open Windows Credential Manager -> Windows Credentials.\n3. Delete cached MicrosoftOffice16 credentials.\n4. Reopen Outlook and authenticate once with MFA.',
          timeOffset: '-5 hours'
        },
        {
          title: 'Production API returning 500 Internal Server Error - DB connection timeout',
          description: 'Our backend microservices are throwing HTTP 500 errors on the checkout route. Error logs state: "Connection pool exhausted, could not acquire connection from pool within 30000ms". Postgres CPU is at 98%.',
          priority: 'Urgent',
          category: 'Cloud & Infrastructure',
          status: 'In Progress',
          resolution: null,
          ai_summary: 'Critical checkout API outage due to database connection pool exhaustion and 98% DB CPU spike.',
          ai_cause: 'Unindexed slow query locking table or runaway backend workers not releasing connections back to the pool.',
          ai_solution: '1. Query pg_stat_activity to inspect and terminate stuck locks.\n2. Restart backend connection poolers.\n3. Implement rate limiting and verify PgBouncer configuration.',
          timeOffset: '-1 day'
        },
        {
          title: 'Marketing 2nd floor printer appears offline for all Mac laptops',
          description: 'No one on the marketing team using macOS can print to the 2nd floor HP LaserJet. Print jobs stay queued indefinitely and the printer status says "Printer is offline". Windows users report being able to print.',
          priority: 'Low',
          category: 'Hardware',
          status: 'Open',
          resolution: null,
          ai_summary: 'Mac users unable to print to 2nd floor HP printer while Windows users have connectivity.',
          ai_cause: 'AirPrint / Bonjour protocol discovery cache issue or incorrect IP queue configuration on macOS clients.',
          ai_solution: '1. Reset Printing System in macOS System Settings.\n2. Re-add printer directly via IP using LPD/IPP protocol instead of AirPrint.',
          timeOffset: '-2 days'
        },
        {
          title: 'Unable to export client analytics reports to S3 bucket - 403 Forbidden',
          description: 'When running the nightly export script to s3://digiplus-client-reports/2026/, the script terminates with An error occurred (AccessDenied) when calling the PutObject operation.',
          priority: 'High',
          category: 'Access & Security',
          status: 'Resolved',
          resolution: 'Updated the IAM role policy attached to the export worker instance to include s3:PutObject permissions on the target bucket ARN and added KMS key decrypt permissions.',
          ai_summary: 'Nightly analytics export script failing with AWS S3 AccessDenied (403 Forbidden).',
          ai_cause: 'IAM role attached to export worker missing PutObject or KMS decrypt policy for new bucket.',
          ai_solution: 'Attach updated IAM policy allowing s3:PutObject and kms:GenerateDataKey on the reports bucket.',
          timeOffset: '-3 days'
        }
      ];

      for (const ticket of initialTickets) {
        insertTicket.run(
          ticket.title,
          ticket.description,
          ticket.priority,
          ticket.category,
          ticket.status,
          ticket.resolution,
          ticket.ai_summary,
          ticket.ai_cause,
          ticket.ai_solution,
          ticket.timeOffset
        );
      }
    }
  } catch (err) {
    console.error('Seed data error (skipped if already initialized):', err);
  }
}

// Ticket queries
export function getAllTickets(filters?: { status?: string; priority?: string; category?: string; search?: string }): Ticket[] {
  const db = getDatabase();
  let query = 'SELECT * FROM tickets WHERE 1=1';
  const params: any[] = [];

  if (filters?.status && filters.status !== 'All') {
    query += ' AND status = ?';
    params.push(filters.status);
  }
  if (filters?.priority && filters.priority !== 'All') {
    query += ' AND priority = ?';
    params.push(filters.priority);
  }
  if (filters?.category && filters.category !== 'All') {
    query += ' AND category = ?';
    params.push(filters.category);
  }
  if (filters?.search && filters.search.trim()) {
    query += ' AND (title LIKE ? OR description LIKE ? OR id LIKE ?)';
    const term = `%${filters.search.trim()}%`;
    params.push(term, term, term);
  }

  query += ' ORDER BY created_at DESC';
  return db.prepare(query).all(...params) as Ticket[];
}

export function getTicketById(id: number): Ticket | null {
  const db = getDatabase();
  const ticket = db.prepare('SELECT * FROM tickets WHERE id = ?').get(id) as Ticket | undefined;
  return ticket || null;
}

export function getTicketByExternalId(externalId: string): Ticket | null {
  const db = getDatabase();
  const ticket = db.prepare('SELECT * FROM tickets WHERE external_id = ?').get(externalId) as Ticket | undefined;
  return ticket || null;
}

export function createTicket(data: {
  title: string;
  description: string;
  priority?: TicketPriority;
  category?: TicketCategory;
  status?: TicketStatus;
  resolution?: string | null;
  source?: string;
  external_id?: string | null;
  created_at?: string;
}): Ticket {
  const db = getDatabase();
  const stmt = db.prepare(`
    INSERT INTO tickets (title, description, priority, category, status, resolution, source, external_id, created_at)
    VALUES (?, ?, ?, ?, ?, ?, ?, ?, COALESCE(?, CURRENT_TIMESTAMP))
  `);
  const info = stmt.run(
    data.title,
    data.description,
    data.priority || 'Medium',
    data.category || 'Other',
    data.status || 'Open',
    data.resolution || null,
    data.source || 'manual',
    data.external_id || null,
    data.created_at || null
  );
  return getTicketById(Number(info.lastInsertRowid))!;
}

export function updateTicket(
  id: number,
  updates: Partial<{
    title: string;
    description: string;
    priority: TicketPriority;
    category: TicketCategory;
    status: TicketStatus;
    resolution: string | null;
    ai_summary: string | null;
    ai_cause: string | null;
    ai_solution: string | null;
    ai_suggested_category: string | null;
    ai_suggested_priority: string | null;
    source: string;
    external_id: string | null;
  }>
): Ticket | null {
  const db = getDatabase();
  const allowedFields = [
    'title',
    'description',
    'priority',
    'category',
    'status',
    'resolution',
    'ai_summary',
    'ai_cause',
    'ai_solution',
    'ai_suggested_category',
    'ai_suggested_priority',
    'source',
    'external_id'
  ];

  const setClauses: string[] = [];
  const params: any[] = [];

  for (const [key, value] of Object.entries(updates)) {
    if (allowedFields.includes(key) && value !== undefined) {
      setClauses.push(`${key} = ?`);
      params.push(value);
    }
  }

  if (setClauses.length === 0) {
    return getTicketById(id);
  }

  setClauses.push("updated_at = CURRENT_TIMESTAMP");
  params.push(id);

  const query = `UPDATE tickets SET ${setClauses.join(', ')} WHERE id = ?`;
  db.prepare(query).run(...params);

  return getTicketById(id);
}

export function deleteTicket(id: number): boolean {
  const db = getDatabase();
  const info = db.prepare('DELETE FROM tickets WHERE id = ?').run(id);
  return info.changes > 0;
}

// Knowledge Base queries
export function getAllKBArticles(search?: string, category?: string): KnowledgeArticle[] {
  const db = getDatabase();
  let query = 'SELECT * FROM knowledge_base WHERE 1=1';
  const params: any[] = [];

  if (category && category !== 'All') {
    query += ' AND category = ?';
    params.push(category);
  }

  if (search && search.trim()) {
    query += ' AND (title LIKE ? OR summary LIKE ? OR content LIKE ? OR tags LIKE ?)';
    const term = `%${search.trim()}%`;
    params.push(term, term, term, term);
  }

  query += ' ORDER BY id ASC';
  const rows = db.prepare(query).all(...params) as any[];
  
  return rows.map(row => ({
    ...row,
    tags: JSON.parse(row.tags || '[]')
  }));
}

export function getKBArticleById(id: number): KnowledgeArticle | null {
  const db = getDatabase();
  const row = db.prepare('SELECT * FROM knowledge_base WHERE id = ?').get(id) as any;
  if (!row) return null;
  return {
    ...row,
    tags: JSON.parse(row.tags || '[]')
  };
}

export function findRelevantKBArticles(ticketTitle: string, ticketDesc: string, ticketCategory?: string): KnowledgeArticle[] {
  const allArticles = getAllKBArticles();
  const textToSearch = `${ticketTitle} ${ticketDesc} ${ticketCategory || ''}`.toLowerCase();
  
  const scored = allArticles.map(article => {
    let score = 0;
    
    if (ticketCategory && article.category.toLowerCase() === ticketCategory.toLowerCase()) {
      score += 3;
    }
    
    for (const tag of article.tags) {
      if (textToSearch.includes(tag.toLowerCase())) {
        score += 4;
      }
    }
    
    const titleWords = article.title.toLowerCase().split(/\s+/);
    for (const word of titleWords) {
      if (word.length > 3 && textToSearch.includes(word)) {
        score += 2;
      }
    }

    return { article, score };
  });

  return scored
    .filter(item => item.score > 0)
    .sort((a, b) => b.score - a.score)
    .slice(0, 3)
    .map(item => item.article);
}

// Dashboard statistics
export function getDashboardStats() {
  const db = getDatabase();
  const totalTickets = (db.prepare('SELECT COUNT(*) as count FROM tickets').get() as any).count;
  const openTickets = (db.prepare("SELECT COUNT(*) as count FROM tickets WHERE status = 'Open'").get() as any).count;
  const inProgressTickets = (db.prepare("SELECT COUNT(*) as count FROM tickets WHERE status = 'In Progress'").get() as any).count;
  const resolvedTickets = (db.prepare("SELECT COUNT(*) as count FROM tickets WHERE status = 'Resolved'").get() as any).count;
  const closedTickets = (db.prepare("SELECT COUNT(*) as count FROM tickets WHERE status = 'Closed'").get() as any).count;

  const recentTickets = db.prepare('SELECT * FROM tickets ORDER BY created_at DESC LIMIT 6').all() as Ticket[];

  const priorityCounts = db.prepare(`
    SELECT priority, COUNT(*) as count FROM tickets GROUP BY priority
  `).all() as { priority: TicketPriority; count: number }[];

  const categoryCounts = db.prepare(`
    SELECT category, COUNT(*) as count FROM tickets GROUP BY category
  `).all() as { category: TicketCategory; count: number }[];

  return {
    totalTickets,
    openTickets,
    inProgressTickets,
    resolvedTickets,
    closedTickets,
    recentTickets,
    priorityBreakdown: priorityCounts,
    categoryBreakdown: categoryCounts
  };
}

// Batch import support dataset records with duplicate avoidance
export function importTicketsBatch(records: Array<{
  title: string;
  description: string;
  priority: TicketPriority;
  category: TicketCategory;
  status: TicketStatus;
  resolution?: string | null;
  external_id: string;
  source: string;
  created_at?: string;
}>): { imported: Ticket[]; skippedCount: number } {
  const db = getDatabase();
  const checkStmt = db.prepare('SELECT id FROM tickets WHERE external_id = ?');
  const insertStmt = db.prepare(`
    INSERT INTO tickets (title, description, priority, category, status, resolution, source, external_id, created_at)
    VALUES (?, ?, ?, ?, ?, ?, ?, ?, COALESCE(?, CURRENT_TIMESTAMP))
  `);

  const imported: Ticket[] = [];
  let skippedCount = 0;

  const runTransaction = db.transaction((items: typeof records) => {
    for (const item of items) {
      const existing = checkStmt.get(item.external_id);
      if (existing) {
        skippedCount++;
        continue;
      }
      const info = insertStmt.run(
        item.title,
        item.description,
        item.priority,
        item.category,
        item.status,
        item.resolution || null,
        item.source,
        item.external_id,
        item.created_at || null
      );
      const insertedTicket = getTicketById(Number(info.lastInsertRowid));
      if (insertedTicket) {
        imported.push(insertedTicket);
      }
    }
  });

  runTransaction(records);
  return { imported, skippedCount };
}

// Ticket Embeddings for Semantic Similarity
export function saveTicketEmbedding(ticketId: number, embedding: number[], contentHash: string): void {
  const db = getDatabase();
  const stmt = db.prepare(`
    INSERT INTO ticket_embeddings (ticket_id, embedding_json, content_hash, updated_at)
    VALUES (?, ?, ?, CURRENT_TIMESTAMP)
    ON CONFLICT(ticket_id) DO UPDATE SET
      embedding_json = excluded.embedding_json,
      content_hash = excluded.content_hash,
      updated_at = CURRENT_TIMESTAMP
  `);
  stmt.run(ticketId, JSON.stringify(embedding), contentHash);
}

export function getTicketEmbedding(ticketId: number): { embedding: number[]; contentHash: string } | null {
  const db = getDatabase();
  const row = db.prepare('SELECT embedding_json, content_hash FROM ticket_embeddings WHERE ticket_id = ?').get(ticketId) as any;
  if (!row) return null;
  return {
    embedding: JSON.parse(row.embedding_json || '[]'),
    contentHash: row.content_hash
  };
}

export function getAllTicketEmbeddings(): Array<{ ticket_id: number; embedding: number[]; contentHash: string }> {
  const db = getDatabase();
  const rows = db.prepare('SELECT ticket_id, embedding_json, content_hash FROM ticket_embeddings').all() as any[];
  return rows.map(r => ({
    ticket_id: r.ticket_id,
    embedding: JSON.parse(r.embedding_json || '[]'),
    contentHash: r.content_hash
  }));
}

export function deleteTicketEmbedding(ticketId: number): void {
  const db = getDatabase();
  db.prepare('DELETE FROM ticket_embeddings WHERE ticket_id = ?').run(ticketId);
}

// Conversational Chat Messages Storage per Ticket
export function getTicketMessages(ticketId: number): TicketChatMessage[] {
  const db = getDatabase();
  const rows = db.prepare('SELECT * FROM ticket_messages WHERE ticket_id = ? ORDER BY id ASC').all(ticketId) as any[];
  return rows.map(r => ({
    ...r,
    is_fallback: Boolean(r.is_fallback)
  }));
}

export function saveTicketMessage(ticketId: number, sender: 'user' | 'assistant', message: string, isFallback: boolean = false): TicketChatMessage {
  const db = getDatabase();
  const stmt = db.prepare(`
    INSERT INTO ticket_messages (ticket_id, sender, message, is_fallback)
    VALUES (?, ?, ?, ?)
  `);
  const info = stmt.run(ticketId, sender, message, isFallback ? 1 : 0);
  const row = db.prepare('SELECT * FROM ticket_messages WHERE id = ?').get(Number(info.lastInsertRowid)) as any;
  return {
    ...row,
    is_fallback: Boolean(row.is_fallback)
  };
}

export function clearTicketMessages(ticketId: number): boolean {
  const db = getDatabase();
  const res = db.prepare('DELETE FROM ticket_messages WHERE ticket_id = ?').run(ticketId);
  return res.changes >= 0;
}
