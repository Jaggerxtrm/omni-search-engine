# Handoff: Configurazione Dotfiles (Bare Git Repository)

**Stato Corrente:** 
Abbiamo discusso la teoria per trasformare la home directory (`/home/dawid`) in un repository Git utilizzando l'approccio "Bare Repository". L'utente vuole procedere in modo interattivo, passo dopo passo, analizzando cartella per cartella.

**Obiettivo:** 
Sincronizzare configurazioni tra laptop e desktop in modo sicuro ed elegante.

**Strategia:**
1. Creare cartella `.cfg` (git dir).
2. Configurare alias `config`.
3. Nascondere file non tracciati.
4. **CRUCIALE:** Configurare `.gitignore` PRIMA di aggiungere qualsiasi file.

## Piano d'Azione Interattivo (Da eseguire alla ripresa)

### Fase 1: Fondamenta e Sicurezza
1.  Inizializzare il bare repo: `git init --bare $HOME/.cfg`
2.  Impostare l'alias temporaneo per la sessione.
3.  Configurare `status.showUntrackedFiles no`.
4.  **Creazione .gitignore (Safety Net):**
    *   Creare il file `.gitignore`.
    *   Inserire immediatamente le directory sensibili/pesanti:
        *   `.ssh/` (Chiavi private)
        *   `.gnupg/` (Chiavi GPG)
        *   `.claude-mem/` (Memoria AI)
        *   `.gemini/` (Cache e log Gemini)
        *   `projects/` (Codice sorgente)
        *   `Downloads/`, `Documents/`, `Pictures/`, `Videos/`
        *   `.cache/`
        *   `.local/` (A meno di sottocartelle specifiche)

### Fase 2: Selezione Cartella per Cartella
Procederemo chiedendo all'utente conferma per ogni gruppo di file.

**Gruppo A: Shell & Terminal**
- `.bashrc` / `.zshrc`
- `.profile` / `.bash_profile`
- `.aliases` (se esiste)

**Gruppo B: Git & Tools**
- `.gitconfig`
- `.vimrc` / `.nano`
- `.tmux.conf`

**Gruppo C: Configurazioni in .config/**
*Nota: Non aggiungere intera .config, ma solo sottocartelle specifiche.*
- `.config/nvim/`
- `.config/htop/`
- Altro (da esplorare con `ls -d ~/.config/*/`)

### Fase 3: Persistenza e Remote
1.  Aggiungere l'alias in modo permanente nel file rc della shell (`.bashrc` o `.zshrc`).
2.  Collegare a un remote repository (GitHub/GitLab) privato.

---

**Istruzioni per l'AI:**
Quando l'utente chiede di riprendere, leggi questo file, verifica se la cartella `.cfg` esiste già, e guida l'utente a partire dalla "Fase 1". Non eseguire comandi di massa. Chiedi conferma prima di ogni `add`.
