# Omni Search Engine - Documentazione & Overview

**Descrizione**
Motore di ricerca semantico "Agent-First" progettato specificamente per Obsidian. Utilizza OpenAI embeddings, ChromaDB e FastMCP per trasformare il vault statico in una knowledge base dinamica e interrogabile via linguaggio naturale.

---

## Stato del Progetto

*   **Core Architecture**: Refactoring a micro-servizi **COMPLETATO**. Struttura modulare (Services, Repositories, API) pronta per lo scale-up.
*   **Infrastruttura**: Supporto Docker/Podman **ATTIVO** con volumi persistenti.
*   **Stabilità**: Sistema di logging strutturato e gestione lifecycle asincrona **OPERATIVI**.

## Funzionalità Attive (v0.0.1)

*   🔍 **Semantic Search**: Ricerca vettoriale su tutto il vault. Chunking intelligente che preserva la struttura Markdown (header, tabelle, blocchi di codice).
*   🔗 **Smart Link Suggestions**: Analisi di similarità per suggerire connessioni pertinenti tra le note (con deduplicazione nativa).
*   ⚡ **Auto-Indexing**: Watcher file system con debounce coalescente. Rileva modifiche e aggiorna l'indice in tempo reale senza intervento manuale.
*   💾 **Efficienza**: Hashing dei contenuti (SHA256) per evitare chiamate API ridondanti su file non modificati.
*   🛠️ **Strumenti di Diagnostica**: Suite completa per ispezione indice (`get_index_stats`) e struttura vault (`get_vault_structure`).

## Stack Tecnico

*   **Backend**: Python 3.13 (Asyncio/FastAPI patterns).
*   **Vector Store**: ChromaDB (Locale, Privacy-first).
*   **Interface**: FastMCP (Integrazione nativa Claude Desktop).
*   **Embeddings**: OpenAI `text-embedding-3-small`.

## Prossimi Step (Roadmap Phase 2)

*   [ ] **Analytics Tools**: Identificazione note orfane e contenuti duplicati.
*   [ ] **Reranking**: Miglioramento precisione search con second-pass ranking.
*   [ ] **Multi-Vault**: Supporto per indicizzazione contestuale di più knowledge base.
