import { NextResponse } from 'next/server';
import { getDashboardStats } from '@/lib/db';
import { isPostgresAvailable, pgGetDashboardStats } from '@/lib/postgres';

export const dynamic = 'force-dynamic';

export async function GET() {
  try {
    let stats;
    if (await isPostgresAvailable()) {
      stats = await pgGetDashboardStats();
    } else {
      stats = getDashboardStats();
    }
    return NextResponse.json({ success: true, data: stats });
  } catch (error: any) {
    console.error('Failed to get dashboard stats:', error);
    return NextResponse.json({ success: false, error: error.message }, { status: 500 });
  }
}
