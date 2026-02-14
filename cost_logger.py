# LOCAL SCRIPT for testing purpose: cost_logger.py
# Place in your project root and run: python cost_logger.py

import sys
import json
import pandas as pd
from datetime import datetime
from typing import List, Tuple, Optional

# Import from existing codebase
from config import CHAT_MODEL, EMBEDDING_MODEL, TOP_K, SUPABASE_URL, SUPABASE_SERVICE_ROLE_KEY
from constants import SYSTEM_PROMPT, MAX_HISTORY_TURNS
from rag_service import rag_service
from chat_service import chat_service
from langchain_openai import ChatOpenAI
from langchain_core.messages import HumanMessage, SystemMessage

# OpenAI pricing per 1M tokens
OPENAI_PRICING = {
    "gpt-4o": {"input": 5.00, "output": 15.00},
    "gpt-4o-latest": {"input": 5.00, "output": 15.00},
    "gpt-4-turbo-2024-04-09": {"input": 10.00, "output": 30.00},
    "gpt-3.5-turbo": {"input": 0.50, "output": 1.50},
}

call_logs = []

def count_tokens(text):
    """Rough token estimation: ~4 chars per token"""
    return max(1, len(text) // 4)

def calculate_costs(system_content, rag_context, question, gpt_response):
    """Calculate API costs using actual final prompt structure"""
    
    full_input = f"{system_content}\n\nQuestion: {question}"
    
    input_tokens = count_tokens(full_input)
    output_tokens = count_tokens(gpt_response)
    embedding_tokens = count_tokens(rag_context)
    
    model = CHAT_MODEL
    if model not in OPENAI_PRICING:
        model = "gpt-4o"
    
    input_cost = (input_tokens / 1_000_000) * OPENAI_PRICING[model]["input"]
    output_cost = (output_tokens / 1_000_000) * OPENAI_PRICING[model]["output"]
    embed_cost = (embedding_tokens / 1_000_000) * 0.02
    
    total = input_cost + output_cost + embed_cost
    
    return {
        "input_tokens": input_tokens,
        "output_tokens": output_tokens,
        "embedding_tokens": embedding_tokens,
        "input_cost": round(input_cost, 8),
        "output_cost": round(output_cost, 8),
        "embedding_cost": round(embed_cost, 8),
        "total_cost": round(total, 8)
    }

def process_and_log_query(query: str, conversation_history: Optional[List[Tuple[str, str]]] = None, top_k: int = TOP_K, call_gpt: bool = True):
    """
    Process user query:
    1. Perform RAG search
    2. Build final system prompt
    3. Call GPT (if call_gpt=True) or use dummy response
    4. Log costs
    
    Args:
        query: User question
        conversation_history: Previous conversation turns
        top_k: Number of RAG results
        call_gpt: Whether to actually call GPT API (True) or use dummy response (False)
    """
    
    # Step 1: RAG Search
    print(f"\n🔍 Searching RAG for: {query}")
    search_results = rag_service.search_common_knowledge(query, top_k)
    
    if not search_results:
        rag_context = "[No documents found in knowledge base]"
        document_names = []
    else:
        context_parts = []
        document_names = []
        
        for chunk, source, similarity, metadata in search_results:
            document_name = source if source != 'Unknown' else metadata.get('file_name', 'Unknown Document')
            context_part = f"[Document: {document_name}]\n{chunk}"
            context_parts.append(context_part)
            if document_name not in document_names:
                document_names.append(document_name)
        
        rag_context = "\n\n".join(context_parts)
    
    print(f"✅ Found {len(document_names)} documents")
    
    # Step 2: Build system content
    history_context = ""
    if conversation_history:
        recent_history = conversation_history[-MAX_HISTORY_TURNS:] if len(conversation_history) > MAX_HISTORY_TURNS else conversation_history
        history_parts = []
        for user_msg, assistant_msg in recent_history:
            history_parts.append(f"User: {user_msg}")
            history_parts.append(f"Assistant: {assistant_msg}")
        history_context = "\n".join(history_parts)
    
    system_content = f"""{SYSTEM_PROMPT}

CONVERSATION HISTORY:
{history_context}

AVAILABLE DOCUMENTS FOR CITATION: {', '.join(document_names) if document_names else 'None'}

CONTEXT FROM DOCUMENTS:
{rag_context}

REMEMBER: You MUST start your response with source citations like "Based on [Document Name] and [Document Name]..." and continue citing sources throughout your response."""
    
    # Step 3: Call GPT or use dummy response
    if call_gpt:
        print(f"📤 Calling {CHAT_MODEL}...")
        try:
            chat_model = ChatOpenAI(
                api_key=sys.argv[1] if len(sys.argv) > 1 else None,  # Pass OPENAI_API_KEY as arg
                model=CHAT_MODEL
            )
            
            messages = [
                SystemMessage(content=system_content),
                HumanMessage(content=query)
            ]
            
            response = chat_model.invoke(messages)
            gpt_response = response.content
        except Exception as e:
            print(f"⚠️  GPT call failed ({e}), using dummy response for cost calculation")
            gpt_response = f"[Dummy response - estimated output for cost calculation]"
    else:
        print(f"⏭️  Skipping GPT call, using dummy response for cost estimation")
        gpt_response = f"[Dummy response - estimated output for cost calculation]"
    
    # Step 4: Calculate costs
    costs = calculate_costs(system_content, rag_context, query, gpt_response)
    
    log_entry = {
        "timestamp": datetime.now().isoformat(),
        "query": query,
        "documents_cited": len(document_names),
        "document_names": document_names,
        "system_prompt_chars": len(system_content),
        "rag_context_chars": len(rag_context),
        "response_chars": len(gpt_response),
        "top_k_retrieved": top_k,
        "results_found": len(search_results),
        "has_history": bool(conversation_history and len(conversation_history) > 0),
        "model": CHAT_MODEL,
        "embedding_model": EMBEDDING_MODEL,
        **costs
    }
    
    call_logs.append(log_entry)
    
    return log_entry, system_content, rag_context, gpt_response

def print_breakdown(log_entry, query, system_content, rag_context, gpt_response):
    """Pretty print cost breakdown"""
    print("\n" + "="*80)
    print(f"🤖 API CALL LOGGED: {log_entry['timestamp']}")
    print("="*80)
    
    print(f"\n❓ QUERY:")
    print(f"   {query}")
    
    if log_entry['document_names']:
        print(f"\n📄 DOCUMENTS CITED: {len(log_entry['document_names'])}")
        for doc in log_entry['document_names']:
            print(f"   - {doc}")
    else:
        print(f"\n📄 DOCUMENTS CITED: None")
    
    print(f"\n📚 RAG CONTEXT ({log_entry['rag_context_chars']} chars, {log_entry['results_found']} results):")
    context_preview = rag_context[:500] + "..." if len(rag_context) > 500 else rag_context
    print(f"   {context_preview}")
    
    print(f"\n💬 FINAL SYSTEM PROMPT ({log_entry['system_prompt_chars']} chars):")
    prompt_preview = system_content[:500] + "..." if len(system_content) > 500 else system_content
    print(f"   {prompt_preview}")
    
    print(f"\n📝 RESPONSE ({log_entry['response_chars']} chars):")
    response_preview = gpt_response[:500] + "..." if len(gpt_response) > 500 else gpt_response
    print(f"   {response_preview}")
    
    print(f"\n📊 TOKEN BREAKDOWN:")
    print(f"   Input Tokens (system + context + query): {log_entry['input_tokens']:,}")
    print(f"   Output Tokens (response): {log_entry['output_tokens']:,}")
    print(f"   Embedding Tokens (RAG search): {log_entry['embedding_tokens']:,}")
    print(f"   Total Tokens: {log_entry['input_tokens'] + log_entry['output_tokens'] + log_entry['embedding_tokens']:,}")
    
    print(f"\n💰 COST BREAKDOWN:")
    print(f"   Chat Input Cost: ${log_entry['input_cost']:.8f}")
    print(f"   Chat Output Cost: ${log_entry['output_cost']:.8f}")
    print(f"   Embedding Cost (RAG): ${log_entry['embedding_cost']:.8f}")
    print(f"   {'─'*40}")
    print(f"   💵 TOTAL CALL COST: ${log_entry['total_cost']:.8f}")
    
    print(f"\n⚙️ CONFIGURATION:")
    print(f"   Model: {log_entry['model']}")
    print(f"   Embedding: {log_entry['embedding_model']}")
    print(f"   Has Conversation History: {log_entry['has_history']}")
    print("="*80 + "\n")

def get_stats(df=None):
    """Get statistics from logs"""
    if df is None:
        if not call_logs:
            return {"message": "No logs yet"}
        df = pd.DataFrame(call_logs)
    
    if len(df) == 0:
        return {"message": "No logs yet"}
    
    stats = {
        "total_calls": len(df),
        "total_cost": round(df["total_cost"].sum(), 8),
        "avg_cost_per_call": round(df["total_cost"].mean(), 8),
        "min_cost_per_call": round(df["total_cost"].min(), 8),
        "max_cost_per_call": round(df["total_cost"].max(), 8),
        "avg_input_tokens": round(df["input_tokens"].mean(), 0),
        "avg_output_tokens": round(df["output_tokens"].mean(), 0),
        "total_tokens": int(df["input_tokens"].sum() + df["output_tokens"].sum()),
        "avg_documents_cited": round(df["documents_cited"].mean(), 1),
        "cost_breakdown": {
            "chat_input_total": round(df["input_cost"].sum(), 8),
            "chat_output_total": round(df["output_cost"].sum(), 8),
            "embedding_total": round(df["embedding_cost"].sum(), 8),
        }
    }
    
    return stats

def forecast_budget(daily_call_volume, days=30):
    """Forecast costs based on average call costs and daily volume"""
    
    if not call_logs:
        return {"message": "No historical data to forecast"}
    
    df = pd.DataFrame(call_logs)
    avg_cost = df["total_cost"].mean()
    daily_cost = daily_call_volume * avg_cost
    
    forecast = {
        "daily_volume": daily_call_volume,
        "avg_cost_per_call": round(avg_cost, 8),
        "daily_cost": round(daily_cost, 8),
        "weekly_cost": round(daily_cost * 7, 8),
        "monthly_cost": round(daily_cost * 30, 8),
        "forecast_period_days": days,
        "forecast_period_cost": round(daily_cost * days, 8)
    }
    
    return forecast

def save_logs(filename="sevabot_call_logs.json"):
    """Save logs to JSON file"""
    try:
        with open(filename, "a") as f:
            for log in call_logs:
                json.dump(log, f)
                f.write("\n")
        print(f"\n✅ Logs saved to {filename}")
    except Exception as e:
        print(f"❌ Error saving logs: {e}")

def auto_save_log(log_entry, filename="sevabot_call_logs.json"):
    """Auto-save individual log entry to file immediately after query"""
    try:
        with open(filename, "a") as f:
            json.dump(log_entry, f)
            f.write("\n")
    except Exception as e:
        print(f"⚠️  Warning: Could not auto-save log: {e}")

def get_dataframe():
    """Return logs as pandas DataFrame"""
    if not call_logs:
        return pd.DataFrame()
    return pd.DataFrame(call_logs)

# ============================================================================
# MAIN USAGE - Interactive Mode
# ============================================================================

if __name__ == "__main__":
    print("🤖 Sevabot Cost Logger - Interactive Mode")
    print(f"   Model: {CHAT_MODEL}")
    print(f"   Embedding: {EMBEDDING_MODEL}")
    print(f"   Top-K Retrieval: {TOP_K}\n")
    
    conversation_history = []
    
    while True:
        print("\n" + "─"*80)
        query = input("❓ Enter your question (or 'stats', 'forecast', 'save', 'quit'): ").strip()
        
        if query.lower() == 'quit':
            print("\n👋 Exiting...")
            break
        elif query.lower() == 'stats':
            print("\n📈 STATISTICS:")
            stats = get_stats()
            for key, val in stats.items():
                if key != "cost_breakdown":
                    print(f"   {key}: {val}")
            if "cost_breakdown" in stats:
                print(f"\n   Cost Breakdown:")
                for key, val in stats["cost_breakdown"].items():
                    print(f"      {key}: ${val}")
            continue
        elif query.lower() == 'forecast':
            print("\n💹 BUDGET FORECAST (100 calls/day for 30 days):")
            forecast = forecast_budget(daily_call_volume=100, days=30)
            for key, val in forecast.items():
                print(f"   {key}: {val}")
            continue
        elif query.lower() == 'save':
            save_logs("sevabot_call_logs.json")
            continue
        
        if not query:
            print("⚠️  Please enter a question")
            continue
        
        # Process query with RAG and calculate costs
        log_entry, system_content, rag_context, gpt_response = process_and_log_query(
            query, 
            conversation_history=conversation_history if conversation_history else None,
            call_gpt=True  # Set to False to skip actual GPT calls, True to call GPT (requires OPENAI_API_KEY)
        )
        
        # Print breakdown
        print_breakdown(log_entry, query, system_content, rag_context, gpt_response)
        
        # Auto-save log immediately
        auto_save_log(log_entry, filename="sevabot_call_logs.json")
        
        # Add to conversation history
        conversation_history.append((query, gpt_response))
        
        # Keep history within limits
        if len(conversation_history) > MAX_HISTORY_TURNS:
            conversation_history = conversation_history[-MAX_HISTORY_TURNS:]