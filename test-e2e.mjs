async function runE2ETest() {
  console.log('🚀 Starting DigiPlus AI Service Desk Complete End-to-End Verification...\n');
  const baseUrl = 'http://localhost:3000';

  // 1. Test Dashboard Stats
  console.log('1️⃣ Testing Dashboard Statistics API (/api/stats)...');
  const statsRes = await fetch(`${baseUrl}/api/stats`);
  const statsData = await statsRes.json();
  console.log(`Initial total tickets: ${statsData.data?.totalTickets}, open: ${statsData.data?.openTickets}`);
  if (!statsData.success) throw new Error('Stats API failed');
  console.log('✅ Dashboard Stats OK!\n');

  // 2. Test Listing Initial Tickets
  console.log('2️⃣ Testing Tickets List API (/api/tickets)...');
  const ticketsRes = await fetch(`${baseUrl}/api/tickets`);
  const ticketsData = await ticketsRes.json();
  console.log(`Retrieved ${ticketsData.count} tickets.`);
  if (!ticketsData.success || ticketsData.count === 0) throw new Error('Tickets listing failed');
  console.log('✅ Tickets List OK!\n');

  // 3. Test Knowledge Base
  console.log('3️⃣ Testing Knowledge Base API (/api/knowledge-base)...');
  const kbRes = await fetch(`${baseUrl}/api/knowledge-base`);
  const kbData = await kbRes.json();
  console.log(`Retrieved ${kbData.count} knowledge base articles.`);
  if (!kbData.success || kbData.count === 0) throw new Error('Knowledge base listing failed');
  console.log('✅ Knowledge Base OK!\n');

  // 4. Test Create Ticket
  console.log('4️⃣ Testing Ticket Creation (/api/tickets)...');
  const newTicketPayload = {
    title: 'PostgreSQL RDS connection pool exhausted during peak billing batch',
    description: 'During the 2AM billing job, clients receive 500 Internal Server Error. Backend logs report: Connection pool exhausted (100/100 active connections). Postgres CPU at 95%.',
    priority: 'Urgent',
    category: 'Cloud & Infrastructure'
  };
  const createRes = await fetch(`${baseUrl}/api/tickets`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(newTicketPayload)
  });
  const createdData = await createRes.json();
  console.log('Created Ticket ID:', createdData.data?.id);
  if (!createdData.success || !createdData.data?.id) throw new Error('Ticket creation failed');
  const ticketId = createdData.data.id;
  console.log(`✅ Ticket #${ticketId} Created Successfully!\n`);

  // 5. Test AI Analysis
  console.log(`5️⃣ Testing AI Ticket Analysis (/api/ai/analyze for Ticket #${ticketId})...`);
  const aiRes = await fetch(`${baseUrl}/api/ai/analyze`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ ticketId })
  });
  const aiData = await aiRes.json();
  console.log('AI Summary:', aiData.data?.analysis?.summary);
  console.log('Matched KB Articles:', aiData.data?.relevantArticles?.map((a) => a.title));
  if (!aiData.success || !aiData.data?.analysis?.summary) throw new Error('AI analysis failed');
  console.log('✅ AI Analysis & Knowledge Runbook Matching OK!\n');

  // 6. Test Updating Status & Resolution (Lifecycle)
  console.log(`6️⃣ Testing Ticket Resolution (/api/tickets/${ticketId})...`);
  const resolutionNotes = `[Verified & Resolved]\n1. Terminated locking long-running billing aggregation query via pg_terminate_backend.\n2. Increased RDS max_connections and configured PgBouncer pool_size=50.\n3. Verified application throughput restored to normal.`;
  const resolveRes = await fetch(`${baseUrl}/api/tickets/${ticketId}`, {
    method: 'PATCH',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({
      resolution: resolutionNotes,
      status: 'Resolved'
    })
  });
  const resolvedData = await resolveRes.json();
  if (!resolvedData.success || resolvedData.data.status !== 'Resolved') throw new Error('Ticket resolution failed');
  console.log('✅ Ticket Resolution Persisted!\n');

  // 7. FEATURE 3 TEST: Hugging Face Dataset Preview & Batch Import
  console.log('7️⃣ Testing FEATURE 3: Hugging Face Dataset Integration (/api/dataset)...');
  const prevRes = await fetch(`${baseUrl}/api/dataset/preview?limit=3`);
  const prevData = await prevRes.json();
  console.log(`Dataset Preview: total available = ${prevData.data?.totalAvailable}, sample rows = ${prevData.data?.preview?.length}`);
  if (!prevData.success || !prevData.data?.preview || prevData.data.preview.length === 0) {
    throw new Error('Dataset preview failed');
  }

  const importBatchCount = 5;
  const impRes = await fetch(`${baseUrl}/api/dataset/import`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ count: importBatchCount })
  });
  const impData = await impRes.json();
  console.log(`Dataset Import: processed ${impData.data?.totalProcessed}, imported ${impData.data?.importedCount}, skipped duplicates ${impData.data?.skippedCount}`);
  if (!impData.success) throw new Error('Dataset import failed');

  // Verify duplicate prevention
  const dupRes = await fetch(`${baseUrl}/api/dataset/import`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ count: importBatchCount })
  });
  const dupData = await dupRes.json();
  console.log(`Duplicate prevention check: ${dupData.data?.skippedCount} skipped on re-import`);
  if (!dupData.success || dupData.data.skippedCount === 0) {
    throw new Error('Duplicate prevention failed to skip existing tickets');
  }
  console.log('✅ Hugging Face Dataset Integration & Duplicate Prevention OK!\n');

  // 8. FEATURE 2 TEST: Semantic Similar Incident Detection
  console.log(`8️⃣ Testing FEATURE 2: Similar Incident Detection (/api/tickets/${ticketId}/similar)...`);
  const simRes = await fetch(`${baseUrl}/api/tickets/${ticketId}/similar?limit=3`);
  const simData = await simRes.json();
  console.log(`Found ${simData.count} contextually similar tickets.`);
  if (!simData.success || !Array.isArray(simData.data)) throw new Error('Similar incident detection failed');
  for (const match of simData.data) {
    if (match.id === ticketId) throw new Error('Similar incidents must exclude the ticket itself');
    console.log(`   - Match #${match.id}: "${match.title}" -> ${match.similarityScore}% similarity (Status: ${match.status}, Resolution: ${match.hasResolution ? 'Yes' : 'No'})`);
  }
  console.log('✅ AI Semantic Similar Incident Detection OK!\n');

  // 9. FEATURE 1 TEST: Conversational AI Support Assistant
  console.log(`9️⃣ Testing FEATURE 1: Conversational AI Assistant (/api/ai/chat for Ticket #${ticketId})...`);
  
  // Q1
  const chatQ1 = 'What logs should I check to debug this connection pool exhaustion?';
  console.log(`Asking Assistant: "${chatQ1}"`);
  const chatRes1 = await fetch(`${baseUrl}/api/ai/chat`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ ticketId, message: chatQ1 })
  });
  const chatData1 = await chatRes1.json();
  if (!chatData1.success || !chatData1.data?.assistantMessage?.message) {
    throw new Error('Chat message 1 failed');
  }
  console.log('Assistant Answer 1:', chatData1.data.assistantMessage.message.substring(0, 140) + '...');

  // Q2 (Follow-up)
  const chatQ2 = 'Can you explain the root cause in simpler terms?';
  console.log(`Asking Follow-Up: "${chatQ2}"`);
  const chatRes2 = await fetch(`${baseUrl}/api/ai/chat`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ ticketId, message: chatQ2 })
  });
  const chatData2 = await chatRes2.json();
  if (!chatData2.success || !chatData2.data?.assistantMessage?.message) {
    throw new Error('Chat follow-up failed');
  }
  console.log('Assistant Answer 2:', chatData2.data.assistantMessage.message.substring(0, 140) + '...');

  // Check persistent history
  const histRes = await fetch(`${baseUrl}/api/ai/chat?ticketId=${ticketId}`);
  const histData = await histRes.json();
  console.log(`Persisted chat history count for Ticket #${ticketId}: ${histData.count} turns`);
  if (!histData.success || histData.count < 4) throw new Error('Chat history not persisted accurately');

  // Check ticket isolation: other ticket has 0 messages
  const isoRes = await fetch(`${baseUrl}/api/ai/chat?ticketId=99999`);
  const isoData = await isoRes.json();
  if (isoData.success) throw new Error('Invalid ticket ID should return 404 in chat history');

  console.log('✅ Conversational AI Multi-Turn Support Assistant & Persistence OK!\n');

  // 10. Verify Updated Dashboard Stats
  console.log('🔟 Verifying Updated Dashboard Stats...');
  const updatedStatsRes = await fetch(`${baseUrl}/api/stats`);
  const updatedStats = await updatedStatsRes.json();
  console.log(`Updated Stats: Total tickets = ${updatedStats.data?.totalTickets}, Resolved = ${updatedStats.data?.resolvedTickets}`);
  if (updatedStats.data.totalTickets <= statsData.data.totalTickets) {
    throw new Error('Total tickets count did not increment');
  }
  console.log('✅ Dashboard Stats Accurately Recalculated!\n');

  // 11. Verify HTML Page Renders
  console.log('1️⃣1️⃣ Verifying HTML Page Renders (SSR / Client Pages)...');
  const pages = ['/', '/tickets', `/tickets/${ticketId}`, '/knowledge-base'];
  for (const page of pages) {
    const pageRes = await fetch(`${baseUrl}${page}`);
    if (!pageRes.ok) throw new Error(`Page ${page} returned status ${pageRes.status}`);
    console.log(`   - ${page} => HTTP ${pageRes.status} OK`);
  }

  console.log('\n🎉 ALL 11 END-TO-END VERIFICATION SUITES PASSED! 🚀');
}

runE2ETest().catch((err) => {
  console.error('❌ E2E Test Failed:', err);
  process.exit(1);
});
