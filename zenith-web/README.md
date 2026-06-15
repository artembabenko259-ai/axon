# AXON Web Control Panel

Premium dark-mode control panel for the AXON AI CLI.

## Stack

- **Next.js 16** (App Router)
- **Tailwind CSS v4**
- **Framer Motion**
- **Lucide React**

## Getting Started

```bash
cd zenith-web
npm install
npm run dev
```

Open [http://localhost:3000](http://localhost:3000)

## WebSocket Sync

Start the Python CLI to enable terminal ↔ web chat sync:

```bash
# Terminal 1 — CLI (starts WS bridge on ws://127.0.0.1:8765)
python main.py

# Terminal 2 — Web dashboard
cd zenith-web && npm run dev
```

Messages typed in `/chat` or the terminal appear in both places in real time.

## Pages

| Route | Description |
|-------|-------------|
| `/` | Landing page — central orb, hero |
| `/chat` | Real-time chat synced with terminal via WebSocket |
| `/dashboard` | Agent orb, model marketplace, model selection, live logs |
| `/marketplace` | Full-width model marketplace table |
| `/config` | API keys and local path settings |

## Design System

- Deep space gradients (`space-bg`)
- Glassmorphism cards (`.glass`, `.glass-strong`)
- Neon cyan / purple accents
- Outfit (display) + DM Sans (body) typography

Swap themes by editing CSS variables in `app/globals.css`.

## Project Structure

```
zenith-web/
├── app/
│   ├── page.tsx           # Landing
│   ├── chat/page.tsx
│   ├── dashboard/page.tsx
│   └── config/page.tsx
├── components/
│   ├── layout/            # Sidebar, TopNav, AppShell
│   ├── dashboard/         # Status, models, logs
│   ├── landing/           # Hero section
│   └── ui/                # GlassCard, AgentOrb
└── lib/utils.ts
```
