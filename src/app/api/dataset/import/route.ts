import { NextResponse } from 'next/server';
import { importDatasetTickets } from '@/lib/dataset';

export const dynamic = 'force-dynamic';

export async function POST(request: Request) {
  try {
    let count = 25;
    let offset = 0;

    try {
      const body = await request.json();
      if (body.count && typeof body.count === 'number') {
        count = Math.max(1, Math.min(100, body.count));
      }
      if (body.offset && typeof body.offset === 'number') {
        offset = Math.max(0, body.offset);
      }
    } catch {
      // Body is optional, default to count=25
    }

    const result = await importDatasetTickets(count, offset);
    return NextResponse.json({
      success: true,
      data: result,
      message: `Successfully processed ${result.totalProcessed} records. ${result.importedCount} new incidents imported, ${result.skippedCount} duplicates skipped.`
    });
  } catch (error: any) {
    console.error('Failed to import dataset tickets:', error);
    return NextResponse.json(
      { success: false, error: error.message || 'Failed to import dataset tickets' },
      { status: 500 }
    );
  }
}
