import { NextResponse } from 'next/server';
import { getTicketById, getTicketMessages, clearTicketMessages } from '@/lib/db';
import { isPostgresAvailable, pgGetTicketById } from '@/lib/postgres';
import { processTicketChat } from '@/lib/chat';

export const dynamic = 'force-dynamic';

export async function GET(request: Request) {
  try {
    const { searchParams } = new URL(request.url);
    const ticketIdParam = searchParams.get('ticketId');

    if (!ticketIdParam) {
      return NextResponse.json(
        { success: false, error: 'ticketId parameter is required' },
        { status: 400 }
      );
    }

    const ticketId = parseInt(ticketIdParam, 10);
    if (isNaN(ticketId)) {
      return NextResponse.json(
        { success: false, error: 'Invalid ticketId parameter' },
        { status: 400 }
      );
    }

    const usePg = await isPostgresAvailable();
    const ticket = usePg ? await pgGetTicketById(ticketId) : getTicketById(ticketId);
    if (!ticket) {
      return NextResponse.json(
        { success: false, error: 'Ticket not found' },
        { status: 404 }
      );
    }

    const messages = getTicketMessages(ticketId);
    return NextResponse.json({
      success: true,
      count: messages.length,
      data: messages
    });
  } catch (error: any) {
    console.error('Failed to get ticket chat messages:', error);
    return NextResponse.json(
      { success: false, error: error.message || 'Failed to retrieve messages' },
      { status: 500 }
    );
  }
}

export async function POST(request: Request) {
  try {
    const body = await request.json();
    const { ticketId, message } = body;

    if (!ticketId || typeof ticketId !== 'number') {
      return NextResponse.json(
        { success: false, error: 'Valid numeric ticketId is required' },
        { status: 400 }
      );
    }

    if (!message || typeof message !== 'string' || message.trim().length === 0) {
      return NextResponse.json(
        { success: false, error: 'Message cannot be empty' },
        { status: 400 }
      );
    }

    const usePg = await isPostgresAvailable();
    const ticket = usePg ? await pgGetTicketById(ticketId) : getTicketById(ticketId);
    if (!ticket) {
      return NextResponse.json(
        { success: false, error: 'Ticket not found' },
        { status: 404 }
      );
    }

    const result = await processTicketChat(ticketId, message.trim());

    return NextResponse.json({
      success: true,
      data: result
    });
  } catch (error: any) {
    console.error('Failed to process ticket chat message:', error);
    return NextResponse.json(
      { success: false, error: error.message || 'Failed to generate assistant response' },
      { status: 500 }
    );
  }
}

export async function DELETE(request: Request) {
  try {
    const { searchParams } = new URL(request.url);
    const ticketIdParam = searchParams.get('ticketId');

    if (!ticketIdParam) {
      return NextResponse.json(
        { success: false, error: 'ticketId parameter is required' },
        { status: 400 }
      );
    }

    const ticketId = parseInt(ticketIdParam, 10);
    if (isNaN(ticketId)) {
      return NextResponse.json(
        { success: false, error: 'Invalid ticketId parameter' },
        { status: 400 }
      );
    }

    const success = clearTicketMessages(ticketId);
    return NextResponse.json({
      success,
      message: `Chat history cleared for Ticket #${ticketId}`
    });
  } catch (error: any) {
    console.error('Failed to clear ticket chat history:', error);
    return NextResponse.json(
      { success: false, error: error.message || 'Failed to clear chat history' },
      { status: 500 }
    );
  }
}
