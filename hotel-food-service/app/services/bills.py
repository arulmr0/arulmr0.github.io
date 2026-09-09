"""Guest bills: a structured document plus a printable HTML rendering."""

import html
from datetime import datetime

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.config import get_settings
from app.core.money import to_major
from app.models.base import utcnow
from app.models.reservation import Reservation
from app.schemas.bill import BillLine, BillPayment, BillRead
from app.services.orders import get_order


def build_bill(db: Session, order_id: int) -> BillRead:
    order = get_order(db, order_id)
    settings = get_settings()
    reservation = db.scalar(select(Reservation).where(Reservation.order_id == order.id))
    paid = sum(p.amount_minor for p in order.payments)
    return BillRead(
        business_name=settings.business_name,
        business_address=settings.business_address,
        tax_id=settings.tax_id,
        currency=settings.currency,
        bill_number=order.number,
        order_type=order.order_type,
        location=order.location,
        status=order.status,
        issued_at=order.closed_at or utcnow(),
        guest_name=reservation.guest_name if reservation else None,
        lines=[
            BillLine(
                description=line.menu_item.name,
                quantity=line.quantity,
                unit_price_minor=line.unit_price_minor,
                line_total_minor=line.line_total_minor,
            )
            for line in order.lines
        ],
        subtotal_minor=order.subtotal_minor,
        tax_rate_percent=settings.tax_rate_percent,
        tax_minor=order.tax_minor,
        total_minor=order.total_minor,
        payments=[
            BillPayment(method=p.method, amount_minor=p.amount_minor, paid_at=p.paid_at)
            for p in order.payments
        ],
        paid_minor=paid,
        balance_due_minor=max(order.total_minor - paid, 0),
        footer=settings.bill_footer,
    )


def render_html(bill: BillRead) -> str:
    """Printable bill sized for an 80 mm receipt printer; also fine on A4."""
    e = html.escape
    money = lambda minor: f"{to_major(minor):,.2f}"  # noqa: E731
    fmt = lambda dt: datetime.strftime(dt, "%d %b %Y %H:%M")  # noqa: E731

    lines = "".join(
        f"<tr><td>{e(line.description)}</td><td class='n'>{line.quantity}</td>"
        f"<td class='n'>{money(line.unit_price_minor)}</td>"
        f"<td class='n'>{money(line.line_total_minor)}</td></tr>"
        for line in bill.lines
    )
    payments = "".join(
        f"<tr><td colspan='3'>Paid by {e(p.method.value.replace('_', ' '))} "
        f"<span class='muted'>{fmt(p.paid_at)}</span></td>"
        f"<td class='n'>{money(p.amount_minor)}</td></tr>"
        for p in bill.payments
    )
    where = f"{e(bill.order_type.value.replace('_', ' ').title())}"
    if bill.location:
        where += f" &middot; {e(bill.location)}"
    stamp = (
        "<div class='stamp paid'>PAID</div>"
        if bill.balance_due_minor == 0 and bill.paid_minor > 0
        else f"<div class='stamp due'>BALANCE DUE {e(bill.currency)} {money(bill.balance_due_minor)}</div>"
    )
    optional = "".join(
        f"<div class='muted'>{e(v)}</div>"
        for v in (bill.business_address, f"Tax ID: {bill.tax_id}" if bill.tax_id else None)
        if v
    )
    guest = f"<div>Guest: {e(bill.guest_name)}</div>" if bill.guest_name else ""
    footer = f"<p class='footer'>{e(bill.footer)}</p>" if bill.footer else ""

    return f"""<!doctype html>
<html lang="en"><head><meta charset="utf-8">
<title>Bill {e(bill.bill_number)}</title>
<style>
  body {{ font: 13px/1.4 "Courier New", monospace; color: #000; margin: 0; padding: 12px; }}
  .bill {{ max-width: 80mm; margin: 0 auto; }}
  h1 {{ font-size: 16px; text-align: center; margin: 0 0 4px; }}
  .center {{ text-align: center; }} .muted {{ color: #444; font-size: 12px; }}
  table {{ width: 100%; border-collapse: collapse; margin-top: 8px; }}
  th, td {{ padding: 3px 2px; vertical-align: top; }}
  th {{ text-align: left; border-bottom: 1px dashed #000; font-size: 12px; }}
  td.n, th.n {{ text-align: right; white-space: nowrap; }}
  tr.total td {{ border-top: 1px dashed #000; font-weight: bold; }}
  .stamp {{ text-align: center; font-weight: bold; margin: 10px 0; padding: 6px; border: 2px solid #000; }}
  .footer {{ text-align: center; margin-top: 12px; }}
  .noprint {{ text-align: center; margin: 14px 0; }}
  @media print {{ .noprint {{ display: none; }} body {{ padding: 0; }} }}
</style></head><body>
<div class="bill">
  <h1>{e(bill.business_name)}</h1>
  <div class="center">{optional}</div>
  <table>
    <tr><td>Bill no.</td><td class="n">{e(bill.bill_number)}</td></tr>
    <tr><td>Date</td><td class="n">{fmt(bill.issued_at)}</td></tr>
    <tr><td>{where}</td><td class="n">{e(bill.status.value.replace("_", " "))}</td></tr>
  </table>
  {guest}
  <table>
    <thead><tr><th>Item</th><th class="n">Qty</th><th class="n">Rate</th><th class="n">Amount</th></tr></thead>
    <tbody>{lines}</tbody>
    <tfoot>
      <tr><td colspan="3">Subtotal</td><td class="n">{money(bill.subtotal_minor)}</td></tr>
      <tr><td colspan="3">Tax {bill.tax_rate_percent:g}%</td><td class="n">{money(bill.tax_minor)}</td></tr>
      <tr class="total"><td colspan="3">TOTAL ({e(bill.currency)})</td><td class="n">{money(bill.total_minor)}</td></tr>
      {payments}
    </tfoot>
  </table>
  {stamp}
  {footer}
  <div class="noprint"><button onclick="window.print()">Print</button></div>
</div>
</body></html>"""
