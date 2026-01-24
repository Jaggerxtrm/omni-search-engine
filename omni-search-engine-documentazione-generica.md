# Omni Search Engine - Documentazione & Overview

**Descrizione**
Motore di ricerca semantico "Agent-First" progettato specificamente per Obsidian. Utilizza OpenAI embeddings, ChromaDB e FastMCP per trasformare il vault statico in una knowledge base dinamica e interrogabile via linguaggio naturale.

---

## Stato del Progetto

*   **Core Architecture**: Refactoring a micro-servizi **COMPLETATO**. Struttura modulare (Services, Repositories, API) pronta per lo scale-up.
*   **Infrastruttura**: Supporto Docker/Podman **ATTIVO** con volumi persistenti.
*   **Stabilità**: Sistema di logging strutturato e gestione lifecycle asincrona **OPERATIVI**.

## Funzionalità Attive (v0.0.2)
 
 *   🔍 **Semantic Search (+ Reranking)**: Ricerca vettoriale con Hybrid Search (Embeddings + FlashRank Local Reranking) per massima precisione.
 *   📊 **Analytics**: Strumenti per identificare note orfane, contenuti duplicati e concetti chiave (`most_linked`).
 *   🔗 **Smart Link Suggestions**: Analisi di similarità per suggerire connessioni pertinenti tra le note (con deduplicazione nativa).
 *   ⚡ **Auto-Indexing**: Watcher file system con debounce coalescente. Rileva modifiche (e spostamenti offline) e aggiorna l'indice in tempo reale.
 *   💾 **Efficienza**: Hashing dei contenuti (SHA256) per evitare chiamate API ridondanti su file non modificati.
 *   🛠️ **Strumenti di Diagnostica**: Suite completa per ispezione indice (`get_index_stats`) e struttura vault (`get_vault_structure`).
 
 ## Stack Tecnico
 
 *   **Backend**: Python 3.13 (Asyncio/FastAPI patterns).
 *   **Vector Store**: ChromaDB (Locale, Privacy-first).
 *   **Reranking**: FlashRank (On-device, No-GPU req).
 *   **Interface**: FastMCP (Integrazione nativa Claude Desktop).
 *   **Embeddings**: OpenAI `text-embedding-3-small`.
 
 ## Prossimi Step (Roadmap Phase 2)
 
 *   [x] **Analytics Tools**: Identificazione note orfane e contenuti duplicati.
 *   [x] **Reranking**: Miglioramento precisione search con second-pass ranking.
 *   [ ] **Multi-Vault**: Supporto per indicizzazione contestuale di più knowledge base.
