#!/usr/bin/env bash
# Create the folders for a new monthly close: tools/pnl_studio/new_month.sh 2026-10
set -euo pipefail

month="${1:-}"
if [[ ! "$month" =~ ^[0-9]{4}-(0[1-9]|1[0-2])$ ]]; then
  echo "usage: $0 YYYY-MM   (e.g. $0 2026-10)" >&2
  exit 1
fi

root="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)/Finance/Profit_Loss/$month"
mkdir -p "$root/Amazon" "$root/Flipkart" "$root/Meesho" "$root/Reports"
echo "Ready: ${root#"$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)/"}"
echo "  Amazon/    All Orders report (.txt) + GST MTR B2C (.csv, for refunds)"
echo "  Flipkart/  monthly Sales Report (.xlsx)"
echo "  Meesho/    payment workbooks (PREVIOUS / OUTSTANDING)"
echo "  Reports/   P&L markdown saved from the Report tab"
