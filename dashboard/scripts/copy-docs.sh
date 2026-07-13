#!/usr/bin/env bash
# Copy repo docs into dashboard public folder before Vercel build
cp -r "$(dirname "$0")/../docs" "$(dirname "$0")/public/docs"
