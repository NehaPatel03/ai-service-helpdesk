import { NextResponse } from 'next/server';
import { getTicketById, updateTicket, deleteTicket } from '@/lib/db';
import { isPostgresAvailable, pgGetTicketById, pgUpdateTicket, pgDeleteTicket } from '@/lib/postgres';

export const dynamic = 'force-dynamic';

export async function GET(
  request: Request,
  { params }: { params: Promise<{ id: string }> }
) {
  try {
    const { id } = await params;
    const ticketId = parseInt(id, 10);
    
    if (isNaN(ticketId)) {
      return NextResponse.json({ success: false, error: 'Invalid ticket ID.' }, { status: 400 });
    }

    let ticket;
    if (await isPostgresAvailable()) {
      ticket = await pgGetTicketById(ticketId);
    } else {
      ticket = getTicketById(ticketId);
    }

    if (!ticket) {
      return NextResponse.json({ success: false, error: 'Ticket not found.' }, { status: 404 });
    }

    return NextResponse.json({ success: true, data: ticket });
  } catch (error: any) {
    console.error('Failed to get ticket:', error);
    return NextResponse.json({ success: false, error: error.message }, { status: 500 });
  }
}

export async function PATCH(
  request: Request,
  { params }: { params: Promise<{ id: string }> }
) {
  try {
    const { id } = await params;
    const ticketId = parseInt(id, 10);
    
    if (isNaN(ticketId)) {
      return NextResponse.json({ success: false, error: 'Invalid ticket ID.' }, { status: 400 });
    }

    const body = await request.json();
    let updated;
    if (await isPostgresAvailable()) {
      updated = await pgUpdateTicket(ticketId, body);
    } else {
      updated = updateTicket(ticketId, body);
    }

    if (!updated) {
      return NextResponse.json({ success: false, error: 'Ticket not found or update failed.' }, { status: 404 });
    }

    return NextResponse.json({ success: true, data: updated });
  } catch (error: any) {
    console.error('Failed to update ticket:', error);
    return NextResponse.json({ success: false, error: error.message }, { status: 500 });
  }
}

export async function DELETE(
  request: Request,
  { params }: { params: Promise<{ id: string }> }
) {
  try {
    const { id } = await params;
    const ticketId = parseInt(id, 10);
    
    if (isNaN(ticketId)) {
      return NextResponse.json({ success: false, error: 'Invalid ticket ID.' }, { status: 400 });
    }

    let success = false;
    if (await isPostgresAvailable()) {
      success = await pgDeleteTicket(ticketId);
    } else {
      success = deleteTicket(ticketId);
    }
    if (!success) {
      return NextResponse.json({ success: false, error: 'Ticket not found.' }, { status: 404 });
    }

    return NextResponse.json({ success: true, message: 'Ticket deleted successfully.' });
  } catch (error: any) {
    console.error('Failed to delete ticket:', error);
    return NextResponse.json({ success: false, error: error.message }, { status: 500 });
  }
}
