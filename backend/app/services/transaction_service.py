from sqlalchemy.orm import Session
from datetime import datetime
from decimal import Decimal
from uuid import uuid4

from app.db.models import Transaction, Account
# Use TransactionStatusEnum from db.schemas only to avoid import conflict with app.schemas
from app.db.schemas import TransactionStatusEnum
from app.exceptions import AccountNotFound
from app.schemas import TransactionCreate


class TransactionService:

    @staticmethod
    def create_transaction(transaction_data: TransactionCreate, db: Session):
        """
        Create a new transaction after validating balance and account existence.
        Records a FAILED transaction if balance is insufficient instead of raising.
        """
        sender_account = db.query(Account).filter(
            Account.account_number == transaction_data.account_number
        ).first()

        if not sender_account:
            raise AccountNotFound(
                f"Sender account with number {transaction_data.account_number} not found."
            )

        if not sender_account.is_active:
            raise AccountNotFound(
                f"Sender account {transaction_data.account_number} is inactive."
            )

        if sender_account.balance < transaction_data.amount:
            failed_tx = Transaction(
                transaction_id=uuid4(),
                from_account_id=sender_account.account_id,
                to_account_number=transaction_data.to_account_number,
                amount=transaction_data.amount,
                status=TransactionStatusEnum.failed.value,
                reference_id=str(uuid4()),
                message_metadata={"reason": "Insufficient balance"},
                created_at=datetime.utcnow(),
            )
            db.add(failed_tx)
            db.commit()
            db.refresh(failed_tx)
            return failed_tx

        sender_account.balance -= transaction_data.amount

        completed_tx = Transaction(
            transaction_id=uuid4(),
            from_account_id=sender_account.account_id,
            to_account_number=transaction_data.to_account_number,
            amount=transaction_data.amount,
            status=TransactionStatusEnum.completed.value,
            reference_id=str(uuid4()),
            message_metadata=transaction_data.message_metadata,
            created_at=datetime.utcnow(),
        )
        db.add(completed_tx)
        db.commit()
        db.refresh(completed_tx)
        return completed_tx

    @staticmethod
    def get_transaction_by_id(transaction_id: str, db: Session):
        """
        Retrieve a transaction by its ID.
        """
        transaction = db.query(Transaction).filter(
            Transaction.transaction_id == transaction_id
        ).first()
        if not transaction:
            raise ValueError(f"Transaction with ID {transaction_id} not found.")
        return transaction

    @staticmethod
    def list_transactions_by_account(account_number: str, db: Session):
        """
        List all transactions from a given account.
        """
        account = db.query(Account).filter(
            Account.account_number == account_number
        ).first()

        if not account:
            raise ValueError(f"Account with number {account_number} not found.")

        transactions = db.query(Transaction).filter(
            Transaction.from_account_id == account.account_id
        ).all()
        return transactions