import contextlib
import csv
import logging
import re
from datetime import datetime, timedelta
from decimal import Decimal

import openpyxl
import PyPDF2
from django.conf import settings
from django.contrib.auth import get_user_model
from django.core.mail import send_mail
from django.db import models
from django.db import transaction as db_transaction

from .models import BankAccount, BankStatement, FinanceAuditLog, ReconciliationResult, Transaction

logger = logging.getLogger(__name__)


class ReconciliationService:
    @classmethod
    def reconcile(cls, statement_id, file_path, bank_account_id, user=None):  # noqa: ARG003
        statement = BankStatement.objects.get(id=statement_id)
        file_ext = file_path.lower().split(".")[-1]
        entries = []

        try:
            if file_ext == "pdf":
                entries = cls.parse_pdf(file_path)
            elif file_ext == "csv":
                entries = cls.parse_csv(file_path)
            elif file_ext in ["xlsx", "xls"]:
                entries = cls.parse_excel(file_path)

            if not entries:
                raise ValueError("No entries found in statement file or unsupported file format")

            return cls.process_entries(statement_id, entries, bank_account_id)
        except Exception as e:
            statement.status = "flagged"
            statement.save()
            raise e

    @classmethod
    def parse_pdf(cls, file_path):
        entries = []
        try:
            reader = PyPDF2.PdfReader(file_path)
            text = ""
            for page in reader.pages:
                text += page.extract_text() or ""

            # Clean up text: replace multiple spaces with single space
            cleaned_text = re.sub(r" +", " ", text)
            lines = [line.strip() for line in cleaned_text.split("\n") if line.strip()]

            date_regex = re.compile(r"^(\d{1,4}[-/\s][A-Za-z0-9]{2,3}[-/\s]\d{2,4})$")
            date_regex_lax = re.compile(r"(\d{1,4}[-/\s][A-Za-z0-9]{2,3}[-/\s]\d{2,4})")
            amount_regex = re.compile(r"(-?\$?\s?\d{1,3}(?:,\d{3})*(?:\.\d{2})?)")

            # 1. Try single-line horizontal parser
            for line in lines:
                date_match = date_regex_lax.search(line)
                amount_match = amount_regex.search(line)
                if date_match and amount_match and len(line) > 15:
                    amount_str = amount_match.group(1).replace("$", "").replace(",", "").replace(" ", "")
                    try:
                        amount = abs(float(amount_str))
                        if amount > 0:
                            normalized = cls.normalize_date(date_match.group(1))
                            line_lower = line.lower()
                            entry_type = (
                                "credit"
                                if any(kw in line_lower for kw in ["credit", "cr", "deposit", "dep"])
                                else "debit"
                            )
                            entries.append(
                                {"date": normalized, "amount": amount, "description": line[:200], "type": entry_type}
                            )
                    except ValueError:
                        continue

            # 2. Try multi-line vertical parser if no entries found
            if not entries:
                i = 0
                while i < len(lines):
                    date_match = date_regex.match(lines[i])
                    if date_match:
                        entry_date = cls.normalize_date(lines[i])
                        tx_id = None
                        desc_parts = []
                        numeric_vals = []

                        j = i + 1
                        # Consume lines until next date
                        while j < len(lines) and not date_regex.match(lines[j]):
                            line_val = lines[j].strip()
                            if line_val:
                                # Check if it looks like a transaction ID
                                if line_val.startswith("TX-") or (
                                    re.match(r"^[A-Za-z0-9]{8,20}$", line_val)
                                    and not line_val.replace(".", "", 1).isdigit()
                                ):
                                    tx_id = line_val
                                elif (
                                    line_val.replace(".", "", 1).isdigit()
                                    or line_val.replace("-", "").replace(".", "", 1).isdigit()
                                ):
                                    try:
                                        numeric_vals.append(abs(float(line_val.replace("$", "").replace(",", ""))))
                                    except ValueError:
                                        desc_parts.append(line_val)
                                else:
                                    # Skip header junk
                                    if not any(
                                        kw in line_val.lower()
                                        for kw in [
                                            "date",
                                            "balance",
                                            "description",
                                            "particulars",
                                            "narration",
                                            "withdrawal",
                                            "deposit",
                                            "debit",
                                            "credit",
                                            "account",
                                            "statement",
                                        ]
                                    ):
                                        desc_parts.append(line_val)
                            j += 1

                        # Extract amount
                        amount = None
                        if numeric_vals:
                            for val in numeric_vals:
                                if val > 0 and val < 10000000:
                                    amount = val
                                    break

                        desc = " ".join(desc_parts).strip()
                        desc_lower = desc.lower()
                        entry_type = (
                            "credit" if any(kw in desc_lower for kw in ["credit", "cr", "deposit", "dep"]) else "debit"
                        )

                        if amount is not None:
                            entries.append(
                                {
                                    "date": entry_date,
                                    "amount": amount,
                                    "description": desc or "Bank Transaction",
                                    "transaction_id": tx_id,
                                    "type": entry_type,
                                }
                            )
                        # Advance index
                        i = j - 1
                    i += 1
        except Exception as e:
            logger.warning(f"Parse error: {e}")

        return entries

    @classmethod
    def match_column(cls, headers, keywords):
        # Try exact matches first
        for kw in keywords:
            for idx, h in enumerate(headers):
                if h == kw:
                    return idx
        # Try substring matches, but prevent false positives
        for kw in keywords:
            for idx, h in enumerate(headers):
                if kw in h:
                    # Prevent matching date/ID/ref columns as amount columns
                    if kw in ["amount", "total", "value"] and any(
                        d in h for d in ["date", "dt", "id", "ref", "no", "chq"]
                    ):
                        continue
                    # Prevent matching ID columns as date columns
                    if kw in ["date", "value_dt", "tran_date"] and any(
                        d in h for d in ["id", "ref", "no", "chq", "sl"]
                    ):
                        continue
                    return idx
        return None

    @classmethod
    def parse_headers_and_rows(cls, raw_headers, data_rows):
        headers = [str(h).strip().lower().replace(" ", "_").replace("\n", "_") if h else "" for h in raw_headers]

        date_kws = ["transaction_date", "date", "value_date", "posted_date", "value_dt", "tran_date"]
        txid_kws = ["transaction_id", "tran_id", "ref_no", "chq_no", "cheque", "reference", "ref", "chq"]
        desc_kws = ["transaction_remarks", "remarks", "narration", "description", "particulars", "memo"]
        amount_kws = ["amount", "total", "value"]
        debit_kws = ["withdrawal", "debit", "dr_amt", "dr"]
        credit_kws = ["deposit", "credit", "cr_amt", "cr"]

        date_idx = cls.match_column(headers, date_kws)
        txid_idx = cls.match_column(headers, txid_kws)
        desc_idx = cls.match_column(headers, desc_kws)
        amount_idx = cls.match_column(headers, amount_kws)
        debit_idx = cls.match_column(headers, debit_kws)
        credit_idx = cls.match_column(headers, credit_kws)

        entries = []
        for row in data_rows:
            if not row or all(v is None or str(v).strip() == "" for v in row):
                continue

            # 1. Date
            entry_date = None
            if date_idx is not None and date_idx < len(row) and row[date_idx] is not None:
                val = row[date_idx]
                entry_date = val.strftime("%Y-%m-%d") if isinstance(val, datetime) else cls.normalize_date(str(val))

            if not entry_date:
                continue

            # 2. Transaction ID
            tx_id = None
            if txid_idx is not None and txid_idx < len(row) and row[txid_idx] is not None:
                tx_id = str(row[txid_idx]).strip()

            # 3. Description
            desc = ""
            if desc_idx is not None and desc_idx < len(row) and row[desc_idx] is not None:
                desc = str(row[desc_idx]).strip()

            # 4. Amount
            amount = 0.0
            amount_found = False

            # Try split columns first (debit/credit)
            debit_val = 0.0
            credit_val = 0.0
            debit_found = False
            credit_found = False

            if debit_idx is not None and debit_idx < len(row) and row[debit_idx] is not None:
                try:
                    d_str = str(row[debit_idx]).replace("$", "").replace(",", "").replace(" ", "").strip()
                    if d_str:
                        debit_val = abs(float(d_str))
                        debit_found = True
                except ValueError:
                    pass

            if credit_idx is not None and credit_idx < len(row) and row[credit_idx] is not None:
                try:
                    c_str = str(row[credit_idx]).replace("$", "").replace(",", "").replace(" ", "").strip()
                    if c_str:
                        credit_val = abs(float(c_str))
                        credit_found = True
                except ValueError:
                    pass

            entry_type = "debit"
            if debit_found or credit_found:
                amount = max(debit_val, credit_val)
                amount_found = True
                entry_type = "credit" if credit_val > debit_val else "debit"

            # If not found or amount is 0, fall back to single amount column
            if (
                (not amount_found or amount == 0.0)
                and amount_idx is not None
                and amount_idx < len(row)
                and row[amount_idx] is not None
            ):
                try:
                    a_str = str(row[amount_idx]).replace("$", "").replace(",", "").replace(" ", "").strip()
                    if a_str:
                        amount = abs(float(a_str))
                        amount_found = True
                        desc_lower = desc.lower() if desc else ""
                        if any(kw in desc_lower for kw in ["credit", "cr", "deposit", "dep"]):
                            entry_type = "credit"
                except ValueError:
                    pass

            if amount > 0:
                entries.append(
                    {
                        "date": entry_date,
                        "amount": amount,
                        "description": desc,
                        "transaction_id": tx_id,
                        "type": entry_type,
                    }
                )
        return entries

    @classmethod
    def parse_csv(cls, file_path):
        entries = []
        try:
            with open(file_path, encoding="utf-8-sig", errors="replace") as f:
                reader = csv.reader(f)
                raw_rows = list(reader)

            header_index = 0
            for i, row in enumerate(raw_rows[:15]):
                if any(
                    any(
                        kw in str(cell).lower()
                        for kw in [
                            "date",
                            "amount",
                            "transaction",
                            "narration",
                            "description",
                            "remarks",
                            "withdrawal",
                            "deposit",
                            "debit",
                            "credit",
                        ]
                    )
                    for cell in row
                    if cell
                ):
                    header_index = i
                    break

            headers = raw_rows[header_index]
            data_rows = raw_rows[header_index + 1 :]
            entries = cls.parse_headers_and_rows(headers, data_rows)
        except Exception as e:
            logger.warning(f"Parse error: {e}")
        return entries

    @classmethod
    def parse_excel(cls, file_path):
        entries = []
        try:
            wb = openpyxl.load_workbook(file_path, data_only=True)
            sheet = wb.active
            raw_rows = [list(row) for row in sheet.iter_rows(values_only=True)]

            header_index = 0
            for i, row in enumerate(raw_rows[:15]):
                if any(
                    isinstance(cell, str)
                    and any(
                        kw in cell.lower()
                        for kw in [
                            "date",
                            "amount",
                            "transaction",
                            "narration",
                            "description",
                            "remarks",
                            "withdrawal",
                            "deposit",
                            "debit",
                            "credit",
                        ]
                    )
                    for cell in row
                    if cell
                ):
                    header_index = i
                    break

            headers = raw_rows[header_index]
            data_rows = raw_rows[header_index + 1 :]
            entries = cls.parse_headers_and_rows(headers, data_rows)
        except Exception as e:
            logger.warning(f"Parse error: {e}")
        return entries

    @classmethod
    def normalize_date(cls, date_str):
        date_str = str(date_str).strip()
        for fmt in ("%Y-%m-%d", "%d/%m/%Y", "%m/%d/%Y", "%d-%m-%Y", "%Y/%m/%d", "%d %b %Y", "%d-%b-%Y"):
            try:
                return datetime.strptime(date_str, fmt).strftime("%Y-%m-%d")
            except ValueError:
                pass
        # Fallback to current date if parsing fails completely
        return datetime.now().strftime("%Y-%m-%d")

    @classmethod
    def process_entries(cls, statement_id, entries, bank_account_id):
        flagged_count = 0

        with db_transaction.atomic():
            statement = BankStatement.objects.get(id=statement_id)
            bank_acc = BankAccount.objects.get(id=bank_account_id)

            for entry in entries:
                matched_tx = None
                entry_type = entry.get("type", "debit")

                # 1. Match by Transaction ID (if present)
                tx_id = entry.get("transaction_id")
                if tx_id:
                    matched_tx = Transaction.objects.filter(
                        transaction_id=tx_id,
                        bank_account=bank_acc,
                        transaction_type=entry_type,
                        reconciliationresult__isnull=True,
                    ).first()

                # 2. Match by Amount & Date range (within 7 days)
                if not matched_tx and entry.get("amount") and entry.get("date"):
                    try:
                        entry_date = datetime.strptime(entry["date"], "%Y-%m-%d").date()
                    except ValueError:
                        entry_date = datetime.now().date()
                    min_date = entry_date - timedelta(days=7)
                    max_date = entry_date + timedelta(days=7)

                    matched_tx = Transaction.objects.filter(
                        bank_account=bank_acc,
                        amount=Decimal(str(entry["amount"])),
                        transaction_type=entry_type,
                        created_at__date__range=(min_date, max_date),
                        reconciliationresult__isnull=True,
                    ).first()

                # Verify if matched transaction is valid (credits don't require PR, debits require approved PR)
                is_valid_match = False
                if matched_tx:
                    if (
                        matched_tx.transaction_type == "credit"
                        or matched_tx.purchase_request
                        and matched_tx.purchase_request.status == "approved"
                    ):
                        is_valid_match = True
                    else:
                        is_valid_match = False

                match_status = "matched" if (matched_tx and is_valid_match) else "unrecognized"
                if not matched_tx or not is_valid_match:
                    flagged_count += 1
                    if matched_tx:
                        matched_tx.status = "flagged"
                        if matched_tx.transaction_type == "debit":
                            matched_tx.mismatch_reason = (
                                "Transaction lacks an approved purchase request from Superadmin"
                            )
                        else:
                            matched_tx.mismatch_reason = "Credit transaction unrecognized discrepancy"
                        matched_tx.save()

                # Create Reconciliation Result
                ReconciliationResult.objects.create(
                    bank_statement=statement,
                    transaction=matched_tx,
                    statement_entry_date=entry["date"],
                    statement_entry_amount=Decimal(str(entry["amount"])),
                    statement_entry_description=entry.get("description", ""),
                    match_status=match_status,
                    raw_data=entry,
                )

                if matched_tx and is_valid_match:
                    # Update transaction status
                    matched_tx.status = "completed"
                    matched_tx.save()

            # Handle system transactions not found in statement
            # Select start and end dates from entries
            entry_dates = []
            for e in entries:
                with contextlib.suppress(ValueError):
                    entry_dates.append(datetime.strptime(e["date"], "%Y-%m-%d").date())

            if entry_dates:
                start_date = min(entry_dates) - timedelta(days=3)
                end_date = max(entry_dates) + timedelta(days=3)
            else:
                start_date = datetime.now().date() - timedelta(days=30)
                end_date = datetime.now().date() + timedelta(days=3)

            # Query system transactions in the timeframe that aren't reconciled
            unmatched_txs = Transaction.objects.filter(
                bank_account=bank_acc, created_at__date__range=(start_date, end_date), reconciliationresult__isnull=True
            )

            for txn in unmatched_txs:
                txn.status = "flagged"
                txn.mismatch_reason = "Not found in bank statement"
                txn.save()

                raw_data = {
                    "date": txn.created_at.strftime("%Y-%m-%d"),
                    "amount": float(txn.amount),
                    "description": f"System transaction not found in bank statement: {txn.purchase_request.item_name if txn.purchase_request else 'No request details'}",
                    "transaction_id": txn.transaction_id,
                }

                # Save reconciliation result as mismatch
                ReconciliationResult.objects.create(
                    bank_statement=statement,
                    transaction=txn,
                    statement_entry_date=txn.created_at.date(),
                    statement_entry_amount=txn.amount,
                    statement_entry_description=f"System transaction: {txn.purchase_request.item_name if txn.purchase_request else 'Manual Ledger'}",
                    match_status="mismatch",
                    raw_data=raw_data,
                )
                flagged_count += 1

            # Balance verification
            statement_sum = sum(float(e["amount"]) for e in entries)
            system_sum = float(
                Transaction.objects.filter(
                    bank_account=bank_acc, created_at__date__range=(start_date, end_date)
                ).aggregate(total=models.Sum("amount"))["total"]
                or 0.0
            )

            balance_difference = abs(statement_sum - system_sum)
            has_balance_discrepancy = balance_difference > 0.01

            # Update statement status
            status = "flagged" if (flagged_count > 0 or has_balance_discrepancy) else "reconciled"
            statement.status = status
            statement.save()

            # Trigger immediate security alert if any flagged discrepancies exist
            if flagged_count > 0 or has_balance_discrepancy:
                # Log security flag in Audit Logs
                FinanceAuditLog.objects.create(
                    user=None,  # System
                    action="SECURITY_FLAG",
                    details=f"Reconciliation Flagged on {bank_acc.bank_name}. Mismatches: {flagged_count}. Balance Diff: {balance_difference:.2f}",
                )
                cls.send_alert_email(bank_acc, flagged_count, balance_difference, statement_sum, system_sum, user=None)

        return {
            "total": len(entries),
            "matched": len(entries) - flagged_count,
            "flagged": flagged_count,
        }

    @classmethod
    def send_alert_email(cls, bank_account, flagged_count, balance_diff, stmt_sum, sys_sum, user=None):
        User = get_user_model()
        recipients = User.objects.filter(models.Q(is_superuser=True) | models.Q(role="SUPERADMIN"))
        recipient_list = list({u.email for u in recipients if u.email})
        if user and user.email and user.email not in recipient_list:
            recipient_list.append(user.email)

        if recipient_list:
            subject = "⚠️ IMMEDIATE SECURITY ALERT: Bank Reconciliation Discrepancy"
            message_html = f"""
            <div style="font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif; max-width: 650px; margin: 0 auto; padding: 24px; border: 2px solid #dc2626; border-radius: 12px;">
                <div style="text-align: center; margin-bottom: 20px;">
                    <span style="font-size: 40px;">⚠️</span>
                    <h2 style="color: #dc2626; margin: 10px 0 5px 0; font-size: 24px; font-weight: 800;">SECURITY AUDIT FLAG DETECTED</h2>
                    <p style="color: #4b5563; font-size: 14px; margin: 0;">Reconciliation mismatch identified on uploaded bank statement.</p>
                </div>
                <div style="background-color: #fef2f2; padding: 18px; border-radius: 8px; border-left: 6px solid #ef4444; margin-bottom: 24px;">
                    <h3 style="color: #991b1b; margin: 0 0 10px 0; font-size: 16px;">Audit Target Information</h3>
                    <table style="width: 100%; font-size: 14px; color: #1f2937;">
                        <tr><td><strong>Bank Name:</strong></td><td>{bank_account.bank_name}</td></tr>
                        <tr><td><strong>Account Number:</strong></td><td>{bank_account.account_number}</td></tr>
                        <tr><td><strong>Total Flagged Mismatches:</strong></td><td style="color: #ef4444; font-weight: bold;">{flagged_count}</td></tr>
                    </table>
                </div>
                <div style="background-color: #fffbeb; padding: 18px; border-radius: 8px; border-left: 6px solid #f59e0b; margin-bottom: 24px;">
                    <h3 style="color: #92400e; margin: 0 0 10px 0; font-size: 16px;">💰 Bank Balance Discrepancy</h3>
                    <table style="width: 100%; font-size: 14px; color: #1f2937;">
                        <tr><td><strong>Statement Total:</strong></td><td>${stmt_sum:,.2f}</td></tr>
                        <tr><td><strong>System Total (Expected):</strong></td><td>${sys_sum:,.2f}</td></tr>
                        <tr style="border-top: 1px solid #f3f4f6;"><td style="color: #b45309; font-weight: bold;">Variance:</td><td style="color: #b45309; font-weight: bold;">${balance_diff:,.2f}</td></tr>
                    </table>
                </div>
                <p style="color: #374151; font-size: 15px; line-height: 1.6;">
                    <strong>Required Action:</strong> Please log into the Finance Portal and submit a formal explanation detailing the reasons for this discrepancy.
                </p>
            </div>
            """

            send_mail(
                subject=subject,
                message=f"Reconciliation detected {flagged_count} mismatches on bank {bank_account.bank_name}. Variance: ${balance_diff:.2f}",
                from_email=settings.DEFAULT_FROM_EMAIL,
                recipient_list=recipient_list,
                html_message=message_html,
                fail_silently=True,
            )
