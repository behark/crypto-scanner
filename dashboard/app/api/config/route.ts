import { NextRequest, NextResponse } from "next/server";
import { put, list, del } from "@vercel/blob";
import yaml from "js-yaml";
import { defaultConfig } from "@/lib/defaultConfig";
import type { ScannerConfig } from "@/lib/types";

const BLOB_NAME = "scanner-config.json";

function checkAuth(req: NextRequest): boolean {
  const secret = process.env.DASHBOARD_SECRET;
  if (!secret) return true; // local dev without secret
  const header = req.headers.get("x-dashboard-secret");
  const urlSecret = req.nextUrl.searchParams.get("secret");
  return header === secret || urlSecret === secret;
}

async function loadConfig(): Promise<ScannerConfig> {
  const token = process.env.BLOB_READ_WRITE_TOKEN;
  if (!token) {
    return defaultConfig;
  }
  try {
    const { blobs } = await list({ prefix: BLOB_NAME, token });
    if (blobs.length === 0) return defaultConfig;
    const res = await fetch(blobs[0].url);
    return (await res.json()) as ScannerConfig;
  } catch {
    return defaultConfig;
  }
}

export async function GET(req: NextRequest) {
  if (!checkAuth(req)) {
    return NextResponse.json({ error: "Unauthorized" }, { status: 401 });
  }
  const config = await loadConfig();
  const format = req.nextUrl.searchParams.get("format");
  if (format === "yaml") {
    return new NextResponse(yaml.dump(config, { lineWidth: 100 }), {
      headers: { "Content-Type": "text/yaml" },
    });
  }
  return NextResponse.json({ config, blobEnabled: !!process.env.BLOB_READ_WRITE_TOKEN });
}

export async function POST(req: NextRequest) {
  if (!checkAuth(req)) {
    return NextResponse.json({ error: "Unauthorized" }, { status: 401 });
  }
  const body = (await req.json()) as { config: ScannerConfig };
  const config = body.config;
  const token = process.env.BLOB_READ_WRITE_TOKEN;

  if (token) {
    try {
      const { blobs } = await list({ prefix: BLOB_NAME, token });
      for (const b of blobs) {
        await del(b.url, { token });
      }
      await put(BLOB_NAME, JSON.stringify(config, null, 2), {
        access: "public",
        token,
        contentType: "application/json",
      });
    } catch (e) {
      return NextResponse.json({ error: String(e) }, { status: 500 });
    }
  }

  return NextResponse.json({
    ok: true,
    savedToBlob: !!token,
    yaml: yaml.dump(config, { lineWidth: 100 }),
  });
}
