import { NextResponse } from 'next/server';
import { getTicketById, updateTicket, findRelevantKBArticles } from '@/lib/db';
import { isPostgresAvailable, pgGetTicketById, pgUpdateTicket, pgGetRelevantKBArticles } from '@/lib/postgres';
import { analyzeTicketWithAI } from '@/lib/ai';

export const dynamic = 'force-dynamic';

export async function POST(request: Request) {
  try {
    const body = await request.json();
    const { ticketId } = body;

    if (!ticketId) {
      return NextResponse.json({ success: false, error: 'ticketId is required' }, { status: 400 });
    }

    const usePg = await isPostgresAvailable();
    const ticket = usePg ? await pgGetTicketById(Number(ticketId)) : getTicketById(Number(ticketId));
    if (!ticket) {
      return NextResponse.json({ success: false, error: 'Ticket not found' }, { status: 404 });
    }

    // Call FastAPI AI service if available, with resilient local fallback
    const aiServiceUrl = process.env.AI_SERVICE_URL || 'http://127.0.0.1:8000';
    let analysis;

    try {
      const aiResponse = await fetch(`${aiServiceUrl}/analyze-ticket`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          ticket: {
            id: ticket.id,
            title: ticket.title,
            description: ticket.description,
            category: ticket.category,
            priority: ticket.priority
          }
        }),
        signal: AbortSignal.timeout(60000)
      });

      if (aiResponse.ok) {
        analysis = await aiResponse.json();
      } else {
        throw new Error(`AI service returned HTTP ${aiResponse.status}`);
      }
    } catch (aiErr) {
      console.warn('FastAPI AI Service unavailable, using internal diagnostic fallback:', aiErr);
      analysis = await analyzeTicketWithAI(ticket);
    }

    // Save AI insights to the ticket record
    const updatedTicket = usePg 
      ? await pgUpdateTicket(ticket.id, {
          ai_summary: analysis.summary,
          ai_cause: analysis.possibleCause,
          ai_solution: analysis.suggestedSolution,
          ai_suggested_category: analysis.suggestedCategory,
          ai_suggested_priority: analysis.suggestedPriority
        })
      : updateTicket(ticket.id, {
          ai_summary: analysis.summary,
          ai_cause: analysis.possibleCause,
          ai_solution: analysis.suggestedSolution,
          ai_suggested_category: analysis.suggestedCategory,
          ai_suggested_priority: analysis.suggestedPriority
        });

    // Find relevant knowledge base articles
    const matchedArticles = usePg
      ? await pgGetRelevantKBArticles(ticket.title, ticket.description, analysis.suggestedCategory || ticket.category)
      : findRelevantKBArticles(
          ticket.title,
          ticket.description,
          analysis.suggestedCategory || ticket.category
        );

    return NextResponse.json({
      success: true,
      data: {
        ticket: updatedTicket,
        analysis,
        relevantArticles: matchedArticles
      }
    });
  } catch (error: any) {
    console.error('Error during AI analysis:', error);
    return NextResponse.json(
      { success: false, error: error.message || 'AI analysis failed' },
      { status: 500 }
    );
  }
}
