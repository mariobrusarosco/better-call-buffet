from fastapi import APIRouter

# Note: Invoice creation and retrieval has been moved to the credit cards router
# following RESTful nested resource design patterns:
# - POST /api/v1/credit_cards/{id}/invoices (create invoice for specific credit card)
# - GET  /api/v1/credit_cards/{id}/invoices (list invoices for specific credit card)

router = APIRouter()
