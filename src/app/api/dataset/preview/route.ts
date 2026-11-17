import { NextResponse } from 'next/server';
import { fetchDatasetPreview } from '@/lib/dataset';

export const dynamic = 'force-dynamic';

export async function GET(request: Request) {
  try {
    const { searchParams } = new URL(request.url);
    const limitParam = searchParams.get('limit');
    const limit = limitParam ? Math.max(1, Math.min(20, parseInt(limitParam, 10))) : 6;

    const data = await fetchDatasetPreview(limit);
    return NextResponse.json({ success: true, data });
  } catch (error: any) {
    console.error('Failed to preview dataset:', error);
    return NextResponse.json(
      { success: false, error: error.message || 'Failed to fetch dataset preview' },
      { status: 500 }
    );
  }
}
