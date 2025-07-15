# Wumpus World AI Agent 🧠🏹

A Python-based intelligent agent for navigating a dangerous 10x10 Wumpus World, built with symbolic reasoning (Z3), tactical exploration, and visual replay. Inspired by classic AI techniques (logical inference, knowledge-based systems, and planning).

## 📂 Project Structure

├── agent.py # Main Agent logic (percepts, planning, logging)
├── kb.py # KnowledgeBase using symbolic Z3 logic
├── const.py # Enum definitions for World objects, actions, etc.
├── test.py # Simulation runner with optional Pygame rendering
├── visualize.py # Tkinter-based visualizer from generated logs
├── testcaseX.txt # Sample test boards
├── agent_log.jsonl # Step-by-step agent logs for visualization
└── README.md # You're reading it!


## 🌍 World Format (`input/test1.txt`)

Each world is described in a simple grid format. The first line is always the board size (`10` for 10×10). Each cell is separated by `.` and may contain multiple symbols:

| Symbol  | Meaning            |
|---------|--------------------|
| `A`     | Agent start        |
| `G`     | Gold               |
| `W`     | Wumpus             |
| `P`     | Pit (deadly)       |
| `H_P`   | Healing Potion     |
| `P_G`   | Poison Gas         |
| `-`     | Empty cell         |

---

## 🧠 Agent Features

- ✅ **Heuristic Scoring + Logic Reasoning**
- ✅ Avoids dangerous locations with incomplete knowledge
- ✅ Infers from **breeze**, **stench**, and **gas smell**
- ✅ Collects **GOLD** and **POTIONS**
- ✅ Uses **arrows to shoot** Wumpus if necessary
- ✅ Uses **potion** to heal when HP is low
- ✅ Logs **every decision**, perception, and action

---

## 📊 Visualization Features (`visualize.py`)

A fully interactive Tkinter GUI to inspect each step in the simulation.

| Feature                        | Description |
|-------------------------------|-------------|
| 🔁 Play / pause               | Replay full session step-by-step
| 🗺️ Mini world map             | World overview with object positions
| 🔍 Zoom & pan                | Inspect large boards or areas
| 🖱️ Scrollable sidebar        | All agent status, legend, controls
| 🧭 Directional symbols        | Shows which way agent is facing
| ⚠️ Alerts and event log      | Shows important events like gold collected, gas damage, death
| 🖼 Export as image or .gif     | For reporting or demo

---

## ✅ How to Run

### 1. Install Requirements

```bash
pip install pillow

