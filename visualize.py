import tkinter as tk
from tkinter import ttk, messagebox
import json
import time
from PIL import Image, ImageTk, ImageDraw
import os
from itertools import cycle
import io

BOARD_SIZE = 10
CELL_SIZE = 75
AUTO_STEP_DELAY = 1000  # ms between auto steps
MINI_CELL_SIZE = 20  # Size for mini world cells

# Directional arrows and entity symbols
SYMBOLS = {
    "UP": "↑",
    "DOWN": "↓",
    "LEFT": "←",
    "RIGHT": "→",
    "WUMPUS": "W",
    "PIT": "P",
    "GOLD": "★",
    "BREEZE": "~",
    "STENCH": "S",
    "POTION": "P",
    "GAS": "G",
}

COLORS = {
    "visited": "#d0f0d0",
    "current": "#a0d0ff",
    "inpath": "#fceabb",
    "best": "#ffcc99",

    "wumpus": "#ff6666",
    "pit": "#333333",
    "gold": "#ffcc00",
    "breeze": "#e6f9ff",
    "stench": "#ffeb99",
    "potion": "#ff99cc",
    "gas": "#99ff99",
    "empty": "#f0f0f0",
}

class AgentVisualizer:
    def __init__(self, root, log_file, txt_file):
        self.root = root
        self.root.title("Wumpus Agent Visualizer Pro")
        
        
        # Load JSONL steps
        try:
            with open(log_file, 'r') as f:
                self.steps = [json.loads(line) for line in f]
                print("First step:", self.steps[0] if self.steps else "No steps found")
        except Exception as e:
            messagebox.showerror("Error", f"Failed to load log file: {str(e)}")
            self.root.destroy()
            return

        self.current_step = 0
        self.auto_playing = False
        self.auto_play_id = None
        self.zoom_level = 1.0
        self.pan_start = None
        self.world_state = self.load_world(txt_file)  # Adjust path as needed

        self.alert_frames = []  # Track active alerts
        
        # Set up main UI
        self.create_widgets()
        self.create_legend()
        
        self.draw_grid()
        self.draw_mini_world()
        self.draw_step()
        
        # Bind keyboard shortcuts
        self.root.bind("<Right>", lambda e: self.next_step())
        self.root.bind("<Left>", lambda e: self.prev_step())
        self.root.bind("<space>", lambda e: self.toggle_play_pause())
        self.root.bind("<Escape>", lambda e: self.stop_auto_play())
        # self.canvas.bind("<MouseWheel>", self.zoom)    # Bug now, update later
        self.canvas.bind("<ButtonPress-1>", self.start_pan)
        self.canvas.bind("<B1-Motion>", self.pan)
        
    def create_widgets(self):
        # Main frame
        self.main_frame = ttk.Frame(self.root)
        self.main_frame.pack(fill=tk.BOTH, expand=True)
        
        # Left panel - main canvas
        self.left_frame = ttk.Frame(self.main_frame)
        self.left_frame.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        
        # Main canvas with scrollbars
        self.canvas_frame = ttk.Frame(self.left_frame)
        self.canvas_frame.pack(fill=tk.BOTH, expand=True)
        
        self.hscroll = ttk.Scrollbar(self.canvas_frame, orient=tk.HORIZONTAL)
        self.vscroll = ttk.Scrollbar(self.canvas_frame, orient=tk.VERTICAL)
        
        self.canvas = tk.Canvas(
            self.canvas_frame,
            width=800,
            height=600,
            xscrollcommand=self.hscroll.set,
            yscrollcommand=self.vscroll.set,
            scrollregion=(0, 0, BOARD_SIZE*CELL_SIZE, BOARD_SIZE*CELL_SIZE)
        )
        
        self.hscroll.pack(side=tk.BOTTOM, fill=tk.X)
        self.vscroll.pack(side=tk.RIGHT, fill=tk.Y)
        self.canvas.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        
        self.hscroll.config(command=self.canvas.xview)
        self.vscroll.config(command=self.canvas.yview)
        
        # Right panel - controls and mini world
        self.right_frame = ttk.Frame(self.main_frame, width=400)
        self.right_frame.pack(side=tk.RIGHT, fill=tk.BOTH, padx=5, pady=5)

        # Create scrollable container for right panel
        self.right_canvas = tk.Canvas(self.right_frame, highlightthickness=0)
        self.right_scroll = ttk.Scrollbar(self.right_frame, orient=tk.VERTICAL, command=self.right_canvas.yview)
        self.right_canvas.configure(yscrollcommand=self.right_scroll.set)
        
        # Pack scrollbar and canvas
        self.right_scroll.pack(side=tk.RIGHT, fill=tk.Y)
        self.right_canvas.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        
        # Create frame inside canvas for right panel content
        self.right_content = ttk.Frame(self.right_canvas)
        self.right_canvas.create_window((0, 0), window=self.right_content, anchor="nw", width=380)  # Set width
        
        # Bind canvas configure event
        self.right_content.bind("<Configure>", lambda e: self.right_canvas.configure(
            scrollregion=self.right_canvas.bbox("all")))
        
        # Mini world at top
        self.mini_world_frame = ttk.LabelFrame(self.right_content, text="World Overview", padding=5)
        self.mini_world_frame.pack(fill=tk.X, pady=5)
        
        self.mini_world_canvas = tk.Canvas(
            self.mini_world_frame,
            width=BOARD_SIZE*MINI_CELL_SIZE,
            height=BOARD_SIZE*MINI_CELL_SIZE,
            bg="white"
        )
        self.mini_world_canvas.pack()
        
        # Control panel below mini world
        self.control_frame = ttk.Frame(self.right_content)
        self.control_frame.pack(fill=tk.BOTH, expand=True)
        
        # Step controls
        self.step_controls_frame = ttk.LabelFrame(self.control_frame, text="Step Controls", padding=5)
        self.step_controls_frame.pack(fill=tk.X, pady=5)
        
        btn_frame = ttk.Frame(self.step_controls_frame)
        btn_frame.pack(pady=5)
        
        self.prev_btn = ttk.Button(btn_frame, text="◀ Prev", command=self.prev_step)
        self.prev_btn.pack(side=tk.LEFT, padx=2)
        
        self.play_btn = ttk.Button(btn_frame, text="▶ Play", command=self.toggle_play_pause)
        self.play_btn.pack(side=tk.LEFT, padx=2)
        
        self.next_btn = ttk.Button(btn_frame, text="Next ▶", command=self.next_step)
        self.next_btn.pack(side=tk.LEFT, padx=2)
        
        # Speed control
        ttk.Label(self.step_controls_frame, text="Speed:").pack(anchor=tk.W)
        self.speed_slider = ttk.Scale(
            self.step_controls_frame, 
            from_=100, to=2000, 
            value=AUTO_STEP_DELAY,
            command=lambda v: setattr(self, 'auto_step_delay', int(float(v)))
        )
        self.speed_slider.pack(fill=tk.X)
        
        # Step slider
        ttk.Label(self.step_controls_frame, text="Go to Step:").pack(anchor=tk.W)
        self.step_slider = ttk.Scale(
            self.step_controls_frame,
            from_=1, to=len(self.steps),
            command=self.on_slider_change
        )
        self.step_slider.pack(fill=tk.X)
        
        # Info panel
        self.info_frame = ttk.LabelFrame(self.control_frame, text="Agent Status", padding=5)
        self.info_frame.pack(fill=tk.X, pady=5)
        
        self.info_label = ttk.Label(
            self.info_frame, 
            text="", 
            wraplength=280,
            justify=tk.LEFT
        )
        self.info_label.pack(fill=tk.X, padx=5, pady=5)
        
        # Export buttons
        export_frame = ttk.Frame(self.control_frame)
        export_frame.pack(fill=tk.X, pady=5)
        
        ttk.Button(export_frame, text="Save Image", command=self.export_image).pack(side=tk.LEFT, fill=tk.X, expand=True, padx=2)
        ttk.Button(export_frame, text="Export GIF", command=self.export_gif).pack(side=tk.LEFT, fill=tk.X, expand=True, padx=2)
        
        # Add mousewheel scrolling for the right panel
        self.right_canvas.bind("<Enter>", lambda e: self.right_canvas.focus_set())
        self.right_canvas.bind_all("<MouseWheel>", lambda e: self.right_canvas.yview_scroll(int(-1*(e.delta/120)), "units"))
    
    def create_legend(self):
        legend_frame = ttk.LabelFrame(self.control_frame, text="Legend")
        legend_frame.pack(fill=tk.X, pady=5)
        
        # Create legend items
        legend_items = [
            ("Visited", COLORS["visited"]),
            ("Current", COLORS["current"]),
            ("Best", COLORS["best"]),
            ("Wumpus", COLORS["wumpus"], SYMBOLS["WUMPUS"]),
            ("Pit", COLORS["pit"], SYMBOLS["PIT"]),
            ("Gold", COLORS["gold"], SYMBOLS["GOLD"]),
            ("Breeze", COLORS["breeze"], SYMBOLS["BREEZE"]),
            ("Stench", COLORS["stench"], SYMBOLS["STENCH"]),
            ("Potion", COLORS["potion"], SYMBOLS["POTION"]),
            ("Gas", COLORS["gas"], SYMBOLS["GAS"]),
        ]
        
        for item in legend_items:
            frame = ttk.Frame(legend_frame)
            frame.pack(fill=tk.X, pady=1)
            
            color = item[1]
            if len(item) > 2:
                text = item[2]
            else:
                text = ""
                
            # Create color swatch
            swatch = tk.Canvas(frame, width=20, height=20, highlightthickness=0)
            swatch.create_rectangle(0, 0, 20, 20, fill=color, outline="black")
            if text:
                swatch.create_text(10, 10, text=text, font=("Arial", 10))
            swatch.pack(side=tk.LEFT, padx=2)
            
            # Create label
            ttk.Label(frame, text=item[0]).pack(side=tk.LEFT)
    
    def draw_grid(self):
        self.canvas.delete("grid")
        for i in range(BOARD_SIZE):
            for j in range(BOARD_SIZE):
                x0, y0 = j * CELL_SIZE, i * CELL_SIZE
                x1, y1 = x0 + CELL_SIZE, y0 + CELL_SIZE
                self.canvas.create_rectangle(x0, y0, x1, y1, outline="black", tags="grid")
    
    def load_world(self, file_path):
        try:
            with open(file_path, 'r') as f:
                lines = [line.strip() for line in f.readlines() if line.strip()]
                
                # First line is the board size
                board_size = int(lines[0])
                
                # Initialize empty world
                world = {
                    "wumpus": [],
                    "pit": [],
                    "gold": [],
                    "gas": [],
                    "potion": [],
                    "walls": set(),
                    "agent": [],
                }
                
                # Parse each row
                for row in range(board_size):
                    if row + 1 >= len(lines):
                        break
                        
                    cells = lines[row + 1].split('.')
                    for col in range(min(len(cells), board_size)):
                        cell = cells[col]
                        
                        if 'W' in cell:
                            world["wumpus"].append([row, col])
                        if 'P' in cell and 'G' not in cell and 'H' not in cell:
                            world["pit"].append([row, col])
                        if 'G' in cell and 'H' not in cell and 'P' not in cell:
                            world["gold"].append([row, col])
                        if 'A' in cell:
                            world["agent"] = [row, col]
                        if 'H_P' in cell:
                            world["potion"].append([row, col])
                        if 'P_G' in cell:
                            world["gas"].append([row, col])

                    for i in range(BOARD_SIZE):
                        world["walls"].add((i, -1))
                        world["walls"].add((i, BOARD_SIZE))
                        world["walls"].add((-1, i))
                        world["walls"].add((BOARD_SIZE, i))

                return world
                
        except Exception as e:
            messagebox.showerror("Error", f"Failed to load world file: {str(e)}")
            return None

    def draw_mini_world(self):
        """Draw the complete world state in the mini view"""
        self.mini_world_canvas.delete("grid", "entity")
                
        # Draw grid
        for i in range(BOARD_SIZE):
            for j in range(BOARD_SIZE):
                x0, y0 = j * MINI_CELL_SIZE, i * MINI_CELL_SIZE
                x1, y1 = x0 + MINI_CELL_SIZE, y0 + MINI_CELL_SIZE
                self.mini_world_canvas.create_rectangle(
                    x0, y0, x1, y1,
                    outline="#cccccc", fill=COLORS["empty"], tags="grid"
                )
        
        # Draw entities
        for (x, y) in self.world_state["wumpus"]:
            if 0 <= x < BOARD_SIZE and 0 <= y < BOARD_SIZE:
                self.draw_mini_entity(x, y, COLORS["wumpus"], SYMBOLS["WUMPUS"])
        
        for (x, y) in self.world_state["pit"]:
            if 0 <= x < BOARD_SIZE and 0 <= y < BOARD_SIZE:
                self.draw_mini_entity(x, y, COLORS["pit"], SYMBOLS["PIT"])
        
        for (x, y) in self.world_state["gold"]:
            if 0 <= x < BOARD_SIZE and 0 <= y < BOARD_SIZE:
                self.draw_mini_entity(x, y, COLORS["gold"], SYMBOLS["GOLD"])

        for (x, y) in self.world_state["gas"]:
            if 0 <= x < BOARD_SIZE and 0 <= y < BOARD_SIZE:
                self.draw_mini_entity(x, y, COLORS["gas"], SYMBOLS["GAS"])
                
        for (x, y) in self.world_state["potion"]:
            if 0 <= x < BOARD_SIZE and 0 <= y < BOARD_SIZE:
                self.draw_mini_entity(x, y, COLORS["potion"], SYMBOLS["POTION"])

        # Draw agent (Default direction is UP)
        if self.world_state["agent"]:
            agent_x, agent_y = self.world_state["agent"]
            if 0 <= agent_x < BOARD_SIZE and 0 <= agent_y < BOARD_SIZE:
                self.draw_mini_entity(agent_x, agent_y, COLORS["current"], SYMBOLS["UP"])
    
    def draw_mini_entity(self, x, y, color, symbol):
        """Draw an entity in the mini world view"""
        x0, y0 = y * MINI_CELL_SIZE, x * MINI_CELL_SIZE
        x1, y1 = x0 + MINI_CELL_SIZE, y0 + MINI_CELL_SIZE
        self.mini_world_canvas.create_rectangle(
            x0, y0, x1, y1,
            fill=color, outline="black", tags="entity"
        )
        self.mini_world_canvas.create_text(
            x0 + MINI_CELL_SIZE//2, y0 + MINI_CELL_SIZE//2,
            text=symbol, font=("Arial", 8), tags="entity"
        )


    def draw_step(self):
        self.canvas.delete("cell")
        self.canvas.delete("entity")
        self.canvas.delete("agent")

        if self.current_step >= len(self.steps):
            self.info_label.config(text="🎉 Simulation complete.")
            return

        step = self.steps[self.current_step]
        visited = step.get("visited", [])
        loc = tuple(step.get("location", (-1, -1)))
        direction = step.get("direction", "UP")
        hp = step.get("hp", 0)
        potions = step.get("potions", 0)
        score = step.get("score", 0)
        arrows = step.get("arrows", 0)
        events = step.get("events", [])
        actions = step.get("actions", [])
        best = step.get("best", [-1, -1])
        path = step.get("path", [])

        # Log the current step
        print(f"Drawing step {self.current_step + 1} with location {loc} and direction {direction}")
        print(f"Visited cells: {visited}")
        print(f"Best cell: {best}")
        print(f"Agent info: HP={hp}, Potions={potions}, Score={score}, Arrows={arrows}")

        # Draw visited cells 
        for (x, y) in visited:
            x0, y0 = y * CELL_SIZE, x * CELL_SIZE
            self.canvas.create_rectangle(
                x0, y0, x0 + CELL_SIZE, y0 + CELL_SIZE, 
                fill=COLORS["visited"], tags="cell"
            )

        # Highlight best cell
        if best:
            x0, y0 = best[1] * CELL_SIZE, best[0] * CELL_SIZE
            self.canvas.create_rectangle(
                x0, y0, x0 + CELL_SIZE, y0 + CELL_SIZE, 
                fill=COLORS["best"], tags="cell"
            )

        # Draw path
        if path:
            for (x, y) in path:
                x0, y0 = y * CELL_SIZE, x * CELL_SIZE 
                self.canvas.create_rectangle(
                    x0, y0, x0 + CELL_SIZE, y0 + CELL_SIZE,
                    fill=COLORS["inpath"], outline="black", tags="cell"
                )
        
        # Draw entities
        possible_entities = {
            "wumpus": (COLORS["wumpus"], SYMBOLS["WUMPUS"]),
            "pit": (COLORS["pit"], SYMBOLS["PIT"]),
            "gas": (COLORS["gas"], SYMBOLS["GAS"]),
            "potion": (COLORS["potion"], SYMBOLS["POTION"]),
        }

        possible_wumpus = []
        possible_pit = []
        possible_gas = []
        possible_potion = []

        for cell, rank in step.get("ranked", []):
            if rank < -900:
                possible_pit.append(cell)
            elif rank < -400:
                possible_wumpus.append(cell)
            elif rank < 200:
                possible_gas.append(cell)
            elif rank > 1000:
                possible_potion.append(cell)

        for (x, y) in possible_wumpus:
            x0, y0 = y * CELL_SIZE, x * CELL_SIZE
            self.canvas.create_rectangle(
                x0, y0, x0 + CELL_SIZE, y0 + CELL_SIZE,
                fill=COLORS["wumpus"], outline="black", tags="entity"
            )
            self.canvas.create_text(
                x0 + CELL_SIZE//2, y0 + CELL_SIZE//2,
                text=SYMBOLS["WUMPUS"], font=("Arial", 16, "bold"), tags="entity", fill="white"
            )

        for (x, y) in possible_pit:
            x0, y0 = y * CELL_SIZE, x * CELL_SIZE
            self.canvas.create_rectangle(
                x0, y0, x0 + CELL_SIZE, y0 + CELL_SIZE,
                fill=COLORS["pit"], outline="black", tags="entity"
            )
            self.canvas.create_text(
                x0 + CELL_SIZE//2, y0 + CELL_SIZE//2,
                text=SYMBOLS["PIT"], font=("Arial", 16, "bold"), tags="entity", fill="white"
            )
        for (x, y) in possible_gas:
            x0, y0 = y * CELL_SIZE, x * CELL_SIZE
            self.canvas.create_rectangle(
                x0, y0, x0 + CELL_SIZE, y0 + CELL_SIZE,
                fill=COLORS["gas"], outline="black", tags="entity"
            )
            self.canvas.create_text(
                x0 + CELL_SIZE//2, y0 + CELL_SIZE//2,
                text=SYMBOLS["GAS"], font=("Arial", 16, "bold"), tags="entity", fill="white"
            )
        for (x, y) in possible_potion:
            x0, y0 = y * CELL_SIZE, x * CELL_SIZE
            self.canvas.create_rectangle(
                x0, y0, x0 + CELL_SIZE, y0 + CELL_SIZE,
                fill=COLORS["potion"], outline="black", tags="entity"
            )
            self.canvas.create_text(
                x0 + CELL_SIZE//2, y0 + CELL_SIZE//2,
                text=SYMBOLS["POTION"], font=("Arial", 16, "bold"), tags="entity", fill="white"
            )

        # Draw agent
        if loc != (-1, -1):
            x0, y0 = loc[1] * CELL_SIZE, loc[0] * CELL_SIZE
            self.canvas.create_rectangle(
                x0, y0, x0 + CELL_SIZE, y0 + CELL_SIZE, 
                fill=COLORS["current"], tags="agent"
            )
            self.canvas.create_text(
                x0 + CELL_SIZE//2, y0 + CELL_SIZE//2,
                text=SYMBOLS.get(direction, "?"), 
                font=("Arial", 24, "bold"), tags="agent", fill="blue"
            )

        # Display agent status
        info = f"Step {self.current_step + 1}/{len(self.steps)}\n"
        info += f"Location: {loc}\n"
        info += f"Direction: {direction.split('.')[-1]}\n"
        info += f"HP: {hp} | Potions: {potions}\n"
        info += f"Arrows: {arrows} | Score: {score}\n"
        if best:
            info += f"Best Cell: {best}\n"
        if path:
            info += f"Path: {', '.join(map(str, path))}\n"
        if events:
            info += f"Events: {', '.join(events)}\n"
        if actions:
            info += f"Actions: {', '.join(actions)}\n"

        self.info_label.config(text=info)
        self.step_slider.set(self.current_step + 1)
        
        # Update scroll region after zoom
        self.canvas.configure(scrollregion=self.canvas.bbox("all"))
        if hasattr(self, 'alert_frame'):
            self.alert_frame.destroy()

        # Enhanced event alerts
        if events:
            # Create alert frame at the top of right panel
            self.alert_frame = ttk.Frame(self.right_frame)
            self.alert_frame.pack(fill=tk.X, pady=5, before=self.mini_world_frame)  # Position above mini map

            # Process events and determine alert level
            alert_level = "info"
            alert_messages = []
            
            for event in events:
                if "DIED" in event or "DEAD" in event:
                    alert_level = "fatal"
                    alert_messages.append(f"💀 FATAL: {event}")
                elif "WIN" in event or "GOLD" in event:
                    alert_level = "success" 
                    alert_messages.append(f"🎉 GOLD COLLECTED: {event}")
                elif "DAMAGED" in event:
                    alert_level = "danger"
                    alert_messages.append(f"⚠️ DANGER: {event}")
                else:
                    alert_messages.append(f"ℹ️ {event}")

            # Configure alert style based on severity
            alert_style = {
                "fatal": {"bg": "#ffdddd", "fg": "red", "font": ("Arial", 10, "bold")},
                "danger": {"bg": "#fff3cd", "fg": "#856404", "font": ("Arial", 10, "bold")},
                "success": {"bg": "#d4edda", "fg": "#155724", "font": ("Arial", 10, "bold")},
                "info": {"bg": "#d1ecf1", "fg": "#0c5460", "font": ("Arial", 10)}
            }[alert_level]

            # Create alert label
            alert_label = tk.Label(
                self.alert_frame,
                text="\n".join(alert_messages),
                wraplength=280,
                justify=tk.LEFT,
                **alert_style,
                padx=10,
                pady=10,
                relief=tk.RAISED,
                borderwidth=2
            )
            alert_label.pack(fill=tk.X, expand=True)

            # Add dismiss button for serious alerts
            if alert_level in ("fatal", "danger", "success"):
                dismiss_btn = tk.Button(
                    self.alert_frame,
                    text="✕",
                    command=self.alert_frame.destroy,
                    bg=alert_style["bg"],
                    fg=alert_style["fg"],
                    font=("Arial", 8, "bold"),
                    borderwidth=1,
                    relief=tk.FLAT
                )
                dismiss_btn.place(relx=1.0, x=-2, y=2, anchor=tk.NE)

            # Visual effects for serious alerts
            if alert_level == "fatal":
                self.flash_alert(self.alert_frame, "#ffdddd", "#ffaaaa")
                self.root.bell()  # System beep
            elif alert_level == "danger":
                self.flash_alert(self.alert_frame, "#fff3cd", "#ffeeba")

    def flash_alert(self, frame, color1, color2):
        """Flash the alert between two colors"""
        def flash(count=0):
            if count < 6:  # Flash 3 times (6 color changes)
                color = color2 if count % 2 else color1
                frame.config(bg=color)
                for child in frame.winfo_children():
                    if isinstance(child, tk.Label):
                        child.config(bg=color)
                self.root.after(200, flash, count+1)
        flash()

    def next_step(self):
        if self.current_step < len(self.steps) - 1:
            self.current_step += 1
            self.draw_step()

    def prev_step(self):
        if self.current_step > 0:
            self.current_step -= 1
            self.draw_step()

    def toggle_play_pause(self):
        if self.auto_playing:
            self.stop_auto_play()
        else:
            self.start_auto_play()

    def start_auto_play(self):
        self.auto_playing = True
        self.play_btn.config(text="⏸ Pause")
        self.auto_play()

    def stop_auto_play(self):
        self.auto_playing = False
        if self.auto_play_id:
            self.root.after_cancel(self.auto_play_id)
            self.auto_play_id = None
        self.play_btn.config(text="▶ Play")

    def auto_play(self):
        if self.auto_playing and self.current_step < len(self.steps) - 1:
            self.next_step()
            self.auto_play_id = self.root.after(self.auto_step_delay, self.auto_play)
        else:
            self.stop_auto_play()

    def on_slider_change(self, value):
        step = int(float(value)) - 1
        if 0 <= step < len(self.steps) and step != self.current_step:
            self.current_step = step
            self.draw_step()

    # def zoom(self, event):
    #     # Determine zoom factor
    #     factor = 1.1 if event.delta > 0 else 0.9

    #     # Get mouse position on canvas
    #     canvas_x = self.canvas.canvasx(event.x)
    #     canvas_y = self.canvas.canvasy(event.y)

    #     # Apply scaling
    #     self.canvas.scale("all", canvas_x, canvas_y, factor, factor)
    #     self.zoom_level *= factor

    #     # Update scrollregion
    #     self.canvas.configure(scrollregion=self.canvas.bbox("all"))

    #     # Optional: adjust view to keep mouse in the same position after zoom
    #     # Get new canvas coordinates
    #     new_canvas_x = self.canvas.canvasx(event.x)
    #     new_canvas_y = self.canvas.canvasy(event.y)

    #     # Calculate scroll offset
    #     dx = new_canvas_x - canvas_x
    #     dy = new_canvas_y - canvas_y

    #     self.canvas.xview_scroll(int(dx), "units")
    #     self.canvas.yview_scroll(int(dy), "units")
    

    def start_pan(self, event):
        self.pan_start = (event.x, event.y)

    def pan(self, event):
        if self.pan_start:
            dx = event.x - self.pan_start[0]
            dy = event.y - self.pan_start[1]
            self.canvas.xview_scroll(-dx, "units")
            self.canvas.yview_scroll(-dy, "units")
            self.pan_start = (event.x, event.y)

    def export_image(self):
        from datetime import datetime
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = f"wumpus_visualization_{timestamp}.png"
        
        # Create a PostScript file and convert to PNG
        try:
            self.canvas.postscript(file="temp.ps", colormode='color')
            img = Image.open("temp.ps")
            img.save(filename, "PNG")
            os.remove("temp.ps")
            messagebox.showinfo("Success", f"Image saved as {filename}")
        except Exception as e:
            messagebox.showerror("Error", f"Failed to save image: {str(e)}")

    def export_gif(self):
        from datetime import datetime
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = f"wumpus_animation_{timestamp}.gif"
        
        try:
            images = []
            current_step = self.current_step
            
            # Save each step as an image
            for i in range(len(self.steps)):
                self.current_step = i
                self.draw_step()
                self.canvas.update()
                
                # Capture canvas as image
                ps = self.canvas.postscript(colormode='color')
                img = Image.open(io.BytesIO(ps.encode('utf-8')))
                images.append(img)
            
            # Save as animated GIF
            images[0].save(
                filename,
                save_all=True,
                append_images=images[1:],
                optimize=False,
                duration=self.auto_step_delay,
                loop=0
            )
            
            self.current_step = current_step
            self.draw_step()
            messagebox.showinfo("Success", f"Animation saved as {filename}")
        except Exception as e:
            messagebox.showerror("Error", f"Failed to create animation: {str(e)}")

if __name__ == "__main__":
    root = tk.Tk()
    root.geometry("1200x800")
    
    # Ask for log file
    from tkinter import filedialog
    log_file = filedialog.askopenfilename(
        title="Select Agent Log File",
        filetypes=[("JSONL files", "*.jsonl"), ("All files", "*.*")]
    )

    file_name = os.path.basename(log_file)
    print(f"Selected log file: {file_name}")
    txt_file = "input/" + os.path.splitext(file_name)[0] + ".txt"

    
    if log_file:
        app = AgentVisualizer(root, log_file, txt_file)
        root.mainloop()