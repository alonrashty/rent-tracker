"""
digest.py — daily email digest of new listings.

Usage:
    python src/digest.py               # preview: print HTML to stdout
    python src/digest.py --scheduled   # send via Gmail SMTP (skips if 0 new)
    python src/digest.py --since 48    # look back N hours (default 24)
"""

import argparse
import smtplib
import sys
from datetime import datetime, timedelta, timezone
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")

import config
import db

MAX_LISTINGS = 20
APP_URL = "https://london-rent-tracker.up.railway.app"

COMMUTE_GOOD = 30
COMMUTE_BAD  = 40


def _ct_style(mins):
    if mins is None:
        return "background:#f5f5f5;color:#9e9e9e"
    if mins < COMMUTE_GOOD:
        return "background:#e8f5e9;color:#2e7d32"
    if mins < COMMUTE_BAD:
        return "background:#eceff1;color:#546e7a"
    return "background:#fce4ec;color:#880e4f"


def _ct_label(mins):
    return f"{mins}m" if mins is not None else "N/A"


def _rank_key(row):
    work = row["commute_work_mins"] if row["commute_work_mins"] is not None else 9999
    return (work, row["rent_pcm"])


def _fmt_date(iso: str | None) -> str:
    if not iso:
        return ""
    try:
        return datetime.fromisoformat(iso).strftime("%d %b %Y").lstrip("0")
    except ValueError:
        return iso


def fetch_new_listings(conn, since_hours: int) -> list:
    cutoff = (datetime.now(timezone.utc) - timedelta(hours=since_hours)).isoformat()
    return conn.execute("""
        SELECT id, url, platform, title, address, area, neighbourhood,
               bedrooms, bathrooms, rent_pcm, available_date, days_on_market,
               commute_work_mins, commute_lse_mins, image_url
        FROM listings
        WHERE created_at >= ?
          AND status != 'dismissed'
        ORDER BY created_at DESC
    """, (cutoff,)).fetchall()


def build_html(rows: list, total_new: int) -> str:
    today_str = datetime.now().strftime("%d %B %Y").lstrip("0")
    count_label = f"{total_new} new listing{'s' if total_new != 1 else ''}"
    shown = sorted(rows, key=_rank_key)[:MAX_LISTINGS]
    overflow = total_new - len(shown)

    # ── listing cards ──────────────────────────────────────────────────────
    cards_html = ""

    if not shown:
        cards_html = """
        <tr>
          <td style="background:white;padding:40px 24px;text-align:center;color:#9e9e9e;font-size:14px;">
            No new listings in the last 24 hours.
          </td>
        </tr>"""
    else:
        for i, row in enumerate(shown):
            border = "none" if (i == len(shown) - 1 and overflow == 0) else "1px solid #e0e0e0"

            photo_html = ""
            if row["image_url"]:
                photo_html = (
                    f'<img src="{row["image_url"]}" width="552" alt="" '
                    f'style="display:block;width:100%;max-width:552px;height:180px;'
                    f'object-fit:cover;border-radius:8px;margin-bottom:12px;">'
                )

            address_line = row["address"] or row["title"] or ""

            beds_label = ""
            if row["bedrooms"]:
                beds_label = f"{row['bedrooms']} bed"
                if row["bathrooms"]:
                    beds_label += f" · {row['bathrooms']} bath"

            meta_parts = []
            if row["days_on_market"] is not None:
                meta_parts.append(f"{row['days_on_market']}d on market")
            if row["available_date"]:
                meta_parts.append(f"From {_fmt_date(row['available_date'])}")
            meta_str = " · ".join(meta_parts)

            area_label   = row["area"] or ""
            platform_cap = (row["platform"] or "").capitalize()

            work_s = _ct_style(row["commute_work_mins"])
            lse_s  = _ct_style(row["commute_lse_mins"])

            cards_html += f"""
        <tr>
          <td style="background:white;padding:20px 24px;border-bottom:{border};">
            {photo_html}
            <table width="100%" cellpadding="0" cellspacing="0">
              <tr>
                <td>
                  <span style="font-size:22px;font-weight:700;color:#1a1a1a;">£{row['rent_pcm']:,}/mo</span>
                  {'<span style="font-size:13px;color:#757575;margin-left:8px;">' + beds_label + '</span>' if beds_label else ''}
                </td>
                <td align="right">
                  <span style="font-size:12px;color:#757575;background:#ebebeb;padding:3px 8px;border-radius:4px;">{area_label}</span>
                </td>
              </tr>
            </table>
            <p style="font-size:14px;color:#1a1a1a;margin:6px 0 4px;line-height:1.4;">{address_line}</p>
            <p style="font-size:12px;color:#757575;margin:0 0 10px;">{meta_str}</p>
            <table cellpadding="0" cellspacing="4" style="margin-bottom:14px;">
              <tr>
                <td><span style="font-size:12px;font-weight:500;padding:3px 8px;border-radius:4px;{work_s}">Office {_ct_label(row['commute_work_mins'])}</span></td>
                <td><span style="font-size:12px;font-weight:500;padding:3px 8px;border-radius:4px;{lse_s}">LSE {_ct_label(row['commute_lse_mins'])}</span></td>
                <td><span style="font-size:12px;color:#9e9e9e;background:#f5f5f5;padding:3px 8px;border-radius:4px;">{platform_cap}</span></td>
              </tr>
            </table>
            <a href="{row['url']}" style="display:inline-block;font-size:13px;font-weight:500;color:#0066FF;text-decoration:none;border:1px solid #0066FF;border-radius:6px;padding:6px 14px;">View listing →</a>
          </td>
        </tr>"""

    overflow_html = ""
    if overflow > 0:
        overflow_html = f"""
        <tr>
          <td style="background:#ebebeb;padding:12px 24px;text-align:center;border-top:1px solid #e0e0e0;">
            <p style="margin:0;font-size:14px;color:#757575;">and {overflow} more — <a href="{APP_URL}" style="color:#0066FF;text-decoration:none;">view all in the app</a></p>
          </td>
        </tr>"""

    return f"""<!DOCTYPE html>
<html>
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>London Flat Hunt — {count_label}</title>
</head>
<body style="margin:0;padding:0;background:#f5f5f5;font-family:-apple-system,BlinkMacSystemFont,'Segoe UI',sans-serif;">
<table width="100%" cellpadding="0" cellspacing="0" style="background:#f5f5f5;">
  <tr>
    <td align="center" style="padding:24px 16px;">
      <table width="600" cellpadding="0" cellspacing="0" style="max-width:600px;width:100%;">
        <tr>
          <td style="background:#0066FF;border-radius:12px 12px 0 0;padding:20px 24px;">
            <h1 style="color:white;font-size:20px;font-weight:700;margin:0;letter-spacing:-0.3px;">London Flat Hunt</h1>
            <p style="color:rgba(255,255,255,0.85);font-size:14px;margin:4px 0 0;">{count_label} · {today_str}</p>
          </td>
        </tr>
        {cards_html}
        {overflow_html}
        <tr>
          <td style="background:#ebebeb;border-radius:0 0 12px 12px;padding:14px 24px;text-align:center;">
            <p style="margin:0;font-size:12px;color:#9e9e9e;">
              <a href="{APP_URL}" style="color:#0066FF;text-decoration:none;">Open app</a>
              &nbsp;·&nbsp;Photos may need one click to display in Gmail
            </p>
          </td>
        </tr>
      </table>
    </td>
  </tr>
</table>
</body>
</html>"""


def send_email(html: str, subject: str, cfg: dict) -> None:
    from_addr  = cfg["EMAIL_FROM"]
    to_addrs   = [a.strip() for a in cfg["EMAIL_TO"].split(",") if a.strip()]
    password   = cfg["GMAIL_APP_PASSWORD"]

    msg = MIMEMultipart("alternative")
    msg["Subject"] = subject
    msg["From"]    = from_addr
    msg["To"]      = ", ".join(to_addrs)
    msg.attach(MIMEText(html, "html", "utf-8"))

    with smtplib.SMTP("smtp.gmail.com", 587) as smtp:
        smtp.ehlo()
        smtp.starttls()
        smtp.login(from_addr, password)
        smtp.sendmail(from_addr, to_addrs, msg.as_string())


def main() -> None:
    ap = argparse.ArgumentParser(description="Daily digest of new rental listings")
    ap.add_argument("--scheduled", action="store_true",
                    help="Send via Gmail SMTP; without this flag, prints HTML preview to stdout")
    ap.add_argument("--since", type=int, default=24,
                    help="Look back N hours for new listings (default 24)")
    args = ap.parse_args()

    cfg  = config.load()
    conn = db.connect()
    rows = fetch_new_listings(conn, args.since)
    conn.close()

    total_new = len(rows)

    if total_new == 0 and args.scheduled:
        print("[digest] 0 new listings — skipping email", file=sys.stderr)
        return

    today_str   = datetime.now().strftime("%d %B %Y").lstrip("0")
    count_label = f"{total_new} new listing{'s' if total_new != 1 else ''}"
    subject     = f"London Flat Hunt — {count_label} · {today_str}"
    html        = build_html(rows, total_new)

    if args.scheduled:
        send_email(html, subject, cfg)
        print(f"[digest] sent to {cfg['EMAIL_TO']} — {count_label}", file=sys.stderr)
    else:
        sys.stdout.write(html)
        print(f"\n<!-- [digest] preview: {count_label} — would send: '{subject}' -->",
              file=sys.stderr)


if __name__ == "__main__":
    main()
