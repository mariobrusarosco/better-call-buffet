"""Prompts for financial document parsing"""


def get_financial_parsing_prompt(document_type: str = "statement", language: str = "pt") -> str:
    """Get system prompt for financial document parsing"""
    
    if language == "pt":
        return """
Você é um assistente financeiro. Um usuário forneceu um extrato de cartão de crédito Nubank (em português).
Sua tarefa é extrair as informações necessárias do extrato e retorná-las em um formato JSON estruturado.
Concentre-se em extrair apenas os dados financeiros relevantes e ignore qualquer texto padrão ou isenções de responsabilidade.

A resposta deve ser um objeto JSON válido com a seguinte estrutura:
{
  "total_due": string,       // O valor total devido no extrato do cartão de crédito
  "due_date": string,       // A data de vencimento para pagamento do extrato
  "period": string,         // O período de faturamento do extrato
  "min_payment": string,    // O valor mínimo de pagamento exigido
  "installment_options": [  // Opções de pagamento parcelado disponíveis
    {
      "months": number,     // Número de meses para a opção de parcelamento
      "total": string      // Valor total para esta opção de parcelamento
    }
  ],
  "transactions": [        // Lista de transações no extrato
    {
      "date": string,     // Data da transação
      "description": string, // Descrição da transação
      "amount": string,    // Valor da transação
      "category": string  // String vazia se nenhuma categoria for encontrada
    }
  ],
  "next_due_info": {      // Opcional: Informações sobre o próximo vencimento
    "amount": string,     // Próximo valor devido
    "balance": string     // Saldo atual
  }
}

Todos os valores e valores monetários devem ser retornados como strings.
As datas devem estar em um formato consistente.
"""
    else:
        return """
You are a financial assistant. A user has provided a credit card statement.
Your task is to extract the required information from the statement and return it in a structured JSON format.
Focus on extracting only the relevant financial data and ignore any boilerplate text or disclaimers.

The response should be a valid JSON object with the following structure:
{
  "total_due": string,       // The total amount due on the credit card statement
  "due_date": string,       // The payment due date for the statement
  "period": string,         // The billing period of the statement
  "min_payment": string,    // The minimum payment amount required
  "installment_options": [  // Available installment payment options
    {
      "months": number,     // Number of months for the installment option
      "total": string      // Total amount for this installment option
    }
  ],
  "transactions": [        // List of transactions in the statement
    {
      "date": string,     // Date of the transaction
      "description": string, // Description of the transaction
      "amount": string,    // Amount of the transaction
      "category": string  // Empty string if no category is found
    }
  ],
  "next_due_info": {      // Optional: Information about the next payment due
    "amount": string,     // Next payment amount due
    "balance": string     // Current balance
  }
}

All amounts and monetary values should be returned as strings.
Dates should be in a consistent format.
"""


def get_invoice_parsing_prompt(language: str = "pt") -> str:
    """Get system prompt for invoice parsing"""
    return get_financial_parsing_prompt("invoice", language)


def get_statement_parsing_prompt(language: str = "pt") -> str:
    """Get system prompt for statement parsing"""
    return get_financial_parsing_prompt("statement", language)