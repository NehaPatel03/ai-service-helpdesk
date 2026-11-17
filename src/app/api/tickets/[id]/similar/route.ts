import { NextResponse } from 'next/server';
import { getTicketById } from '@/lib/db';
import { findSimilarIncidents } from '@/lib/similarity';

export const dynamic = 'force-dynamic';

export async function GET(
  request: Request,
  { params }: { params: Promise<{ id: string }> }
) {
  try {
    const { id } = await params;
    const ticketId = parseInt(id, 10);

    if (isNaN(ticketId)) {
      return NextResponse.json(
        { success: false, error: 'Invalid ticket ID.' },
        { status: 400 }
      );
    }

    const ticket = getTicketById(ticketId);
    if (!ticket) {
      return NextResponse.json(
        { success: false, error: 'Ticket not found.' },
        { status: 404 }
      );
    }

    const { searchParams } = new URL(request.url);
    const limitParam = searchParams.get('limit');
    const limit = limitParam ? Math.max(1, Math.min(10, parseInt(limitParam, 10))) : 4;

    const similar = await findSimilarIncidents(ticketId, limit);

    return NextResponse.json({
      success: true,
      count: similar.length,
      data: similar
    });
  } catch (error: any) {
    console.error('Failed to find similar incidents:', error);
    return NextResponse.json(
      { success: false, error: error.message || 'Failed to detect similar incidents' },
      { status: 500 }
    );
  }
}
