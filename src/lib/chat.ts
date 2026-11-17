import { GoogleGenAI } from '@google/genai';
import { TicketChatMessage, Ticket } from './types';
import { 
  getTicketById, 
  getTicketMessages, 
  saveTicketMessage, 
  findRelevantKBArticles 
} from './db';
import { isPostgresAvailable, pgGetTicketById, pgGetRelevantKBArticles } from './postgres';
import { findSimilarIncidents } from './similarity';

export async function processTicketChat(
  ticketId: number, 
  messageText: string
): Promise<{ 
  userMessage: TicketChatMessage; 
  assistantMessage: TicketChatMessage 
}> {
  const usePg = await isPostgresAvailable();
  const ticket = usePg ? await pgGetTicketById(ticketId) : getTicketById(ticketId);
  if (!ticket) {
    throw new Error(`Ticket #${ticketId} not found.`);
  }

  // 1. Save user message to database
  const userMessage = saveTicketMessage(ticketId, 'user', messageText.trim(), false);

  // 2. Gather full incident context
  const previousMessages = getTicketMessages(ticketId).filter(m => m.id !== userMessage.id);
  const relevantArticles = usePg
    ? await pgGetRelevantKBArticles(
        ticket.title, 
        ticket.description, 
        ticket.ai_suggested_category || ticket.category
      )
    : findRelevantKBArticles(
        ticket.title, 
        ticket.description, 
        ticket.ai_suggested_category || ticket.category
      );
  const similarIncidents = await findSimilarIncidents(ticket.id, 3);

  // 3. Try Gemini generation with full context
  const apiKey = process.env.GEMINI_API_KEY || process.env.GOOGLE_API_KEY;
  let assistantReply = '';
  let isFallback = false;

  if (apiKey) {
    try {
      assistantReply = await callGeminiChat(
        apiKey, 
        ticket, 
        previousMessages, 
        messageText, 
        relevantArticles, 
        similarIncidents
      );
    } catch (err) {
      console.warn('Gemini chat API call failed, switching to intelligent fallback assistant:', err);
    }
  }

  // 4. Use context-aware heuristic fallback if Gemini was unavailable or threw an error
  if (!assistantReply) {
    isFallback = true;
    assistantReply = generateIntelligentChatFallback(
      ticket, 
      messageText, 
      previousMessages, 
      relevantArticles, 
      similarIncidents
    );
  }

  // 5. Save assistant reply to database
  const assistantMessage = saveTicketMessage(ticketId, 'assistant', assistantReply, isFallback);

  return { userMessage, assistantMessage };
}

/**
 * Calls Google GenAI with full ticket context and conversation turns
 */
async function callGeminiChat(
  apiKey: string,
  ticket: Ticket,
  history: TicketChatMessage[],
  newMessage: string,
  relevantArticles: any[],
  similarIncidents: any[]
): Promise<string> {
  const ai = new GoogleGenAI({ apiKey });

  const kbContext = relevantArticles.length > 0
    ? relevantArticles.map(a => `- [Runbook #${a.id}] ${a.title}: ${a.summary}`).join('\n')
    : 'None currently matched.';

  const similarContext = similarIncidents.length > 0
    ? similarIncidents.map(s => `- [Incident #${s.id} (${s.similarityScore}% match)] "${s.title}" (Status: ${s.status}). Resolution notes: ${s.resolution || 'None recorded'}`).join('\n')
    : 'No prior similar incidents.';

  const systemPrompt = `You are the DigiPlus Senior IT Service Desk AI Assistant.
You are helping a support engineer triage, debug, and resolve the following active incident:

=== TICKET CONTEXT ===
- Ticket ID: #${ticket.id}
- Title: ${ticket.title}
- Description: ${ticket.description}
- Category: ${ticket.category} (AI Recommended: ${ticket.ai_suggested_category || 'N/A'})
- Priority: ${ticket.priority} (AI Recommended: ${ticket.ai_suggested_priority || 'N/A'})
- Current Status: ${ticket.status}
- Existing AI Root Cause: ${ticket.ai_cause || 'Not yet analyzed'}
- Existing AI Suggested Solution: ${ticket.ai_solution || 'Not yet analyzed'}

=== RELEVANT KNOWLEDGE BASE RUNBOOKS ===
${kbContext}

=== SIMILAR HISTORICAL INCIDENTS ===
${similarContext}

=== INSTRUCTIONS ===
1. Answer the engineer's technical question directly, accurately, and professionally.
2. Ground your response in the incident description, existing root causes, matched runbooks, and previous similar incident resolutions.
3. If asked about logs, specify exact file paths, event viewer logs, or shell commands for this category.
4. If asked for a simpler explanation, explain in clear, non-jargon language suitable for non-technical stakeholders.
5. If the proposed solution failed, propose practical secondary troubleshooting steps or alternative workarounds.
6. Use markdown formatting with bolding, numbered steps, or code formatting where helpful.`;

  // Format contents for Gemini
  const contents: any[] = [];
  contents.push({ role: 'user', parts: [{ text: systemPrompt }] });
  contents.push({ role: 'model', parts: [{ text: `Understood. I am ready to assist you with Ticket #${ticket.id}: "${ticket.title}". What would you like to know?` }] });

  // Add conversation history
  for (const msg of history) {
    contents.push({
      role: msg.sender === 'user' ? 'user' : 'model',
      parts: [{ text: msg.message }]
    });
  }

  // Add current user message
  contents.push({
    role: 'user',
    parts: [{ text: newMessage }]
  });

  const modelsToTry = ['gemini-2.5-flash', 'gemini-2.0-flash', 'gemini-1.5-flash'];
  let replyText = '';

  for (const model of modelsToTry) {
    try {
      const response = await ai.models.generateContent({
        model,
        contents,
        config: {
          temperature: 0.3,
        }
      });
      replyText = response.text || response.candidates?.[0]?.content?.parts?.[0]?.text || '';
      if (replyText) break;
    } catch {
      // try fallback model
    }
  }

  return replyText.trim();
}

/**
 * Intelligent, context-grounded fallback assistant when Gemini API key is absent or quota limited
 */
function generateIntelligentChatFallback(
  ticket: Ticket,
  query: string,
  history: TicketChatMessage[],
  relevantArticles: any[],
  similarIncidents: any[]
): string {
  const q = query.toLowerCase();
  const title = ticket.title;
  const desc = ticket.description;
  const category = ticket.category;
  const aiCause = ticket.ai_cause || 'configuration mismatch or service latency';

  // 1. Logs inquiry
  if (q.includes('log') || q.includes('where to check') || q.includes('where should i look')) {
    if (category === 'Network') {
      return `### 🔍 Recommended Diagnostic Logs for ${title}\n` +
        `1. **VPN Client Logs**: Check \`%LOCALAPPDATA%\\Palo Alto Networks\\GlobalProtect\\PanGPS.log\` or Cisco AnyConnect \`vpn_cli.log\`.\n` +
        `2. **Windows Event Viewer**: Check **Applications and Services Logs** ➔ **Microsoft** ➔ **Windows** ➔ **RemoteAccess-Client**.\n` +
        `3. **Network Connection Verification**: Execute \`ipconfig /all\`, \`nslookup <gateway-fqdn>\`, and \`route print\`.\n` +
        `4. **MFA Radius / Okta Logs**: Verify server-side authentication drops in Okta System Log filtering by requester ID.`;
    } else if (category === 'Email & Communication') {
      return `### 🔍 Recommended Diagnostic Logs for ${title}\n` +
        `1. **Outlook Connection Status**: Hold \`Ctrl\` and right-click the Outlook system tray icon ➔ select **Connection Status**.\n` +
        `2. **Office Identity & ADAL Logs**: Check \`%LOCALAPPDATA%\\Microsoft\\Office\\16.0\\WebServiceCache\` and Event Viewer **Application Logs** with source \`MSExchange\`.\n` +
        `3. **Entra ID / Azure AD Sign-in Logs**: Search tenant Sign-in logs for conditional access policy failures matching the user's UPN.`;
    } else if (category === 'Cloud & Infrastructure') {
      return `### 🔍 Recommended Diagnostic Logs for ${title}\n` +
        `1. **PostgreSQL/MySQL Active Sessions**: Run \`SELECT pid, now() - query_start AS duration, state, query FROM pg_stat_activity WHERE state != 'idle';\`\n` +
        `2. **CloudWatch / Server Metrics**: Inspect Database CPU, IOPS, and \`DatabaseConnections\` graph over the past 2 hours.\n` +
        `3. **Application Container Logs**: Inspect backend pod logs: \`kubectl logs -n production -l app=backend --tail=200 --previous\`.`;
    } else if (category === 'Hardware') {
      return `### 🔍 Recommended Diagnostic Logs for ${title}\n` +
        `1. **Windows Print Service Log**: Open Event Viewer ➔ **Applications and Services** ➔ **Microsoft** ➔ **Windows** ➔ **PrintService** ➔ **Operational**.\n` +
        `2. **Device Manager**: Check for warning glyphs (code 43/10) on USB hubs and network adapters.\n` +
        `3. **System System Events**: Check Windows Event ID 7036 (Print Spooler terminated unexpectedly).`;
    } else {
      return `### 🔍 Diagnostic Logs to Inspect\n` +
        `1. **Local System Logs**: Event Viewer (Windows) or \`/var/log/syslog\` (Linux).\n` +
        `2. **Application Error Traces**: Inspect stack traces in the application logs corresponding to the timestamp of the report.\n` +
        `3. **Authentication Audit**: Review IAM and SSO directory access logs for permission rejections.`;
    }
  }

  // 2. Simpler terms / Layman explanation
  if (q.includes('simpler') || q.includes('simple term') || q.includes('explain') || q.includes('in plain english')) {
    return `### 💡 Plain-English Summary of Ticket #${ticket.id}\n\n` +
      `**What is happening?**\n` +
      `The user cannot complete their normal workflow because ${ticket.title.toLowerCase()}.\n\n` +
      `**Why is it happening?**\n` +
      `In simple terms, ${aiCause.toLowerCase().replace('detected in the user environment.', '')}. Think of it like a lock that has changed keys, or a bridge where traffic has backed up so much that new cars are being turned away.\n\n` +
      `**What do we need to do?**\n` +
      `We need to clear out the stuck connections/stale credentials and reset the communication channel between the user's computer and the service.`;
  }

  // 3. Solution does not work / Alternative solution
  if (q.includes('not work') || q.includes('alternative') || q.includes('fails') || q.includes('failed') || q.includes('another')) {
    const similarRes = similarIncidents.find(s => s.hasResolution);
    const similarNote = similarRes ? `\n\n**Reference from similar incident #${similarRes.id} ("${similarRes.title}")**:\n${similarRes.resolution}` : '';

    return `### 🔄 Alternative Troubleshooting Steps\n\n` +
      `If the primary diagnostic steps do not resolve the issue, execute this secondary escalation path:\n\n` +
      `1. **Safe Mode / Clean Isolation**: Restart the application or service in isolation/safe mode without third-party add-ins or extensions.\n` +
      `2. **Network Bypass**: Have the user test connectivity from an alternate network (e.g. mobile hotspot) to rule out corporate firewall or local ISP routing issues.\n` +
      `3. **Session Cache Purge**: Fully invalidate the user's active session from the administration console (force session revocation).\n` +
      `4. **Reinstall / Rollback**: If this followed a recent update, roll back to the previously stable driver/software package version.` +
      similarNote;
  }

  // 4. Why is this happening?
  if (q.includes('why') || q.includes('cause') || q.includes('reason')) {
    return `### ❓ Underlying Root Cause Analysis for Ticket #${ticket.id}\n\n` +
      `Based on the reported symptoms (${ticket.description}), the primary driver is:\n\n` +
      `> **${aiCause}**\n\n` +
      `This typically happens when:\n` +
      `- Security tokens or cached credentials become desynchronized from the central identity provider.\n` +
      `- A background timeout prevents the handshake between client and server within the expected SLA window.\n` +
      `- Concurrent sessions exceed allocated pool limits.`;
  }

  // 5. Default contextual assistant response
  const runbookTip = relevantArticles[0]
    ? `\n\n*Recommended Runbook: "${relevantArticles[0].title}" contains verified remediation procedures.*`
    : '';

  return `### 🤖 Assistant Incident Triage Note\n\n` +
    `Regarding your question on **Ticket #${ticket.id} (${ticket.title})**:\n\n` +
    `The current status is **${ticket.status}** with priority **${ticket.priority}** in **${ticket.category}**.\n\n` +
    `The primary suspected cause is: **${aiCause}**.\n\n` +
    `**Suggested immediate next steps:**\n` +
    `1. Verify if this issue affects only this user or multiple endpoints in the department.\n` +
    `2. Compare against the solution guide in the incident resolution tab.\n` +
    `3. You can ask me for specific log locations, alternative workarounds, or a plain-English explanation at any time.` +
    runbookTip;
}
