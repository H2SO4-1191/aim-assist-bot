import tkinter as tk
from tkinter import ttk


def launch_ui(state):
    root = tk.Tk()
    root.title("Aim Assist Control")
    root.geometry("500x350")
    root.attributes("-topmost", True)  # stays above the game window

    def on_close():
        state.stop()
        root.destroy()
    root.protocol("WM_DELETE_WINDOW", on_close)

    # --- Enabled toggle ---
    enabled_var = tk.BooleanVar(value=state.enabled)
    def on_enabled_toggle():
        state.set_enabled(enabled_var.get())
    ttk.Checkbutton(root, text="Aim Assist Enabled", variable=enabled_var,
                    command=on_enabled_toggle).pack(pady=(15, 5), padx=15, anchor="w")

    # --- ADS-only toggle ---
    ads_var = tk.BooleanVar(value=state.ads_only)
    def on_ads_toggle():
        state.set_ads_only(ads_var.get())
    ttk.Checkbutton(root, text="Only assist while ADS (right-click held)",
                    variable=ads_var, command=on_ads_toggle).pack(pady=5, padx=15, anchor="w")

    # --- Strength slider ---
    ttk.Label(root, text="Assist Strength").pack(pady=(15, 0), padx=15, anchor="w")
    strength_var = tk.DoubleVar(value=state.strength)
    strength_label = ttk.Label(root, text=f"{state.strength:.2f}")

    def on_strength_change(val):
        strength_var.set(float(val))
        state.set_strength(float(val))
        strength_label.config(text=f"{float(val):.2f}")

    ttk.Scale(root, from_=0.05, to=0.35, orient="horizontal",
              variable=strength_var, command=on_strength_change).pack(fill="x", padx=15)
    strength_label.pack(padx=15, anchor="e")

    # --- Global hotkey hint (all wired in main_app.py) ---
    ttk.Label(root, text="F1 enable | F2 ADS-only | F3/F4 strength | F5 debug window",
              font=("Segoe UI", 8), foreground="gray", wraplength=250).pack(pady=(15, 0))

    def sync_from_state():
        """Keep the UI in sync if hotkeys (F1-F4) change state externally."""
        enabled_var.set(state.enabled)
        ads_var.set(state.ads_only)
        if abs(strength_var.get() - state.strength) > 0.001:
            strength_var.set(state.strength)
            strength_label.config(text=f"{state.strength:.2f}")
        if not state.running:
            root.destroy()
            return
        root.after(200, sync_from_state)

    root.after(200, sync_from_state)
    root.mainloop()
